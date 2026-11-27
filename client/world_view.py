"""클라이언트가 화면에 표시할 서버의 게임 데이터"""
import os
import sys
import sdl2

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common import protocol
from common.constants import PLAYER_SPEED

SHOP_RESULT_MESSAGES = {
    0: "구매 완료!",
    1: "금괴가 부족합니다.",
    2: "이미 보유 중이거나 더 높은 등급의 장비가 있습니다.",
    3: "잘못된 아이템 번호입니다.",
}
import sdl2
global running

class ClientWorld:
    def __init__(self):
        self.time_limit = 0
        self.costs = ()
        self.players = {}                # player_id -> 위치, 방향, 상태
        self.gold_count = 0
        self.golds = {}                  # spot_id -> 위치
        self.remain_x10 = 0              # STATE 패킷과 같은 0.1초 단위
        self.team_gold = 0
        self.item_level = 0
        self.running = False
        self.selection = 1               # 상점에서 선택된 아이템 번호 (1 장갑 ~ 4 드릴, 상점 진입시 기본 1)
        self.store_mode = False
        self.shop_message = ""           # [11/27] 최근 상점 구매 결과 안내 메시지

    def init_from_start(self, time_limit, costs, players, gold_count, golds):
        self.time_limit = time_limit
        self.costs = tuple(costs)
        self.players = {
            player_id: {'x': float(x), 'y': float(y), 'dir': 0, 'state': 0, 'dx': 0.0, 'dy': 0.0}
            for player_id, x, y in players
        }
        self.gold_count = gold_count
        self.golds = {
            spot_id: {'x': x, 'y': y}
            for spot_id, x, y in golds
        }
        self.remain_x10 = time_limit * 10
        self.team_gold = 0
        self.item_level = 0
        self.shop_message = ""
        self.running = True

    def calc_dir(self, player_id, new_x, new_y):
        # STATE 패킷에 dir 이 없을 때 좌표 변화량으로 방향 계산 (dir : 0 아래 / 1 왼쪽 / 2 오른쪽 / 3 위)
        player = self.players[player_id]
        dx = new_x - player['x']
        dy = new_y - player['y']
        if dx == 0 and dy == 0:
            return
        if abs(dx) >= abs(dy):
            player['dir'] = 2 if dx > 0 else 1
        else:
            player['dir'] = 3 if dy > 0 else 0

    def interpolate(self, dt):
        speed = PLAYER_SPEED  # 초당 픽셀 이동량
        for player in self.players.values():
            if player['state'] == 1:  # 이동 중인 플레이어만 보간
                if abs(player['dx']) < 0.01 and abs(player['dy']) < 0.01:
                    player['dx'] = 0.0
                    player['dy'] = 0.0
                    continue
                dx = speed * dt
                if abs(player['dx']) < dx:
                    dx = abs(player['dx'])

                if player['dx'] > 0:
                    player['x'] += dx
                    player['dx'] -= dx
                else:
                    player['x'] -= dx
                    player['dx'] += dx

                dy = speed * dt
                if abs(player['dy']) < dy:
                    dy = abs(player['dy'])
                if player['dy'] > 0:
                    player['y'] += dy
                    player['dy'] -= dy
                else:
                    player['y'] -= dy
                    player['dy'] += dy

    def apply_world_message(self, name, payload):
        if name == 'StoC_GAME_START':
            data = protocol.unpack_game_start(payload) if isinstance(payload, (bytes, bytearray)) else payload
            self.init_from_start(*data)
        elif name == 'StoC_GOLD_MINED':
            data = protocol.unpack_gold_mined(payload) if isinstance(payload, (bytes, bytearray)) else payload
            self.apply_gold_mined(*data)
        elif name == 'StoC_GOLD_RESPAWN':
            data = protocol.unpack_gold_respawn(payload) if isinstance(payload, (bytes, bytearray)) else payload
            self.apply_gold_respawn(data)
        elif name == 'StoC_SHOP_RESULT':
            data = protocol.unpack_shop_result(payload) if isinstance(payload, (bytes, bytearray)) else payload
            self.apply_shop_result(*data)
        elif name == 'StoC_STATE':
            data = protocol.unpack_state(payload) if isinstance(payload, (bytes, bytearray)) else payload
            remain_x10, team_gold, item_level, players = data
            for p_info in players:
                if len(p_info) == 5:
                    player_id, x, y, direction, state = p_info
                    player = self.players[player_id]
                    player['dir'] = direction
                else:
                    player_id, x, y, state = p_info
                    player = self.players[player_id]
                    self.calc_dir(player_id, x, y)
                player['dx'] = float(x) - float(player['x'])
                player['dy'] = float(y) - float(player['y'])
                player['state'] = state
            self.remain_x10 = remain_x10
            self.team_gold = team_gold
            self.item_level = item_level

    def update(self, dt):
        self.interpolate(dt)

    def apply_gold_mined(self, spot_id, player_id, team_gold):
        # [11/24] GOLD_MINED 반영 : 해당 금괴를 지우면 GoldView 가 다음 프레임부터 그리지 않는다.
        self.golds.pop(spot_id, None)
        self.gold_count = len(self.golds)
        self.team_gold = team_gold

    def apply_gold_respawn(self, golds):
        self.golds = {spot_id: {'x': x, 'y': y} for spot_id, x, y in golds}
        self.gold_count = len(self.golds)
    def handle_store_key(self, event):
        if event.key == sdl2.SDLK_w:        # 1,2 면 1, 3,4 면 3
            self.selection = 1 if self.selection in (1, 2) else 3
        elif event.key == sdl2.SDLK_s:      # 1,2 면 2, 3,4 면 4
            self.selection = 2 if self.selection in (1, 2) else 4
        elif event.key == sdl2.SDLK_a:      # 1,3 면 1, 2,4 면 2
            self.selection = 1 if self.selection in (1, 3) else 2
        elif event.key == sdl2.SDLK_d:      # 1,3 면 3, 2,4 면 4
            self.selection = 3 if self.selection in (1, 3) else 4


    def handle_event(self, events, client):     # 상점 모드 전환용 이벤트 처리
        if self.store_mode:
            for event in events:
                if event.type == sdl2.SDL_KEYDOWN:
                    if event.key == sdl2.SDLK_p:
                        self.store_mode = False
                        client.exit_shop()
                    else:
                        self.handle_store_key(event)
                        client.send_shop_buy(self.selection)
        else:
            for event in events:
                if event.type == sdl2.SDL_KEYDOWN:
                    if event.key == sdl2.SDLK_p:
                        self.store_mode = True
            client.play_state(events)

    def apply_shop_result(self, result, item_id, item_level, team_gold):
        # [11/27] 구매 결과 반영 : 성공 시 팀 아이템 등급과 팀 금괴 갱신, 실패 시 안내 메시지 기록
        self.shop_message = SHOP_RESULT_MESSAGES.get(result, f"알 수 없는 응답 ({result})")
        if result == 0:
            self.item_level = item_level
            self.team_gold = team_gold

    def handle_store_key(self, event):
        if event.key == sdl2.SDLK_w:        # 1,2 면 1, 3,4 면 3
            self.selection = 1 if self.selection in (1, 2) else 3
        elif event.key == sdl2.SDLK_s:      # 1,2 면 2, 3,4 면 4
            self.selection = 2 if self.selection in (1, 2) else 4
        elif event.key == sdl2.SDLK_a:      # 1,3 면 1, 2,4 면 2
            self.selection = 1 if self.selection in (1, 3) else 2
        elif event.key == sdl2.SDLK_d:      # 1,3 면 3, 2,4 면 4
            self.selection = 3 if self.selection in (1, 3) else 4

    def handle_event(self, events, client):     # 상점 모드 전환 및 구매 요청 처리
        if self.store_mode:
            for event in events:
                if event.type == sdl2.SDL_KEYDOWN:
                    if event.key == sdl2.SDLK_p:
                        self.store_mode = False
                        self.shop_message = ""
                        if client is not None:
                            client.exit_shop()
                    elif event.key == sdl2.SDLK_SPACE:
                        if client is not None:
                            client.send_shop_buy(self.selection)
                    else:
                        self.handle_store_key(event)
        else:
            for event in events:
                if event.type == sdl2.SDL_KEYDOWN:
                    if event.key == sdl2.SDLK_p:
                        self.store_mode = True
            if client is not None:
                client.play_state(events)

    def print_data(self):
        print(f"ClientWorld: time_limit={self.time_limit}, costs={self.costs}, players={self.players}, gold_count={self.gold_count}, golds={self.golds}, remain_x10={self.remain_x10}, team_gold={self.team_gold}, item_level={self.item_level}, selection={self.selection}")
        print(f"ClientWorld: time_limit={self.time_limit}, costs={self.costs}, players={self.players}, gold_count={self.gold_count}, golds={self.golds}, remain_x10={self.remain_x10}, team_gold={self.team_gold}, item_level={self.item_level}, selection={self.selection}")


if __name__ == '__main__':
    import play_view
    import pico2d

    world = ClientWorld()

    name = 'StoC_GAME_START'
    time_limit = 180
    costs = (10, 14, 24, 40)
    players = [(0, 100, 200), (1, 100, 100), (2, 900, 400)]
    gold_count = 3
    golds = [(7, 1000, 1), (8, 100, 200), (9, 300, 400)]
    value = (time_limit, costs, players, gold_count, golds)
    world.apply_world_message(name, value)
    world.print_data()
    pico2d.open_canvas(1000, 600)
    render = play_view.PlayView()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)
    '''
    name = 'StoC_STATE'
    remain_x10 = 1799
    team_gold = 0
    item_level = 0
    players = [(0, 100, 200, 0), (1, 200, 200, 1), (2, 900, 400, 2)]
    value = remain_x10, team_gold, item_level, players
    world.apply_world_message(name, value)
    world.print_data()
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.delay(1)
    for i in range(10):
        world.update(0.1)
        render.update(world)
        pico2d.clear_canvas()
        render.draw(world)
        pico2d.update_canvas()
        pico2d.delay(0.1)
    world.print_data()
    render.update(world)
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)
    '''
    # 상점 모드 테스트 테스트시 world handle_event()의 client 관련 부분을 주석 처리하고 실행
    class key_event:
        def __init__(self, key):
            self.type = sdl2.SDL_KEYDOWN
            self.key = key

    key = sdl2.SDLK_p
    events = key_event(key)

    world.handle_event([events], None)
    world.print_data()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)

    events.key = sdl2.SDLK_w        # 1 인 상황에서 w 누르면 1
    world.handle_event([events], None)
    world.print_data()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)

    events.key = sdl2.SDLK_s
    world.handle_event([events], None)
    world.print_data()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)

    events.key = sdl2.SDLK_d
    world.handle_event([events], None)
    world.print_data()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)

    events.key = sdl2.SDLK_a
    world.handle_event([events], None)
    world.print_data()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)

    events.key = sdl2.SDLK_a
    world.handle_event([events], None)
    world.print_data()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)

    events.key = sdl2.SDLK_w
    world.handle_event([events], None)
    world.print_data()
    render.update(world)
    pico2d.clear_canvas()
    render.draw(world)
    pico2d.update_canvas()
    pico2d.delay(1)
