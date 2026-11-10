import queue
import socket

from common.constants import PORT
from server.session import ClientSession


# '0.0.0.0' = INADDR_ANY
def main(host='0.0.0.0', port=PORT, event_queue=None):
    # 수신 스레드들이 이벤트를 넣는 큐. 게임 루프(GameServer)가 여기서 꺼내 처리한다.
    if event_queue is None:
        event_queue = queue.Queue()
    sessions = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        # 소켓 재사용 옵션 추가 (서버 재시작 시 Address already in use 에러 방지)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen()

        try:
            while True:
                client_sock, _ = server_sock.accept()

                sessions = [s for s in sessions if not s.is_closed()]

                session = ClientSession(client_sock, event_queue)
                sessions.append(session)
                session.start()  # EV_JOIN 을 큐에 넣고 수신 스레드를 시작한다
        finally:
            # 예외 또는 서버 종료 시 모든 소켓 자원 정리
            for session in sessions:
                session.close()


if __name__ == '__main__':
    main()