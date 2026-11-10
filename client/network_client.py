import queue
import socket
import threading

from common import protocol
from common.constants import PORT
from common.net_utils import PacketBuffer, send_packet

DISCONNECTED = 'DISCONNECTED'       # 연결이 끊겼을 때 inbox 에 들어가는 메시지 이름

# 패킷 종류 번호 -> 이름 (ex. 101 -> "StoC_JOIN_OK")
PACKET_NAMES = {number: name for name, number in protocol.packet_types.items()}

# 패킷 종류 -> 본문을 값으로 바꾸는 함수.
# 아직 함수가 없는 패킷(GAME_START, STATE 등)은 본문 바이트(bytes)를 그대로 inbox 에 넣는다.
# 해당 unpack 함수가 만들어지면 여기에 한 줄씩 추가한다.
DECODERS = {
    protocol.packet_types["StoC_JOIN_OK"]: protocol.unpack_join_ok,
    protocol.packet_types["StoC_LOBBY_STATE"]: protocol.unpack_lobby_state,
    protocol.packet_types["StoC_ERROR"]: protocol.unpack_error,
}


class NetworkClient:

    def __init__(self):
        self.sock = None
        self.inbox = queue.Queue()      # 수신 스레드 -> 메인 스레드. 항목 : (이름, 값)
        self.running = False
        self.last_error = ''
        self._thread = None

    def connect(self, ip, port=PORT):
        # 서버에 접속하고 수신 스레드를 시작한다. 성공 True / 실패 False (사유는 last_error).
        try:
            sock = socket.create_connection((ip, port), timeout=3.0)
        except OSError as e:
            self.last_error = f'서버에 접속할 수 없습니다. ({e})'
            return False
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # 작은 패킷이 지연되지 않게
        sock.settimeout(0.5)            # recv 가 0.5초마다 깨어나 종료 요청(running)을 확인한다
        self.sock = sock
        self.running = True
        self._thread = threading.Thread(target=self.recv_loop, daemon=True)
        self._thread.start()
        return True

    def recv_loop(self):
        # 수신 스레드 : recv() -> PacketBuffer 로 조립 -> 값으로 해석해서 inbox 에 넣는다.
        buffer = PacketBuffer()
        try:
            while self.running:
                try:
                    data = self.sock.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    break               # 서버가 연결을 닫았다
                for packet in buffer.feed(data):
                    self._dispatch(packet)
        except (OSError, ValueError):
            pass                        # 연결 끊김 또는 잘못된 패킷
        finally:
            was_running = self.running
            self.running = False
            self._shutdown_socket()
            if was_running:             # 내가 close() 한 경우가 아니라 서버/네트워크 때문에 끊긴 경우만 알린다
                self.inbox.put((DISCONNECTED, '서버와의 연결이 끊어졌습니다.'))

    def _dispatch(self, packet):
        ptype, length = protocol.unpack_header(packet[:3])
        payload = packet[3:3 + length]
        name = PACKET_NAMES.get(ptype)
        if name is None:
            return                      # 알 수 없는 종류는 무시
        decoder = DECODERS.get(ptype)
        value = decoder(payload) if decoder else payload    # 본문 길이가 틀리면 ValueError -> 연결 종료
        self.inbox.put((name, value))

    def poll(self):
        # 메인 스레드가 매 프레임 호출한다. inbox 에 쌓인 메시지를 모두 꺼내 리스트로 돌려준다.
        messages = []
        while True:
            try:
                messages.append(self.inbox.get_nowait())
            except queue.Empty:
                return messages

    def send(self, packet):
        # pack_xxx() 로 만든 패킷을 서버로 보낸다. (send_input / send_shop_buy 가 이 함수를 쓴다)
        if not self.running:
            return False
        try:
            send_packet(self.sock, packet)
            return True
        except OSError:
            self._shutdown_socket()     # 수신 스레드가 끊김을 감지해 DISCONNECTED 를 넣는다
            return False

    def close(self):
        # 내가 직접 연결을 끊는다. (DISCONNECTED 메시지는 넣지 않는다)
        self.running = False
        self._shutdown_socket()

    def _shutdown_socket(self):
        if self.sock is None:
            return
        try:
            self.sock.shutdown(socket.SHUT_RDWR)    # 블록된 recv() 를 깨운다
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass