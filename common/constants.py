# 포트, 맵크기, 속도, 틱 주기, 게임 제한 시간, 아이템 별 채굴시간, 비용의 상수 정의

# 포트
PORT = 5000
# 맵 크기
WIDTH = 1000
HEIGHT = 600
# 플레이어의 속도 기존 클라처리에서는 프레임 당 2 픽셀이동에 초당 60프레임 120픽셀 이동
PLAYER_SPEED = 120  # 픽셀/초

# 틱 주기 (초) 서버는 20HZ 주기로 업데이트 해서 클라이언트에 전송
TICK_RATE = 1 / 20

# 게임 제한 시간 (초)
TIME_LIMIT = 180

# 아이템 별 채굴 시간 (초)
DIG_TIME = {
    'hand': 5,
    'glove': 4,
    'shovel': 3,
    'pickaxe': 2,
    'drill': 1
}

# 아이템 별 비용
ITEM_COST = {
    'hand': 0,
    'glove': 5,
    'shovel': 7,
    'pickaxe': 12,
    'drill': 20
}
