from pico2d import *
from sdl2 import SDL_KEYDOWN, SDLK_d, SDLK_a, SDLK_w, SDLK_s, SDL_KEYUP

class Player:
    def __init__(self):
        self.x, self.y = 400, 300
        self.frame = 0
        self.dir_x = 0
        self.dir_y = 0
        self.image = load_image('Player.png')
        self.state = 's'
        self.frame_timer = 0
        self.is_stopped = False

    def update(self):
        if not self.is_stopped:
            new_x = self.x + (self.dir_x * 2)
            new_y = self.y + (self.dir_y * 2)
            if 0 <= new_x <= 1000:
                self.x = new_x
            if 0 <= new_y <= 330:
                self.y = new_y

            if self.dir_x != 0 or self.dir_y != 0:
                self.frame_timer += 1
                if self.frame_timer % 10 == 0:
                    self.frame = (self.frame + 1) % 3

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_d:
                self.dir_x = 1
                self.state = 'd'
                self.is_stopped = False
            elif event.key == SDLK_a:
                self.dir_x = -1
                self.state = 'a'
                self.is_stopped = False
            elif event.key == SDLK_w:
                self.dir_y = 1
                self.state = 'w'
                self.is_stopped = False
            elif event.key == SDLK_s:
                self.dir_y = -1
                self.state = 's'
                self.is_stopped = False
        elif event.type == SDL_KEYUP:
            if event.key == SDLK_d and self.dir_x == 1:
                self.dir_x = 0
            elif event.key == SDLK_a and self.dir_x == -1:
                self.dir_x = 0
            elif event.key == SDLK_w and self.dir_y == 1:
                self.dir_y = 0
            elif event.key == SDLK_s and self.dir_y == -1:
                self.dir_y = 0

    def stop(self):
        self.dir_x = 0
        self.dir_y = 0
        self.is_stopped = True

    def draw(self):
        if self.state == 's':
            self.image.clip_draw(self.frame * 33, 130, 33, 56, self.x, self.y, 90, 80)
        elif self.state == 'w':
            self.image.clip_draw(self.frame * 33, 86, 33, 46, self.x, self.y, 90, 90)
        elif self.state == 'd':
            self.image.clip_draw(self.frame * 33, 45, 33, 48, self.x, self.y, 90, 100)
        elif self.state == 'a':
            self.image.clip_draw(self.frame * 33, 0, 33, 57, self.x, self.y, 90, 100)
