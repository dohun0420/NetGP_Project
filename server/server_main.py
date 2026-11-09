import socket

from common.constants import PORT
from server.session import ClientSession

#'0.0.0.0' = INADDR_ANY
def main(host='0.0.0.0', port=PORT):
    sessions = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((host, port))
        server_sock.listen()

        try:
            while True:
                client_sock, _ = server_sock.accept()
                sessions.append(ClientSession(client_sock))
        finally:
            # 예외로 루프가 끝나도 연결 소켓을 정리한다
            for session in sessions:
                session.close()


if __name__ == '__main__':
    main()
