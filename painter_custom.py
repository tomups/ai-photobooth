import sys
import time
import cv2
import torch
from diffusers.utils import load_image
from sam2.sam2_image_predictor import SAM2ImagePredictor
from PIL import Image
import numpy as np
from transformers import pipeline
from ultralytics import YOLO
from diffusers import (
    ControlNetModel,
    StableDiffusionControlNetPipeline,
    UniPCMultistepScheduler,
)
import random


class Painter:
    def __init__(self, prompts):
        self.prompts = prompts
        self.pipe = None
        self.depth_estimator = None
        self.segmenter = None
        self.face_detector = None

    def load_analysis_models(self):
        self.depth_estimator = pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Small-hf', device="cuda", use_fast=True) if not self.depth_estimator else self.depth_estimator
        self.segmenter = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-tiny") if not self.segmenter else self.segmenter
        self.face_detector = YOLO("https://github.com/akanametov/yolo-face/releases/download/v0.0.0/yolov11n-face.pt") if not self.face_detector else self.face_detector
            
        
    def load_model(self, warmup=False):
        self.load_analysis_models()
        
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):            
            checkpoint = "lllyasviel/control_v11f1p_sd15_depth"
            controlnet = ControlNetModel.from_pretrained(checkpoint, torch_dtype=torch.float16)
            self.pipe = StableDiffusionControlNetPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5", controlnet=controlnet, torch_dtype=torch.float16,
                safety_checker = None,
                requires_safety_checker = False
            )
            self.pipe.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)
            self.pipe.enable_model_cpu_offload()            
            self.pipe.enable_xformers_memory_efficient_attention()
            self.pipe.enable_freeu(b1=1.5, b2=1.6, s1=0.9, s2=0.2)           
        
        if warmup:            
            self.generate("logo.png", "AI Tinkerers")

    def unload_analysis_models(self):
        self.depth_estimator = None
        self.segmenter = None
        self.face_detector = None
        torch.cuda.empty_cache()        
    
    def unload_model(self):
        self.unload_analysis_models()
        self.pipe = None
        torch.cuda.empty_cache()

    def generate(self, filename, forced_prompt=None, callback=None):
        self.load_analysis_models()
        # Load the original image
        original_image = load_image(filename)

        def callback_wrapper(pipe, step_index, timestep, callback_kwargs):
            if callback:
                callback()
            return callback_kwargs
        
        # Generate depth map
        depth_image = self.depth_estimator(original_image)['depth']
        depth_image = np.array(depth_image)
        depth_image = depth_image[:, :, None]
        depth_image = np.concatenate([depth_image, depth_image, depth_image], axis=2)
        control_image = Image.fromarray(depth_image)
        
        # Get prompt
        prompt_dict = (
            {"caption": forced_prompt, "prompt": forced_prompt}
            if forced_prompt
            else random.Random(time.time()).choice(self.prompts)
        )
        
        prompt = prompt_dict["prompt"] + ", high quality, no text"
        print(prompt)
        
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
            # Detect faces
            face_boxes = self.face_detector(original_image)[0].boxes.xyxy
            
            # Initialize combined mask
            combined_mask = np.zeros((original_image.height, original_image.width), dtype=np.uint8)
            
            # Process each detected face
            for box in face_boxes:
                x1, y1, x2, y2 = box.cpu().numpy()
                
                # Expand bounding box
                width = x2 - x1
                height = y2 - y1
                expand_w = width * 0.2
                expand_h = height * 0.3
                
                # Calculate expanded coordinates (clamped to image bounds)
                x1_expanded = max(0, x1 - expand_w / 2)
                y1_expanded = max(0, y1 - expand_h / 2)
                x2_expanded = min(original_image.width, x2 + expand_w / 2)
                y2_expanded = min(original_image.height, y2 + expand_h / 2)
                
                # Create expanded box tensor
                expanded_box = torch.tensor([x1_expanded, y1_expanded, x2_expanded, y2_expanded])
                
                self.segmenter.set_image(original_image)
                masks, _, _ = self.segmenter.predict(box=expanded_box, multimask_output=False)
                
                mask = masks[0].astype(np.uint8) * 255
                
                # Add this face mask to the combined mask
                combined_mask = np.maximum(combined_mask, mask)
            
            # Apply gaussian blur to the final combined mask
            combined_mask_blurred = cv2.GaussianBlur(combined_mask, (21, 21), 0)
            self.unload_analysis_models()
            
            # Generate image using ControlNet
            generator = torch.manual_seed(1)
            generated_image = self.pipe(prompt, num_inference_steps=10, callback_on_step_end=callback_wrapper, generator=generator, image=control_image).images[0]
        
        # Image combination happens outside autocast context
        # Convert images to numpy arrays for blending
        original_np = np.array(original_image)
        generated_np = np.array(generated_image)
        
        # Ensure all images have the same dimensions
        original_height, original_width = original_np.shape[:2]
        generated_resized = cv2.resize(generated_np, (original_width, original_height))
        
        # Normalize mask to 0-1 range for blending
        mask_normalized = combined_mask_blurred.astype(np.float32) / 255.0
        mask_normalized = mask_normalized[:, :, np.newaxis]  # Add channel dimension for RGB
        
        # Blend the images: original * mask + generated * (1 - mask)
        # This keeps the original face and applies the generated background
        combined_image = (original_np * mask_normalized + 
                         generated_resized * (1 - mask_normalized)).astype(np.uint8)
        
        # Convert back to PIL Image and save
        final_image = Image.fromarray(combined_image)
        output_filename = filename.split(".")[0] + "_generated." + filename.split(".")[1]
        final_image.save(output_filename)

        #self.unload_model()
        
        return final_image


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate.py <filename> <prompt>")
        sys.exit(1)
    
    # Default prompts for standalone usage
    default_prompts = [
        {
            "caption": "Robots",
            "prompt": "androids and robots, futuristic cyberpunk style",
        },
        {
            "caption": "Van Gogh",
            "prompt": "in the style of Van Gogh, surrounded by swirling clouds and stars",
        },
    ]
    
    generator = Painter(prompts=default_prompts, warmup=False)
    generator.generate(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None, None)
