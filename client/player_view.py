from pico2d import load_image
from sdl2 import SDL_GetError, SDL_SetTextureColorMod

from Dig_ani import Dig_ani

# 서버의 player_id에 대응하는 색상: 0 빨강 / 1 파랑 / 2 초록
PLAYER_COLORS = ((255, 70, 70), (40, 50, 255), (70, 255, 70))

# 바라보는 방향 -> (스프라이트 시트에서 잘라낼 y, 잘라낼 높이, 화면에 그릴 폭, 화면에 그릴 높이)
# 's' 아래 / 'w' 위 / 'd' 오른쪽 / 'a' 왼쪽.  잘라낼 폭은 모두 33, 프레임은 3장(0~2)이다.
SPRITES = {
    's': (130, 56, 90, 80),
    'w': (86, 46, 90, 90),
    'd': (45, 48, 90, 100),
    'a': (0, 57, 90, 100),
}
FRAME_WIDTH = 33
FRAME_COUNT = 3
FRAME_DELAY = 10            # 걷는 동안 update() 를 10번 부를 때마다 다음 프레임


class PlayerView:
    # 플레이어 "그리기" 전용 클래스. 입력 처리와 이동 계산은 하지 않는다. (이동은 서버가 계산한다)
    # 위치 · 방향 · 이동과 채굴 상태는 밖(서버가 보낸 STATE)에서 받아서 그린다.
    def __init__(self, player_id=0):
        if player_id not in (0, 1, 2):
            raise ValueError('player_id는 0, 1, 2 중 하나여야 합니다.')
        self.player_id = player_id
        # 플레이어마다 별도 이미지를 로딩해 자신의 색상만 적용한다. (이미지를 같이 쓰면 색이 서로 덮어써진다)
        self.image = load_image('Player.png')
        if SDL_SetTextureColorMod(self.image.texture, *PLAYER_COLORS[player_id]) != 0:
            raise RuntimeError('색상 적용 실패: ' + SDL_GetError().decode('utf-8'))
        self.x, self.y = 400, 300
        self.facing = 's'
        self.moving = False
        self.frame = 0
        self.frame_timer = 0
        self.dig_animation = None

    def set_state(self, x, y, facing, moving, *, mining=False):
        # 그릴 값을 바꾼다. (나중에 서버의 STATE 를 받아서 이 함수로 넘긴다)
        self.x, self.y = x, y
        self.facing = facing
        self.moving = moving
        if not mining:
            self.dig_animation = None
        elif self.dig_animation is None:
            self.dig_animation = Dig_ani(x, y + 40)
        else:
            self.dig_animation.x, self.dig_animation.y = x, y + 40

    def update(self):
        # 이동 중에는 걷는 프레임을, 채굴 중에는 채굴 효과를 진행한다.
        if self.moving:
            self.frame_timer += 1
            if self.frame_timer % FRAME_DELAY == 0:
                self.frame = (self.frame + 1) % FRAME_COUNT
        if self.dig_animation is not None:
            self.dig_animation.update()

    def draw(self):
        self.draw_at(self.x, self.y, self.facing, self.frame)
        if self.dig_animation is not None:
            self.dig_animation.draw()

    def draw_at(self, x, y, facing, frame):
        # 값을 받아서 그리기만 하는 가장 기본 함수. (기존 Player.draw 와 같은 모양으로 그린다)
        sprite = SPRITES.get(facing)
        if sprite is None:
            return
        src_y, src_h, dst_w, dst_h = sprite
        self.image.clip_draw(frame * FRAME_WIDTH, src_y, FRAME_WIDTH, src_h, x, y, dst_w, dst_h)