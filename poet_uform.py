from uform.gen_model import VLMForCausalLM, VLMProcessor
import torch
from PIL import Image
import os

class Poet:
    def __init__(self):
        self.processor = None
        self.model = None

    def load_model(self):
        # load the model and processor
        self.model = VLMForCausalLM.from_pretrained("unum-cloud/uform-gen")
        self.processor = VLMProcessor.from_pretrained("unum-cloud/uform-gen")

    def generate(self, image_path):
        if not self.processor or not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")

        # prepare the prompt and image
        prompt = "[cap] Write a 4 lines poem about this image. Maximum 6 words per line. Make sure it rhymes!"
        image = Image.open(image_path)

        # process the inputs
        inputs = self.processor(texts=[prompt], images=[image], return_tensors="pt")
        
        # generate output with torch.inference_mode
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                do_sample=False,
                use_cache=True,
                max_new_tokens=200,
                eos_token_id=32001,
                pad_token_id=self.processor.tokenizer.pad_token_id
            )

        # decode only the generated tokens
        prompt_len = inputs["input_ids"].shape[1]
        generated_text = self.processor.batch_decode(output[:, prompt_len:])[0]

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
