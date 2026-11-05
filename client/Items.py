from pico2d import load_image


class Items:
    def __init__(self):
        self.x, self.y = 55, 543
        self.own_item = 0
        self.frame = 0
        self.image = None
        self.update_image()

    def update_image(self):
        if self.own_item == 1:
            self.image = load_image('Glove.png')
        elif self.own_item == 2:
            self.image = load_image('Shovel.png')
        elif self.own_item == 3:
            self.image = load_image('Pickaxe.png')
        elif self.own_item == 4:
            self.image = load_image('Drill.png')
        else:
            self.image = None

    def set_item(self, item_number):
        self.own_item = item_number
        self.update_image()

    def update(self):
        pass

    def draw(self):
        if self.image:
            self.image.clip_draw(self.frame, 0, 980, 980, self.x, self.y, 60, 60)
