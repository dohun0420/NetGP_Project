from pico2d import load_image


class Selection:
    def __init__(self):
        self.x, self.y = 250, 354
        self.frame = 0
        self.image = load_image('Selection.png')

    def update(self):
        pass

    def draw(self):
        self.image.clip_draw(self.frame * 614, 0, 614, 211, self.x, self.y, 461, 170)

    def move(self, dir_x, dir_y):
        self.x = min(max(self.x + dir_x, 250), 750)
        self.y = min(max(self.y + dir_y, 164), 354)
