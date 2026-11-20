# [11/18] 렌더링 분리 검증 : PlayerView(그리기 전용) 와 Player(입력 · 이동) 로 나눈 뒤에도
#         기존과 똑같이 그려지고 똑같이 움직이는지, 3명의 색이 서로 분리되는지 확인한다.
# 실제 Pico2D 없이 "가짜 pico2d / sdl2" 로 어떤 호출이 일어나는지만 본다. (눈으로 보는 확인은 test_player_view_visual.py)
import os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "client")]     # 최상위 폴더 / client 폴더 어디에 두어도 player_view, Player 를 찾는다

draw_calls = []                 # (이미지 번호, clip_draw 인자...)
color_calls = []                # (이미지 번호, r, g, b)
images = []
color_result = [0]              # SDL_SetTextureColorMod 가 돌려줄 값 (0 = 성공)

class FakeTexture: pass
class FakeImage:
    def __init__(self, name):
        self.name = name; self.texture = FakeTexture(); self.id = len(images); images.append(self)
    def clip_draw(self, *a): draw_calls.append((self.id,) + a)
pico = types.ModuleType("pico2d"); pico.load_image = FakeImage
sdl = types.ModuleType("sdl2")
sdl.SDL_KEYDOWN, sdl.SDL_KEYUP = 768, 769
sdl.SDLK_d, sdl.SDLK_a, sdl.SDLK_w, sdl.SDLK_s = 100, 97, 119, 115
sdl.SDL_GetError = lambda: b"fake error"
def set_color(texture, r, g, b):
    color_calls.append((next(i.id for i in images if i.texture is texture), r, g, b)); return color_result[0]
sdl.SDL_SetTextureColorMod = set_color
sys.modules["pico2d"], sys.modules["sdl2"] = pico, sdl

import player_view
from player_view import PlayerView, PLAYER_COLORS
import Player as NewMod            # 분리한 Player

# 분리 전 Player 원본 코드 (비교용). 별도 파일 없이 이 안에서 그대로 실행한다.
OLD_PLAYER_SOURCE = r'''
from pico2d import *
from sdl2 import (
    SDL_GetError, SDL_KEYDOWN, SDLK_d, SDLK_a, SDLK_w, SDLK_s, SDL_KEYUP,
    SDL_SetTextureColorMod,
)

# 서버의 player_id에 대응하는 색상: 0 빨강 / 1 파랑 / 2 초록
PLAYER_COLORS = ((255, 70, 70), (40, 50, 255), (70, 255, 70))

class Player:
    def __init__(self, player_id=0):
        if player_id not in (0, 1, 2):
            raise ValueError('player_id는 0, 1, 2 중 하나여야 합니다.')
        self.player_id = player_id
        self.x, self.y = 400, 300
        self.frame = 0
        self.dir_x = 0
        self.dir_y = 0
        # 플레이어마다 별도 이미지를 로딩해 자신의 색상만 적용한다.
        self.image = load_image('Player.png')
        if SDL_SetTextureColorMod(self.image.texture, *PLAYER_COLORS[player_id]) != 0:
            raise RuntimeError('색상 적용 실패: ' + SDL_GetError().decode('utf-8'))
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

'''
OldMod = types.ModuleType("Player_orig")
exec(OLD_PLAYER_SOURCE, OldMod.__dict__)

class Ev:
    def __init__(self, t, k): self.type, self.key = t, k

# ------------------------------------------------------------- 1) 3명의 색이 서로 분리되는가
images.clear(); color_calls.clear()
views = [PlayerView(i) for i in range(3)]
assert len({id(v.image) for v in views}) == 3                         # 이미지를 각자 따로 로딩
assert [c[1:] for c in color_calls] == list(PLAYER_COLORS)            # 0 빨강 / 1 파랑 / 2 초록
assert [c[0] for c in color_calls] == [v.image.id for v in views]     # 각 색은 자기 이미지에만 적용
assert len(set(PLAYER_COLORS)) == 3
print("1) 색 분리 OK : 이미지 3장을 따로 로딩하고 각자 빨강/파랑/초록을 자기 이미지에만 적용")

# ------------------------------------------------------------- 2) 분리 전 Player.draw 와 분리 후 Player.draw 가 똑같이 그리는가
same = 0
for state in "swad":
    for frame in range(3):
        for (x, y) in ((400, 300), (0, 0), (1000, 330), (123.5, 77)):
            images.clear(); draw_calls.clear()
            old = OldMod.Player(1); old.state, old.frame, old.x, old.y = state, frame, x, y; old.draw()
            old_call = draw_calls[0][1:]
            draw_calls.clear()
            new = NewMod.Player(1); new.state, new.frame, new.x, new.y = state, frame, x, y; new.draw()
            assert draw_calls[0][1:] == old_call, (state, frame, x, y)
            same += 1
print(f"2) 그리기 동일 OK : 방향 4 x 프레임 3 x 위치 4 = {same}가지 조합에서 clip_draw 인자가 분리 전과 완전히 같음")

# ------------------------------------------------------------- 3) 입력 · 이동은 분리 전과 똑같이 동작하는가
script = {0: Ev(768, 100), 12: Ev(768, 119), 50: Ev(769, 100), 80: Ev(768, 97), 120: Ev(769, 119), 150: Ev(769, 97),
          200: Ev(768, 115), 230: "stop", 240: Ev(768, 100), 300: Ev(769, 100)}
old, new = OldMod.Player(2), NewMod.Player(2)
for step in range(400):
    ev = script.get(step)
    for pl in (old, new):
        if ev == "stop": pl.stop()
        elif ev: pl.handle_event(ev)
        pl.update()
    assert (old.x, old.y, old.frame, old.state, old.dir_x, old.dir_y, old.is_stopped) == \
           (new.x, new.y, new.frame, new.state, new.dir_x, new.dir_y, new.is_stopped), step
print("3) 이동 동일 OK : 키 입력 10번 · 400프레임 시뮬레이션에서 위치/프레임/방향이 분리 전과 매 프레임 같음")

# ------------------------------------------------------------- 4) PlayerView 만으로 그릴 수 있는가 (서버 값 사용)
images.clear(); draw_calls.clear()
v = PlayerView(0); v.set_state(250, 120, 'd', False); v.draw()
assert draw_calls == [(0, 0, 45, 33, 48, 250, 120, 90, 100)], draw_calls
draw_calls.clear(); v.draw_at(10, 20, 'w', 2)
assert draw_calls == [(0, 66, 86, 33, 46, 10, 20, 90, 90)]
draw_calls.clear(); v.draw_at(10, 20, 'x', 0)                     # 모르는 방향은 그리지 않는다
assert draw_calls == []
print("4) PlayerView OK : set_state 한 값 그대로 그리고, 모르는 방향은 그리지 않음")

# ------------------------------------------------------------- 5) 걷는 애니메이션
v = PlayerView(1)
v.set_state(0, 0, 's', False)
for _ in range(50): v.update()
assert v.frame == 0                                              # 서 있으면 프레임 유지
v.set_state(0, 0, 's', True); seen = []
for _ in range(30):
    v.update(); seen.append(v.frame)
assert [seen[9], seen[19], seen[29]] == [1, 2, 0] and seen[:9] == [0] * 9      # 10프레임마다 0 -> 1 -> 2 -> 0
print("5) 애니메이션 OK : 걸을 때만 10프레임마다 0 -> 1 -> 2 -> 0, 서 있으면 유지")

# ------------------------------------------------------------- 6) 잘못된 값
for bad in (-1, 3, 9, None):
    try: PlayerView(bad)
    except ValueError: continue
    raise AssertionError(f"player_id {bad} 를 통과시킴")
color_result[0] = -1
try: PlayerView(0); raise AssertionError("색상 적용 실패를 무시함")
except RuntimeError as e: assert "fake error" in str(e)
color_result[0] = 0
print("6) 오류 처리 OK : player_id 가 0~2 가 아니면 ValueError, 색상 적용 실패는 RuntimeError")

print("\n전부 통과")