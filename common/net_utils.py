from common import protocol

# 헤더를 포함한 패킷 하나의 최대 크기 (4KB)
MAX_PACKET = 4096


class PacketBuffer:
    def __init__(self):
        self.buf = bytearray()    

    def feed(self, data):
        self.buf.extend(data)
        packets = []
        while len(self.buf) >= 3:        # 헤더가 전부 도착했을 때만 길이를 읽는다.
            # 헤더 : 종류 1B + 본문 길이 2B (big-endian)
            _, payload_length = protocol.unpack_header(self.buf[:3])
            size = 3 + payload_length
            if size > MAX_PACKET:
                raise ValueError(f"패킷 길이 오류 (전체 {size}B, 최대 {MAX_PACKET}B)")
            if len(self.buf) < size:
                break                   # 아직 덜 도착한 패킷은 다음 feed() 까지 보관한다.
            packets.append(bytes(self.buf[:size]))
            del self.buf[:size]
        return packets


def send_packet(sock, packet):
    sock.sendall(packet)
