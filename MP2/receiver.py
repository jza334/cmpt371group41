import socket
import struct
import random

#host/port
HOST = "localhost"
PORT = 1234

#globals
PACKET_HEADER = "!IIHH"
MAX_PAYLOAD = 1024
FLAG_SYN = 0x1
FLAG_ACK = 0x2
FLAG_FIN = 0x4

#simulate error / loss
LOSS_PROB = 0.1
ERROR_PROB = 0.1

def parse_packet(packet):
    header = packet[:12]
    seq, ack, flags, window = struct.unpack(PACKET_HEADER, header)
    payload = packet[12:]
    return seq, ack, flags, window, payload

def make_packet(seq, ack, flags, window, payload=b''):
    header = struct.pack(PACKET_HEADER, seq, ack, flags, window)
    return header + payload

#PRTP Receiver
class PRTPReceiver:
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))
        self.expected_seq = 1
        self.window = 16
        self.client_addr = None
        self.connected = False
        self.buffer = {}  # seq -> payload
        self.drop = 0

    def start(self):
        print(f"Receiver running on http://{HOST}:{PORT}...")
        while True:
            data, addr = self.sock.recvfrom(2048)
            seq, ack, flags, window, payload = parse_packet(data)

            #connection establishment
            if not self.connected:
                if flags & FLAG_SYN:
                    print("[Receiver] Received SYN, sending SYN+ACK")
                    self.client_addr = addr
                    syn_ack = make_packet(0, seq+1, FLAG_SYN | FLAG_ACK, self.window)
                    self.sock.sendto(syn_ack, addr)
                    print("[Receiver] SYN+ACK sent")
                elif flags & FLAG_ACK:
                    self.connected = True
                    self.expected_seq = 1
                    print("[Receiver] Connection established with client")
                continue

            #FIN handling
            if flags & FLAG_FIN:
                ack_pkt = make_packet(0, seq+1, FLAG_ACK, self.window)
                self.sock.sendto(ack_pkt, addr)
                print("[Receiver] Received FIN, sent ACK, closing connection")
                break

            #data handling
            if seq >= self.expected_seq:
                if seq == self.expected_seq:
                    #in-order packet
                    print(f"[Receiver] Received seq={seq}, payload={payload}")
                    self.expected_seq += 1

                    #deliver buffered in-order packets
                    while self.expected_seq in self.buffer:
                        self.buffer.pop(self.expected_seq)
                        self.expected_seq += 1
                else:
                    #out-of-order buffer it
                    if random.random() < LOSS_PROB:
                        self.drop = 1
                    if self.drop == 0:
                        self.buffer[seq] = payload
                        print(f"[Receiver] Buffered out-of-order seq={seq}, payload={payload}")

            #send ACK with SACK info
            if self.buffer:
                sack_payload = ",".join(str(s) for s in self.buffer.keys()).encode()
            else:
                sack_payload = b''
            ack_pkt = make_packet(0, self.expected_seq, FLAG_ACK, self.window, sack_payload)
            if self.drop == 1:
                print(f"[Receiver] Simulating loss of ACK for seq={seq}")
            else:
                self.sock.sendto(ack_pkt, addr)
                print(f"[Receiver] Sent ACK for seq={seq} with SACK={list(self.buffer.keys())}")
            self.drop = 0

if __name__ == "__main__":
    receiver = PRTPReceiver(PORT)
    receiver.start()
