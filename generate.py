import os
import sys
from imaginairy.api.generate import imagine, imagine_image_files
from imaginairy.schema import ImaginePrompt, ControlInput, LazyLoadingImage, MaskMode

# from imaginairy.enhancers.describe_image_blip import generate_caption
import random
import threading


class ImageGenerator:
    prompts = [
        {
            "caption": "Robots",
            "prompt": "androids and robots, futuristic cyberpunk style",
        },
        {
            "caption": "Knitted",
            "prompt": "made out of crochet, knitted",
        },
        {
            "caption": "Van Gogh",
            "prompt": "in the style of Van Gogh, surrounded by swirling clouds and stars",
        },
        {
            "caption": "Neon Dreams",
            "prompt": "futuristic astronauts in a neon-lit cityscape, inspired by Syd Mead",
        },
        {
            "caption": "Steampunk",
            "prompt": "Victorian-era, in the style of steampunk",
        },
        {
            "caption": "Wave Rider",
            "prompt": "riding a giant wave, inspired by Hokusai's ukiyo-e woodblock prints",
        },
        {
            "caption": "Cyberpunk",
            "prompt": "cyberpunk-inspired hacker, surrounded by screens and wires, in the style of Blade Runner",
        },
        {
            "caption": "Renaissance Revival",
            "prompt": "dressed as a Renaissance-era noble, surrounded by ornate gold frames and velvet drapes",
        },
        {
            "caption": "Lab Life",
            "prompt": "futuristic, high-tech laboratory, inspired by the art of Syd Mead",
        },
        {
            "caption": "Dali's Dream",
            "prompt": "surreal, dreamlike landscape, inspired by the art of Salvador Dali",
        },
        {
            "caption": "Superhero",
            "prompt": "superhero, in the style of a superman comic book",
        },
        {
            "caption": "Dragon Ball",
            "prompt": "dressed as Dragon Ball Z characters, in the style of Akira Toriyama",
        },
        {
            "caption": "Detective",
            "prompt": "wearing a stylish suit of a detective, film noir-inspired cityscape",
        },
        {
            "caption": "Knight's Tale",
            "prompt": "dressed as a medieval knight, surrounded by Gothic architecture and stained glass windows",
        },
        {
            "caption": "Retro Futurism",
            "prompt": "futuristic, space-age landscape, inspired by the art of retro-futurism",
        },
        {
            "caption": "Greek Gods",
            "prompt": "dressed as a ancient Greek god, surrounded by marble columns and statues",
        },
        {
            "caption": "Pop Art",
            "prompt": "bright, colorful landscape, pop art, inspired by the art of Andy Warhol",
        },
    ]

    already_used_prompts = set()

    def __init__(self, warmup=True):
        if warmup:
            threading.Thread(
                target=self.generate, args=("logo.png", "AI Tinkerers")
            ).start()

    def generate(self, filename, forced_prompt=None, callback=None):
        from PIL import Image

        image = Image.open(filename)
        image = image.resize(
            (int(512 * image.width / image.height), 512), resample=Image.BICUBIC
        )
        width, height = image.size
        left = (width - 512) / 2
        top = (height - 512) / 2
        right = (width + 512) / 2
        bottom = (height + 512) / 2
        image = image.crop((left, top, right, bottom))
        image = LazyLoadingImage(img=image)
        control_mode_depth = ControlInput(mode="depth", image=image, strength=0.5)
        control_mode_openpose = ControlInput(mode="openpose", image=image, strength=0.2)
        control_mode_canny = ControlInput(mode="canny", image=image, strength=0.2)
        control_mode_edit = ControlInput(mode="edit", image=image, strength=0.5)

        prompt = (
            {"caption": forced_prompt, "prompt": forced_prompt}
            if forced_prompt
            else random.choice(self.prompts)
        )

        if len(self.already_used_prompts) == len(self.prompts):
            self.already_used_prompts.clear()

        while prompt["prompt"] in self.already_used_prompts:
            prompt = random.choice(self.prompts)
        self.already_used_prompts.add(prompt["prompt"])

        # caption = generate_caption(image)

        # prompt = self.prompts[0]

        print(", ".join([prompt["prompt"], "high quality, no text"]))

        imagine_prompt = ImaginePrompt(
            prompt=", ".join([prompt["prompt"], "high quality, no text"]),
            negative_prompt="deformed hands, too many fingers, weird fingers, wrong fingers, weird hands, malformed, strange, ugly, duplication, duplicates, mutilation, deformed, mutilated, mutation, twisted body, disfigured, bad anatomy, out of frame, extra fingers, mutated hands, poorly drawn hands, extra limbs, malformed limbs, missing arms, extra arms, missing legs, extra legs, mutated hands, extra hands, fused fingers, missing fingers, extra fingers, long neck, small head, closed eyes, rolling eyes, weird eyes, smudged face, blurred face, poorly drawn face, mutation, mutilation, cloned face, strange mouth, grainy, blurred, blurry, writing, calligraphy, signature, text, watermark, bad art",
            control_inputs=[control_mode_depth, control_mode_edit],
            seed=1,
            caption_text=prompt["caption"].upper(),
            init_image_strength=0.2,
            mask_prompt="(face OR hair){-2}",
            mask_mode=MaskMode.KEEP,
            init_image=image,
            fix_faces=True,
        )

        def debug_callback(img, description, image_count, step_count, prompt):
            if callback:
                callback()

        result = next(
            imagine(prompts=imagine_prompt, debug_img_callback=debug_callback)
        )

        # imagine_image_files(prompts=final_prompt, outdir="final", print_caption=True)

        result.img.save(filename.split(".")[0] + "_generated." + filename.split(".")[1])

    def caption(self, filename):
        image = LazyLoadingImage(filepath=filename)
        return generate_caption(image)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate.py <filename> <prompt>")
        sys.exit(1)
    generator = ImageGenerator(warmup=False)
    # print(generator.caption(sys.argv[1]))

    generator.generate(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None, None)
