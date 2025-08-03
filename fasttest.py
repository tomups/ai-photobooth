from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()           # Lower memory for attention
pipe.enable_sequential_cpu_offload()      # Further offload to system RAM

# Optionally: pipe.enable_vae_tiling()
prompt = "A fantasy landscape, trending artstation"

result = pipe(prompt, height=512, width=512, num_inference_steps=20)
result.images[0].save("output.png")