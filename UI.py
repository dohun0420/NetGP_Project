from pico2d import load_image


class UI:
    def __init__(self):
        self.image = load_image('UI.png')

    def draw(self):
        self.image.draw(156, 543, 313, 114)

    def update(self):
        pass