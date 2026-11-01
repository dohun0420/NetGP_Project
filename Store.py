from pico2d import load_image, load_music


class Store:
    def __init__(self):
        self.image = load_image('Store.png')
        self.bgm = load_music("Store.mp3")
        self.bgm.set_volume(32)
        self.bgm.repeat_play()


    def draw(self):
        self.image.draw(500, 300, 1000, 600)

    def update(self):
        pass

