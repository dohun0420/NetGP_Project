# [11/18~11/20] 렌더링 분리 검증 : GoldView / MapView / Bgm / PlayView
#   분리 전 GoldSpot · Map 과 똑같이 그리는지, 서버 값(ClientWorld)만으로 한 화면이 올바른 순서로 그려지는지 확인한다.
# 실제 Pico2D 없이 "가짜 pico2d / sdl2" 로 어떤 호출이 일어나는지만 본다. (눈으로 보는 확인은 client/test_play_view_visual.py)
# 실행 : python test_play_view.py     (이 파일을 프로젝트 최상위 폴더나 client 폴더 어디에 두어도 된다)
import os, sys, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "client")]

log = []                                   # 그리기 호출 기록 : (종류, 이미지 이름, 이미지 번호, 인자...)
texts = []                                 # 글자 그리기 기록 : (글자, 색)
music_log = []                             # 음악 호출 기록
images = []
class FakeTexture: pass
class FakeImage:
    def __init__(self, name):
        self.name = name; self.texture = FakeTexture(); self.id = len(images); images.append(self)
    def draw(self, *a): log.append(("draw", self.name, self.id) + a)
    def clip_draw(self, *a): log.append(("clip", self.name, self.id) + a)
class FakeFont:
    def draw(self, x, y, text, color): texts.append((text, color))
class FakeMusic:
    def __init__(self, name): self.name = name; music_log.append(("load", name))
    def set_volume(self, v): music_log.append(("volume", v))
    def repeat_play(self): music_log.append(("repeat_play",))
    def stop(self): music_log.append(("stop",))
pico = types.ModuleType("pico2d")
pico.load_image = FakeImage; pico.load_font = lambda path, size: FakeFont(); pico.load_music = FakeMusic
pico.load_wav = FakeMusic
sdl = types.ModuleType("sdl2")
sdl.SDL_GetError = lambda: b""; sdl.SDL_SetTextureColorMod = lambda *a: 0
for n, v in (("SDL_KEYDOWN", 768), ("SDL_KEYUP", 769), ("SDLK_d", 100), ("SDLK_a", 97), ("SDLK_w", 119), ("SDLK_s", 115)):
    setattr(sdl, n, v)
sys.modules["pico2d"], sys.modules["sdl2"] = pico, sdl

class Clock:                               # time.time() 을 우리가 정한 값으로 바꾼다 (반짝임 간격을 정확히 검사하려고)
    now = 1000.0
time.time = lambda: Clock.now

# 분리 전 원본 코드 (비교용). 별도 파일 없이 이 안에서 그대로 실행한다.
OLD_GOLDSPOT_SOURCE = r'''
import random
import time

from pico2d import load_image


class GoldSpot:
    image = None

    def __init__(self):
        self.x, self.y = random.randint(10, 1000), random.randint(10, 300)
        self.frame = 0
        self.frame_delay = 0.3
        self.last_update_time = time.time()
        if GoldSpot.image == None:
            GoldSpot.image = load_image('GoldSpot.png')

    def update(self):
        current_time = time.time()
        if current_time - self.last_update_time >= self.frame_delay:
            self.frame = (self.frame + 1) % 4
            self.last_update_time = current_time

    def draw(self):
        self.image.clip_draw(self.frame * 190, 0, 190, 244, self.x, self.y, 25, 25)



'''
OLD_MAP_SOURCE = r'''
from pico2d import load_image, load_music


class Map:
    def __init__(self):
        self.image = load_image('map.png')
        self.bgm = load_music('Cave.mp3')
        self.bgm.set_volume(32)
        self.bgm.repeat_play()

    def draw(self):
        self.image.draw(500, 300, 1000, 600)

    def update(self):
        pass

'''
OldGold = types.ModuleType("GoldSpot_orig"); exec(OLD_GOLDSPOT_SOURCE, OldGold.__dict__)
OldMap = types.ModuleType("Map_orig"); exec(OLD_MAP_SOURCE, OldMap.__dict__)

import gold_view, map_view, BGM, play_view
from gold_view import GoldView
from map_view import MapView
from BGM import BGM
from play_view import PlayView, facing_from_dir
from world_view import ClientWorld

def reset():
    log.clear(); texts.clear(); music_log.clear()

# ------------------------------------------------------------- 1) GoldView : 분리 전 GoldSpot 과 같은 모양, 같은 타이밍
reset(); Clock.now = 1000.0
old = OldGold.GoldSpot(); old.x, old.y = 123, 45
view = GoldView()
frames_seen = set()
for step in range(1, 70):                                  # 0.05초 간격으로 3.5초
    Clock.now = 1000.0 + step * 0.05
    old.update(); view.update()
    assert old.frame == view.frame, (step, old.frame, view.frame)
    frames_seen.add(view.frame)
    log.clear(); old.draw(); old_call = log[0][3:]
    log.clear(); view.draw({7: {"x": 123, "y": 45}})
    assert log == [("clip", "GoldSpot.png", view.image.id) + old_call], (log, old_call)
assert frames_seen == {0, 1, 2, 3}
log.clear(); view.draw({}); assert log == []               # 금괴가 없으면 아무것도 그리지 않는다
log.clear(); view.draw({i: {"x": i * 10, "y": 5} for i in range(20)}); assert len(log) == 20     # 서버가 보낸 개수만큼 그린다
print("1) GoldView OK : 3.5초 동안 프레임(0~3)과 그리는 인자가 분리 전 GoldSpot 과 매 순간 같음, 개수는 서버 값대로")

# ------------------------------------------------------------- 2) MapView : 분리 전 Map 과 같은 그림, 음악은 따로
reset()
old_map = OldMap.Map(); old_call = [c for c in log if c[0] == "draw"]; log.clear(); old_map.draw(); old_call = log[0][3:]
assert any(m[0] == "repeat_play" for m in music_log)       # 분리 전 Map 은 만들 때 음악까지 재생했다
reset()
mv = MapView(); mv.draw()
assert log == [("draw", "map.png", mv.image.id) + old_call] and old_call == (500, 300, 1000, 600)
assert music_log == []                                     # 분리 후 MapView 는 음악을 건드리지 않는다
print("2) MapView OK : 배경 그리기(500, 300, 1000, 600)는 분리 전과 같고, 음악은 하지 않음")

# ------------------------------------------------------------- 3) Bgm
reset()
b = BGM("Cave.mp3"); b.play(); b.stop()
assert music_log == [("load", "Cave.mp3"), ("volume", 32), ("repeat_play",), ("stop",)], music_log
reset(); BGM("Store.mp3", 10); assert music_log == [("load", "Store.mp3"), ("volume", 10)]
print("3) Bgm OK : 파일 로딩 + 볼륨 32(기본), play = 반복 재생, stop = 정지")

# ------------------------------------------------------------- 4) 서버 dir -> 스프라이트 방향
assert [facing_from_dir(d) for d in range(4)] == ["s", "a", "d", "w"]
assert facing_from_dir(99) == "s"
print("4) 방향 변환 OK : 0~4 -> 아래/왼/오른/위, 모르는 값은 아래")

# ------------------------------------------------------------- 5) PlayView : 서버 값만으로 한 화면 (그리는 순서까지)
world = ClientWorld()
world.init_from_start(180, (10, 14, 24, 40), [(0, 300, 100), (1, 500, 250), (2, 700, 180)], 2, [(0, 100, 50), (1, 200, 60)])
world.team_gold, world.item_level, world.remain_x10 = 7, 2, 1234
reset(); images.clear()
pv = PlayView()
pv.update(world)
reset(); pv.draw(world)
names = [c[1] for c in log]
assert names == ["map.png", "GoldSpot.png", "GoldSpot.png", "Player.png", "Player.png", "Player.png",
                 "UI.png", "Gold.png", "Shovel.png", "Timer.png"], names
player_calls = [c for c in log if c[1] == "Player.png"]
assert [c[7] for c in player_calls] == [500, 700, 300]       # 위쪽(y 큰) 플레이어부터 : 1번(250) -> 2번(180) -> 0번(100)
assert len({c[2] for c in player_calls}) == 3               # 3명이 각자 다른 이미지(= 각자 다른 색)로 그려짐
assert [t[0] for t in texts] == ["X 7", "124"]              # HUD : 팀 금괴 7, 남은 시간 123.4초 -> 124
print("5) PlayView OK : 배경 -> 금괴 2개 -> 플레이어 3명(위쪽부터, 서로 다른 이미지) -> HUD, 값은 서버(ClientWorld) 그대로")

# ------------------------------------------------------------- 6) 서버 방향/상태가 그림과 애니메이션에 반영되는가
world.players[0].update({"dir": 1, "state": 1}); world.players[1].update({"dir": 4, "state": 0})
before = (pv.players[0].frame, pv.players[1].frame)
for _ in range(10): pv.update(world)
assert pv.players[0].frame == (before[0] + 1) % 3            # 이동(state 1) 중인 0번은 10프레임에 1칸
assert pv.players[1].frame == before[1]                      # 대기(state 0) 중인 1번은 그대로
reset(); pv.draw(world)
p0 = [c for c in log if c[1] == "Player.png" and c[7] == 300][0]
assert p0[3:] == (pv.players[0].frame * 33, 0, 33, 57, 300, 100, 90, 100)       # dir 1(왼쪽) -> 'a' 스프라이트
print("6) 상태 반영 OK : dir 6 -> 왼쪽 그림, 이동 중일 때만 걷는 프레임이 진행")

# ------------------------------------------------------------- 7) 게임 시작 전(빈 ClientWorld)에도 죽지 않는가
empty = ClientWorld(); reset(); pv2 = PlayView(); pv2.update(empty); reset(); pv2.draw(empty)
assert [c[1] for c in log] == ["map.png", "UI.png", "Gold.png", "Timer.png"] and texts[0][0] == "X 0"
print("7) 빈 화면 OK : 플레이어/금괴가 없어도 배경과 HUD 만 그림")

# 서버가 채굴 상태를 보낸 플레이어에게만 기존 효과가 표시된다.
world.players[0]['state'] = 2
world.players[1]['state'] = 2
pv.update(world)
reset(); pv.draw(world)
effects = [call for call in log if call[1] == 'dig_animation.png']
assert {call[7:9] for call in effects} == {(300, 140), (500, 290)}
assert all(call[3] == 0 for call in effects)

world.players[0].update(x=320, y=110)
for _ in range(11):
    pv.update(world)
reset(); pv.draw(world)
effects = [call for call in log if call[1] == 'dig_animation.png']
assert {call[7:9] for call in effects} == {(320, 150), (500, 290)}
assert all(call[3] == 25 for call in effects)

world.players[0]['state'] = 0
world.players[1]['state'] = 0
pv.update(world)
reset(); pv.draw(world)
assert all(call[1] != 'dig_animation.png' for call in log)
print("8) 채굴 효과 OK : 두 플레이어의 위치와 프레임을 갱신하고 채굴 상태가 끝나면 제거")

print("\n전부 통과")