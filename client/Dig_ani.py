from pico2d import load_image, load_wav


class Dig_ani:
    def __init__(self, x, y):
        self.image = load_image('dig_animation.png')
        self.frame = 0
        self.x, self.y = x, y
        self.frame_time = 0
        self.bgm2 = load_wav('Digdone.wav')
        self.bgm2.set_volume(30)

    def draw(self):
        self.image.clip_draw(self.frame * 25 , 0, 25, 25, self.x, self.y, 25, 25)

    def update(self):
        self.frame_time += 0.01
        if self.frame_time >= 0.1:
            self.frame = (self.frame + 1) % 2
            self.frame_time = 0
