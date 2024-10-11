from PIL import Image, ImageDraw, ImageFont
import win32print
import win32ui
from PIL import ImageWin
import os


class ImagePrinter:
    def __init__(
        self, printer_name=None
    ):
        self.canvas_width = 1748
        self.canvas_height = 1181
        self.image_size = (870, 870)        
        self.logo = Image.open("sidebarlogo.png")
        self.printer_name = printer_name
        

    def compose(self, image_path, poem_path):        
        image_path = self.normalize_path(image_path)
        if os.path.exists(image_path):
            image = Image.open(image_path)
        else:
            print(f"Warning: Image not found: {image_path}")
            image = Image.new("RGB", self.image_size, color="white")    

        poem_path = self.normalize_path(poem_path)
        if os.path.exists(poem_path):
            with open(poem_path, "r") as file:
                poem = file.read()
        else:
            print(f"Warning: Poem not found: {poem_path}")
            poem = ""
        
        # Resize the images
        image = image.resize(self.image_size)        

        # Create a new image with the desired size
        canvas = Image.new("RGB", (self.canvas_width, self.canvas_height), color="white")        

        canvas.paste(image, (self.canvas_width // 2 - self.image_size[0] // 2, 30))        

        # Load the font
        font_path = "assets/PixeloidMono.ttf"
        font_size = 40  # Increased font size
        font = ImageFont.truetype(font_path, font_size)

        # Create a draw object
        draw = ImageDraw.Draw(canvas)

        # Set the text color to red
        text_color = (255, 0, 0)  # RGB for red

        # Calculate the position for the poem
        text_x = self.canvas_width // 2  # Center horizontally
        
        # Calculate text height and position for vertical centering
        text_lines = poem.split('\n')        
        text_y = self.image_size[1] + 45

        # Write the poem
        for line in text_lines:
            # Get the width of the current line
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            # Calculate the x-coordinate to center the line
            line_x = text_x - line_width // 2
            draw.text((line_x, text_y), line, font=font, fill=text_color)
            text_y += font_size + 20

        canvas.paste(self.logo, (120, 80), self.logo)
        canvas.paste(self.logo, (self.canvas_width - self.logo.width - 120, 80), self.logo)

        canvas = canvas.rotate(90, expand=True)  

        return canvas

    def normalize_path(self, path):
        return os.path.normpath(path.replace('\\', '/'))

    def print_image(self, image_path, printer_name=None):
        image_path = self.normalize_path(image_path)
        if not os.path.exists(image_path):
            print(f"Error: Image not found: {image_path}")
            return

        img = Image.open(image_path).rotate(90, expand=True)

        # Get the printer name
        if printer_name is None:
            if self.printer_name is None:
                print("Using default printer...")
                printer_name = win32print.GetDefaultPrinter()
            else:
                printer_name = self.printer_name

        hprinter = win32print.OpenPrinter(printer_name)

        try:
            print("Printing...")
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc(image_path)
            hdc.StartPage()

            # Get the printer surface size
            printer_surface_width = hdc.GetDeviceCaps(8)  # HORZRES
            printer_surface_height = hdc.GetDeviceCaps(10)  # VERTRES

            # Calculate the position to center the image
            x = (printer_surface_width - img.width) // 2
            y = (printer_surface_height - img.height) // 2

            dib = ImageWin.Dib(img)
            dib.draw(
                hdc.GetHandleOutput(),
                (x, y, x + img.width, y + img.height),
            )

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
        finally:
            win32print.ClosePrinter(hprinter)

    def print_session(self, session):
        session_dir = self.normalize_path(f"sessions/{session}")
        if not os.path.exists(session_dir):
            print(f"Error: Session directory not found: {session_dir}")
            return

        composition = self.compose(
            os.path.join(session_dir, "0_generated.jpg"),
            os.path.join(session_dir, "poem.txt")
        )

        composition_path = os.path.join(session_dir, "composition.jpg")
        composition.save(composition_path)
        composition.show()
        #self.print_image(composition_path, self.printer_name)


def main():
    generator = ImagePrinter(printer_name="Canon SELPHY CP1300")

    generator.print_session(1728640417)


if __name__ == "__main__":
    main()
