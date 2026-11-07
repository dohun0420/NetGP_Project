"""서버가 관리하는 게임 데이터"""

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
        self.dir = 0                   # 0 아래 / 1 왼쪽 / 2 오른쪽 / 3 위
        self.state = 0                 # 0 대기 / 1 이동 / 2 채굴
        self.key_flags = 0
        self.mined = 0                 # 개인별 채굴 수

class GoldSpot:
    def __init__(self, spot_id, x, y):
        self.spot_id = spot_id
        self.x = x
        self.y = y
        self.miner = None              # 채굴 점유자
