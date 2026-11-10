from pico2d import load_image


class Sad:
    def __init__(self, x, y):
        self.image = load_image('Sad.png')
        self.x, self.y = x, y
        self.frame = 0

    def draw(self):
        self.image.clip_draw(self.frame * 225 , 0, 225, 225, self.x, self.y, 25, 25)

    def update(self):
        pass
