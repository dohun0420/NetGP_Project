from pico2d import load_image


class Happy:
    def __init__(self, x, y):
        self.image = load_image('Happy.png')
        self.x, self.y = x, y
        self.frame = 0

    def draw(self):
        self.image.clip_draw(self.frame * 500 , 0, 500, 500, self.x, self.y, 25, 25)

    def update(self):
        pass
