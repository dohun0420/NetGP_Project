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

    def apply_world_message(self, name, payload):
        # inbox에는 월드, 로비, 오류 등 여러 종류의 수신 메시지가 도착 순서대로 쌓인다.
        # 메인 스레드가 poll()로 꺼낸 메시지 중 GAME_START와 STATE만 ClientWorld에 반영한다.
        # name은 메시지 종류이고, 이 두 메시지의 payload는 헤더를 제외한 본문 바이트다.
        from common import protocol

        if name == 'StoC_GAME_START':
            # 게임 시작 시 제한 시간, 가격표, 플레이어 시작 위치와 금괴 배치를 설정한다.
            self.init_from_start(*protocol.unpack_game_start(payload))
        elif name == 'StoC_STATE':
            # 플레이 중에는 서버가 보낸 최신 값으로 플레이어와 HUD에 표시할 데이터를 갱신한다.
            remain_x10, team_gold, item_level, players = protocol.unpack_state(payload)
            self.players = {
                player_id: {'x': x, 'y': y, 'dir': direction, 'state': state}
                for player_id, x, y, direction, state in players
            }
            self.remain_x10 = remain_x10
            self.team_gold = team_gold
            self.item_level = item_level
