# client 진입점 정의
import network_client
import world_view
import pico2d
import play_view
import time
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common.constants import PORT, WIDTH, HEIGHT
from common import protocol

# 본문은 render 시험은 world_view.py에서 수행한다. (world_view.py는 단독으로 실행 가능)
def main():
    client = network_client.NetworkClient()
    world = world_view.ClientWorld()
    pico2d.open_canvas(WIDTH, HEIGHT)
    render = play_view.PlayView()
    if client.connect(network_client.title(), PORT) and client.connect_udp(PORT - 1):
        '''
        # 서버로부터 게임 시작 패킷을 받았다고 가정하고 world를 초기화한다. (실제 게임에서는 서버에서 패킷을 받아서 world를 초기화한다)
        '임의의 테스트 값'

        name = 'StoC_GAME_START'
        time_limit = 180
        costs = (10, 14, 24, 40)
        players = [(0, 100, 200), (1, 100, 100), (2, 900, 400)]
        gold_count = 3
        golds = [(7, 1000, 1), (8, 100, 200), (9, 300, 400)]
        value = (time_limit, costs, players, gold_count, golds)
        msgs = [(name, value)]
        '''
        while True:
            msgs = client.poll()
            for name, value in msgs:
                world.apply_world_message(name, value)
            if world.running:
                events = pico2d.get_events()
                client.play_state(events)
                last_frame_time = time.monotonic()
                dt = time.monotonic() - last_frame_time
                world.update(dt)
                render.update(world)
                pico2d.clear_canvas()
                render.draw(world)
                pico2d.update_canvas()
                pico2d.delay(0.01)
            #msgs = client.poll()  # 테스트시 위의 같은 코드를 주석처리 하고 해당 코드를 활성화
if __name__ == '__main__':
    main()