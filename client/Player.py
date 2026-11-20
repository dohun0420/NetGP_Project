from pico2d import *
from sdl2 import SDL_KEYDOWN, SDLK_d, SDLK_a, SDLK_w, SDLK_s, SDL_KEYUP

from player_view import PlayerView, PLAYER_COLORS     # 그리기는 PlayerView 가 담당한다


class Player:
    # 입력 처리와 이동만 담당한다. 그리기(이미지 · 색상 · 스프라이트)는 PlayerView 로 분리했다.
    def __init__(self, player_id=0):
        self.player_id = player_id
        self.x, self.y = 400, 300
        self.frame = 0
        self.dir_x = 0
        self.dir_y = 0
        self.view = PlayerView(player_id)       # player_id 가 0~2 가 아니면 여기서 ValueError
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
        self.view.draw_at(self.x, self.y, self.state, self.frame)