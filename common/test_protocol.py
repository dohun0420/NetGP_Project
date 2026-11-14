# protocol.py 검증 테스트 (11/6 작업 : INPUT, SHOP_BUY, JOIN_OK, LOBBY_STATE, ERROR)
# 11/7 추가 : GAME_START, STATE, GOLD_MINED, GOLD_RESPAWN, SHOP_RESULT, GAME_END
# 실행 :  python test_protocol.py     (모두 통과하면 마지막에 "전부 통과" 출력)
import socket, threading
import protocol as p

# 테스트에 사용할 값
COSTS = (10, 14, 24, 40)                                  # 장갑, 삽, 곡괭이, 드릴 순서
PLAYERS = [(0, 1, 2), (1, -1, 0), (2, 1000, 600)]           # (플레이어 번호, x, y)
STATES = [(0, 1, 2, 0, 0), (1, -1, 0, 1, 1), (2, 1000, 600, 3, 2)]  # (번호, x, y, 방향, 상태), 진행률 없음
GOLDS = [(7, 1000, -2)]                                   # (금괴 번호, x, y), 음수 좌표도 복원하는지 확인
GOLD_COUNT = len(GOLDS)
MINED = [(0, 5), (1, 256), (2, 7)]                        # (플레이어 번호, 채굴 수), 256으로 u16 확인

# ---------------------------------------------------------------- 1) 값 전체 범위 왕복
def test_roundtrip_all_values():
    # 여러 인자를 받는 패킷 : (입력값, 예상 반환값, 본문 길이)
    # 금괴 1개 기준 GAME_START = 26 + 5 = 31B, GOLD_RESPAWN = 1 + 5 = 6B
    # STATE = 공통 정보 5B + 플레이어 7B x 3명 = 26B
    samples = {
        "StoC_GAME_START": ((180, COSTS, PLAYERS, GOLD_COUNT, GOLDS), (180, COSTS, PLAYERS, GOLD_COUNT, GOLDS), 31),
        "StoC_STATE": ((1800, 300, 4, STATES), (1800, 300, 4, STATES), 26),
        "StoC_GOLD_MINED": ((7, 2, 300), (7, 2, 300), 4),
        "StoC_GOLD_RESPAWN": ((GOLDS,), GOLDS, 6),
        "StoC_SHOP_RESULT": ((0, 4, 4, 300), (0, 4, 4, 300), 5),
        "StoC_GAME_END": ((300, MINED), (300, MINED), 11),
    }
    pairs = [("CtoS_INPUT",      p.pack_input,       p.unpack_input),
             ("CtoS_SHOP_BUY",   p.pack_shop_buy,    p.unpack_shop_buy),
             ("StoC_JOIN_OK",    p.pack_join_ok,     p.unpack_join_ok),
             ("StoC_LOBBY_STATE",p.pack_lobby_state, p.unpack_lobby_state),
             ("StoC_ERROR",      p.pack_error,       p.unpack_error),
             ("StoC_GAME_START", p.pack_game_start,  p.unpack_game_start),
             ("StoC_STATE",      p.pack_state,       p.unpack_state),
             ("StoC_GOLD_MINED", p.pack_gold_mined,  p.unpack_gold_mined),
             ("StoC_GOLD_RESPAWN",p.pack_gold_respawn,p.unpack_gold_respawn),
             ("StoC_SHOP_RESULT",p.pack_shop_result, p.unpack_shop_result),
             ("StoC_GAME_END",   p.pack_game_end,    p.unpack_game_end)]
    for name, pack, unpack in pairs:
        if name in samples:
            values, expected, size = samples[name]
            packet = pack(*values)                       # 입력값 튜플을 각 매개변수로 풀어서 전달
            ptype, length = p.unpack_header(packet[:3])
            assert ptype == p.packet_types[name], name
            assert length == size and len(packet) == 3 + size, name
            assert unpack(packet[3:3 + length]) == expected, name  # 헤더를 제외한 본문만 전달
            continue                                    # 아래 pack(v)는 값 하나를 받는 기존 5종용
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
    # 예상 바이트를 직접 비교해 pack/unpack 양쪽이 같은 실수를 해도 발견한다
    # 앞의 3바이트는 종류 1B + 본문 길이 2B이며, 여러 바이트 숫자는 big-endian
    assert p.pack_game_start(180, COSTS, PLAYERS, GOLD_COUNT, GOLDS) == bytes.fromhex(
        '67 00 1f 00 b4 00 0a 00 0e 00 18 00 28 '
        '00 00 01 00 02 01 ff ff 00 00 02 03 e8 02 58 01 07 03 e8 ff fe')
    assert p.pack_state(1800, 300, 4, STATES) == bytes.fromhex(
        '68 00 1a 07 08 01 2c 04 '
        '00 00 01 00 02 00 00 01 ff ff 00 00 01 01 02 03 e8 02 58 03 02')
    assert p.pack_gold_mined(7, 2, 300) == bytes([105, 0, 4, 7, 2, 1, 44])
    assert p.pack_gold_respawn(GOLDS) == bytes.fromhex('6a 00 06 01 07 03 e8 ff fe')
    assert p.pack_shop_result(0, 4, 4, 300) == bytes([107, 0, 5, 0, 4, 4, 1, 44])
    assert p.pack_game_end(300, MINED) == bytes.fromhex(
        '6c 00 0b 01 2c 00 00 05 01 01 00 02 00 07')
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
        result["got"] = read_packets(conn, 9)            # 기존 입력 3개 + 아래에 추가한 6종
        conn.close()
    t = threading.Thread(target=server); t.start()

    cli = socket.socket(); cli.connect(("127.0.0.1", port))
    # 3개를 한 덩어리로 붙여서 보낸다 (TCP 에서 패킷이 붙어서 도착하는 상황)
    blob = p.pack_input(p.KEY_W | p.KEY_D) + p.pack_shop_buy(p.ITEM_PICKAXE) + p.pack_input(0)
    # 고정 길이와 금괴 목록이 들어가는 가변 길이 패킷을 함께 전송한다
    blob += p.pack_game_start(180, COSTS, PLAYERS, GOLD_COUNT, GOLDS)
    blob += p.pack_state(1800, 300, 4, STATES)
    blob += p.pack_gold_mined(7, 2, 300)
    blob += p.pack_gold_respawn(GOLDS)
    blob += p.pack_shop_result(0, 4, 4, 300)
    blob += p.pack_game_end(300, MINED)
    # 그리고 아무 데서나 쪼개서 보낸다 (패킷이 쪼개져서 도착하는 상황)
    cli.sendall(blob[:2]); cli.sendall(blob[2:7]); cli.sendall(blob[7:])
    cli.close(); t.join(); srv.close()

    got = result["got"]
    assert [pt for pt, _ in got] == [1, 2, 1, 103, 104, 105, 106, 107, 108]
    assert p.unpack_input(got[0][1]) == 9
    assert p.unpack_shop_buy(got[1][1]) == 3
    assert p.unpack_input(got[2][1]) == 0
    assert p.unpack_game_start(got[3][1]) == (180, COSTS, PLAYERS, GOLD_COUNT, GOLDS)
    assert p.unpack_state(got[4][1]) == (1800, 300, 4, STATES)
    assert p.unpack_gold_mined(got[5][1]) == (7, 2, 300)
    assert p.unpack_gold_respawn(got[6][1]) == GOLDS
    assert p.unpack_shop_result(got[7][1]) == (0, 4, 4, 300)
    assert p.unpack_game_end(got[8][1]) == (300, MINED)
    print("3) 실제 TCP OK : 붙어서/쪼개져서 도착해도 9개 패킷을 정확히 복원")

# ---------------------------------------------------------------- 4) 잘못된 입력 거부
def test_rejects_bad_input():
    for unpack in (p.unpack_input, p.unpack_shop_buy, p.unpack_join_ok, p.unpack_lobby_state, p.unpack_error,
                   p.unpack_game_start, p.unpack_state, p.unpack_gold_mined, p.unpack_gold_respawn,
                   p.unpack_shop_result, p.unpack_game_end):
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
