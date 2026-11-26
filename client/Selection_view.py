from pico2d import load_image

# id 1 = x 250, y 354
# id 2 = x 250, y 164
# id 3 = x 750, y 354
# id 4 = x 750, y 164
class Selection:
    def __init__(self):
        self.x, self.y = 250, 354
        self.frame = 0
        self.image = load_image('Selection.png')

    def update(self):
        pass

    def draw(self):
        self.image.clip_draw(self.frame * 614, 0, 614, 211, self.x, self.y, 461, 170)

    def move(self, item_id):
        if item_id == 1:
            self.x = 250
            self.y = 354
        elif item_id == 2:
            self.x = 250
            self.y = 164
        elif item_id == 3:
            self.x = 750
            self.y = 354
        elif item_id == 4:
            self.x = 750
            self.y = 164