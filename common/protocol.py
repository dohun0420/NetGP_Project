# 통신에 필요한 패킷정의
import struct

# 1	CtoS_INPUT	키 상태가 바뀔 때 (+ 0.5초마다)	지금 눌린 키(W/A/S/D/Space)를 서버에 알린다
# 2	CtoS_SHOP_BUY	상점에서 구매할 때	사고 싶은 아이템을 서버에 요청한다
# 101	StoC_JOIN_OK	접속 직후	접속 성공. 내 번호(= 내 색상)를 알려준다
# 102	StoC_LOBBY_STATE	대기 인원이 바뀔 때	로비에서 기다리는 인원 수 (n / 3)
# 103	StoC_GAME_START	3명이 모였을 때 게임 시작 : 금괴 위치 · 시작 위치 · 제한 시간 · 아이템 가격
# 104	StoC_STATE	게임 중 매 틱 (20 Hz)	현재 상태 : 플레이어 위치 · 남은 시간 · 팀 금괴 · 아이템 등급
# 105	StoC_GOLD_MINED	채굴이 끝났을 때 어느 금괴를 누가 캤는지, 팀 금괴 수
# 106	StoC_GOLD_RESPAWN	금괴를 전부 캤을 때 새로 생긴 금괴 위치
# 107	StoC_SHOP_RESULT	구매 요청을 처리한 뒤 구매 성공 또는 실패 여부를 알려준다. (성공 시 아이템 등급과 남은 금액)
# 108	StoC_GAME_END	제한 시간이 끝났을 때	최종 금괴 수와 플레이어별 채굴 수 (이후 서버가 연결 종료)
# 109	StoC_ERROR	접속 거부 또는 게임 중 한 명이 나갔을 때	이유 번호를 알려준다. 클라이언트는 에러 메시지를 표시하고 접속을 종료

packet_types = {
    "CtoS_INPUT": 1,
    "CtoS_SHOP_BUY": 2,
    "StoC_JOIN_OK": 101,
    "StoC_LOBBY_STATE": 102,
    "StoC_GAME_START": 103,
    "StoC_STATE": 104,
    "StoC_GOLD_MINED": 105,
    "StoC_GOLD_RESPAWN": 106,
    "StoC_SHOP_RESULT": 107,
    "StoC_GAME_END": 108,
    "StoC_ERROR": 109
}


def pack_header(packet_type, payload_length):  #패킷 종류와 실제 보낼 데이터 길이
    return bytes([packet_type]) + payload_length.to_bytes(2, 'big') # big-endian
def unpack_header(header_bytes):
    packet_type = header_bytes[0]
    payload_length = int.from_bytes(header_bytes[1:3], 'big') # big-endian
    return packet_type, payload_length


# =====================================================================
# 패킷 pack / unpack : 클라이언트 요청 및 서버 응답 전체 11종
#   - pack_xxx(...)   : 값 -> 전송할 바이트 (헤더 + 본문)
#   - unpack_xxx(payload) : 본문 바이트 -> 값  (헤더는 unpack_header 로 먼저 읽은 뒤 본문만 넘긴다)
# =====================================================================
BYTE_ORDER = '>'   # 본문 바이트 순서. 헤더(pack_header)와 같은 big-endian 으로 통일

# CtoS_INPUT 의 key_flags 비트 (눌린 키의 값을 더해서 보낸다)
KEY_W = 1
KEY_A = 2
KEY_S = 4
KEY_D = 8
KEY_SPACE = 16

# CtoS_SHOP_BUY 의 item_id
ITEM_GLOVE = 1
ITEM_SHOVEL = 2
ITEM_PICKAXE = 3
ITEM_DRILL = 4

# StoC_ERROR 의 reason
ERR_ROOM_FULL = 1       # 방이 가득 참 (접속 거부)
ERR_GAME_RUNNING = 2    # 게임이 이미 진행 중 (접속 거부)
ERR_PLAYER_LEFT = 3     # 다른 플레이어의 접속이 끊겨 게임 강제 종료


def _make_packet(name, payload):
    return pack_header(packet_types[name], len(payload)) + payload


def _check_len(name, payload, size):
    if len(payload) != size:
        raise ValueError(f"{name}: 본문 길이 오류 (받은 {len(payload)}B, 필요 {size}B)")


# ---- 1  CtoS_INPUT : 눌린 키 상태 (key_flags u8) --------------------------
def pack_input(key_flags):
    return _make_packet("CtoS_INPUT", struct.pack(BYTE_ORDER + 'B', key_flags))

def unpack_input(payload):
    _check_len("CtoS_INPUT", payload, 1)
    (key_flags,) = struct.unpack(BYTE_ORDER + 'B', payload)
    return key_flags


# ---- 2  CtoS_SHOP_BUY : 구매할 아이템 번호 (item_id u8) -------------------
def pack_shop_buy(item_id):
    return _make_packet("CtoS_SHOP_BUY", struct.pack(BYTE_ORDER + 'B', item_id))

def unpack_shop_buy(payload):
    _check_len("CtoS_SHOP_BUY", payload, 1)   # item_id 범위(1~4) 검증은 서버가 하고 SHOP_RESULT 로 응답
    (item_id,) = struct.unpack(BYTE_ORDER + 'B', payload)
    return item_id


# ---- 101  StoC_JOIN_OK : 내 번호 = 내 색상 (player_id u8) -----------------
def pack_join_ok(player_id):
    return _make_packet("StoC_JOIN_OK", struct.pack(BYTE_ORDER + 'B', player_id))

def unpack_join_ok(payload):
    _check_len("StoC_JOIN_OK", payload, 1)
    (player_id,) = struct.unpack(BYTE_ORDER + 'B', payload)
    return player_id


# ---- 102  StoC_LOBBY_STATE : 로비 대기 인원 (waiting_count u8) -----------
def pack_lobby_state(waiting_count):
    return _make_packet("StoC_LOBBY_STATE", struct.pack(BYTE_ORDER + 'B', waiting_count))

def unpack_lobby_state(payload):
    _check_len("StoC_LOBBY_STATE", payload, 1)
    (waiting_count,) = struct.unpack(BYTE_ORDER + 'B', payload)
    return waiting_count


# ---- 103  StoC_GAME_START : 제한 시간, 가격표, 플레이어, 금괴 위치 --------
def pack_game_start(time_limit, costs, players, golds):
    payload = struct.pack(BYTE_ORDER + 'H4H', time_limit, *costs)
    for player in players:
        payload += struct.pack(BYTE_ORDER + 'Bhh', *player)
    _check_len("StoC_GAME_START", payload, 25)
    payload += struct.pack(BYTE_ORDER + 'B', len(golds))
    for gold in golds:
        payload += struct.pack(BYTE_ORDER + 'Bhh', *gold)
    return _make_packet("StoC_GAME_START", payload)


def unpack_game_start(payload):
    _check_len("StoC_GAME_START", payload[:26], 26)    # count 를 읽을 고정 부분 확인
    gold_count = payload[25]
    _check_len("StoC_GAME_START", payload, 26 + 5 * gold_count)
    (time_limit,) = struct.unpack(BYTE_ORDER + 'H', payload[:2])
    costs = struct.unpack(BYTE_ORDER + '4H', payload[2:10])
    players = [struct.unpack(BYTE_ORDER + 'Bhh', payload[10 + 5 * i:15 + 5 * i])
               for i in range(3)]
    golds = [struct.unpack(BYTE_ORDER + 'Bhh', payload[26 + 5 * i:31 + 5 * i])
             for i in range(gold_count)]
    return time_limit, costs, players, golds


# ---- 104  StoC_STATE : 남은 시간, 팀 금괴, 등급, 플레이어 상태 -----------
# dir : 0 아래 / 1 왼쪽 / 2 오른쪽 / 3 위
# state : 0 대기 / 1 이동 / 2 채굴
def pack_state(remain_x10, team_gold, item_level, players):
    payload = struct.pack(BYTE_ORDER + 'HHB', remain_x10, team_gold, item_level)
    for player in players:
        payload += struct.pack(BYTE_ORDER + 'BhhBB', *player)
    _check_len("StoC_STATE", payload, 26)
    return _make_packet("StoC_STATE", payload)


def unpack_state(payload):
    _check_len("StoC_STATE", payload, 26)
    remain_x10, team_gold, item_level = struct.unpack(BYTE_ORDER + 'HHB', payload[:5])
    players = [struct.unpack(BYTE_ORDER + 'BhhBB', payload[5 + 7 * i:12 + 7 * i])
               for i in range(3)]
    return remain_x10, team_gold, item_level, players


# ---- 105  StoC_GOLD_MINED : 채굴 완료 (spot_id u8, player_id u8, team_gold u16) ----
def pack_gold_mined(spot_id, player_id, team_gold):
    payload = struct.pack(BYTE_ORDER + 'BBH', spot_id, player_id, team_gold)
    return _make_packet("StoC_GOLD_MINED", payload)


def unpack_gold_mined(payload):
    _check_len("StoC_GOLD_MINED", payload, 4)
    spot_id, player_id, team_gold = struct.unpack(BYTE_ORDER + 'BBH', payload)
    return spot_id, player_id, team_gold


# ---- 106  StoC_GOLD_RESPAWN : 금괴 재생성 (count u8, golds[count]) -------
# golds : (spot_id u8, x i16, y i16) 목록
def pack_gold_respawn(golds):
    payload = struct.pack(BYTE_ORDER + 'B', len(golds))
    for gold in golds:
        payload += struct.pack(BYTE_ORDER + 'Bhh', *gold)
    return _make_packet("StoC_GOLD_RESPAWN", payload)


def unpack_gold_respawn(payload):
    _check_len("StoC_GOLD_RESPAWN", payload[:1], 1)
    count = payload[0]
    _check_len("StoC_GOLD_RESPAWN", payload, 1 + 5 * count)
    golds = [struct.unpack(BYTE_ORDER + 'Bhh', payload[1 + 5 * i:6 + 5 * i])
             for i in range(count)]
    return golds


# ---- 107  StoC_SHOP_RESULT : 구매 결과 (result u8, item_id u8, item_level u8, team_gold u16) ----
# result : 0 성공 / 1 금괴 부족 / 2 현재 등급 이하 / 3 잘못된 번호
def pack_shop_result(result, item_id, item_level, team_gold):
    payload = struct.pack(BYTE_ORDER + 'BBBH', result, item_id, item_level, team_gold)
    return _make_packet("StoC_SHOP_RESULT", payload)


def unpack_shop_result(payload):
    _check_len("StoC_SHOP_RESULT", payload, 5)
    result, item_id, item_level, team_gold = struct.unpack(BYTE_ORDER + 'BBBH', payload)
    return result, item_id, item_level, team_gold


# ---- 108  StoC_GAME_END : 종료 (final_gold u16, players[3]) -------------
# mined 는 개인별 채굴 수
def pack_game_end(final_gold, players):
    payload = struct.pack(BYTE_ORDER + 'H', final_gold)
    for player in players:
        payload += struct.pack(BYTE_ORDER + 'BH', *player)
    _check_len("StoC_GAME_END", payload, 11)
    return _make_packet("StoC_GAME_END", payload)


def unpack_game_end(payload):
    _check_len("StoC_GAME_END", payload, 11)
    (final_gold,) = struct.unpack(BYTE_ORDER + 'H', payload[:2])
    players = [struct.unpack(BYTE_ORDER + 'BH', payload[2 + 3 * i:5 + 3 * i])
               for i in range(3)]
    return final_gold, players


# ---- 109  StoC_ERROR : 에러 사유 (reason u8) -----------------------------
def pack_error(reason):
    return _make_packet("StoC_ERROR", struct.pack(BYTE_ORDER + 'B', reason))

def unpack_error(payload):
    _check_len("StoC_ERROR", payload, 1)
    (reason,) = struct.unpack(BYTE_ORDER + 'B', payload)
    return reason


if __name__ == "__main__":
    # 테스트
    packet_type = packet_types["CtoS_INPUT"]
    payload_length = 10
    header = pack_header(packet_type, payload_length)
    print("Packed Header:", header)

    unpacked_type, unpacked_length = unpack_header(header)
    print("Unpacked Type:", unpacked_type)
    print("Unpacked Length:", unpacked_length)


    # ---- pack / unpack 왕복 테스트 ----
    def roundtrip(pack, unpack, value, name):
        packet = pack(value)
        ptype, length = unpack_header(packet[:3])        # 헤더 먼저 읽고
        payload = packet[3:3 + length]                    # 본문만 잘라서
        assert ptype == packet_types[name], name
        assert len(packet) == 3 + length, name
        assert unpack(payload) == value, name
        print(f"{name:18s} {value!r:>4} -> {packet.hex(' ')}")

    roundtrip(pack_input, unpack_input, KEY_W | KEY_D, "CtoS_INPUT")          # W + D = 9
    roundtrip(pack_shop_buy, unpack_shop_buy, ITEM_PICKAXE, "CtoS_SHOP_BUY")
    roundtrip(pack_join_ok, unpack_join_ok, 2, "StoC_JOIN_OK")
    roundtrip(pack_lobby_state, unpack_lobby_state, 3, "StoC_LOBBY_STATE")
    roundtrip(pack_error, unpack_error, ERR_PLAYER_LEFT, "StoC_ERROR")

    try:                                                   # 길이가 틀린 본문은 거부해야 한다
        unpack_input(b"\x01\x02")
    except ValueError as e:
        print("잘못된 본문 거부 OK:", e)
