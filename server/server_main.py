import queue
import socket
import threading


import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common.constants import PORT
from server.game_server import GameServer
from server.session import ClientSession

#'0.0.0.0' = INADDR_ANY
def main(host='0.0.0.0', port=PORT, game_server=None):
    if game_server is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        game_server = GameServer(queue.Queue(), udp_socket=sock)  # UDP 소켓을 만들어서 게임 서버에 넘긴다
    event_queue = game_server.event_queue       # 수신 스레드들이 이벤트를 넣는 큐 (게임 루프가 꺼내 처리)
    sessions = []

    # 게임 루프는 별도 스레드에서 돌린다. 이 스레드(메인)는 accept 만 담당한다.
    threading.Thread(target=game_server.run, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((host, port))
        server_sock.listen()
        adress, port = server_sock.getsockname()
        print(f"서버 시작 : {adress}:{port})")
        try:
            while True:
                client_sock, _ = server_sock.accept()
                session = ClientSession(client_sock, event_queue)
                sessions.append(session)
                session.start()         # EV_JOIN 을 큐에 넣고 수신 스레드를 시작한다
        finally:
            # 예외로 루프가 끝나도 게임 루프와 연결 소켓을 정리한다
            game_server.stop()
            for session in sessions:
                session.close()


if __name__ == '__main__':
    main()