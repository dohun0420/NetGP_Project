# 통신에 필요한 패킷정의

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

if __name__ == "__main__":
    # 테스트
    packet_type = packet_types["CtoS_INPUT"]
    payload_length = 10
    header = pack_header(packet_type, payload_length)
    print("Packed Header:", header)

    unpacked_type, unpacked_length = unpack_header(header)
    print("Unpacked Type:", unpacked_type)
    print("Unpacked Length:", unpacked_length)
