import sys
import time
from imaginairy.api.generate import imagine, imagine_image_files
from imaginairy.schema import ImaginePrompt, ControlInput, LazyLoadingImage, MaskMode
from PIL import Image


import random
import threading


class Painter:
    def __init__(self, prompts, warmup=True):
        self.prompts = prompts
        if warmup:            
            self.generate("logo.png", "AI Tinkerers")

    def generate(self, filename, forced_prompt=None, callback=None):
        image = Image.open(filename)
        width, height = image.size
        new_size = min(width, height)
        left = (width - new_size) / 2
        top = (height - new_size) / 2
        right = (width + new_size) / 2
        bottom = (height + new_size) / 2
        image = image.crop((left, top, right, bottom))
        image.thumbnail((512, 512))
        control_mode_depth = ControlInput(mode="depth", image=image, strength=0.5)
        #control_mode_openpose = ControlInput(mode="openpose", image=image, strength=0.2)
        #control_mode_canny = ControlInput(mode="canny", image=image, strength=0.2)
        #control_mode_edit = ControlInput(mode="edit", image=image, strength=0.5)

        prompt = (
            {"caption": forced_prompt, "prompt": forced_prompt}
            if forced_prompt
            else random.Random(time.time()).choice(self.prompts)
        )        

        # caption = generate_caption(image)

        # prompt = self.prompts[0]

        print(", ".join([prompt["prompt"], "high quality, no text"]))

        imagine_prompt = ImaginePrompt(
            prompt=", ".join([prompt["prompt"], "high quality, no text"]),
            negative_prompt="deformed hands, too many fingers, weird fingers, wrong fingers, weird hands, malformed, strange, ugly, duplication, duplicates, mutilation, deformed, mutilated, mutation, twisted body, disfigured, bad anatomy, out of frame, extra fingers, mutated hands, poorly drawn hands, extra limbs, malformed limbs, missing arms, extra arms, missing legs, extra legs, mutated hands, extra hands, fused fingers, missing fingers, extra fingers, long neck, small head, closed eyes, rolling eyes, weird eyes, smudged face, blurred face, poorly drawn face, mutation, mutilation, cloned face, strange mouth, grainy, blurred, blurry, writing, calligraphy, signature, text, watermark, bad art",
            control_inputs=[control_mode_depth],
            seed=1,
            #caption_text=prompt["caption"].upper(),
            init_image_strength=0.2,
            mask_prompt="(female face OR male face OR person face OR face OR hair){-2}",
            mask_mode=MaskMode.KEEP,
            init_image=image,
            fix_faces=False,
        )

        def debug_callback(img, description, image_count, step_count, prompt):
            if callback:
                callback()

        result = next(
            imagine(prompts=imagine_prompt, debug_img_callback=debug_callback)
        )

        # imagine_image_files(prompts=imagine_prompt, outdir="final", print_caption=True)

        result.img.save(filename.split(".")[0] + "_generated." + filename.split(".")[1])


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
