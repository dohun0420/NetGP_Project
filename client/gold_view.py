import time

from pico2d import load_image

FRAME_COUNT = 4
FRAME_DELAY = 0.3           # 초. 금괴가 반짝이는 프레임이 바뀌는 간격 (기존 GoldSpot 과 같다)


class GoldView:
    # 금괴 "그리기" 전용 클래스. 금괴를 어디에 만들지는 정하지 않는다. (위치는 서버가 정해서 보내 준다)
    # 위치 목록은 밖(ClientWorld.golds)에서 받아서 그린다. 반짝이는 프레임은 모든 금괴가 함께 바뀐다.
    def __init__(self):
        self.image = load_image('GoldSpot.png')     # 이미지는 한 번만 로딩해서 모든 금괴가 같이 쓴다
        self.frame = 0
        self.last_update_time = time.time()

    def update(self):
        # 반짝이는 애니메이션 프레임만 진행한다. 매 프레임 호출한다.
        now = time.time()
        if now - self.last_update_time >= FRAME_DELAY:
            self.frame = (self.frame + 1) % FRAME_COUNT
            self.last_update_time = now

    def draw(self, golds):
        # golds : {spot_id: {'x': x, 'y': y}}  (ClientWorld.golds 와 같은 모양)
        for gold in golds.values():
            self.image.clip_draw(self.frame * 190, 0, 190, 244, gold['x'], gold['y'], 25, 25)