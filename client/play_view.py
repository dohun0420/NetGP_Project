from gold_view import GoldView
from hud import HUD
from map_view import MapView
from player_view import PlayerView
from Selection_view import Selection
from Store import Store

def facing_from_dir(direction):
    # dir : 0 아래 / 1 왼쪽 / 2 오른쪽 / 3 위
    if direction == 1:
        return 'a'
    elif direction == 2:
        return 'd'
    elif direction == 3:
        return 'w'
    else:
        return 's'


class PlayView:
    # 플레이 화면 하나를 그린다. 서버가 보낸 값을 담은 ClientWorld 를 받아서
    # 배경 -> 금괴 -> 플레이어 3명 -> HUD 순서로 그리기만 한다. (이동 · 채굴 · 시간 계산은 서버가 한다)
    def __init__(self):
        self.map = MapView()
        self.golds = GoldView()
        self.hud = HUD()
        self.players = {}                   # player_id -> PlayerView (처음 나왔을 때 만든다)
        self.selection = Selection()
        self.store = Store()

    def _player_view(self, player_id):
        if player_id not in self.players:
            self.players[player_id] = PlayerView(player_id)
        return self.players[player_id]

    def update(self, world):
        # 매 프레임 호출 : 서버 값을 PlayerView 에 넣고, 애니메이션 프레임을 진행한다.
        if world.store_mode:
            self.selection.move(world.selection)
        else:
            for player_id, data in world.players.items():
                view = self._player_view(player_id)
                view.set_state(
                    data['x'], data['y'], facing_from_dir(data['dir']),
                    moving=data['state'] == 1,
                    mining=data['state'] == 2,
                )
                view.update()

    def draw(self, world):
        if world.store_mode:
            self.store.draw()
            self.selection.draw()
            self.hud.draw_count_only(world.team_gold)  # 상점 모드에서는 gold count 만 그린다.
        else:
            self.map.draw()
            self.golds.draw(world.golds)
            # 화면 위쪽(y 가 큰 쪽)이 먼저 그려져야 아래쪽 캐릭터가 위에 겹쳐 보인다.
            for view in sorted(self.players.values(), key=lambda v: -v.y):
                view.draw()
            self.hud.draw(world.team_gold, world.remain_x10, world.item_level)