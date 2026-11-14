import queue
import time

from common import protocol
from common.constants import TICK_RATE, PORT, TIME_LIMIT
from server.session import EV_JOIN, EV_PACKET, EV_LEAVE, ClientSession
from common import net_utils
from server.world import ITEM_TABLE


class GameServer:
    # 게임 루프(20Hz). run() 은 게임 상태를 수정하는 유일한 스레드에서 돈다.
    # 수신 스레드들은 event_queue 에 넣기만 하고, 이 클래스가 꺼내서 처리한다.

    def __init__(self, event_queue, udp_socket=None):
        self.event_queue = event_queue
        self.sessions = []                  # 접속 중인 세션 (게임 루프 스레드만 수정한다)
        self.running = False
        self.game_started = False          # GAME_START 중복 전송 방지
        self.udp_socket = udp_socket
        self.subnet_mask = None
        # 패킷 종류 -> 처리 함수. 새 패킷을 처리하는 함수를 만들면 여기에 한 줄 추가한다. 서버가 처리하니 Ctos_ 패킷만 들어간다.
        self.packet_handlers = {
            protocol.packet_types["CtoS_INPUT"]: self.handle_input,
            protocol.packet_types["CtoS_SHOP_BUY"]: self.handle_shop_buy,
        }

    # ------------------------------------------------------------ 게임 루프
    def run(self):
        # 고정 주기 루프 : 이벤트 처리 -> 월드 갱신 -> 브로드캐스트 -> 남은 시간만큼 sleep.
        self.running = True

        last = next_tick = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            dt = now - last                 # 직전 틱 이후 실제로 지난 시간(초)
            last = now

            self.process_events()
            self.update(dt)
            self.broadcast()

            # sleep 보정 : "처리 시간 + sleep" 이 항상 TICK_RATE 가 되도록 다음 틱 시각을 기준으로 잔다.
            next_tick += TICK_RATE
            wait = next_tick - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
            else:
                next_tick = time.perf_counter()     # 처리가 밀렸으면 따라잡으려고 연속 실행하지 않는다

    def stop(self):
        self.running = False

    # ------------------------------------------------------------ 이벤트 처리
    def process_events(self):
        # 이 틱이 시작될 때 큐에 있던 이벤트만 처리한다. (계속 들어와도 루프가 끝나지 않는 일을 막는다)
        for _ in range(self.event_queue.qsize()):
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                return
            kind = event[0]
            if kind == EV_JOIN:
                self.handle_join(event[1])
            elif kind == EV_PACKET:
                self.handle_packet(event[1], event[2], event[3])
            elif kind == EV_LEAVE:
                self.handle_leave(event[1])

    def handle_join(self, session):
        player_count = len(self.sessions)
        if player_count >= 3:            # 최대 3명까지만 허용
            packet = protocol.pack_lobby_state(player_count)   # 3명 이상이면 접속 거부
            session.send(packet)                # 최대 인원 수용시 자동 시작 따라서 진행중 상태를 알려주고 접속 종료
            session.close()
            return
        session.player_id = player_count      # 0~2
        packet = protocol.pack_join_ok(session.player_id)
        session.send(packet)
        self.sessions.append(session)
        self.broadcast_LobbyState()
        self.start_game()

    def start_game(self):
        if self.game_started or len(self.sessions) != 3:
            return
        costs = tuple(ITEM_TABLE[item_id]['cost'] for item_id in range(1, 5))
        players = [(s.player_id, 400 + s.player_id * 100, 300) for s in self.sessions]
        golds = []                          # TODO(11/15) generate_gold_spots() 결과 연결
        gold_count = len(golds)
        packet = protocol.pack_game_start(TIME_LIMIT, costs, players, gold_count, golds)
        self.game_started = True
        for session in self.sessions:
            session.send(packet)

    def handle_leave(self, session):
        if session in self.sessions:
            self.sessions.remove(session)
        session.close()                     # 이미 닫혀 있어도 안전하다
        # TODO(11/29) 게임 중이면 강제 종료 : 남은 플레이어에게 ERROR(사유 3) 전송

    def handle_packet(self, session, ptype, payload):
        handler = self.packet_handlers.get(ptype)
        if handler is None:
            session.close()                 # 알 수 없는 종류 -> 접속 종료 (수신 스레드가 EV_LEAVE 를 넣는다)
            return
        try:
            handler(session, payload)
        except ValueError:                  # 본문 길이가 틀린 패킷
            session.close()

    def handle_input(self, session, payload):
        key_flags = protocol.unpack_input(payload)
        # TODO(11/17) World.apply_input(session.player_id, key_flags)

    def handle_shop_buy(self, session, payload):
        item_id = protocol.unpack_shop_buy(payload)
        # TODO(11/27) handle_shop_buy : 검증 -> SHOP_RESULT 전송
    def subnet_mask(self, subnet_mask):
        self.subnet_mask = subnet_mask
    def broadcast_LobbyState(self):
        # 대기 인원수를 모든 세션에 전송한다. (게임 시작 전 로비 상태)
        waiting_count = len(self.sessions)
        packet = protocol.pack_lobby_state(waiting_count)
        address = ('<broadcast>', PORT -1)  # 브로드캐스트 주소와 포트 설정
        self.udp_socket.sendto(packet, address)
    # ------------------------------------------------------------ 매 틱 처리 (이후 채워 나간다)
    def update(self, dt):
        pass                                # TODO(11/16) World.update(dt)

    def broadcast(self):
        pass                                # TODO(11/17) STATE 를 모든 세션에 전송
