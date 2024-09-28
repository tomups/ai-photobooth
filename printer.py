from PIL import Image
import win32print
import win32ui
from PIL import ImageWin
import os


class ImagePrinter:
    def __init__(
        self, margin_left=80, margin_top=52, image_size=(512, 512), printer_name=None
    ):
        self.margin_left = margin_left
        self.margin_top = margin_top
        self.image_size = image_size
        self.logo = Image.open("logo.png").rotate(90, expand=True)
        self.printer_name = printer_name

        self.logo = self.logo.resize(
            (int(image_size[1] * self.logo.width / self.logo.height), image_size[1])
        )

    def compose(self, orig1, orig2, orig3, gen1, gen2, gen3):
        # Open the images
        orig_imgs = []
        gen_imgs = []
        for img_path in [orig1, orig2, orig3]:
            img_path = self.normalize_path(img_path)
            if os.path.exists(img_path):
                orig_imgs.append(Image.open(img_path))
            else:
                print(f"Warning: Image not found: {img_path}")
                orig_imgs.append(Image.new("RGB", self.image_size, color="white"))
        
        for img_path in [gen1, gen2, gen3]:
            img_path = self.normalize_path(img_path)
            if os.path.exists(img_path):
                gen_imgs.append(Image.open(img_path))
            else:
                print(f"Warning: Image not found: {img_path}")
                gen_imgs.append(Image.new("RGB", self.image_size, color="white"))

        # Resize the images
        orig_imgs = [img.resize(self.image_size) for img in orig_imgs]
        gen_imgs = [img.resize(self.image_size) for img in gen_imgs]

        # Create a new image with the desired size
        new_img = Image.new("RGB", (1181, 1748), color="white")

        # Calculate the positions to paste the images
        pos_list = [
            (
                self.margin_left,
                self.margin_top + i * (self.image_size[1] + self.margin_top),
            )
            for i in range(3)
        ]

        # Paste the images and logos
        for i, (orig_img, gen_img) in enumerate(zip(orig_imgs, gen_imgs)):
            new_img.paste(
                self.logo,
                (pos_list[i][0] - self.logo.width - 5, pos_list[i][1]),
                mask=self.logo,
            )
            new_img.paste(orig_img, pos_list[i])
            new_img.paste(
                gen_img, (pos_list[i][0] + self.image_size[0], pos_list[i][1])
            )
            new_img.paste(
                self.logo.rotate(180),
                (pos_list[i][0] + self.image_size[0] * 2 + 5, pos_list[i][1]),
                mask=self.logo.rotate(180),
            )

        return new_img

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
            os.path.join(session_dir, "1.jpg"),
            os.path.join(session_dir, "2.jpg"),
            os.path.join(session_dir, "3.jpg"),
            os.path.join(session_dir, "1_generated.jpg"),
            os.path.join(session_dir, "2_generated.jpg"),
            os.path.join(session_dir, "3_generated.jpg"),
        )

        composition_path = os.path.join(session_dir, "composition.jpg")
        composition.save(composition_path)
        self.print_image(composition_path, self.printer_name)


def main():
    generator = ImagePrinter()

    generator.print_session(1718651223)


if __name__ == "__main__":
    main()
