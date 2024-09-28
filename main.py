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
        self.sidebar_width = (self.screen_width - self.screen_height) / 2
        self.fullscreen = False
        self.screen = pygame.display.set_mode((1280, 720))
        self.screen.fill((255, 255, 255))
        pygame.display.set_caption("AI Tinkerers Photobooth")
        self.cap = cv2.VideoCapture(
            0, cv2.CAP_DSHOW
        )  # makes it load faster in Windows. Most likely no needed in Mac / Linux?
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Set webcam to 720p
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.webcam_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.webcam_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.running = True
        self.countdown_enabled = False
        self.countdown_message = "Get ready!"
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
        self.printer = ImagePrinter(
            printer_name="Canon SELPHY CP1300"  # "Microsoft Print to PDF"
        )
        self.sounds = {
            "shutter": pygame.mixer.Sound("sounds/shutter.mp3"),
            "success": pygame.mixer.Sound("sounds/success.mp3"),
            "print": pygame.mixer.Sound("sounds/print.mp3"),
            "blip": pygame.mixer.Sound("sounds/blip.mp3"),
        }
        self.logo = pygame.image.load("sidebarlogo.png")
        self.confirmation_countdown_enabled = False
        self.confirmation_start_time = None
        
        # Define font colors
        self.main_font_color = (72, 89, 173)
        self.side_font_color = (200, 50, 50)

        # Create a surface for the "Warming up" message
        self.warmup_surface = pygame.Surface((self.screen_width, self.screen_height))
        self.warmup_surface.fill((255, 255, 255))  # White background

        self.render_text_with_outline("Warming up", pygame.font.Font(None, 100), self.main_font_color, (self.screen_width // 2, self.screen_height // 2))       
        

        pygame.display.flip()
        

        self.image_generator = ImageGenerator(warmup=True)

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
                ):
                    if self.confirmation_countdown_enabled:
                        self.confirmation_countdown_enabled = False
                        self.current_take -= 1
                    self.start_next_take()

    def toggle_fullscreen(self):
        if not self.fullscreen:
            desktop_sizes = pygame.display.get_desktop_sizes()
            self.screen = pygame.display.set_mode(
                (desktop_sizes[0][0], desktop_sizes[0][1]), pygame.FULLSCREEN
            )
            self.screen_width = desktop_sizes[0][0]
            self.screen_height = desktop_sizes[0][1]
            self.fullscreen = True
        else:
            self.screen = pygame.display.set_mode((1280, 720))
            self.screen_width = 1280
            self.screen_height = 720
            self.fullscreen = False

        self.sidebar_width = (self.screen_width - self.screen_height) / 2

    def take_photo(self):
        self.flash_screen_enabled = True
        self.sounds["shutter"].play()
        self.flash_start_time = time.time()
        os.makedirs(f"sessions/{self.session}", exist_ok=True)
        ret, frame = self.cap.read()
        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape
        new_size = min(width, height)
        left = (width - new_size) // 2
        top = (height - new_size) // 2
        right = (width + new_size) // 2
        bottom = (height + new_size) // 2
        frame = frame[top:bottom, left:right]
        frame = cv2.resize(frame, (512, 512))
        cv2.imwrite(f"sessions/{self.session}/{self.current_take}.jpg", frame)
        self.hold_frame_enabled = True
        self.generation_progress = 0
        self.confirmation_countdown_enabled = True
        self.confirmation_start_time = time.time()

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
            self.generated_image, (self.screen_height, self.screen_height)
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
        self.countdown_enabled = True
        self.countdown_start_time = time.time()

        if self.current_take == 1:
            self.session = int(time.time())
            self.countdown_message = "Get ready!"

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
            self.camera_frame = pygame.transform.smoothscale(
                frame, (self.screen_width, self.screen_height)
            )
        self.screen.fill(
            (255, 255, 255)
        )  # Fill the screen with white color before blitting the frame
        self.screen.blit(
            self.camera_frame,
            (0, 0),
        )

    def render_take_number(self):
        if self.current_take > 0:
            take_text = pygame.font.Font(None, 50).render(
                f"Photo {self.current_take} / 3", True, self.main_font_color
            )

            self.screen.blit(
                take_text,
                (
                    45,
                    30,
                ),
            )
            self.screen.blit(
                take_text,
                (
                    self.screen_width - take_text.get_width() - 45,
                    30,
                ),
            )

           

    def render_text_with_outline(self, text, font, color, position, alpha=255):
        outline_color = (255, 255, 255)  # White outline
        outline_width = 2

        # Render the outline
        outline_surface = font.render(text, True, outline_color)
        outline_surface.set_alpha(alpha)
        outline_rect = outline_surface.get_rect(center=position)

        # Create a temporary surface for blitting outlines
        temp_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)

        # Blit outline in all directions on the temporary surface
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            temp_surface.blit(outline_surface, (outline_rect.x + dx * outline_width, outline_rect.y + dy * outline_width))

        # Render the main text
        text_surface = font.render(text, True, color)
        text_surface.set_alpha(alpha)
        text_rect = text_surface.get_rect(center=position)
        temp_surface.blit(text_surface, text_rect)

        # Blit the temporary surface onto the screen
        self.screen.blit(temp_surface, (0, 0))

    

    def render_press_button(self):
        if (
            self.current_take == 0
        ) and not self.printer_message_enabled:
            font = pygame.font.Font(None, 50)
            font.align = pygame.FONT_CENTER
            alpha = int((math.sin(time.time() * 2) + 1) * 155 + 100)
            
            left_position = (self.sidebar_width // 2, self.screen_height - 50)
            right_position = (self.screen_width - self.sidebar_width // 2, self.screen_height - 50)
            
            for position in [left_position, right_position]:

                text_surface = font.render("Press the big\nred button!", True, self.side_font_color)
                text_surface.set_alpha(alpha)
                text_rect = text_surface.get_rect(center=position)
                self.screen.blit(text_surface, text_rect)

    def render_countdown(self):
        if self.countdown_enabled:
            elapsed_time = time.time() - self.countdown_start_time
            if elapsed_time >= 2 and elapsed_time < 3:
                if not pygame.mixer.get_busy():
                    self.sounds["blip"].play()
                self.countdown_message = 3
            elif elapsed_time >= 3 and elapsed_time < 4:
                if not pygame.mixer.get_busy():
                    self.sounds["blip"].play()
                self.countdown_message = 2
            elif elapsed_time >= 4 and elapsed_time < 4.5:
                if not pygame.mixer.get_busy():
                    self.sounds["blip"].play()
                self.countdown_message = 1
            elif elapsed_time > 5:
                self.countdown_enabled = False
                self.take_photo()

            alpha = int(255 - (elapsed_time % 1) * 255)
            font = pygame.font.Font(None, 300 if len(str(self.countdown_message)) == 1 else 100)
            position = (self.screen_width // 2, self.screen_height // 2)
            
            self.render_text_with_outline(
                str(self.countdown_message),
                font,
                self.main_font_color,
                position,
                alpha=alpha                
            )

    def render_confirmation_countdown(self):
        if self.confirmation_countdown_enabled:
            elapsed_time = time.time() - self.confirmation_start_time
            remaining_time = max(0, 5 - int(elapsed_time))

            font = pygame.font.Font(None, 100)
            position = (self.screen_width // 2, 100)
            self.render_text_with_outline(f"Is it good?", font, self.main_font_color, position)
            
            font = pygame.font.Font(None, 50)
            position = (self.screen_width // 2, self.screen_height - 150)
            self.render_text_with_outline(f"If not, press the button to retake", font, self.main_font_color, position)

            font = pygame.font.Font(None, 100)            
            position = (self.screen_width // 2, self.screen_height - 90)
            self.render_text_with_outline(f"{remaining_time}", font, self.main_font_color, position)
            
            if elapsed_time > 5:
                self.confirmation_countdown_enabled = False
                self.generate_image()

    def render_press_to_continue(self):
        if self.generated_image_enabled:
            font = pygame.font.Font(None, 50)
            position = (self.screen_width // 2, 50)            
            
            alpha = int(127.5 + 127.5 * math.sin(time.time() * 2))  
            
            self.render_text_with_outline(
                f"Press the button to {'take the next photo' if self.current_take < 3 else 'print your photos'}",
                font,
                self.main_font_color,
                position,
                alpha=alpha
            )
            

    def render_printer_message(self):
        if self.printer_message_enabled:
            elapsed_time = time.time() - self.printer_message_start_time
            font = pygame.font.Font(None, 70)
            font.align = pygame.FONT_CENTER
            position = (self.screen_width // 2, self.screen_height // 2)
            
            if elapsed_time <= 1:
                alpha = int(255 * elapsed_time)
            elif elapsed_time > 1 and elapsed_time <= 6:
                alpha = 255
            elif elapsed_time > 6 and elapsed_time <= 7:
                alpha = int(255 - (elapsed_time - 6) * 255)
            else:
                self.printer_message_enabled = False
                alpha = 0
                self.current_take = 0  # Reset for the next photo

            message = "Check the printer\nfor your photo!".upper()
            self.render_text_with_outline(message, font, self.main_font_color, position, alpha=alpha)

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

            self.screen.blit(
                self.generated_image,
                (((self.screen_width - self.screen_height) / 2), 0),
            )

    def render_logo(self):
        logo = pygame.transform.smoothscale(
            self.logo,
            (
                self.sidebar_width,
                int(
                    self.logo.get_height() * self.sidebar_width / self.logo.get_width()
                ),
            ),
        )

        self.screen.blit(logo, (0, self.screen_height / 2 - logo.get_height() / 2))
        self.screen.blit(
            logo,
            (
                self.sidebar_width + self.screen_height,
                self.screen_height / 2 - logo.get_height() / 2,
            ),
        )

    def render_progress_bar(self):
        if self.hold_frame_enabled and not self.generated_image_enabled and not self.confirmation_countdown_enabled:
            if os.path.exists(
                f"sessions/{self.session}/{self.current_take}_generated.jpg"
            ):
                self.show_generated_image()

            # Draw progress bar border
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                (
                    self.screen_width / 2 - (self.screen_width / 2) / 2,
                    self.screen_height / 2 + 20,
                    self.screen_width / 2,
                    40,
                ),
                2,
            )
            # Draw progress bar
            pygame.draw.rect(
                self.screen,
                self.main_font_color,
                (
                    self.screen_width / 2 - (self.screen_width / 2) / 2,
                    self.screen_height / 2 + 20,
                    (self.generation_progress / 59) * (self.screen_width / 2),
                    40,
                ),
            )
            # Draw "Generating..." text
            font = pygame.font.Font(None, 100)
            position = (self.screen_width / 2, self.screen_height / 2 - 60)
            
            alpha = int((math.sin(time.time() * 2) + 1) * 127.5 + 127.5)  # Adjusted to range 127.5-255
            self.render_text_with_outline("Generating...", font, self.main_font_color, position, alpha)

    def render_sidebars(self):
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            (0, 0, self.sidebar_width, self.screen_height),
        )
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            (
                self.sidebar_width + self.screen_height,
                0,
                self.sidebar_width,
                self.screen_height,
            ),
        )

    def run(self):
        while self.running:
            self.handle_events()
            self.render_camera_frame()
            self.render_sidebars()            
            self.render_countdown()
            self.render_confirmation_countdown()            
            self.render_progress_bar()
            self.render_generated_image()
            self.render_printer_message()
            self.render_press_button()
            self.render_press_to_continue()
            self.render_flash_screen()
            
            self.render_take_number()
            self.render_logo()

            pygame.display.flip()
        self.cap.release()
        pygame.quit()


if __name__ == "__main__":
    webcam_feed = PhotoBooth()
    webcam_feed.run()
