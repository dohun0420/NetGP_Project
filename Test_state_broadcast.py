# [11/17] 검증 : World.snapshot() + GameServer.broadcast() (STATE 20Hz)
# 실행 (프로젝트 최상위 폴더에서) :  python Test_state_broadcast.py
import os, sys, queue, socket, threading, time
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, "server")]

from common import protocol as p
from common.constants import TIME_LIMIT
from client.network_client import NetworkClient
from server import server_main
from server.game_server import GameServer
from server.world import World, Player

class FakeUDP:
    def sendto(self, packet, addr): pass

class FakeSession:
    def __init__(self): self.sent = []; self.player_id = None; self.closed = False
    def send(self, packet): self.sent.append(packet); return True
    def close(self): self.closed = True

def states_of(session):
    out = []
    for packet in session.sent:
        ptype, length = p.unpack_header(packet[:3])
        if ptype == p.packet_types["StoC_STATE"]:
            out.append(p.unpack_state(packet[3:3 + length]))
    return out

# ------------------------------------------------------------- 1) World.snapshot()
w = World()
w.players[2] = Player(2, 600, 300)
w.players[0] = Player(0, 400.9, 299.2)
w.players[1] = Player(1, 500, 300)
w.players[1].dir, w.players[1].state = 3, 1
w.team_gold, w.item_level, w.remain = 7, 2, 123.46
snap = w.snapshot()
assert snap == (1235, 7, 2, [(0, 400, 299, 0, 0), (1, 500, 300, 3, 1), (2, 600, 300, 0, 0)]), snap
assert p.unpack_state(p.pack_state(*snap)[3:]) == snap
w.remain = -0.3; assert w.snapshot()[0] == 0
w.remain = 9999;  assert w.snapshot()[0] == 65535
print("1) snapshot OK : id 순서 정렬, 좌표 정수화, 남은 시간 0.1초 단위, pack_state 왕복 일치")

# ------------------------------------------------------------- 2) 게임 시작 전에는 STATE 를 보내지 않고, 시작하면 World 가 생긴다
gs = GameServer(queue.Queue(), udp_socket=FakeUDP())
s0, s1, s2 = FakeSession(), FakeSession(), FakeSession()
gs.handle_join(s0); gs.handle_join(s1)
gs.broadcast()
assert gs.world is None and not states_of(s0) and not states_of(s1)
gs.handle_join(s2)
assert gs.world is not None and sorted(gs.world.players) == [0, 1, 2] and len(gs.world.golds) == 20
start = p.unpack_game_start(s0.sent[-1][3:])
assert [(i, x, y) for i, x, y in start[2]] == [(i, int(pl.x), int(pl.y)) for i, pl in sorted(gs.world.players.items())]
assert sorted(g[0] for g in start[4]) == sorted(gs.world.golds)
print("2) 시작 OK : 2명일 때는 STATE 없음, 3명이 되면 World 생성(플레이어 3명, 금괴 20개)이 GAME_START 와 일치")

# ------------------------------------------------------------- 3) 20Hz 로 3명 모두에게 같은 STATE 를 보내는가
for s in (s0, s1, s2): s.sent.clear()
threading.Thread(target=gs.run, daemon=True).start()
time.sleep(1.0)
gs.world.players[1].x = 777.0; gs.world.players[1].state = 1
time.sleep(0.3)
gs.stop(); time.sleep(0.1)
a, b, c = states_of(s0), states_of(s1), states_of(s2)
assert 24 <= len(a) <= 28, len(a)
assert len(a) == len(b) == len(c) and a == b == c
remains = [x[0] for x in a]
assert all(m >= n for m, n in zip(remains, remains[1:])) and TIME_LIMIT * 10 - 10 < remains[0] <= TIME_LIMIT * 10
assert 1800 - remains[-1] in range(10, 16), remains[-1]
assert a[0][3][1][1] == 400 + 100 and a[-1][3][1][1] == 777 and a[-1][3][1][4] == 1
print(f"3) 20Hz OK : 1.3초 동안 STATE {len(a)}개, 3명에게 동일, 남은 시간 {remains[0]} -> {remains[-1]} (0.1초 단위), 위치 변경 반영")

# ------------------------------------------------------------- 4) 실제 소켓 : 클라이언트 3명이 접속하면 JOIN_OK -> GAME_START -> STATE 가 연속으로 온다
gs2 = GameServer(queue.Queue(), udp_socket=FakeUDP())
with socket.socket() as sk:
    sk.bind(("127.0.0.1", 0)); port = sk.getsockname()[1]
threading.Thread(target=server_main.main, kwargs=dict(host="127.0.0.1", port=port, game_server=gs2), daemon=True).start()
time.sleep(0.3)
clients = []
for _ in range(3):
    c = NetworkClient()
    for _ in range(20):
        if c.connect("127.0.0.1", port): break
        time.sleep(0.1)
    clients.append(c); time.sleep(0.1)
time.sleep(1.0)
for i, c in enumerate(clients):
    msgs = c.poll()
    names = [n for n, _ in msgs]
    assert names[0] == "StoC_JOIN_OK" and msgs[0][1] == i, names[:3]
    assert names[1] == "StoC_GAME_START" and set(names[2:]) == {"StoC_STATE"}, set(names)
    states = [p.unpack_state(v) for n, v in msgs[2:]]
    assert 15 <= len(states) <= 24, len(states)
    assert [pl[0] for pl in states[0][3]] == [0, 1, 2]
    assert states[0][0] > states[-1][0]
for c in clients: c.close()
gs2.stop()
print(f"4) 실제 TCP OK : 클라 3명 모두 JOIN_OK -> GAME_START -> STATE x{len(states)} 수신, 플레이어 [0,1,2], 남은 시간 감소")

print("\n전부 통과")