import os
import queue
import socket
import sys
import threading
import time
from pico2d import *

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common import protocol
from common.constants import PORT
from common.net_utils import PacketBuffer, send_packet

DISCONNECTED = 'DISCONNECTED'       # 연결이 끊겼을 때 inbox 에 들어가는 메시지 이름

# 패킷 종류 번호 -> 이름 (ex. 101 -> "StoC_JOIN_OK")
PACKET_NAMES = {number: name for name, number in protocol.packet_types.items()}

# 패킷 종류 -> 본문을 값으로 바꾸는 함수 전체 등록
DECODERS = {
    protocol.packet_types["StoC_JOIN_OK"]: protocol.unpack_join_ok,
    protocol.packet_types["StoC_LOBBY_STATE"]: protocol.unpack_lobby_state,
    protocol.packet_types["StoC_GAME_START"]: protocol.unpack_game_start,
    protocol.packet_types["StoC_STATE"]: protocol.unpack_state,
    protocol.packet_types["StoC_GOLD_MINED"]: protocol.unpack_gold_mined,
    protocol.packet_types["StoC_GOLD_RESPAWN"]: protocol.unpack_gold_respawn,
    protocol.packet_types["StoC_SHOP_RESULT"]: protocol.unpack_shop_result,
    protocol.packet_types["StoC_GAME_END"]: protocol.unpack_game_end,
    protocol.packet_types["StoC_ERROR"]: protocol.unpack_error,
}


def title():
    if len(sys.argv) < 2:
        ip = '127.0.0.1'
    else:
        ip = sys.argv[1]
    return ip


class NetworkClient:
    def __init__(self):
        self.sock = None            # TCP 소켓
        self.udp_sock = None        # UDP 브로드캐스트 수신 전용 소켓 (TCP 소켓과 분리)
        self.inbox = queue.Queue()  # 수신 스레드 -> 메인 스레드. 항목 : (이름, 값)
        self.running = False
        self.last_error = ''
        self._thread = None
        self._udp_thread = None
        self.keys = set()           # 눌린 키 상태를 저장하는 집합
        self.last_input_time = 0.0  # 마지막으로 send_input()을 호출한 시간
        self.last_sent_flags = None

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

    def connect_udp(self, port=PORT - 1):
        # UDP 브로드캐스트 수신 소켓을 열고 수신 스레드를 시작한다.
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', port))
        except OSError as e:
            self.last_error = f'UDP 서버에 접속할 수 없습니다. ({e})'
            return False
        sock.settimeout(0.5)
        self.udp_sock = sock
        self._udp_thread = threading.Thread(target=self.recv_loop_udp, daemon=True)
        self._udp_thread.start()
        return True

    def recv_loop(self):
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
        buffer = PacketBuffer()
        try:
            while self.running and self.udp_sock is not None:
                try:
                    data, _ = self.udp_sock.recvfrom(4096)
                except socket.timeout:
                    continue
                if not data:
                    continue
                for packet in buffer.feed(data):
                    self._dispatch(packet)
        except (OSError, ValueError):
            pass

    def _dispatch(self, packet):
        ptype, length = protocol.unpack_header(packet[:3])
        payload = packet[3:3 + length]
        name = PACKET_NAMES.get(ptype)
        if name is None:
            return                      # 알 수 없는 종류는 무시
        decoder = DECODERS.get(ptype)
        value = decoder(payload) if decoder else payload
        self.inbox.put((name, value))

    def poll(self):
        messages = []
        while True:
            try:
                messages.append(self.inbox.get_nowait())
            except queue.Empty:
                return messages

    def send(self, packet):
        if not self.running:
            return False
        try:
            send_packet(self.sock, packet)
            return True
        except OSError:
            self._shutdown_socket()
            return False

    def keys_to_flags(self, keys, key_flags=0):
        if 'p' in keys:
            return protocol.KEY_P   # 상점 진입 시 KEY_P(32) 전송
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
        return flags

    def send_input(self, key_flags):
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
                elif event.key == SDLK_p:
                    self.keys.add('p')
                elif event.key == SDLK_SPACE:
                    self.keys.add('space')
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

        key_flags = self.keys_to_flags(self.keys)
        now = time.time()
        # 키 상태가 바뀌었을 때 또는 0.5초마다 재전송 (계획서 4.2절 규칙)
        if key_flags != self.last_sent_flags or (now - self.last_input_time) >= 0.5:
            self.send_input(key_flags)
            self.last_sent_flags = key_flags
            self.last_input_time = now

    def exit_shop(self):
        self.keys.discard('p')
        self.last_sent_flags = None  # 상점 종료 직후 현재 키 상태를 즉시 다시 전송하도록 초기화

    def send_shop_buy(self, item_id):
        return self.send(protocol.pack_shop_buy(item_id))

    def close(self):
        self.running = False
        self._shutdown_socket()

    def _shutdown_socket(self):
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

        if self.udp_sock is not None:
            try:
                self.udp_sock.close()
            except OSError:
                pass
            self.udp_sock = None


if __name__ == "__main__":
    from client.world_view import ClientWorld

    keys = {'w', 'a', 'space'}
    flags = NetworkClient.keys_to_flags(NetworkClient, keys)
    print(flags)
    client = NetworkClient()
    world = ClientWorld()
    if client.connect(title(), PORT) and client.connect_udp(PORT - 1):
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