from gold_view import GoldView
from hud import HUD
from map_view import MapView
from player_view import PlayerView


def facing_from_dir(direction):
    # [임시] 서버 STATE 의 dir(0~7, 서버 world.py 기준) -> 스프라이트 방향('s' 아래 / 'w' 위 / 'd' 오른쪽 / 'a' 왼쪽).
    # 0 위 / 1 오른쪽 위 / 2 오른쪽 / 3 오른쪽 아래 / 4 아래 / 5 왼쪽 아래 / 6 왼쪽 / 7 왼쪽 위.
    # 스프라이트가 4방향뿐이라 대각선은 좌우 그림을 쓴다. dir 의 의미(4방향/8방향)가 확정되면 이 표만 고친다.
    return {0: 'w', 1: 'd', 2: 'd', 3: 'd', 4: 's', 5: 'a', 6: 'a', 7: 'a'}.get(direction, 's')


class PlayView:
    # 플레이 화면 하나를 그린다. 서버가 보낸 값을 담은 ClientWorld 를 받아서
    # 배경 -> 금괴 -> 플레이어 3명 -> HUD 순서로 그리기만 한다. (이동 · 채굴 · 시간 계산은 서버가 한다)
    def __init__(self):
        self.map = MapView()
        self.golds = GoldView()
        self.hud = HUD()
        self.players = {}                   # player_id -> PlayerView (처음 나왔을 때 만든다)

    def _player_view(self, player_id):
        if player_id not in self.players:
            self.players[player_id] = PlayerView(player_id)
        return self.players[player_id]

    def update(self, world):
        # 매 프레임 호출 : 서버 값을 PlayerView 에 넣고, 애니메이션 프레임을 진행한다.
        self.golds.update()
        for player_id, data in world.players.items():
            view = self._player_view(player_id)
            view.set_state(
                data['x'], data['y'], facing_from_dir(data['dir']),
                moving=data['state'] == 1,
                mining=data['state'] == 2,
            )
            view.update()

    def draw(self, world):
        self.map.draw()
        self.golds.draw(world.golds)
        # 화면 위쪽(y 가 큰 쪽)이 먼저 그려져야 아래쪽 캐릭터가 위에 겹쳐 보인다.
        for view in sorted(self.players.values(), key=lambda v: -v.y):
            view.draw()
        self.hud.draw(world.team_gold, world.remain_x10, world.item_level)