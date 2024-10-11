from transformers import AutoModelForCausalLM, AutoProcessor, GenerationConfig
from PIL import Image
import os

class Poet:
    def __init__(self):
        self.processor = None
        self.model = None

    def load_model(self):
        # load the processor
        self.processor = AutoProcessor.from_pretrained(
            'cyan2k/molmo-7B-D-bnb-4bit',
            trust_remote_code=True,
            torch_dtype='auto',
            device_map='auto'
        )

        # load the model
        self.model = AutoModelForCausalLM.from_pretrained(
            'cyan2k/molmo-7B-D-bnb-4bit',
            trust_remote_code=True,
            torch_dtype='auto',
            device_map='auto'
        )

    def generate(self, image_path):
        if not self.processor or not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")

        # process the image and text
        inputs = self.processor.process(
            images=[Image.open(image_path)],
            text="Write a 4 lines poem about this image. Maximum 6 words per line. Make sure it rhymes!"
        )

        # move inputs to the correct device and make a batch of size 1
        inputs = {k: v.to(self.model.device).unsqueeze(0) for k, v in inputs.items()}

        # generate output; maximum 200 new tokens; stop generation when <|endoftext|> is generated
        output = self.model.generate_from_batch(
            inputs,
            GenerationConfig(max_new_tokens=200, stop_strings="<|endoftext|>"),
            tokenizer=self.processor.tokenizer
        )

        # only get generated tokens; decode them to text
        generated_tokens = output[0,inputs['input_ids'].size(1):]
        generated_text = self.processor.tokenizer.decode(generated_tokens, skip_special_tokens=True)

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
