import random
import time

from pico2d import load_image


class GoldSpot:
    image = None

    def __init__(self):
        self.x, self.y = random.randint(10, 1000), random.randint(10, 300)
        self.frame = 0
        self.frame_delay = 0.3
        self.last_update_time = time.time()
        if GoldSpot.image == None:
            GoldSpot.image = load_image('GoldSpot.png')

    def update(self):
        current_time = time.time()
        if current_time - self.last_update_time >= self.frame_delay:
            self.frame = (self.frame + 1) % 4
            self.last_update_time = current_time

    def draw(self):
        self.image.clip_draw(self.frame * 190, 0, 190, 244, self.x, self.y, 25, 25)


