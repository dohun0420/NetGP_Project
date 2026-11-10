# 11/10 작업 검증 : ClientSession.recv_loop() + 이벤트 큐 + NetworkClient
# 실행 (프로젝트 최상위 폴더에서) :  python test_network.py
import queue, socket, threading, time

from common import protocol as p
from server import server_main
from server.session import EV_JOIN, EV_PACKET, EV_LEAVE
from client.network_client import NetworkClient, DISCONNECTED

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]

def next_event(q, timeout=2.0):
    return q.get(timeout=timeout)

def assert_no_event(q, wait=0.4):
    time.sleep(wait)
    assert q.empty(), f"예상하지 못한 이벤트 : {list(q.queue)}"

def wait_messages(client, count, timeout=2.0):
    got, end = [], time.time() + timeout
    while len(got) < count and time.time() < end:
        got += client.poll(); time.sleep(0.01)
    return got

# ----------------------------------------------------------------- 서버 시작
events = queue.Queue()
port = free_port()
threading.Thread(target=server_main.main, kwargs=dict(host="127.0.0.1", port=port, event_queue=events), daemon=True).start()
time.sleep(0.3)

def new_client():
    c = NetworkClient()
    for _ in range(20):
        if c.connect("127.0.0.1", port): break
        time.sleep(0.1)
    else:
        raise AssertionError("접속 실패 : " + c.last_error)
    kind, session = next_event(events)
    assert kind == EV_JOIN
    return c, session

# 1) 접속 -> EV_JOIN
client, session = new_client()
print("1) 접속 OK : 서버 이벤트 큐에 EV_JOIN")

# 2) 클라 -> 서버 : 패킷 1개 -> EV_PACKET
assert client.send(p.pack_input(p.KEY_W | p.KEY_D))
kind, s, ptype, payload = next_event(events)
assert (kind, s, ptype) == (EV_PACKET, session, p.packet_types["CtoS_INPUT"])
assert p.unpack_input(payload) == 9
print("2) 수신 OK : EV_PACKET, INPUT(W+D) = 9 로 복원")

# 3) 패킷 3개를 붙여서, 중간에서 쪼개서 보내도 3개로 정확히 나뉘는가
blob = p.pack_input(1) + p.pack_shop_buy(p.ITEM_PICKAXE) + p.pack_input(0)
client.sock.sendall(blob[:2]); time.sleep(0.05)
client.sock.sendall(blob[2:7]); time.sleep(0.05)
client.sock.sendall(blob[7:])
got = [next_event(events) for _ in range(3)]
assert [g[2] for g in got] == [1, 2, 1]
assert [p.unpack_input(got[0][3]), p.unpack_shop_buy(got[1][3]), p.unpack_input(got[2][3])] == [1, 3, 0]
print("3) 조립 OK : 붙어서/쪼개져서 와도 EV_PACKET 3개 (순서 유지)")

# 4) 서버 -> 클라 : 해석 함수가 있는 패킷은 값으로, 없는 패킷은 본문 바이트로 inbox 에 들어오는가
session.send(p.pack_join_ok(2) + p.pack_lobby_state(3) + p.pack_error(p.ERR_PLAYER_LEFT)
             + p.pack_header(p.packet_types["StoC_STATE"], 3) + b"abc")
msgs = wait_messages(client, 4)
assert msgs == [("StoC_JOIN_OK", 2), ("StoC_LOBBY_STATE", 3), ("StoC_ERROR", 3), ("StoC_STATE", b"abc")], msgs
print("4) 클라 수신 OK : poll() ->", msgs)

# 5) 한동안 아무것도 안 보내도(서버 recv timeout 2초) 연결이 유지되는가
time.sleep(2.6)
assert_no_event(events, 0.1)
client.send(p.pack_input(16))
kind, s, ptype, payload = next_event(events)
assert kind == EV_PACKET and p.unpack_input(payload) == 16
print("5) timeout OK : 2.6초 무입력 후에도 연결 유지, 패킷 정상 수신")

# 6) 클라가 직접 종료 -> 서버에 EV_LEAVE 한 번, 클라 inbox 에는 DISCONNECTED 없음
client.close()
assert next_event(events) == (EV_LEAVE, session)
assert_no_event(events)
assert client.poll() == []
print("6) 클라 종료 OK : 서버에 EV_LEAVE 1번만, 클라에는 DISCONNECTED 없음")

# 7) 서버가 연결을 닫음 -> 클라에 DISCONNECTED 한 번
client, session = new_client()
session.close()
assert wait_messages(client, 1)[0][0] == DISCONNECTED
assert next_event(events) == (EV_LEAVE, session)
time.sleep(0.4); assert client.poll() == []
print("7) 서버 종료 OK : 클라에 DISCONNECTED 1번, 서버에 EV_LEAVE 1번")

# 8) 잘못된 패킷(본문 길이가 최대 크기 초과) -> 서버가 접속 종료로 처리
client, session = new_client()
client.send(p.pack_header(p.packet_types["CtoS_INPUT"], 60000) + b"x" * 10)
assert next_event(events) == (EV_LEAVE, session)
assert wait_messages(client, 1)[0][0] == DISCONNECTED
print("8) 잘못된 패킷 OK : 서버가 연결을 끊고 EV_LEAVE, 클라는 DISCONNECTED")

# 9) 서버가 없는 곳에 접속 시도
c = NetworkClient()
assert c.connect("127.0.0.1", free_port()) is False and c.last_error
print("9) 접속 실패 OK :", c.last_error)

# 10) 3명 동시 접속 : 세션마다 각자 EV_JOIN, 패킷이 섞이지 않는가
clients = [new_client() for _ in range(3)]
for i, (c, s) in enumerate(clients):
    c.send(p.pack_input(i + 1))
seen = {}
for _ in range(3):
    kind, s, ptype, payload = next_event(events)
    seen[s] = p.unpack_input(payload)
assert sorted(seen.values()) == [1, 2, 3] and all(seen[s] == i + 1 for i, (c, s) in enumerate(clients))
for c, s in clients: c.close()
print("10) 3명 동시 접속 OK : 각 세션의 패킷이 섞이지 않음")

print("\n전부 통과")