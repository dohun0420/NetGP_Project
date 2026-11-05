import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common import protocol

# test
if __name__ == '__main__':
    # 테스트
    packet_type = protocol.packet_types["CtoS_INPUT"]
    payload_length = 10
    header = protocol.pack_header(packet_type, payload_length)
    print("Packed Header:", header)

    unpacked_type, unpacked_length = protocol.unpack_header(header)
    print("Unpacked Type:", unpacked_type)
    print("Unpacked Length:", unpacked_length)