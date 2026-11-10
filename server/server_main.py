import queue
import socket

from common.constants import PORT
from server.session import ClientSession

#'0.0.0.0' = INADDR_ANY
def main(host='0.0.0.0', port=PORT, event_queue=None):
    # 수신 스레드들이 이벤트를 넣는 큐. 게임 루프(GameServer)가 여기서 꺼내 처리한다.
    if event_queue is None:
        event_queue = queue.Queue()
    sessions = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((host, port))
        server_sock.listen()

        try:
            while True:
                client_sock, _ = server_sock.accept()
                session = ClientSession(client_sock, event_queue)
                sessions.append(session)
                session.start()         # EV_JOIN 을 큐에 넣고 수신 스레드를 시작한다
        finally:
            # 예외로 루프가 끝나도 연결 소켓을 정리한다
            for session in sessions:
                session.close()


if __name__ == '__main__':
    main()