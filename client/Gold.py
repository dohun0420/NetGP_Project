from pico2d import load_image, load_font


class Gold:
    def __init__(self):
        self.image = load_image('Gold.png')
        self.font = load_font('arial.ttf', 24)
        self.count = 0

    def draw(self):
        self.image.draw(160, 543, 100, 70)
        self.font.draw(185, 543, f'X {self.count}', (0, 0, 0))

    def draw_count_only(self):
        self.font.draw(120, 510, f'X {self.count}', (0, 0, 0))

    def increase(self):
        self.count += 1

    def update(self):
        pass
