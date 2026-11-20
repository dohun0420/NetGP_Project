# [11/18~11/20] 눈으로 확인하는 테스트 : 서버 값(ClientWorld)만으로 게임 화면 한 장이 제대로 그려지는지 본다.
# 실행 : client 폴더(이미지 · arial.ttf 가 있는 곳)에서  python test_play_view_visual.py      ESC : 종료
# 서버 없이 가짜 값을 계속 바꿔 넣어서, 서버가 STATE 를 보낼 때 어떻게 보일지 미리 보여 준다.
# 확인할 것 : ① 플레이어 3명이 빨강 · 파랑 · 초록으로 구별된다
#            ② 0번(빨강)은 좌우로, 1번(파랑)은 위아래로 걸으면서 방향 그림이 바뀐다
#            ③ 2번(초록)은 제자리에서 8방향(0~7)을 돌아본다 (대각선은 좌우 그림), 3초 걷고 1초 멈춘다
#            ④ 아래쪽에 있는 캐릭터가 위쪽 캐릭터 앞에 그려진다
#            ⑤ 금괴 20개가 반짝인다   ⑥ 왼쪽 위 금괴 수가 2초마다 +1, 아이템 아이콘이 3초마다 바뀐다
#            ⑦ 오른쪽 위 타이머가 180부터 줄어든다
import random
import time

from pico2d import *
from sdl2 import SDL_KEYDOWN, SDLK_ESCAPE

from play_view import PlayView
from world_view import ClientWorld

open_canvas(1000, 600)

world = ClientWorld()
golds = [(i, random.randint(10, 1000), random.randint(10, 300)) for i in range(20)]     # 기존 게임의 금괴 범위
world.init_from_start(180, (10, 14, 24, 40), [(0, 200, 200), (1, 500, 120), (2, 800, 200)], len(golds), golds)

view = PlayView()
start = time.time()


def triangle(t, low, high, speed):
    # low ~ high 사이를 왕복하는 값과, 올라가는 중인지 여부
    length = high - low
    pos = (t * speed) % (2 * length)
    return (low + pos, True) if pos < length else (high - (pos - length), False)


running = True
while running:
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False

    t = time.time() - start

    # ---- 서버가 보낼 STATE 를 흉내 낸다 (좌표 · dir · state · 시간 · 팀 금괴 · 아이템 등급)
    x, rightward = triangle(t, 100, 900, 150)
    world.players[0].update(x=x, y=200, dir=2 if rightward else 6, state=1)          # 좌우로 걷기
    y, upward = triangle(t, 80, 300, 100)
    world.players[1].update(x=500, y=y, dir=0 if upward else 4, state=1)             # 위아래로 걷기
    world.players[2].update(x=800, y=200, dir=int(t) % 8, state=1 if int(t) % 4 < 3 else 0)   # 제자리에서 방향 바꾸기
    world.remain_x10 = max(0, 1800 - int(t * 10))
    world.team_gold = int(t) // 2
    world.item_level = (int(t) // 3) % 5

    view.update(world)
    clear_canvas()
    view.draw(world)
    update_canvas()
    delay(0.01)

close_canvas()