
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from common.constants import GOLD_SPOT_COUNT, WIDTH, HEIGHT
import random



def generate_gold_spots(count=GOLD_SPOT_COUNT, map_width=WIDTH, map_height=HEIGHT):
    # 랜덤한 위치에 금광을 생성한다.
    spots = []
    for spot_id in range(count):
        x = random.randint(0, map_width - 1)
        y = random.randint(0, map_height - 1)
        spots.append((spot_id, x, y))
    return spots
if __name__ == "__main__":
    spots = generate_gold_spots()
    for spot in spots:
        print(f"Spot ID: {spot[0]}, X: {spot[1]}, Y: {spot[2]}")