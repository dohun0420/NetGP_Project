# [11/17] HUD 검증 : 실제 Pico2D 없이 "가짜 pico2d" 로 어떤 그림/글자를 어느 위치에 그리는지만 확인한다.
# (화면에 실제로 보이는 모습은 게임을 실행해서 눈으로 확인해야 한다)
import sys, types

calls = []                                                   # (종류, 이미지/폰트 이름, 인자...)
class FakeImage:
    def __init__(self, name): self.name = name
    def draw(self, *a): calls.append(("draw", self.name) + a)
    def clip_draw(self, *a): calls.append(("clip_draw", self.name) + a)
class FakeFont:
    def __init__(self, size): self.size = size
    def draw(self, x, y, text, color): calls.append(("text", self.size, x, y, text, color))
fake = types.ModuleType("pico2d")
fake.load_image = FakeImage
fake.load_font = lambda path, size: FakeFont(size)
sys.modules["pico2d"] = fake

from client.hud import HUD

def draw(team_gold, remain_x10, item_level):
    calls.clear()
    hud.draw(team_gold, remain_x10, item_level)
    return list(calls)

hud = HUD()

# 1) 처음 상태 : 금괴 0, 180초, 아이템 없음
c = draw(0, 1800, 0)
assert ("draw", "UI.png", 156, 543, 313, 114) in c
assert ("draw", "Gold.png", 160, 543, 100, 70) in c
assert ("text", 24, 185, 543, "X 0", (0, 0, 0)) in c
assert ("text", 30, 925, 560, "180", (255, 255, 255)) in c
assert ("draw", "Timer.png", 900, 560, 100, 100) in c
assert not [x for x in c if x[0] == "clip_draw"]              # 아이템 아이콘 없음
print("1) 시작 화면 OK : 틀 / 금괴 X 0 / 타이머 180 / 아이템 없음")

# 2) 금괴 수와 아이템 등급이 값대로 바뀌는가
for level, image in ((1, "Glove.png"), (2, "Shovel.png"), (3, "Pickaxe.png"), (4, "Drill.png")):
    c = draw(12, 900, level)
    assert ("clip_draw", image, 0, 0, 980, 980, 55, 543, 60, 60) in c, level
    assert len([x for x in c if x[0] == "clip_draw"]) == 1       # 보유 아이템 하나만
    assert ("text", 24, 185, 543, "X 12", (0, 0, 0)) in c
print("2) 아이템 OK : 등급 1~4 에 맞는 아이콘 1개, 금괴 수 X 12")

# 3) 남은 시간 표시 (올림) : 1800 -> 180, 1795 -> 180, 1791 -> 180, 1790 -> 179, 10 -> 1, 1 -> 1, 0 -> 0
for x10, shown in ((1800, "180"), (1795, "180"), (1791, "180"), (1790, "179"), (600, "60"), (10, "1"), (1, "1"), (0, "0")):
    c = draw(0, x10, 0)
    assert ("text", 30, 925, 560, shown, (255, 255, 255)) in c, (x10, shown)
print("3) 타이머 OK : 소수점은 올림, 0 은 시간이 끝났을 때만")

# 4) 이상한 아이템 등급이 와도 죽지 않는가 (아이콘만 생략)
c = draw(3, 500, 9)
assert not [x for x in c if x[0] == "clip_draw"]
print("4) 방어 OK : 알 수 없는 아이템 등급은 그리지 않음")

# 5) 이미지는 시작할 때 한 번만 로딩하고 draw 에서는 다시 로딩하지 않는가
import client.hud as hud_module
loaded = []
hud_module.load_image = lambda name: (loaded.append(name), FakeImage(name))[1]   # hud.py 안의 load_image 를 교체
hud2 = HUD(); n = len(loaded)
for _ in range(100): hud2.draw(1, 1000, 3)
assert len(loaded) == n and n == 3 + 4
print(f"5) 로딩 OK : 시작할 때 이미지 {n}장만 로딩, 매 프레임 로딩 없음")

print("\n전부 통과")