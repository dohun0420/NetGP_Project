"""클라이언트가 화면에 표시할 서버의 게임 데이터"""


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
            player_id: {'x': float(x), 'y': float(y), 'dir': 0, 'state': 0}
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
