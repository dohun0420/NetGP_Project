# [11/18] 눈으로 확인하는 테스트 : 플레이어 3명(빨강 · 파랑 · 초록)이 방향 4가지로 제대로 그려지는지 본다.
# 실행 : client 폴더(Player.png, arial.ttf 가 있는 곳)에서  python test_player_view_visual.py
#   SPACE : 걷는 애니메이션 켜기/끄기      ESC : 종료
# 확인할 것 : ① 열(세로줄)마다 색이 다르다  ② 각 줄이 아래 / 위 / 오른쪽 / 왼쪽을 보고 있다
#            ③ 색이 서로 섞이거나 다른 줄까지 바뀌지 않는다  ④ 애니메이션이 켜져 있으면 다리가 움직인다
from pico2d import *
from sdl2 import SDL_KEYDOWN, SDLK_ESCAPE, SDLK_SPACE

from player_view import PlayerView

open_canvas(1000, 600)
font = load_font('arial.ttf', 22)

views = [PlayerView(player_id) for player_id in range(3)]       # 서버가 알려줄 player_id 0, 1, 2
column_x = (300, 500, 700)
column_name = ('0 : RED', '1 : BLUE', '2 : GREEN')
rows = (('s', 'DOWN (s)', 470), ('w', 'UP (w)', 350), ('d', 'RIGHT (d)', 230), ('a', 'LEFT (a)', 110))

moving = True
running = True
while running:
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                running = False
            elif event.key == SDLK_SPACE:
                moving = not moving

    for view in views:
        view.moving = moving
        view.update()                       # 걷는 프레임만 진행

    clear_canvas()
    for view, x, name in zip(views, column_x, column_name):
        font.draw(x - 45, 565, name, (0, 0, 0))
        for facing, label, y in rows:
            view.draw_at(x, y, facing, view.frame)
    for facing, label, y in rows:
        font.draw(20, y, label, (0, 0, 0))
    font.draw(20, 20, 'SPACE : walk on/off    ESC : quit', (0, 0, 0))
    update_canvas()
    delay(0.01)

close_canvas()