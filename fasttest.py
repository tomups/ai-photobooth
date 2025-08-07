import cv2
import torch
from diffusers.utils import load_image
from sam2.sam2_image_predictor import SAM2ImagePredictor
from PIL import Image
import numpy as np
from transformers import pipeline
from ultralytics import YOLO


# Load the original image first
original_image = load_image("capture.jpg")

# Run depth estimation outside of autocast context to avoid BFloat16 issues
depth_estimator = pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Small-hf', device="cuda", use_fast=True)
depth_image = depth_estimator(original_image)['depth']
depth_image = np.array(depth_image)
depth_image = depth_image[:, :, None]
depth_image = np.concatenate([depth_image, depth_image, depth_image], axis=2)
control_image = Image.fromarray(depth_image)
control_image.save("depth.png")

with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):

    segmenter = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-tiny")

    # Load a model
    face_detector = YOLO("https://github.com/akanametov/yolo-face/releases/download/v0.0.0/yolov11n-face.pt")

    from diffusers import (
        ControlNetModel,
        StableDiffusionControlNetPipeline,
        UniPCMultistepScheduler,
    )

    face_boxes = face_detector(original_image)[0].boxes.xyxy    

    # Initialize combined mask
    combined_mask = np.zeros((original_image.height, original_image.width), dtype=np.uint8)
    
    for box in face_boxes:        
        x1, y1, x2, y2 = box.cpu().numpy()
        
        # Expand bounding box by 20%
        width = x2 - x1
        height = y2 - y1
        expand_w = width * 0.2
        expand_h = height * 0.2
        
        # Calculate expanded coordinates (clamped to image bounds)
        x1_expanded = max(0, x1 - expand_w / 2)
        y1_expanded = max(0, y1 - expand_h / 2)
        x2_expanded = min(original_image.width, x2 + expand_w / 2)
        y2_expanded = min(original_image.height, y2 + expand_h / 2)
        
        # Create expanded box tensor
        expanded_box = torch.tensor([x1_expanded, y1_expanded, x2_expanded, y2_expanded])
        
        segmenter.set_image(original_image)
        masks, _, _ = segmenter.predict(box=expanded_box, multimask_output=False)
        
        mask = masks[0].astype(np.uint8) * 255
        
        # Add this face mask to the combined mask (using maximum to avoid overlap issues)
        combined_mask = np.maximum(combined_mask, mask)
        
        # Save individual mask (without blur)
        mask_image = Image.fromarray(mask)
        mask_image.save(f"mask_{int(x1)}_{int(y1)}.png")
    
    # Apply gaussian blur to the final combined mask
    combined_mask_blurred = cv2.GaussianBlur(combined_mask, (31, 31), 0)
    
    # Save the combined mask (both versions)
    combined_mask_image = Image.fromarray(combined_mask)
    combined_mask_image.save("mask_combined_sharp.png")
    
    combined_mask_blurred_image = Image.fromarray(combined_mask_blurred)
    combined_mask_blurred_image.save("mask_combined.png")

   
    checkpoint = "lllyasviel/control_v11f1p_sd15_depth"
    prompt = "meddressed as a medieval knight, surrounded by Gothic architecture and stained glass windowsieval"

    controlnet = ControlNetModel.from_pretrained(checkpoint, torch_dtype=torch.float16)
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5", controlnet=controlnet, torch_dtype=torch.float16,
    )

    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_model_cpu_offload()

    generator = torch.manual_seed(0)
    generated_image = pipe(prompt, num_inference_steps=30, generator=generator, image=control_image).images[0]

    generated_image.save('generated.png')

# Image combination happens outside autocast context
# Convert images to numpy arrays for blending
original_np = np.array(original_image)
generated_np = np.array(generated_image)

# Ensure all images have the same dimensions
original_height, original_width = original_np.shape[:2]
generated_resized = cv2.resize(generated_np, (original_width, original_height))

# Load the combined mask (includes all detected faces)
mask = cv2.imread("mask_combined.png", cv2.IMREAD_GRAYSCALE)

# Ensure mask is 2D and normalize to 0-1 range for blending
if len(mask.shape) > 2:
    mask = mask.squeeze()  # Remove extra dimensions
mask_normalized = mask.astype(np.float32) / 255.0
mask_normalized = mask_normalized[:, :, np.newaxis]  # Add channel dimension for RGB (H, W, 1)

# Blend the images: original * mask + generated * (1 - mask)
# This keeps the original face and applies the generated background
combined_image = (original_np * mask_normalized + 
                 generated_resized * (1 - mask_normalized)).astype(np.uint8)

# Convert back to PIL Image and save
final_image = Image.fromarray(combined_image)
final_image.save('combined_image.png')

print("Combined image saved as 'combined_image.png'")

