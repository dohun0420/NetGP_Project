"""클라이언트가 화면에 표시할 서버의 게임 데이터"""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common.constants import PLAYER_SPEED

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

    def init_from_start(self, time_limit, costs, players, gold_count, golds):
        self.time_limit = time_limit
        self.costs = tuple(costs)
        self.players = {
            player_id: {'x': float(x), 'y': float(y), 'dir': 0, 'state': 0, 'dx': 0.0, 'dy': 0.0}  # dx,dy는 보간용 이전 좌표와 현재 좌표의 차이값을 저장한다.
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
    def calc_dir(self, player_id, new_x, new_y):
        # 서버는 dir를 보내지 않고 클라에서 계산한다. (dir : 0 아래 / 1 왼쪽 / 2 오른쪽 / 3 위)
        player = self.players[player_id]
        dx = new_x - player['x']
        dy = new_y - player['y']
        if abs(dx) > abs(dy):  # x 방향 이동이 더 크면 좌우 그림, y 방향 이동이 더 크면 위아래 그림
            player['dir'] = 2 if dx > 0 else 1
        else:
            player['dir'] = 3 if dy > 0 else 0

    def interpolate(self, dt):
        # 서버는 20HZ로 STATE를 보내지만 클라이언트는 60프레임으로 그린다 따라서 서버로 부터 받으면 바로 갱신하지 않고 지난 이동에 걸린 시간을 계산해서 그린다.
        # 보간은 현재 데이터와 이전 데이터 사이를 선형으로 계산한다. (단순히 이전 위치에서 현재 위치까지 이동하는 것처럼 보이게 한다)
        # 여기서 dt는 클라가 이전 프레임과 현재 프레임 사이에 걸린 시간이다. (0.016초 정도)
        speed = PLAYER_SPEED  # 초당 픽셀 이동량
        for player in self.players.values():
            if player['state'] == 1:  # 이동 중인 플레이어만 보간
                if abs(player['dx']) < 0.01 and abs(player['dy']) < 0.01:  # 이동할 거리가 거의 없으면 보간하지 않고 바로 현재 위치로 이동한다.
                    player['dx'] = 0.0
                    player['dy'] = 0.0
                    continue
                dx = speed * dt
                if abs(player['dx']) < dx: dx = abs(player['dx']) # dx는 항상 양수 따라서 abs()를 씌워서 비교한다.

                if player['dx'] > 0:
                    player['x'] += dx
                    player['dx'] -= dx
                else:
                    player['x'] -= dx
                    player['dx'] += dx
                dy = speed * dt
                if abs(player['dy']) < dy: dy = abs(player['dy'])
                if player['dy'] > 0:
                    player['y'] += dy
                    player['dy'] -= dy
                else:
                    player['y'] -= dy
                    player['dy'] += dy


    def apply_world_message(self, name, payload):
        # inbox에는 월드, 로비, 오류 등 여러 종류의 수신 메시지가 도착 순서대로 쌓인다.
        # 메인 스레드가 poll()로 꺼낸 메시지 중 GAME_START와 STATE만 ClientWorld에 반영한다.
        # name은 메시지 종류이고, 이 두 메시지의 payload는 헤더를 제외한 본문 바이트다.

        if name == 'StoC_GAME_START':
            # 게임 시작 시 제한 시간, 가격표, 플레이어 시작 위치와 금괴 배치를 설정한다.
            self.init_from_start(*protocol.unpack_game_start(payload))
        elif name == 'StoC_GOLD_MINED':
            # 채굴이 끝난 금괴를 지우고 팀 금괴를 서버 값으로 맞춘다. (STATE 보다 먼저 도착한다)
            self.apply_gold_mined(*protocol.unpack_gold_mined(payload))
        elif name == 'StoC_STATE':
            # 플레이 중에는 서버가 보낸 최신 값으로 플레이어와 HUD에 표시할 데이터를 갱신한다.
            remain_x10, team_gold, item_level, players = protocol.unpack_state(payload)
            # 서버는 20HZ로 STATE를 보내지만 클라이언트는 60프레임으로 그린다 따라서 서버로 부터 받으면 바로 갱신하지 않고 지난 0.033초 동안의 이동을 계산해서 그린다.
            # 또한 서버는 dir를 보내지 않고 클라에서 계산한다
            for player_id, x, y, state in players:
                    player = self.players[player_id]
                    self.calc_dir(player_id, x, y)
                    player['dx'] = float(x) - player['x']
                    player['dy'] = float(y) - player['y']
                    player['x'] = float(x)
                    player['y'] = float(y)
                    player['state'] = state
            self.remain_x10 = remain_x10
            self.team_gold = team_gold
            self.item_level = item_level
    def update(self, dt):
        # 매 프레임 호출 :
        self.interpolate(dt)

if __name__ == '__main__':
    # interpolate()를 테스트한다. 서버에서 임의의 player 데이터를 준다고 가정한다, client main에서 매 프레임 마다 호출하고 받는다 한다
    player = {'x': 100.0, 'y': 100.0, 'dir': 0, 'state': 1, 'dx': 3.0, 'dy': -2.0}
    world = ClientWorld()
    world.players[0] = player
    print(f"Before interpolate: {player}")
    world.interpolate(0.016)  # 16ms = 1/60초
    print(f"After interpolate: {player}")
    world.interpolate(0.016)
    print(f"After interpolate: {player}")


    def apply_gold_mined(self, spot_id, player_id, team_gold):
        # [11/24] GOLD_MINED 반영 : 해당 금괴를 지우면 GoldView 가 다음 프레임부터 그리지 않는다.
        self.golds.pop(spot_id, None)       # 이미 지워진 금괴 번호가 와도 오류 없이 넘어간다
        self.gold_count = len(self.golds)
        self.team_gold = team_gold