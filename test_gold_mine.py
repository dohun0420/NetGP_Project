# [11/24] 검증 : complete_mining() / broadcast_gold_mined() (서버) + apply_gold_mined() / GoldView.draw() (클라이언트)
# 실행 (프로젝트 최상위 폴더에서) :  python test_gold_mine.py
import io, os, queue, socket, sys, threading, time, types

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, "server"), os.path.join(ROOT, "client")]
real_out = sys.stdout
def say(msg): print(msg, file=real_out)
sys.stdout = io.StringIO()                      # world.py / game_server.py 안의 디버그 print 는 숨긴다

# ---- pico2d 가짜 (network_client 의 `from pico2d import *` 와 GoldView 용)
draw_log = []
class FakeImage:
    def __init__(self, name): self.name = name
    def clip_draw(self, *a): draw_log.append(a)
pico = types.ModuleType("pico2d"); pico.load_image = FakeImage; pico.get_events = lambda: []
sys.modules["pico2d"] = pico

from common import protocol as p
import server.world as W
from server.world import World, Player, GoldSpot, MINING_RANGE
from server.game_server import GameServer
from server import server_main
from client.network_client import NetworkClient
from client.world_view import ClientWorld
from client.gold_view import GoldView

class Clock: now = 1000.0
W.monotonic = lambda: Clock.now                 # 채굴 시간을 정확히 검사하려고 시계를 우리가 정한다
W.World.respawn_gold_if_empty = lambda self: None  # 채굴 검증 중 자동 리스폰 방지

def make_world(players=((0, 400, 300), (1, 500, 300), (2, 600, 300)), golds=()):
    w = World()
    for pid, x, y in players: w.players[pid] = Player(pid, x, y)
    for sid, x, y in golds: w.golds[sid] = GoldSpot(sid, x, y)
    return w

# ================================================================ A) World.complete_mining / update_mining
# A1) 가장 가까운 금괴 1개만 지워지고, 팀 금괴 · 개인 채굴 수 · 이벤트가 맞는가
w = make_world(golds=[(0, 430, 300), (1, 445, 300), (2, 900, 500)])
pl = w.players[0]; pl.mining_started_at = Clock.now; pl.state = 2
event = w.complete_mining(pl)
assert event == (0, 0, 1), event
assert sorted(w.golds) == [1, 2] and w.team_gold == 1 and pl.mined == 1
assert pl.mining_started_at is None and pl.state == 0 and pl.key_flags == 0
assert w.events == [(0, 0, 1)] and w.pop_events() == [(0, 0, 1)] and w.events == [] and w.pop_events() == []
say("A1) complete_mining OK : 30px 금괴(가장 가까운 것)만 제거, 팀 금괴 1, 개인 채굴 1, 이벤트 (0, 0, 1), 채굴 상태 종료")

# A2) 근처에 금괴가 없으면 아무 일도 없지만 채굴 상태는 끝난다
w = make_world(golds=[(0, 400, 351)]); pl = w.players[0]; pl.mining_started_at = Clock.now; pl.state = 2
assert w.complete_mining(pl) is None
assert list(w.golds) == [0] and w.team_gold == 0 and pl.mined == 0 and w.events == []
assert pl.mining_started_at is None and pl.state == 0
say("A2) 빈손 OK : 51px 밖에는 금괴가 있어도 채굴 실패, 금괴/팀 금괴 그대로, 채굴 상태는 종료(입력 다시 가능)")

# A3) 경계 : 정확히 50px 는 채굴, 50.1px 는 실패
w = make_world(golds=[(0, 450, 300)]); pl = w.players[0]
assert w.complete_mining(pl) == (0, 0, 1)
w = make_world(golds=[(0, 450.1, 300)]); pl = w.players[0]
assert w.complete_mining(pl) is None
assert MINING_RANGE == 50
say("A3) 경계 OK : 정확히 50px 는 채굴(기존 게임의 distance <= 50), 50.1px 는 실패")

# A4) update() 가 채굴 시간(아이템 등급별 5 ~ 1초)이 지났을 때만 마무리하는가
for level, dig in ((0, 5), (1, 4), (2, 3), (3, 2), (4, 1)):
    Clock.now = 2000.0
    w = make_world(golds=[(0, 410, 300)]); w.item_level = level
    w.update(0.05, {0: p.KEY_SPACE})
    pl = w.players[0]
    assert pl.state == 2 and pl.mining_started_at == 2000.0
    Clock.now = 2000.0 + dig - 0.05; w.update(0.05, {})
    assert pl.state == 2 and w.team_gold == 0 and w.events == [], (level, "너무 일찍 끝남")
    Clock.now = 2000.0 + dig; w.update(0.05, {})
    assert pl.state == 0 and w.team_gold == 1 and w.events == [(0, 0, 1)], (level, "제때 끝나지 않음")
say("A4) 채굴 시간 OK : 아이템 등급 0~4 에서 5, 4, 3, 2, 1초가 되기 전에는 계속 채굴 중, 되는 순간 완료")

# A5) 두 명이 같은 틱에 같은 금괴를 끝내면 한 명만 받는다 (중복 지급 없음)
Clock.now = 3000.0
w = make_world(players=((0, 400, 300), (1, 410, 300), (2, 900, 100)), golds=[(7, 405, 300)])
for pid in (0, 1):
    w.players[pid].mining_started_at = 2990.0; w.players[pid].state = 2
w.update(0.05, {})
assert w.team_gold == 1 and len(w.events) == 1 and w.golds == {}
assert [w.players[0].mined, w.players[1].mined] == [1, 0]
assert w.players[0].state == 0 and w.players[1].state == 0
say("A5) 동시 채굴 OK : 같은 금괴를 두 명이 동시에 끝내도 팀 금괴 +1 한 번, 이벤트 1개")

# A6) 채굴 중에는 입력이 무시되고, 끝나면 다시 움직일 수 있다
Clock.now = 4000.0
w = make_world(golds=[(0, 420, 300)]); w.update(0.05, {0: p.KEY_SPACE}); pl = w.players[0]
x0 = pl.x; w.update(0.05, {0: p.KEY_D}); assert pl.x == x0 and pl.state == 2
Clock.now = 4005.0; w.update(0.05, {}); assert pl.state == 0
w.update(0.05, {0: p.KEY_D}); assert pl.x > x0 and pl.state == 1
say("A6) 입력 OK : 채굴 중에는 이동 입력 무시, 완료 후에는 다시 이동")

# A7) STATE 용 snapshot 에 반영되는가
Clock.now = 5000.0
w = make_world(golds=[(0, 420, 300)]); w.update(0.05, {0: p.KEY_SPACE})
assert w.snapshot()[3][0][3] == 2
Clock.now = 5005.0; w.update(0.05, {})
remain_x10, team_gold, item_level, players = w.snapshot()
assert team_gold == 1 and players[0][3] == 0
say("A7) snapshot OK : 채굴 중 state 2 -> 완료 후 state 0, 팀 금괴 1")

# ================================================================ B) GameServer.broadcast_gold_mined
class FakeUDP:
    def sendto(self, *a): pass
class FakeSession:
    def __init__(self): self.sent = []; self.player_id = None; self.closed = False
    def send(self, packet): self.sent.append(packet); return True
    def close(self): self.closed = True
class TestServer(GameServer):
    def update(self, dt):
        if self.world is not None: self.world.update(dt, {})

def kinds(session):
    out = []
    for packet in session.sent:
        out.append(p.unpack_header(packet[:3])[0])
    return out

def start_server():
    gs = TestServer(queue.Queue(), udp_socket=FakeUDP())
    sessions = [FakeSession() for _ in range(3)]
    for s in sessions: gs.handle_join(s)
    assert gs.world is not None
    for s in sessions: s.sent.clear()
    return gs, sessions

Clock.now = 6000.0
gs, ss = start_server()
gs.world.golds = {5: GoldSpot(5, 510, 300), 6: GoldSpot(6, 900, 500)}
gs.world.players[1].mining_started_at = 5990.0; gs.world.players[1].state = 2
gs.update(0.05); gs.broadcast()
GM, ST = p.packet_types["StoC_GOLD_MINED"], p.packet_types["StoC_STATE"]
for s in ss:
    assert kinds(s) == [GM, ST], kinds(s)
    assert p.unpack_gold_mined(s.sent[0][3:]) == (5, 1, 1)
    assert p.unpack_state(s.sent[1][3:])[1] == 1
assert ss[0].sent == ss[1].sent == ss[2].sent
for s in ss: s.sent.clear()
gs.update(0.05); gs.broadcast()
for s in ss: assert kinds(s) == [ST]
say("B1) 전송 OK : 3명 모두에게 GOLD_MINED(금괴 5, 플레이어 1, 팀 금괴 1) 다음에 STATE, 다음 틱에는 STATE 만")

Clock.now = 7000.0
gs, ss = start_server()
gs.world.golds = {1: GoldSpot(1, 410, 300), 2: GoldSpot(2, 610, 300)}
for pid in (0, 2):
    gs.world.players[pid].mining_started_at = 6990.0; gs.world.players[pid].state = 2
gs.update(0.05); gs.broadcast()
assert kinds(ss[0]) == [GM, GM, ST]
assert [p.unpack_gold_mined(x[3:]) for x in ss[0].sent[:2]] == [(1, 0, 1), (2, 2, 2)]
say("B2) 한 틱에 두 명 OK : GOLD_MINED 2개가 순서대로 (팀 금괴 1 -> 2), 그다음 STATE")

# ================================================================ C) 클라이언트 : apply_gold_mined / GoldView
world = ClientWorld()
world.init_from_start(180, (10, 14, 24, 40), [(0, 300, 100), (1, 500, 250), (2, 700, 180)], 3, [(0, 100, 50), (1, 200, 60), (2, 300, 70)])
world.apply_gold_mined(1, 0, 4)
assert sorted(world.golds) == [0, 2] and world.gold_count == 2 and world.team_gold == 4
world.apply_gold_mined(1, 0, 5)
assert sorted(world.golds) == [0, 2] and world.team_gold == 5
say("C1) apply_gold_mined OK : 금괴 1번 제거(3 -> 2개), 팀 금괴는 서버 값(4, 5)으로, 중복 메시지에도 오류 없음")

world = ClientWorld()
world.init_from_start(180, (10, 14, 24, 40), [(0, 300, 100), (1, 500, 250), (2, 700, 180)], 3, [(0, 100, 50), (1, 200, 60), (2, 300, 70)])
world.apply_world_message("StoC_GOLD_MINED", p.pack_gold_mined(2, 1, 9)[3:])
assert sorted(world.golds) == [0, 1] and world.team_gold == 9
world.apply_world_message("StoC_STATE", p.pack_state(1700, 9, 0, [(0, 300, 100, 0), (1, 500, 250, 0), (2, 700, 180, 0)])[3:])
assert sorted(world.golds) == [0, 1] and world.team_gold == 9 and world.remain_x10 == 1700
say("C2) 메시지 연결 OK : apply_world_message 가 GOLD_MINED 바이트를 해석해 반영, 이어서 온 STATE 와 값이 어긋나지 않음")

view = GoldView()
draw_log.clear(); view.draw(world.golds)
assert len(draw_log) == 2 and sorted((a[4], a[5]) for a in draw_log) == [(100, 50), (200, 60)]
say("C3) GoldView.draw OK : 제거된 금괴(300, 70)는 그리지 않고 남은 2개만 그림")

# ================================================================ D) 실제 소켓 : 클라이언트 3명이 GOLD_MINED 를 받아 화면 데이터에 반영
W.monotonic = time.monotonic
rec = TestServer(queue.Queue(), udp_socket=FakeUDP())
with socket.socket() as sk:
    sk.bind(("127.0.0.1", 0)); port = sk.getsockname()[1]
threading.Thread(target=server_main.main, kwargs=dict(host="127.0.0.1", port=port, game_server=rec), daemon=True).start()
time.sleep(0.3)
clients = []
for _ in range(3):
    c = NetworkClient()
    for _ in range(20):
        if c.connect("127.0.0.1", port): break
        time.sleep(0.1)
    clients.append(c); time.sleep(0.1)
time.sleep(0.4)
rec.world.golds = {4: GoldSpot(4, 515, 300), 8: GoldSpot(8, 900, 500)}
rec.world.players[1].mining_started_at = time.monotonic() - 10
rec.world.players[1].state = 2
time.sleep(0.6)
for i, c in enumerate(clients):
    msgs = c.poll()
    names = [n for n, _ in msgs]
    assert names.count("StoC_GOLD_MINED") == 1, names.count("StoC_GOLD_MINED")
    k = names.index("StoC_GOLD_MINED")
    assert names[k + 1] == "StoC_STATE"
    cw = ClientWorld()
    for n, v in msgs:
        if n in ("StoC_GAME_START", "StoC_GOLD_MINED", "StoC_STATE"): cw.apply_world_message(n, v)
    assert 4 not in cw.golds and cw.team_gold == 1, (i, cw.golds, cw.team_gold)
    assert len(cw.golds) == 19
for c in clients: c.close()
rec.stop()
say("D) 실제 TCP OK : 클라이언트 3명 모두 GOLD_MINED 를 1번 받고 바로 다음이 STATE, 반영 후 금괴 4번 제거 · 팀 금괴 1")

say("\n전부 통과")