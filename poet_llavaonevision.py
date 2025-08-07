import torch
from transformers import AutoProcessor, LlavaOnevisionForConditionalGeneration
from PIL import Image
import os

class Poet:
    def __init__(self):
        self.processor = None
        self.model = None

    def load_model(self):
        # load the model
        model_id = "llava-hf/llava-onevision-qwen2-0.5b-ov-hf"
        self.model = LlavaOnevisionForConditionalGeneration.from_pretrained(
            model_id, 
            torch_dtype=torch.float16, 
            low_cpu_mem_usage=True, 
        ).to(0)

        # load the processor
        self.processor = AutoProcessor.from_pretrained(model_id, use_fast=True)

    def generate(self, image_path):
        if not self.processor or not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")

        # Define a chat history and use `apply_chat_template` to get correctly formatted prompt
        # Each value in "content" has to be a list of dicts with types ("text", "image") 
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Write a poem about this image."},
                    {"type": "image"},
                ],
            },
        ]
        prompt = self.processor.apply_chat_template(conversation, add_generation_prompt=True)

        # Load and process the image
        raw_image = Image.open(image_path)
        inputs = self.processor(images=raw_image, text=prompt, return_tensors='pt').to(0, torch.float16)

        # Generate the output
        output = self.model.generate(**inputs, max_new_tokens=200, do_sample=False)
        generated_text = self.processor.decode(output[0][2:], skip_special_tokens=True)
        generated_text = generated_text.split('assistant')[1]
        generated_text = generated_text.split('\n')[1:5]
        generated_text = '\n'.join(generated_text)

        # Get the directory of the image
        image_dir = os.path.dirname(image_path)
        
        # Create the path for the poem file
        poem_path = os.path.join(image_dir, 'poem.txt')
        
        # Write the generated text to the poem file
        with open(poem_path, 'w') as f:
            f.write(generated_text)

        return generated_text

if __name__ == "__main__":
    poet = Poet()
    poet.load_model()
    poem = poet.generate("capture_generated copy 2.jpg")
    print(poem)
