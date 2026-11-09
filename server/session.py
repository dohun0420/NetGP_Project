from common.net_utils import send_packet


class ClientSession:

    def __init__(self, sock):
        self.sock = sock
        # 송신이 오래 막히지 않도록 제한한다. 추후 recv()에도 같은 제한이 적용된다.
        self.sock.settimeout(2.0)

    def send(self, packet):
        send_packet(self.sock, packet)

    def close(self):
        self.sock.close()
