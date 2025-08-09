import numpy as np
import pygame
import pygame.freetype
import cv2
import time
import math
import os

from painter_custom import Painter
from poet_llavaonevision import Poet
import threading

from printer_side2side import ImagePrinter

# Art style prompts for image generation
PROMPTS = [
    {
        "caption": "Robots",
        "prompt": "androids and robots, futuristic cyberpunk style",
    },
    {
        "caption": "Knitted",
        "prompt": "made out of crochet, knitted",
    },
    {
        "caption": "Van Gogh",
        "prompt": "in the style of Van Gogh, surrounded by swirling clouds and stars",
    },
    {
        "caption": "Neon Dreams",
        "prompt": "futuristic astronauts in a neon-lit cityscape, inspired by Syd Mead",
    },
    {
        "caption": "Steampunk",
        "prompt": "Victorian-era, in the style of steampunk",
    },
    {
        "caption": "Wave Rider",
        "prompt": "riding a giant wave, inspired by Hokusai's ukiyo-e woodblock prints",
    },
    {
        "caption": "Cyberpunk",
        "prompt": "cyberpunk-inspired hacker, surrounded by screens and wires, in the style of Blade Runner",
    },
    {
        "caption": "Renaissance Revival",
        "prompt": "dressed as a Renaissance-era noble, surrounded by ornate gold frames and velvet drapes",
    },
    {
        "caption": "Lab Life",
        "prompt": "futuristic, high-tech laboratory, inspired by the art of Syd Mead",
    },
    {
        "caption": "Dali's Dream",
        "prompt": "surreal, dreamlike landscape, inspired by the art of Salvador Dali",
    },
    {
        "caption": "Superhero",
        "prompt": "superhero, in the style of a superman comic book",
    },
    {
        "caption": "Dragon Ball",
        "prompt": "dressed as Dragon Ball Z characters, in the style of Akira Toriyama",
    },
    #{
    #    "caption": "Detective",
    #    "prompt": "wearing a stylish suit of a detective, film noir-inspired cityscape",
    #},
    {
        "caption": "Knight's Tale",
        "prompt": "dressed as a medieval knight, surrounded by Gothic architecture and stained glass windows",
    },
    {
        "caption": "Retro Futurism",
        "prompt": "futuristic, space-age landscape, inspired by the art of retro-futurism",
    },
    {
        "caption": "Greek Gods",
        "prompt": "dressed as a ancient Greek god, surrounded by marble columns and statues",
    },
    {
        "caption": "Pop Art",
        "prompt": "bright, colorful landscape, pop art, inspired by the art of Andy Warhol",
    },
]


class PhotoBooth:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()

        self.do_poem = False

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
        self.running = True
        
        self.hold_current_camera_frame = False        
        self.generated_image = None
        self.poem = None        
        self.camera_frame = None
        self.session = int(time.time())
        self.current_take = 0
        self.generation_progress = 0       
        
        self.printer = ImagePrinter(
            printer_name="Microsoft Print to PDF"  # "Canon SELPHY CP1300"
        )
        self.sounds = {
            "shutter": pygame.mixer.Sound("sounds/shutter.mp3"),
            "success": pygame.mixer.Sound("sounds/success.mp3"),
            "print": pygame.mixer.Sound("sounds/print.mp3"),
            "blip": pygame.mixer.Sound("sounds/blip.mp3"),
        }
        self.left_logo = pygame.image.load("whymuselogo.png")                  
        self.right_logo = pygame.image.load("why2025logo.png")                  

        # Create a surface for the "Warming up" message
        self.warmup_surface = pygame.Surface((self.screen_width, self.screen_height))
        self.warmup_surface.fill((self.background_color))  # White background

        self.font.size = 100
        self.render_text_with_outline("waking up", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2))        

        pygame.display.flip()

        self.painter = Painter(prompts=PROMPTS)
        self.poet = None
        self.font.size = 40

        self.painter.load_model()
        if self.do_poem:
            self.poet = Poet()
            self.poet.load_model()

        self.init_webcam()

    def init_webcam(self):
        self.cap = cv2.VideoCapture(
            0, cv2.CAP_DSHOW
        )  # makes it load faster in Windows. Most likely no needed in Mac / Linux?
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Set webcam to 720p
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.webcam_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.webcam_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def next_state(self):
        current_index = self.states.index(self.state)
        if current_index == len(self.states) - 1:
            self.state = self.states[0]
            self.hold_current_camera_frame = False
            self.poem = None
            self.generated_image = None
            self.session = int(time.time())
            self.init_webcam()
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
        self.block_interaction = True
        threading.Thread(
            target=self.painter.generate,
            args=(
                f"sessions/{self.session}/{self.current_take}.jpg",
                None,
                self.update_progress,
            ),
        ).start()

    def generate_poem(self):        
        if not self.do_poem or not self.poet:
            return
        threading.Thread(
            target=self.poet.generate,
            args=[
                f"sessions/{self.session}/{self.current_take}_generated.jpg"
            ],
        ).start()

    def update_progress(self, **kwargs):
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
        
        self.font.size = 55
        self.render_text_with_outline("THANK YOU, MY MUSE", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2), alpha=alpha)

        self.font.size = 40
        self.render_text_with_outline("i'm printing it for you", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2 + 100), alpha=alpha)

    def render_flash_screen(self):
        self.screen.fill((255, 255, 255))   
        self.sounds["shutter"].play()        
        pygame.display.flip()     
        

    def render_generated(self):    
        self.block_interaction = False    
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

        if elapsed_time > 5 and (elapsed_time <= 8 or not self.do_poem):
            self.render_text_with_outline("you are a great muse", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2 - 60))
            self.render_text_with_outline("you inspired me", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2))
            self.render_text_with_outline("press the button once again", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height - 60))

            #self.render_text_with_outline("to write this poem", self.font, self.main_font_color, (self.screen_width // 2, self.screen_height // 2 + 60))

        if elapsed_time > 8 and self.do_poem:
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

    def render_logos(self):
        # Calculate the scale factor to fit the logo to the sidebar width
        scale_factor = self.sidebar_width / self.left_logo.get_width()
        
        # Calculate the new dimensions while maintaining aspect ratio
        new_width = int(self.left_logo.get_width() * scale_factor)
        new_height = int(self.left_logo.get_height() * scale_factor)
        
        # Scale the left logo
        scaled_left_logo = pygame.transform.smoothscale(
            self.left_logo,
            (new_width, new_height)
        )
        
        # Scale the right logo (using same scale factor for consistency)
        scaled_right_logo = pygame.transform.smoothscale(
            self.right_logo,
            (new_width, new_height)
        )
        
        # Calculate the alpha value for fading (0-255)
        fade_alpha = int((math.sin(time.time() * 1) + 1) * 80) + 40
        
        # Create copies of the scaled logos with the fading alpha
        faded_left_logo = scaled_left_logo.copy()
        faded_left_logo.set_alpha(fade_alpha)
        
        faded_right_logo = scaled_right_logo.copy()
        faded_right_logo.set_alpha(fade_alpha)
        
        # Calculate the y-position to center the logo vertically in the sidebar
        y_pos = (self.screen_height - new_height) // 2
        
        # Calculate the x-positions for both sidebars
        x_pos_left = 0  # Left sidebar starts at x=0
        x_pos_right = self.sidebar_width + self.screen_height  # Right sidebar starts after left sidebar + main screen
        
        # Blit the faded logos on their respective sidebars
        self.screen.blit(faded_left_logo, (x_pos_left, y_pos))
        self.screen.blit(faded_right_logo, (x_pos_right, y_pos))    

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
                (self.generation_progress / (self.do_poem and 20 or 10)) * (self.screen_width / 2),
                40,
            ),
        )
        # Draw "Generating..." text
        self.font.size = 60
        position = (self.screen_width / 2, self.screen_height / 2 - 40)
        alpha = int((math.sin(time.time() * 2) + 1) * 127.5 + 127.5) 
        
         
        self.render_text_with_outline("let me paint you", self.font, self.main_font_color, position, alpha)
        
        self.font.size = 25
        position = (self.screen_width / 2, self.screen_height / 2 + 100)
        self.render_text_with_outline("please be patient, i'm GPU poor", self.font, self.main_font_color, position, alpha)
        position = (self.screen_width / 2, self.screen_height / 2 + 150)
        self.render_text_with_outline("and everything runs locally", self.font, self.main_font_color, position, alpha)
        if not self.generated_image:            
            try:
                self.generated_image = pygame.image.load(
                    f"sessions/{self.session}/{self.current_take}_generated.jpg"
                )             
                self.generated_image = pygame.transform.smoothscale(
                    self.generated_image, (self.screen_height, self.screen_height)
                )
                if self.do_poem:
                    self.generate_poem()
                    self.generation_progress = 15
                else:
                    self.start_time = time.time()
                    self.next_state()
            except:
                pass
                
        elif self.do_poem and not self.poem:                    
            try:
                with open(f"sessions/{self.session}/poem.txt", "r") as file:
                    self.poem = file.read().strip()        
                self.start_time = time.time()
                self.generation_progress = 20    
            except:
                pass
        elif self.do_poem:
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
            self.render_logos()   
            
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
                                              
                     
            self.render_static_overlay()             
            

            pygame.display.flip()
            self.clock.tick(60)
        self.cap.release()
        pygame.quit()


if __name__ == "__main__":
    photobooth = PhotoBooth()
    photobooth.run()
