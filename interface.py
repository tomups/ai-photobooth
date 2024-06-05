import pygame
import cv2
import time
import math
import os

from generate import ImageGenerator
import threading

from printer import ImagePrinter


class PhotoBooth:
    def __init__(self):
        pygame.init()
        self.screen_info = pygame.display.Info()
        self.screen_width = 1280  # self.screen_info.current_w
        self.screen_height = 720  # self.screen_info.current_h
        self.fullscreen = False
        self.screen = pygame.display.set_mode((1280, 720))
        self.screen.fill((255, 255, 255))
        pygame.display.set_caption("AI Tinkerers Photobooth")
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Set webcam to 720p
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.webcam_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.webcam_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.webcam_aspect_ratio = self.webcam_width / self.webcam_height
        self.screen_aspect_ratio = self.screen_width / self.screen_height
        if self.webcam_aspect_ratio > self.screen_aspect_ratio:
            self.scaled_width = self.screen_width
            self.scaled_height = int(self.screen_width / self.webcam_aspect_ratio)
        else:
            self.scaled_height = self.screen_height
            self.scaled_width = int(self.screen_height * self.webcam_aspect_ratio)
        self.running = True
        self.countdown_enabled = False
        self.countdown_text = "Get ready!"
        self.countdown_start_time = None
        self.flash_screen_enabled = False
        self.flash_start_time = None
        self.hold_frame_enabled = False
        self.generated_image_enabled = False
        self.generated_image = None
        self.generated_image_time = 0
        self.camera_frame = None
        self.session = int(time.time())
        self.current_take = 0
        self.generation_progress = 30
        self.printer_message_enabled = False
        self.printer_message_start_time = None
        self.image_generator = ImageGenerator(warmup=False)
        self.printer = ImagePrinter(printer_name="Microsoft Print to PDF")
        self.sounds = {
            "shutter": pygame.mixer.Sound("sounds/shutter.mp3"),
            "success": pygame.mixer.Sound("sounds/success.mp3"),
            "print": pygame.mixer.Sound("sounds/print.mp3"),
            "blip": pygame.mixer.Sound("sounds/blip.mp3"),
        }

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.mod & pygame.KMOD_LALT and event.key == pygame.K_RETURN:
                    self.toggle_fullscreen()
                elif (
                    event.key == pygame.K_SPACE
                    and not self.countdown_enabled
                    and not self.printer_message_enabled
                    and (not self.hold_frame_enabled or self.generated_image_enabled)
                ):
                    self.start_next_take()

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height), pygame.FULLSCREEN
            )
            self.fullscreen = True
        else:
            self.screen = pygame.display.set_mode((1280, 720))
            self.fullscreen = False

    def take_photo(self):
        self.flash_screen_enabled = True
        self.sounds["shutter"].play()
        self.flash_start_time = time.time()
        os.makedirs(f"sessions/{self.session}", exist_ok=True)
        pygame.image.save(
            self.camera_frame, f"sessions/{self.session}/{self.current_take}.jpg"
        )
        self.hold_frame_enabled = True
        self.generation_progress = 0
        self.generate_image()

    def show_generated_image(self):
        for _ in range(5):
            try:
                self.generated_image = pygame.image.load(
                    f"sessions/{self.session}/{self.current_take}_generated.jpg"
                )
                break
            except:
                time.sleep(0.5)

        self.generated_image_enabled = True
        self.sounds["success"].play()
        self.generated_image = pygame.transform.smoothscale(
            self.generated_image, (self.screen_width, self.screen_height)
        )
        self.generated_image_time = time.time()

    def generate_image(self):
        self.generation_progress = 0
        threading.Thread(
            target=self.image_generator.generate,
            args=(
                f"sessions/{self.session}/{self.current_take}.jpg",
                None,
                self.update_progress,
            ),
        ).start()

    def update_progress(self):
        self.generation_progress += 1

    def start_next_take(self):
        self.current_take += 1
        self.hold_frame_enabled = False
        self.generated_image_enabled = False
        if self.current_take == 4:
            self.current_take = 0
            self.print_photos()
            return
        self.countdown_text = "Two more!" if self.current_take == 2 else "Last one!"
        self.countdown_enabled = True
        self.countdown_start_time = time.time()

        if self.current_take == 1:
            self.session = int(time.time())
            self.countdown_text = "Get ready!"

    def print_photos(self):
        self.printer_message_enabled = True
        self.sounds["print"].play()
        self.printer_message_start_time = time.time()
        self.printer.print_session(self.session)

    def render_camera_frame(self):
        if not self.hold_frame_enabled:
            ret, frame = self.cap.read()
            if not ret:
                return False
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = pygame.surfarray.make_surface(frame)
            frame = pygame.transform.rotate(frame, -90)
            frame = pygame.transform.scale(
                frame, (self.scaled_width, self.scaled_height)
            )
            self.camera_frame = frame
        self.screen.fill(
            (255, 255, 255)
        )  # Fill the screen with white color before blitting the frame
        self.screen.blit(
            self.camera_frame,
            (
                (self.screen_width - self.scaled_width) // 2,
                (self.screen_height - self.scaled_height) // 2,
            ),
        )

    def render_take_number(self):
        if self.current_take > 0:
            take_text = pygame.font.Font(None, 50).render(
                f"Photo {self.current_take} / 3", True, (255, 255, 255)
            )
            self.screen.blit(
                take_text,
                (
                    self.screen_width - take_text.get_width() - 10,
                    self.screen_height - take_text.get_height() - 10,
                ),
            )

    def render_press_button(self):
        if (
            self.current_take == 0 or self.generated_image_enabled
        ) and not self.printer_message_enabled:
            prompt_text = pygame.font.Font(None, 40).render(
                "Press the big red button!", True, (200, 50, 50)
            )
            alpha = int((math.sin(time.time() * 2) + 1) * 155 + 100)
            prompt_text.set_alpha(alpha)
            self.screen.blit(
                prompt_text,
                (
                    (self.screen_width - prompt_text.get_width()) // 2,
                    self.screen_height - prompt_text.get_height() - 10,
                ),
            )

    def render_countdown(self):
        if self.countdown_enabled:
            elapsed_time = time.time() - self.countdown_start_time
            if elapsed_time >= 2 and elapsed_time < 3:
                if not pygame.mixer.get_busy():
                    self.sounds["blip"].play()
                self.countdown_text = 3
            elif elapsed_time >= 3 and elapsed_time < 4:
                if not pygame.mixer.get_busy():
                    self.sounds["blip"].play()
                self.countdown_text = 2
            elif elapsed_time >= 4 and elapsed_time < 5:
                if not pygame.mixer.get_busy():
                    self.sounds["blip"].play()
                self.countdown_text = 1
            elif elapsed_time > 5:
                self.countdown_enabled = False
                self.take_photo()

            alpha = int(255 - (elapsed_time % 1) * 255)
            countdown_text = pygame.font.Font(None, 300).render(
                str(self.countdown_text), True, (255, 255, 255)
            )
            countdown_text.set_alpha(alpha)
            self.screen.blit(
                countdown_text,
                (
                    self.screen_width // 2 - countdown_text.get_width() // 2,
                    self.screen_height // 2 - countdown_text.get_height() // 2,
                ),
            )

    def render_printer_message(self):
        if self.printer_message_enabled:
            elapsed_time = time.time() - self.printer_message_start_time
            font = pygame.font.Font(None, 100)
            font.align = pygame.FONT_CENTER
            printer_message_text = font.render(
                "Check the printer\nfor your photos!".upper(),
                True,
                (255, 255, 255),
            )
            if elapsed_time <= 1:
                alpha = int(255 * elapsed_time)

                printer_message_text.set_alpha(alpha)
                self.screen.blit(
                    printer_message_text,
                    (
                        (self.screen_width - printer_message_text.get_width()) // 2,
                        self.screen_height // 2
                        - printer_message_text.get_height() // 2,
                    ),
                )
            elif elapsed_time > 1 and elapsed_time <= 6:
                printer_message_text.set_alpha(255)
            elif elapsed_time > 6 and elapsed_time <= 7:
                alpha = int(255 - (elapsed_time - 6) * 255)
                printer_message_text.set_alpha(alpha)
            else:
                self.printer_message_enabled = False
                printer_message_text.set_alpha(0)

            self.screen.blit(
                printer_message_text,
                (
                    (self.screen_width - printer_message_text.get_width()) // 2,
                    self.screen_height // 2 - printer_message_text.get_height() // 2,
                ),
            )

    def render_flash_screen(self):
        if self.flash_screen_enabled:
            self.screen.fill((255, 255, 255))
            if time.time() - self.flash_start_time >= 0.5:
                self.flash_screen_enabled = False

    def render_generated_image(self):
        if self.generated_image_enabled:
            elapsed_time = time.time() - self.generated_image_time
            if elapsed_time <= 2:
                alpha = int(255 * elapsed_time / 2)
                self.generated_image.set_alpha(alpha)
            else:
                self.generated_image.set_alpha(255)
            self.screen.blit(self.generated_image, (0, 0))

    def render_logo(self):
        logo = pygame.image.load("logo.png")

        logo_width = int(logo.get_width() * 50 / logo.get_height())
        logo = pygame.transform.smoothscale(logo, (logo_width, 50))
        self.screen.blit(logo, ((self.screen_width - logo.get_width()) // 2, 5))

    def render_progress_bar(self):
        if self.hold_frame_enabled and not self.generated_image_enabled:
            if os.path.exists(
                f"sessions/{self.session}/{self.current_take}_generated.jpg"
            ):
                self.show_generated_image()

            # Draw progress bar border
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                (
                    self.screen_width / 2 - (self.screen_width * 0.7) / 2,
                    self.screen_height / 2 + 20,
                    self.screen_width * 0.7,
                    40,
                ),
                2,
            )
            # Draw progress bar
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                (
                    self.screen_width / 2 - (self.screen_width * 0.7) / 2,
                    self.screen_height / 2 + 20,
                    (self.generation_progress / 59) * (self.screen_width * 0.7),
                    40,
                ),
            )
            # Draw "Generating..." text
            generating_text = pygame.font.Font(None, 100).render(
                "Generating...", True, (255, 255, 255)
            )

            # Fade in and out effect
            alpha = int((math.sin(time.time() * 2) + 1) * 127.5)
            generating_text.set_alpha(alpha)
            self.screen.blit(
                generating_text,
                (
                    self.screen_width / 2 - generating_text.get_width() / 2,
                    self.screen_height / 2 - 60,
                ),
            )

    def run(self):
        while self.running:
            self.handle_events()
            self.render_camera_frame()
            self.render_take_number()
            self.render_countdown()
            self.render_progress_bar()
            self.render_generated_image()
            self.render_logo()
            self.render_printer_message()
            self.render_press_button()
            self.render_flash_screen()
            pygame.display.flip()
        self.cap.release()
        pygame.quit()


if __name__ == "__main__":
    webcam_feed = PhotoBooth()
    webcam_feed.run()
