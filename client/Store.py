from pico2d import load_image, load_music


class Store:
    def __init__(self):
        self.image = load_image('Store.png')


    def draw(self):
        self.image.draw(500, 300, 1000, 600)

    def update(self):
        pass

