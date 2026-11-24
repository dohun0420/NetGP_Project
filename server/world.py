"""서버가 관리하는 게임 데이터"""
import os
import sys
from time import monotonic
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common import constants


# 기존 문자열 상수를 패킷의 아이템 번호(0 기본, 1 장갑 ~ 4 드릴)에 연결한다.
# 팀 전체에 적용되는 아이템이므로 계획서에 따라 기본 비용의 2배로 조립한다.
ITEM_TABLE = {
    item_id: {
        'dig_time': constants.DIG_TIME[name],
        'cost': constants.ITEM_COST[name] * 2,
    }
    for item_id, name in enumerate(('hand', 'glove', 'shovel', 'pickaxe', 'drill'))
}

MINING_RANGE = 50                  # [11/24] 채굴 가능 거리(px). 기존 게임과 같다


class Player:
    def __init__(self, player_id, x, y):
        self.player_id = player_id     # 0 빨강 / 1 파랑 / 2 초록
        self.x = float(x)
        self.y = float(y)
        self.dir = 0                   # 대각 방향도 처리해야하니 0~7까지 8방향으로 처리
        self.state = 0                 # 0 대기 / 1 이동 / 2 채굴
        self.key_flags = 0
        self.mined = 0                 # 개인별 채굴 수
        self.mining_started_at = None
    def move(self, dt):
        print(dt)
        print(self.key_flags)
        if self.key_flags == 0:
            self.state = 0  # 대기
        else:
            self.state = 1  # 이동
            dx, dy = 0, 0

            if self.key_flags & 0x01:  # 위
                dy += 1
            if self.key_flags & 0x02:  # 아래
                dy -= 1
            if self.key_flags & 0x04:  # 왼쪽
                dx -= 1
            if self.key_flags & 0x08:  # 오른쪽
                dx += 1


            # 방향 설정 (0~7)
            if dx == -1 and dy == -1:
                self.dir = 7  # 왼쪽 위
            elif dx == -1 and dy == 0:
                self.dir = 6  # 왼쪽
            elif dx == -1 and dy == 1:
                self.dir = 5  # 왼쪽 아래
            elif dx == 0 and dy == -1:
                self.dir = 0  # 위
            elif dx == 0 and dy == 1:
                self.dir = 4  # 아래
            elif dx == 1 and dy == -1:
                self.dir = 1  # 오른쪽 위
            elif dx == 1 and dy == 0:
                self.dir = 2  # 오른쪽
            elif dx == 1 and dy == 1:
                self.dir = 3  # 오른쪽 아래
            print(dx, dy)
            # 이동 속도 적용 (초당 픽셀 이동량) dt는 실제 서버가 틱에 걸린시간
            speed_per_tick = constants.PLAYER_SPEED * dt
            self.x += dx * speed_per_tick
            self.y += dy * speed_per_tick

            # 맵 경계 처리
            self.x = max(0, min(constants.WIDTH, self.x))
            self.y = max(0, min(constants.HEIGHT, self.y))

class GoldSpot:
    def __init__(self, spot_id, x, y):
        self.spot_id = spot_id
        self.x = x
        self.y = y
        self.miner = None              # 채굴 점유자


class World:
    def __init__(self):
        self.players = {}              # player_id -> Player
        self.golds = {}                # spot_id -> GoldSpot
        self.team_gold = 0
        self.item_level = 0
        self.remain = float(constants.TIME_LIMIT)
        self.ended = False
        self.events = []               # [11/24] 이번 틱에 생긴 GOLD_MINED 등. GameServer 가 꺼내서 전송한다

    def try_start_mining(self, player):
        if player.mining_started_at is None:
            player.mining_started_at = monotonic()
            player.key_flags = 0

    def update_mining(self):
        # [11/24] 채굴 시간이 지난 플레이어의 채굴을 마무리한다. 채굴 시간은 팀 아이템 등급에 따라 5 ~ 1초.
        dig_time = ITEM_TABLE[self.item_level]['dig_time']
        now = monotonic()
        for player in self.players.values():
            if player.mining_started_at is not None and now - player.mining_started_at >= dig_time:
                self.complete_mining(player)

    def complete_mining(self, player):
        # [11/24] 채굴 완료. 가까이(MINING_RANGE 이내) 있는 금괴 중 가장 가까운 1개를 제거하고
        # 팀 금괴 +1, 개인 채굴 수 +1, GOLD_MINED 이벤트를 만든다. 근처에 금괴가 없으면 아무 일도 일어나지 않는다.
        # 성공이든 실패든 채굴 상태는 끝난다. (끝내지 않으면 이 플레이어의 입력이 계속 무시된다)
        player.mining_started_at = None
        player.state = 0
        player.key_flags = 0
        spot = self._nearest_gold(player)
        if spot is None:
            return None
        del self.golds[spot.spot_id]
        self.team_gold += 1
        player.mined += 1
        event = (spot.spot_id, player.player_id, self.team_gold)     # (금괴 번호, 채굴한 플레이어, 갱신된 팀 금괴)
        self.events.append(event)
        return event

    def _nearest_gold(self, player):
        # MINING_RANGE 이내(정확히 50px 도 포함)에서 가장 가까운 금괴. 거리가 같으면 번호가 앞선 금괴.
        nearest, nearest_dist = None, None
        for spot in self.golds.values():
            dist = ((player.x - spot.x) ** 2 + (player.y - spot.y) ** 2) ** 0.5
            if dist <= MINING_RANGE and (nearest is None or dist < nearest_dist):
                nearest, nearest_dist = spot, dist
        return nearest

    def pop_events(self):
        # [11/24] 쌓인 이벤트를 꺼내고 비운다. (GameServer.broadcast_gold_mined 가 호출)
        events, self.events = self.events, []
        return events

    def apply_input(self, dt, input_datas):
        for player_id, key_flags in input_datas.items():
            if self.players[player_id].mining_started_at is not None:
                continue
            self.players[player_id].key_flags = key_flags
            if key_flags < 16:
                self.players[player_id].move(dt)
            elif self.players[player_id].key_flags < 32:
                self.players[player_id].state = 2  # 채굴
                self.try_start_mining(self.players[player_id])
            else:
                self.players[player_id].state = 3  # 상점
    def update(self, dt, input_datas):
        # 게임 시작 후 GameServer가 매 틱 호출한다.
        # 입력을 적용한다
        self.apply_input(dt, input_datas)
        self.update_mining()            # [11/24] 채굴 시간이 끝난 플레이어는 complete_mining() 으로 마무리한다
        # 아래의 주석들을 apply_input()에서 부른다
        # 1. 플레이어 이동: 저장된 입력으로 이동하고 맵 경계를 보정한다.
        # 2. 채굴 시도
        # TODO(11/23): update_mining(dt) 연결 인듯 하지만 채굴진행도를 따로 저장하지 않기에 삭제해야 할듯
        # 3. 채굴 완료 판정: 금괴 제거, 팀 금괴/개인 채굴 수 갱신, GOLD_MINED 이벤트 생성.
        # TODO(11/24): complete_mining() 연결
        # 4. 금괴가 모두 없어지면 재생성하고 GOLD_RESPAWN 이벤트를 생성한다.
        # TODO(11/25): respawn_gold_if_empty() 연결
        # 5. 타이머 갱신과 종료 판정. 상점이 열려 있어도 시간은 흐른다.
        self.remain = max(0.0, self.remain - dt)
        if self.remain <= 0:
            self.ended = True
            # TODO(11/29): calc_result()로 최종 팀 금괴/개인 기여도 집계


    def snapshot(self):
        # [11/17] STATE 패킷에 넣을 값을 만든다. protocol.pack_state(*world.snapshot()) 로 바로 쓴다.
        # 반환 : (remain_x10, team_gold, item_level, players)  players = [(player_id, x, y, dir, state), ...]
        remain_x10 = max(0, min(65535, round(self.remain * 10)))      # 남은 시간 (0.1초 단위)
        players = [(player.player_id, int(player.x), int(player.y), player.dir, player.state)
                   for _, player in sorted(self.players.items())]     # player_id 순서로 고정
        return remain_x10, self.team_gold, self.item_level, players


if __name__ == "__main__":
    # 테스트용 코드
    world = World()
    world.players[0] = Player(0, 400.9, 299.2)
    world.players[1] = Player(1, 500, 300)
    world.players[2] = Player(2, 600, 300)
    world.update(0.4, {0: 0, 1: 0x09, 2: 0})  # 0.4초 동안 입력 적용
    for player_id, player in world.players.items():
        print(f"Player {player_id}: x={player.x}, y={player.y}, dir={player.dir}, state={player.state}")