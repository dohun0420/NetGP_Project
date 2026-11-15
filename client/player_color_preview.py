"""3색 테스트 미리보기 전용 파일. 현재 실제 게임 코드에는 연결되어 있지 않다.

실제 게임에 재사용할 부분은 COLORS와 아래의 이미지 로딩·색상 적용 부분이다.
직접 실행하면 미리보기 창이 열리며, ESC로 종료한다.
"""
from pathlib import Path

from pico2d import (
    clear_canvas, close_canvas, delay, get_events, load_image,
    open_canvas, update_canvas,
)
from sdl2 import (
    SDL_GetError, SDL_KEYDOWN, SDL_QUIT, SDL_SetTextureColorMod, SDLK_ESCAPE,
)

# [게임에 재사용할 코드] 플레이어별 색상 설정: 빨강 / 파랑 / 초록
COLORS = ((255, 70, 70), (40, 50, 255), (70, 255, 70))


def main():
    # [테스트 전용] 미리보기 창 생성
    open_canvas(1000, 600)
    try:
        # [게임에 재사용할 코드 시작] 이미지 로딩 및 색상 적용
        # 캔버스가 열린 뒤 실행해야 하며, 색상마다 별도 이미지를 로딩한다.
        image_path = str(Path(__file__).resolve().with_name('Player.png'))
        images = []
        for color in COLORS:
            image = load_image(image_path)
            if SDL_SetTextureColorMod(image.texture, *color) != 0:
                raise RuntimeError('색상 적용 실패: ' + SDL_GetError().decode('utf-8'))
            images.append(image)
        # [게임에 재사용할 코드 끝]

        # [이 아래는 모두 테스트 전용] 종료 입력 처리 및 3색 나란히 표시
        running = True
        while running:
            for event in get_events():
                if event.type == SDL_QUIT or (
                    event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE
                ):
                    running = False

            clear_canvas()
            for index, image in enumerate(images):
                # 원본 3열·4행 시트에서 정면 첫 프레임만 표시한다.
                width, height = image.w // 3, image.h // 4
                image.clip_draw(
                    0, image.h - height, width, height,
                    250 + index * 250, 300, 90, 110,
                )
            update_canvas()
            delay(0.01)
    finally:
        close_canvas()


# [테스트 전용] 직접 실행할 때만 미리보기 실행 (import 시 실행되지 않음)
if __name__ == '__main__':
    main()
