"""서버가 관리하는 게임 데이터"""
import os
import sys
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

class Player:
    def __init__(self, player_id, x, y):
        self.player_id = player_id     # 0 빨강 / 1 파랑 / 2 초록
        self.x = float(x)
        self.y = float(y)
        self.dir = 0                   # 대각 방향도 처리해야하니 0~7까지 8방향으로 처리
        self.state = 0                 # 0 대기 / 1 이동 / 2 채굴
        self.key_flags = 0
        self.mined = 0                 # 개인별 채굴 수
    def move(self, dt):
        pass

class GoldSpot:
    def __init__(self, spot_id, x, y):
        self.spot_id = spot_id
        self.x = x
        self.y = y
        self.miner = None              # 채굴 점유자

def apply_input(players, input_data):
    for player_id, key_flags in input_data.items():
        player = players[player_id]
        player.key_flags = key_flags
        if key_flags == 0:
            player.state = 0  # 대기
        else:
            player.state = 1  # 이동
            dx, dy = 0, 0
            if key_flags & 0x01:  # 위
                dy -= 1
            if key_flags & 0x02:  # 아래
                dy += 1
            if key_flags & 0x04:  # 왼쪽
                dx -= 1
            if key_flags & 0x08:  # 오른쪽
                dx += 1

            # 방향 설정 (0~7)
            if dx == -1 and dy == -1:
                player.dir = 7  # 왼쪽 위
            elif dx == -1 and dy == 0:
                player.dir = 6  # 왼쪽
            elif dx == -1 and dy == 1:
                player.dir = 5  # 왼쪽 아래
            elif dx == 0 and dy == -1:
                player.dir = 0  # 위
            elif dx == 0 and dy == 1:
                player.dir = 4  # 아래
            elif dx == 1 and dy == -1:
                player.dir = 1  # 오른쪽 위
            elif dx == 1 and dy == 0:
                player.dir = 2  # 오른쪽
            elif dx == 1 and dy == 1:
                player.dir = 3  # 오른쪽 아래

            # 이동 속도 적용 (초당 픽셀 이동량)
            speed_per_tick = constants.PLAYER_SPEED * constants.TICK_RATE
            player.x += dx * speed_per_tick
            player.y += dy * speed_per_tick

            # 맵 경계 처리
            player.x = max(0, min(constants.WIDTH, player.x))
            player.y = max(0, min(constants.HEIGHT, player.y))


class World:
    def __init__(self):
        self.players = {}              # player_id -> Player
        self.golds = {}                # spot_id -> GoldSpot
        self.team_gold = 0
        self.item_level = 0
        self.remain = float(constants.TIME_LIMIT)
        self.ended = False

    def update(self, dt):
        # 게임 시작 후 GameServer가 매 틱 호출한다.
        if dt <= 0 or self.ended:
            return
        dt = min(dt, max(0.0, self.remain))

        # 1. 플레이어 이동: 저장된 입력으로 이동하고 맵 경계를 보정한다.
        for player in self.players.values():
            if dt > 0:
                player.move(dt)

        # 2. 채굴 시도
        # TODO(11/22): try_start_mining() 연결
        # TODO(11/23): update_mining(dt) 연결 인듯 하지만 채굴진행도를 따로 저장하지 않기에 삭제해야 할듯?

        # 3. 채굴 완료 판정: 금괴 제거, 팀 금괴/개인 채굴 수 갱신, GOLD_MINED 이벤트 생성.
        # TODO(11/24): complete_mining() 연결

        # 4. 금괴가 모두 없어지면 재생성하고 GOLD_RESPAWN 이벤트를 생성한다.
        # TODO(11/25): respawn_gold_if_empty() 연결

        # 5. 타이머 갱신과 종료 판정. 상점이 열려 있어도 시간은 흐른다.
        self.remain = max(0.0, self.remain - dt)
        if self.remain <= 0:
            self.ended = True
            # TODO(11/29): calc_result()로 최종 팀 금괴/개인 기여도 집계



if __name__ == "__main__":
    # 테스트용 코드
    players = {
        0: Player(0, 400, 300),
        1: Player(1, 500, 300),
        2: Player(2, 600, 300),
    }
    input_data = {
        0: 0x05,  # Player 0: 위 + 왼쪽 대각 이동
        1: 0x02,  # Player 1: 아래 이동
        2: 0x00,  # Player 2: 이동 없음
    }
    apply_input(players, input_data)
    for player_id, player in players.items():
        print(f"Player {player_id}: x={player.x}, y={player.y}, dir={player.dir}, state={player.state}")