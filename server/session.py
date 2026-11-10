import socket
import threading

from common import protocol
from common.net_utils import PacketBuffer, send_packet

# ---------------------------------------------------------------
# 이벤트 큐에 들어가는 항목 (수신 스레드 -> 게임 루프 스레드)
#   (EV_JOIN,   session)                    새 클라이언트 접속
#   (EV_PACKET, session, ptype, payload)    패킷 1개 수신 (payload = 헤더를 뺀 본문)
#   (EV_LEAVE,  session)                    접속 종료 (정상 종료 / 끊김 / 잘못된 패킷 모두)
# 접속 직후에는 player_id 가 아직 없으므로 session 을 넘기고, 게임 루프는 session.player_id 를 쓴다.
# ---------------------------------------------------------------
EV_JOIN = 'join'
EV_PACKET = 'packet'
EV_LEAVE = 'leave'
from common.net_utils import send_packet

class ClientSession:
    def __init__(self, sock, event_queue):
        self.sock = sock
        self.event_queue = event_queue
        self.player_id = None           # 게임 루프(handle_join)가 번호를 배정한다
        # 송신/수신이 오래 막히지 않도록 제한한다. recv() 의 timeout 은 에러가 아니라 "아직 데이터 없음"이다.
        self.sock.settimeout(2.0)
        self._closed = False
        self._close_lock = threading.Lock()
        self._thread = None

    def is_closed(self):
        with self._close_lock:
            return self._closed

    def start(self):
        # EV_JOIN 을 큐에 넣고 수신 스레드를 시작한다. (accept 직후 한 번 호출)
        self.event_queue.put((EV_JOIN, self))
        self._thread = threading.Thread(target=self.recv_loop, daemon=True)
        self._thread.start()

    def recv_loop(self):
        # 수신 스레드 : recv() -> PacketBuffer 로 조립 -> 패킷마다 EV_PACKET 을 큐에 넣는다.
        buffer = PacketBuffer()
        try:
            while not self.is_closed():
                try:
                    data = self.sock.recv(4096)
                except socket.timeout:
                    continue                    # 데이터가 아직 없을 뿐, 계속 기다린다
                if not data:
                    break                       # 상대가 연결을 닫았다
                for packet in buffer.feed(data):
                    ptype, length = protocol.unpack_header(packet[:3])
                    self.event_queue.put((EV_PACKET, self, ptype, packet[3:3 + length]))
        except (OSError, ValueError):
            pass                                # 연결 끊김(reset) 또는 잘못된 패킷 길이 -> 접속 종료로 처리
        finally:
            self.close()
            self.event_queue.put((EV_LEAVE, self))   # 수신 스레드가 끝날 때 딱 한 번만 넣는다

    def send(self, packet):
        # 게임 루프 스레드가 호출한다. 실패하면 연결을 닫는다 -> 수신 스레드가 EV_LEAVE 를 넣는다.
        try:
            send_packet(self.sock, packet)
            return True
        except OSError:
            self.close()
            return False

    def close(self):
        with self._close_lock:
            if self._closed:
                return
            self._closed = True

        # 소켓 종료 처리 시 OS별 OSError 방지
        try:
            self.sock.shutdown(socket.SHUT_RDWR)    # 블록된 recv() 를 깨운다
        except OSError:
            pass

        try:
            self.sock.close()
        except OSError:
            pass
          
    def __init__(self, sock):
        self.sock = sock
        # 송신이 오래 막히지 않도록 제한한다. 추후 recv()에도 같은 제한이 적용된다.
        self.sock.settimeout(2.0)

    def send(self, packet):
        send_packet(self.sock, packet)

    def close(self):
        self.sock.close()
