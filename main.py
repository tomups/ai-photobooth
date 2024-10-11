import numpy as np
import pygame
import pygame.freetype
import cv2
import time
import math
import os

from painter import Painter
from poet import Poet
import threading

from printer import ImagePrinter


class PhotoBooth:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()

        self.states = ["waiting", "pose", "countdown", "photo", "confirmation", "generating", "generated", "print"]
        self.state = self.states[0]
        self.start_time = 0
        self.block_interaction = False

        # Define font colors
        self.main_font_color = (200, 0, 0)
        self.side_font_color = (200, 0, 0)
        self.background_color = (0, 0, 0)

        # Define font
        pygame.freetype.init()
        self.font = pygame.freetype.Font("assets/PixeloidMono.ttf", 40)
        
        self.screen_info = pygame.display.Info()
        self.screen_width = 1280  # self.screen_info.current_w
        self.screen_height = 720  # self.screen_info.current_h
        self.sidebar_width = (self.screen_width - self.screen_height) / 2
        self.fullscreen = False
        self.screen = pygame.display.set_mode((1280, 720))
        self.screen.fill(self.background_color)
        pygame.display.set_caption("Muse Machine")
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
        
        self.hold_current_camera_frame = False        
        self.generated_image = None
        self.poem = None        
        self.camera_frame = None
        self.session = int(time.time())
        self.current_take = 0
        self.generation_progress = 30        
        
        self.printer = ImagePrinter(
            printer_name="Microsoft Print to PDF"  # "Canon SELPHY CP1300"
        )
        self.sounds = {
            "shutter": pygame.mixer.Sound("sounds/shutter.mp3"),
            "success": pygame.mixer.Sound("sounds/success.mp3"),
            "print": pygame.mixer.Sound("sounds/print.mp3"),
            "blip": pygame.mixer.Sound("sounds/blip.mp3"),
        }
        self.logo = pygame.image.load("sidebarlogo.png")                  

        # Create a surface for the "Warming up" message
        self.warmup_surface = pygame.Surface((self.screen_width, self.screen_height))
        self.warmup_surface.fill((self.background_color))  # White background

        self.font.size = 100
        self.render_text_with_outline("waking up", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2))        

        pygame.display.flip()

        self.painter = Painter(warmup=True)
        self.poet = Poet()
        self.poet.load_model()
        self.font.size = 40

    def next_state(self):
        current_index = self.states.index(self.state)
        if current_index == len(self.states) - 1:
            self.state = self.states[0]
            self.hold_current_camera_frame = False
            self.poem = None
            self.generated_image = None
            self.session = int(time.time())
        else:
            self.state = self.states[current_index + 1]
        self.start_time = time.time()
        self.font.size = 40

    def set_state(self, state):
        self.state = state
        self.start_time = time.time()
        self.font.size = 40

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
                    and not self.block_interaction
                ):
                    if self.state == "confirmation":
                        self.set_state("countdown")
                        self.hold_current_camera_frame = False
                    else:
                        self.next_state()

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
        self.render_flash_screen()     
        time.sleep(0.1)
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
        self.hold_current_camera_frame = True
        self.generation_progress = 0 
        time.sleep(0.3)
        self.next_state()

    def generate_image(self):
        self.generation_progress = 0
        threading.Thread(
            target=self.painter.generate,
            args=(
                f"sessions/{self.session}/{self.current_take}.jpg",
                None,
                self.update_progress,
            ),
        ).start()

    def generate_poem(self):
        threading.Thread(
            target=self.poet.generate,
            args=[
                f"sessions/{self.session}/{self.current_take}_generated.jpg"
            ],
        ).start()

    def update_progress(self):
        self.generation_progress += 1    

    def print_photos(self):        
        #self.sounds["print"].play()        
        self.printer.print_session(self.session)

    def render_camera_frame(self):
        if not self.hold_current_camera_frame:
            ret, frame = self.cap.read()
            if not ret:
                return False
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = pygame.surfarray.make_surface(frame)
            frame = pygame.transform.rotate(frame, -90)
            self.camera_frame = pygame.transform.smoothscale(
                frame, (self.screen_width, self.screen_height)
            )        
        self.screen.blit(
            self.camera_frame,
            (0, 0),
        )   

    def render_text_with_outline(self, text, font, color, position, alpha=255):
        outline_color = self.background_color  # White outline
        outline_width = 2

        # Render the outline
        outline_surface, _ = font.render(text, outline_color)
        outline_surface.set_alpha(alpha)
        outline_rect = outline_surface.get_rect(center=position)

        # Create a temporary surface for blitting outlines
        temp_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)

        # Blit outline in all directions on the temporary surface
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            temp_surface.blit(outline_surface, (outline_rect.x + dx * outline_width, outline_rect.y + dy * outline_width))

        # Render the main text
        text_surface, _ = font.render(text, color)
        text_surface.set_alpha(alpha)
        text_rect = text_surface.get_rect(center=position)
        temp_surface.blit(text_surface, text_rect)

        # Blit the temporary surface onto the screen
        self.screen.blit(temp_surface, (0, 0))

    def render_waiting(self):
        text = "hello human"
        position = (self.screen_width // 2, 50)
        
        self.render_text_with_outline(text, self.font, self.side_font_color, position)

        text = "press the big red button"
        position = (self.screen_width // 2, self.screen_height - 50)
        
        self.render_text_with_outline(text, self.font, self.side_font_color, position)

    def render_pose(self):            
            self.font.size = 48                   
            
            if time.time() - self.start_time < 4:
                self.render_text_with_outline("you are great at", self.font, self.side_font_color, (self.screen_width // 2, self.screen_height // 2 - 40))                
                self.render_text_with_outline("following instructions", self.font, self.side_font_color, (self.screen_width // 2, self.screen_height // 2 + 40))
            else:
                self.render_text_with_outline("now pose for me", self.font, self.side_font_color, (self.screen_width // 2, self.screen_height // 2))

            if time.time() - self.start_time > 6:
                self.next_state()     
            

    def render_countdown(self):
        message = "get ready"
        
        elapsed_time = time.time() - self.start_time
        if elapsed_time >= 2 and elapsed_time < 3:
            if not pygame.mixer.get_busy():
                self.sounds["blip"].play()
            message = "3"
        elif elapsed_time >= 3 and elapsed_time < 4:
            if not pygame.mixer.get_busy():
                self.sounds["blip"].play()
            message = "2"
        elif elapsed_time >= 4 and elapsed_time < 5:
            if not pygame.mixer.get_busy():
                self.sounds["blip"].play()
            message = "1"
        elif elapsed_time > 5:
            self.next_state()            

        alpha = int(255 - (elapsed_time % 1) * 255)
        self.font.size = 300 if len(str(message)) == 1 else 100        
        position = (self.screen_width // 2, self.screen_height // 2)
        
        self.render_text_with_outline(
            str(message),
            self.font,
            self.main_font_color,
            position,
            alpha=alpha                
        )

    def render_confirmation(self):
        elapsed_time = time.time() - self.start_time
        remaining_time = max(0, 5 - int(elapsed_time))

        self.font.size = 50
        position = (self.screen_width // 2, 100)
        self.render_text_with_outline(f"do you like it?", self.font, self.main_font_color, position)
        
        self.font.size = 30
        position = (self.screen_width // 2, self.screen_height - 150)
        self.render_text_with_outline(f"if not, press the button to retake", self.font, self.main_font_color, position)

        self.font.size = 80            
        position = (self.screen_width // 2, self.screen_height - 90)
        self.render_text_with_outline(f"{remaining_time}", self.font, self.main_font_color, position)
        
        if elapsed_time > 5:
            self.next_state()
            self.generate_image()

    def render_printer_message(self):        
        elapsed_time = time.time() - self.start_time
        
        
        if elapsed_time <= 1:
            alpha = int(255 * elapsed_time)
        elif elapsed_time > 1 and elapsed_time <= 6:
            alpha = 255
        elif elapsed_time > 6 and elapsed_time <= 7:
            alpha = int(255 - (elapsed_time - 6) * 255)
        if elapsed_time > 7:
            self.print_photos()
            alpha = 0
            self.next_state()
            return

        self.screen.blit(
            self.generated_image,
            (((self.screen_width - self.screen_height) / 2), 0),
        )        
        
        self.font.size = 60
        self.render_text_with_outline("THANK YOU, MY MUSE", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2), alpha=alpha)

        self.font.size = 40
        self.render_text_with_outline("i'm printing it for you", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2 + 100), alpha=alpha)

    def render_flash_screen(self):
        self.screen.fill((255, 255, 255))   
        self.sounds["shutter"].play()        
        pygame.display.flip()     
        

    def render_generated(self):        
        elapsed_time = time.time() - self.start_time
        if elapsed_time <= 2:
            alpha = int(255 * elapsed_time / 2)
            self.generated_image.set_alpha(alpha)
        else:
            self.generated_image.set_alpha(255)

        self.screen.blit(
            self.generated_image,
            (((self.screen_width - self.screen_height) / 2), 0),
        )

        self.font.size = 40

        if elapsed_time > 5 and elapsed_time <= 8:
            self.render_text_with_outline("you are a great muse", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2 - 60))
            self.render_text_with_outline("you inspired me", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2))
            self.render_text_with_outline("to write this poem", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2 + 60))

        if elapsed_time > 8:
            self.font.size = 35
            lines = self.poem.split('\n')
            for i, line in enumerate(lines):
                y_position = self.screen_height // 2 - (len(lines) - 1) * 30 + i * 60
                self.render_text_with_outline(line, self.font, self.main_font_color, (self.screen_width // 2, y_position))
            
            self.render_text_with_outline("press the button once again", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height - 60))

    def render_static_overlay(self):
        # Create a smaller surface for the static
        static_size = (self.screen_width // 4, self.screen_height // 4)
        static_surface = pygame.Surface(static_size)
        
        # Generate random static using numpy for better performance        
        static_array = np.random.randint(0, 256, (static_size[1], static_size[0]), dtype=np.uint8)
        
        # Convert the numpy array to a 3D array compatible with pygame
        static_3d = np.repeat(static_array[:, :, np.newaxis], 3, axis=2)
        
        # Use pygame.surfarray.make_surface instead of blit_array
        static_surface = pygame.surfarray.make_surface(static_3d)
        
        # Set alpha for the static (adjust for desired intensity)
        static_surface.set_alpha(30)
        
        # Scale up the static surface
        scaled_static = pygame.transform.scale(static_surface, (self.screen_width, self.screen_height))
        
        # Blit the scaled static surface onto the screen
        self.screen.blit(scaled_static, (0, 0))

    def render_logo(self):
        # Calculate the scale factor to fit the logo vertically
        scale_factor = self.screen_height / self.logo.get_height()
        
        # Calculate the new width while maintaining aspect ratio
        new_width = int(self.logo.get_width() * scale_factor)
        
        # Scale the logo
        scaled_logo = pygame.transform.smoothscale(
            self.logo,
            (new_width, self.screen_height)
        )
        
        # Calculate the alpha value for fading (0-255)
        fade_alpha = int((math.sin(time.time() * 1) + 1) * 80) + 40
        
        # Create a copy of the scaled logo with the fading alpha
        faded_logo = scaled_logo.copy()
        faded_logo.set_alpha(fade_alpha)
        
        # Calculate the x-position to center the logo in the sidebar
        x_pos_left = max(0, (self.sidebar_width - new_width) // 2)
        x_pos_right = self.sidebar_width + self.screen_height + max(0, (self.sidebar_width - new_width) // 2)
        
        # Blit the faded logo on both sidebars
        self.screen.blit(faded_logo, (x_pos_left, 0))
        self.screen.blit(faded_logo, (x_pos_right, 0))    

    def render_generating(self):
        # Draw progress bar border
        pygame.draw.rect(
            self.screen,
            self.background_color,
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
        self.font.size = 60
        position = (self.screen_width / 2, self.screen_height / 2 - 40)
        
        alpha = int((math.sin(time.time() * 2) + 1) * 127.5 + 127.5)  
        self.render_text_with_outline("let me paint you", self.font, self.main_font_color, position, alpha)

        if not self.generated_image:            
            try:
                self.generated_image = pygame.image.load(
                    f"sessions/{self.session}/{self.current_take}_generated.jpg"
                )             
                self.generated_image = pygame.transform.smoothscale(
                    self.generated_image, (self.screen_height, self.screen_height)
                )      
                self.generate_poem()                    
            except:
                pass
                
        elif not self.poem:            
            try:
                with open(f"sessions/{self.session}/poem.txt", "r") as file:
                    self.poem = file.read().strip()        
                self.start_time = time.time()        
            except:
                pass
        else:
            self.next_state()        

    def render_sidebars(self):
        pygame.draw.rect(
            self.screen,
            self.background_color,
            (0, 0, self.sidebar_width, self.screen_height),
        )
        pygame.draw.rect(
            self.screen,
            self.background_color,
            (
                self.sidebar_width + self.screen_height,
                0,
                self.sidebar_width,
                self.screen_height,
            ),
        )

    def run(self):
        while self.running:
            self.screen.fill(
                self.background_color
            )
            self.handle_events()        
            self.render_camera_frame()        
            self.render_sidebars()
            
            if self.state == "waiting":
                self.render_waiting()
            if self.state == "pose":
                self.render_pose()
            if self.state == "countdown":
                self.render_countdown()
            if self.state == "photo":
                self.take_photo()
            
            if self.state == "confirmation":
                self.render_confirmation()
            if self.state == "generating":
                self.render_generating()
            if self.state == "generated":
                self.render_generated()       
            if self.state == "print":
                self.render_printer_message()                      
                                              
            self.render_logo()            
            self.render_static_overlay()             
            

            pygame.display.flip()
            self.clock.tick(60)
        self.cap.release()
        pygame.quit()


if __name__ == "__main__":
    webcam_feed = PhotoBooth()
    webcam_feed.run()
