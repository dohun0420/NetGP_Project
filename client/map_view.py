from pico2d import load_image


class MapView:
    # 배경 그리기 전용 클래스. (기존 Map 은 만들 때 배경음악도 같이 재생했는데, 음악은 bgm.py 로 분리했다)
    def __init__(self):
        self.image = load_image('map.png')

    def draw(self):
        self.image.draw(500, 300, 1000, 600)