import queue
import socket
import threading
import os
import sys
import time
from pico2d import *
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
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
# 현재 statemachine이 없는 관계로 title을 여기서 처리

def title():
    if len(sys.argv) < 2:
        ip = '127.0.0.1'
    else:
        ip = sys.argv[1]
    return ip

class NetworkClient:

    def __init__(self):
        self.sock = None
        self.inbox = queue.Queue()      # 수신 스레드 -> 메인 스레드. 항목 : (이름, 값)
        self.running = False
        self.last_error = ''
        self._thread = None
        self.keys = set()  # 눌린 키 상태를 저장하는 집합
        self.last_input_time = 0.0  # 마지막으로 send_input()을 호출한 시간

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
    def connect_udp(self, port=PORT):
        # UDP 서버에 접속하고 수신 스레드를 시작한다. 성공 True / 실패 False (사유는 last_error).
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # sock.connect((ip, port))
            sock.bind(('', port))
        except OSError as e:
            self.last_error = f'UDP 서버에 접속할 수 없습니다. ({e})'
            return False
        sock.settimeout(0.5)            # recv 가 0.5초마다 깨어나 종료 요청(running)을 확인한다
        self.sock = sock
        self.running = True
        self._thread = threading.Thread(target=self.recv_loop_udp, daemon=True)
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
    def recv_loop_udp(self):
        # 수신 스레드 : recv() -> PacketBuffer 로 조립 -> 값으로 해석해서 inbox 에 넣는다.
        buffer = PacketBuffer()
        try:
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)
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
    def keys_to_flags(self, keys, key_flags=0):
        # 키보드 입력 문자열을 key_flags 값으로 바꾼다. (PlayState 에서 호출)
        # PlayState 에서 매 keydown/keyup 마다 keys_to_flags() 를 호출해 key_flags 를 만든다
        flags = key_flags
        if 'w' in keys:
            flags |= protocol.KEY_W
        if 'a' in keys:
            flags |= protocol.KEY_A
        if 's' in keys:
            flags |= protocol.KEY_S
        if 'd' in keys:
            flags |= protocol.KEY_D
        if 'space' in keys:
            flags |= protocol.KEY_SPACE
        if 'p' in keys:
            flags = 0  # 상점 진입시 key_flags 는 0
        return flags

    def send_input(self, key_flags):
        # 눌린 키 상태를 서버로 보낸다. key_flags : protocol.KEY_W | KEY_A | KEY_S | KEY_D | KEY_SPACE 를 더한 값.
        # (키가 바뀔 때만 / 0.5초마다 호출하는 규칙은 PlayState 에서 정한다)
        return self.send(protocol.pack_input(key_flags))
    def play_state(self, events):
        for event in events:
            if event.type == SDL_KEYDOWN:
                if event.key == SDLK_w:
                    self.keys.add('w')
                elif event.key == SDLK_a:
                    self.keys.add('a')
                elif event.key == SDLK_s:
                    self.keys.add('s')
                elif event.key == SDLK_d:
                    self.keys.add('d')
                elif event.key == SDLK_p:      # 상점 진입시 key_flags 는 0
                    self.keys.add('p')
                elif event.key == SDLK_SPACE:
                    self.keys.add('space')
                # p 값은 상점 으로의 진입 및 상점에서의 아이템 구매를 위한 키 입력 처리
                # TODO 11/26 TRYBUY 하면서 구현
            elif event.type == SDL_KEYUP:
                if event.key == SDLK_w:
                    self.keys.discard('w')
                elif event.key == SDLK_a:
                    self.keys.discard('a')
                elif event.key == SDLK_s:
                    self.keys.discard('s')
                elif event.key == SDLK_d:
                    self.keys.discard('d')
                elif event.key == SDLK_SPACE:
                    self.keys.discard('space')
        # PlayState 에서 매 프레임 호출한다. (키보드 입력을 서버로 보낸다)
        # keys_to_flags() 를 호출해 key_flags 를 만들고, send_input() 으로 서버에 보낸다.
        key_flags = self.keys_to_flags(self.keys)
        self.send_input(key_flags)
        # 0.5초마다 키가 바뀌지 않아도 send_input(0) 을 보내야 한다. (PlayState 에서 구현)
        if time.time() - self.last_input_time >= 0.5:
            self.send_input(key_flags)
            self.last_input_time = time.time()
        self.last_input_time = time.time()
    def exit_shop(self):
        self.keys.discard('p')  # 상점에서 나올 때 p 키를 제거하여 상점 모드 종료
    def send_shop_buy(self, item_id):
        # 상점에서 아이템 구매를 요청한다. item_id : protocol.ITEM_GLOVE ~ ITEM_DRILL (1~4).
        return self.send(protocol.pack_shop_buy(item_id))

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
if __name__ == "__main__":
    from client.world_view import ClientWorld

    # 단독 실행하면 서버 접속 테스트
    # keys_to_flags()실험 임의의 keys 값을 준다
    # play_state()는 SDL 이벤트를 처리하므로 단독 실행에서는 호출하지 않는다.
    keys = {'w', 'a', 'space'}
    flags = NetworkClient.keys_to_flags(NetworkClient, keys)
    print(flags)
    # 서버 접속 테스트
    client = NetworkClient()
    world = ClientWorld()
    if client.connect(title(), PORT) and client.connect_udp(PORT-1):
        print("서버 접속 성공")
        while True:
            msgs = client.poll()
            for name, value in msgs:
                world.apply_world_message(name, value)
                print(name, value)
            if not client.running:
                break
    else:
        print(client.last_error)
