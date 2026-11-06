# protocol.py 검증 테스트 (11/6 작업 : INPUT, SHOP_BUY, JOIN_OK, LOBBY_STATE, ERROR)
# 실행 :  python test_protocol.py     (모두 통과하면 마지막에 "전부 통과" 출력)
import socket, threading
import protocol as p

# ---------------------------------------------------------------- 1) 값 전체 범위 왕복
def test_roundtrip_all_values():
    pairs = [("CtoS_INPUT",      p.pack_input,       p.unpack_input),
             ("CtoS_SHOP_BUY",   p.pack_shop_buy,    p.unpack_shop_buy),
             ("StoC_JOIN_OK",    p.pack_join_ok,     p.unpack_join_ok),
             ("StoC_LOBBY_STATE",p.pack_lobby_state, p.unpack_lobby_state),
             ("StoC_ERROR",      p.pack_error,       p.unpack_error)]
    for name, pack, unpack in pairs:
        for v in range(256):                              # u8 이 가질 수 있는 모든 값
            packet = pack(v)
            ptype, length = p.unpack_header(packet[:3])
            assert ptype == p.packet_types[name]          # 종류 번호가 맞는가
            assert length == 1 and len(packet) == 4       # 본문 1B, 전체 4B
            assert unpack(packet[3:3 + length]) == v      # 값이 그대로 돌아오는가
    print("1) 모든 값(0~255) 왕복 OK : 5종 x 256개")

# ---------------------------------------------------------------- 2) 바이트 모양이 약속과 같은가
def test_exact_bytes():
    assert p.pack_input(p.KEY_W | p.KEY_D) == bytes([1, 0, 1, 9])      # 종류1, 길이1, 본문9
    assert p.pack_shop_buy(p.ITEM_DRILL)   == bytes([2, 0, 1, 4])
    assert p.pack_join_ok(0)               == bytes([101, 0, 1, 0])
    assert p.pack_lobby_state(2)           == bytes([102, 0, 1, 2])
    assert p.pack_error(p.ERR_PLAYER_LEFT) == bytes([109, 0, 1, 3])
    assert p.KEY_W + p.KEY_A + p.KEY_S + p.KEY_D + p.KEY_SPACE == 31   # 키 비트가 겹치지 않음
    print("2) 바이트 모양 OK : 종류(1B) + 길이(2B) + 본문(1B)")

# ---------------------------------------------------------------- 3) 실제 TCP 로 주고받기
def read_packets(sock, count):
    def recv_exact(n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk: raise ConnectionError("연결 종료")
            buf += chunk
        return buf
    out = []
    for _ in range(count):
        ptype, length = p.unpack_header(recv_exact(3))
        out.append((ptype, recv_exact(length)))
    return out

def test_over_real_tcp():
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    port = srv.getsockname()[1]
    result = {}
    def server():
        conn, _ = srv.accept()
        result["got"] = read_packets(conn, 3)
        conn.close()
    t = threading.Thread(target=server); t.start()

    cli = socket.socket(); cli.connect(("127.0.0.1", port))
    # 3개를 한 덩어리로 붙여서 보낸다 (TCP 에서 패킷이 붙어서 도착하는 상황)
    blob = p.pack_input(p.KEY_W | p.KEY_D) + p.pack_shop_buy(p.ITEM_PICKAXE) + p.pack_input(0)
    # 그리고 아무 데서나 쪼개서 보낸다 (패킷이 쪼개져서 도착하는 상황)
    cli.sendall(blob[:2]); cli.sendall(blob[2:7]); cli.sendall(blob[7:])
    cli.close(); t.join(); srv.close()

    got = result["got"]
    assert [pt for pt, _ in got] == [1, 2, 1]
    assert p.unpack_input(got[0][1]) == 9
    assert p.unpack_shop_buy(got[1][1]) == 3
    assert p.unpack_input(got[2][1]) == 0
    print("3) 실제 TCP OK : 붙어서/쪼개져서 도착해도 3개 패킷을 정확히 복원")

# ---------------------------------------------------------------- 4) 잘못된 입력 거부
def test_rejects_bad_input():
    for unpack in (p.unpack_input, p.unpack_shop_buy, p.unpack_join_ok, p.unpack_lobby_state, p.unpack_error):
        for bad in (b"", b"\x01\x02"):                    # 본문이 없거나 너무 긴 경우
            try: unpack(bad)
            except ValueError: continue
            raise AssertionError(f"{unpack.__name__} 이(가) 잘못된 길이를 통과시킴")
    for pack in (p.pack_input, p.pack_error):             # u8 범위(0~255) 밖의 값
        for bad in (-1, 256):
            try: pack(bad)
            except Exception: continue
            raise AssertionError(f"{pack.__name__} 이(가) 범위 밖 값 {bad} 을 통과시킴")
    print("4) 잘못된 입력 거부 OK : 길이 오류 / 범위 밖 값")

if __name__ == "__main__":
    test_roundtrip_all_values()
    test_exact_bytes()
    test_over_real_tcp()
    test_rejects_bad_input()
    print("\n전부 통과")
