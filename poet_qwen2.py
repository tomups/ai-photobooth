from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
from PIL import Image
import os

class Poet:
    def __init__(self):
        self.processor = None
        self.model = None

    def load_model(self):
        # load the model
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-2B-Instruct", 
            torch_dtype="auto", 
            device_map="auto"
        )

        # load the processor
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")

    def generate(self, image_path):
        if not self.processor or not self.model:
            raise ValueError("Model not loaded. Call load_model() first.")

        # prepare the messages in the format expected by Qwen2-VL
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": f"file://{image_path}",
                    },
                    {"type": "text", "text": "Write a 4 lines poem about this image. Maximum 6 words per line. It should rhyme."},
                ],
            }
        ]

        # preparation for inference
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)

        # inference: generation of the output
        generated_ids = self.model.generate(**inputs, max_new_tokens=200)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        generated_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

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
