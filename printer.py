from PIL import Image
import win32print
import win32ui
from PIL import ImageWin


class ImagePrinter:
    def __init__(
        self, margin_left=80, margin_top=5, image_size=(512, 288), printer_name=None
    ):
        self.margin_left = margin_left
        self.margin_top = margin_top
        self.image_size = image_size
        self.logo = Image.open("logo.png").rotate(90, expand=True)
        self.printer_name = printer_name

        self.logo = self.logo.resize(
            (int(260 * self.logo.width / self.logo.height), 260)
        )

    def compose(self, orig1, orig2, orig3, gen1, gen2, gen3):
        # Open the images
        orig_imgs = [Image.open(img) for img in [orig1, orig2, orig3]]
        gen_imgs = [Image.open(img) for img in [gen1, gen2, gen3]]

        # Resize the images
        orig_imgs = [img.resize(self.image_size) for img in orig_imgs]
        gen_imgs = [img.resize(self.image_size) for img in gen_imgs]

        # Create a new image with the desired size
        new_img = Image.new("RGB", (1181, 1748), color="white")

        # Calculate the positions to paste the images
        pos_list = [(self.margin_left, self.margin_top + i * 290) for i in range(6)]

        # Paste the images
        for i, (orig_img, gen_img) in enumerate(
            zip(orig_imgs + orig_imgs, gen_imgs + gen_imgs)
        ):
            new_img.paste(
                self.logo,
                (pos_list[i][0] - self.logo.width - 3, pos_list[i][1] + 12),
                mask=self.logo,
            )
            new_img.paste(orig_img, pos_list[i])
            new_img.paste(gen_img, (pos_list[i][0] + 512, pos_list[i][1]))
            new_img.paste(
                self.logo.rotate(180),
                (pos_list[i][0] + 512 * 2 + 3, pos_list[i][1] + 12),
                mask=self.logo.rotate(180),
            )

        return new_img

    def print_image(self, image_path, printer_name=None):
        img = Image.open(image_path).rotate(90, expand=True)

        # printers = win32print.EnumPrinters(2)
        # for p in printers:
        #    print(p[2])

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
        composition = self.compose(
            f"sessions/{session}/1.jpg",
            f"sessions/{session}/2.jpg",
            f"sessions/{session}/3.jpg",
            f"sessions/{session}/1_generated.jpg",
            f"sessions/{session}/2_generated.jpg",
            f"sessions/{session}/3_generated.jpg",
        )

        composition.save(f"sessions/{session}/composition.jpg")
        self.print_image(f"sessions/{session}/composition.jpg", self.printer_name)


def main():
    generator = ImagePrinter()

    generator.print_image(
        "output.jpg",
        "Microsoft Print to PDF",
        # "Canon SELPHY CP1300"
    )
    return

    generator.generate_image(
        "capture.jpg",
        "capture.jpg",
        "capture.jpg",
        "final/capture.jpg",
        "final/capture.jpg",
        "final/capture.jpg",
    )


if __name__ == "__main__":
    main()
