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

#per-client connection state
class ClientState:
    def __init__(self):
        self.expected_seq = 1
        self.window = 16
        self.connected = False
        self.buffer = {}  #seq -> payload
        self.drop = 0

#PRTP Receiver
class PRTPReceiver:
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))
        self.clients = {}  #addr -> ClientState

    def start(self):
        print(f"Receiver running on http://{HOST}:{PORT}...")
        while True:
            data, addr = self.sock.recvfrom(2048)
            seq, ack, flags, window, payload = parse_packet(data)

            #get or create client state
            if addr not in self.clients:
                self.clients[addr] = ClientState()
            client = self.clients[addr]

            #connection establishment
            if not client.connected:
                if flags & FLAG_SYN:
                    print(f"[Receiver] Received SYN, sending SYN+ACK")
                    syn_ack = make_packet(0, seq+1, FLAG_SYN | FLAG_ACK, client.window)
                    self.sock.sendto(syn_ack, addr)
                    print(f"[Receiver] SYN+ACK sent")
                elif flags & FLAG_ACK:
                    client.connected = True
                    client.expected_seq = 1
                    print(f"[Receiver] Connection established with client")
                continue

            #FIN handling
            if flags & FLAG_FIN:
                ack_pkt = make_packet(0, seq+1, FLAG_ACK, client.window)
                self.sock.sendto(ack_pkt, addr)
                print(f"[Receiver] Received FIN, sent ACK, closing connection")
                del self.clients[addr]
                continue

            #data handling
            if seq >= client.expected_seq:
                if seq == client.expected_seq:
                    #in-order packet
                    print(f"[Receiver] Received seq={seq}, payload={payload}")
                    client.expected_seq += 1

                    #deliver buffered in-order packets
                    while client.expected_seq in client.buffer:
                        print(f"[Receiver] Delivered buffered seq={client.expected_seq}")
                        client.buffer.pop(client.expected_seq)
                        client.expected_seq += 1
                else:
                    # out-of-order buffer it
                    if random.random() < LOSS_PROB:
                        client.drop = 1
                    if client.drop == 0:
                        client.buffer[seq] = payload
                        print(f"[Receiver] Buffered out-of-order seq={seq}, payload={payload}")

            #send ACK with SACK info
            if client.buffer:
                sack_payload = ",".join(str(s) for s in client.buffer.keys()).encode()
            else:
                sack_payload = b''
            ack_pkt = make_packet(0, client.expected_seq, FLAG_ACK, client.window, sack_payload)
            if client.drop == 1:
                print(f"[Receiver] Simulating loss of ACK for seq={seq}")
            else:
                self.sock.sendto(ack_pkt, addr)
                print(f"[Receiver] Sent ACK for seq={seq} with SACK={list(client.buffer.keys())}")
            client.drop = 0

if __name__ == "__main__":
    receiver = PRTPReceiver(PORT)
    receiver.start()
