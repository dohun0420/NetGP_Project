from pico2d import load_image, load_font

# 기존 UI.py(틀) / Gold.py(금괴 아이콘 + 수) / Items.py(보유 아이템) / Timer.py(타이머) 의 "그리기" 부분을 하나로 합친 것.
# 값(팀 금괴, 남은 시간, 아이템 등급)은 서버가 보낸 값을 그대로 그린다. (계산과 타이머 진행은 서버가 한다)
# 그리는 위치와 크기는 기존 게임과 같다.

# 아이템 등급 -> 이미지 (0 은 아이템 없음)
ITEM_IMAGES = {1: 'Glove.png', 2: 'Shovel.png', 3: 'Pickaxe.png', 4: 'Drill.png'}


class HUD:
    def __init__(self):
        self.frame_image = load_image('UI.png')
        self.gold_image = load_image('Gold.png')
        self.timer_image = load_image('Timer.png')
        self.item_images = {level: load_image(name) for level, name in ITEM_IMAGES.items()}  # 한 번만 로딩
        self.gold_font = load_font('arial.ttf', 24)
        self.timer_font = load_font('arial.ttf', 30)

    def draw(self, team_gold, remain_x10, item_level):
        # team_gold : 팀 금괴 수 / remain_x10 : 남은 시간(0.1초 단위, STATE 와 같다) / item_level : 팀 아이템 등급(0~4)
        # 좌측 상단 : 틀, 금괴 아이콘과 수, 보유 아이템
        self.frame_image.draw(156, 543, 313, 114)
        self.gold_image.draw(160, 543, 100, 70)
        self.gold_font.draw(185, 543, f'X {team_gold}', (0, 0, 0))
        item_image = self.item_images.get(item_level)        # 0 이거나 모르는 등급이면 아이템을 그리지 않는다
        if item_image:
            item_image.clip_draw(0, 0, 980, 980, 55, 543, 60, 60)

        # 우측 상단 : 타이머 (남은 시간을 초 단위로, 소수점은 올림 -> 0 은 시간이 끝났을 때만 나온다)
        remain_sec = (remain_x10 + 9) // 10
        self.timer_image.draw(900, 560, 100, 100)
        self.timer_font.draw(925, 560, f'{remain_sec}', (255, 255, 255))
    def draw_count_only(self, team_gold):       # 기존 gold count 만 그리는 용도 (상점 모드에서만 사용)
        self.gold_font.draw(120, 510, f'X {team_gold}', (0, 0, 0))