import socket
import threading
import time
import struct

#host/port
HOST = "localhost"
PORT = 1234

#globals
PACKET_HEADER = "!IIHH"  #seq, ack, flags, window I=4bytes H=2bytes
MAX_PAYLOAD = 1024
FLAG_SYN = 0x1
FLAG_ACK = 0x2
FLAG_FIN = 0x4
TIMEOUT = 1

def make_packet(seq, ack, flags, window, payload=b''):
    header = struct.pack(PACKET_HEADER, seq, ack, flags, window)
    return header + payload

def parse_packet(packet):
    header = packet[:12]
    seq, ack, flags, window = struct.unpack(PACKET_HEADER, header)
    payload = packet[12:]
    return seq, ack, flags, window, payload

#PRTP Sender
class PRTPSender:
    def __init__(self, server_ip, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_addr = (server_ip, server_port)
        self.seq = 0
        self.ack = 0
        self.cwnd = 1
        self.ssthresh = 4
        self.window = 16
        self.lock = threading.Lock()
        self.unacked = {}
        self.connected = False

    #establish connection
    def connect(self):
        print("[Sender] Sending SYN...")
        syn_pkt = make_packet(self.seq, 0, FLAG_SYN, self.window)
        self.sock.sendto(syn_pkt, self.server_addr)
        while True:
            data, _ = self.sock.recvfrom(2048)
            seq, ack, flags, window, _ = parse_packet(data)
            if flags & FLAG_SYN and flags & FLAG_ACK:
                print("[Sender] Received SYN+ACK")
                self.ack = seq + 1
                self.seq += 1
                ack_pkt = make_packet(self.seq, self.ack, FLAG_ACK, self.window)
                self.sock.sendto(ack_pkt, self.server_addr)
                print("[Sender] Connection established")
                self.connected = True
                break

    #send data to receiver
    def send_data(self, data):
        for i in range(0, len(data), MAX_PAYLOAD):
            chunk = data[i:i+MAX_PAYLOAD]
            packet = make_packet(self.seq, 0, 0, self.window, chunk)
            self.sock.sendto(packet, self.server_addr)
            print(f"[Sender] Sent seq={self.seq}, {len(chunk)} bytes")
            with self.lock:
                self.unacked[self.seq] = (packet, time.time())
            self.seq += 1

    #retransmit if needed
    def handle_retransmit(self):
        while True:
            time.sleep(0.1)
            now = time.time()
            with self.lock:
                for seq, (pkt, t) in list(self.unacked.items()):
                    if now - t > TIMEOUT:
                        print(f"[Sender] Timeout! Retransmitting seq={seq}")
                        self.sock.sendto(pkt, self.server_addr)
                        self.unacked[seq] = (pkt, now)
                        self.ssthresh = max(self.cwnd // 2, 1)
                        self.cwnd = max(self.cwnd // 2, 1)
                        print(f"[Sender] cwnd reduced to {self.cwnd}")

    #handle ACKs
    def handle_ack(self):
        while True:
            data, _ = self.sock.recvfrom(2048)
            seq, ack, flags, window, _ = parse_packet(data)
            if flags & FLAG_ACK:
                with self.lock:
                    to_delete = [s for s in self.unacked if s < ack]
                    for s in to_delete:
                        del self.unacked[s]
                        print(f"[Sender] Received ACK for seq={s}")
                #congestion control
                if self.cwnd < self.ssthresh:
                    self.cwnd += 1
                    print(f"[Sender] cwnd increased to {self.cwnd}")
                else:
                    self.cwnd += 1 / self.cwnd
                    print(f"[Sender] cwnd increased to {self.cwnd}")

    #close connection
    def close(self):
        fin_pkt = make_packet(self.seq, 0, FLAG_FIN, self.window)
        print("[Sender] Sending FIN...")
        retries = 0
        max_retries = 5
        while retries < max_retries:
            self.sock.sendto(fin_pkt, self.server_addr)
            try:
                self.sock.settimeout(TIMEOUT)
                data, _ = self.sock.recvfrom(2048)
                seq, ack, flags, window, _ = parse_packet(data)
                if flags & FLAG_ACK:
                    print("[Sender] FIN acknowledged, connection closed")
                    self.sock.settimeout(None)
                    return
            except socket.timeout:
                retries += 1
                print(f"[Sender] Timeout waiting for FIN-ACK, retrying ({retries})...")
        print("[Sender] FIN not acknowledged, closing anyway")
        self.sock.settimeout(None)

if __name__ == "__main__":
    sender = PRTPSender(HOST, PORT)
    sender.connect()

    threading.Thread(target=sender.handle_retransmit, daemon=True).start()
    threading.Thread(target=sender.handle_ack, daemon=True).start()

    #send 8 packets (can change range to change amount of packets)
    for i in range(1, 9):
        message = f"Message number {i}".encode()
        sender.send_data(message)

    time.sleep(2)
    sender.close()
