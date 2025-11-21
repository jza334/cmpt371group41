import socket
from threading import *
import os
from email.utils import parsedate_to_datetime

HOST = "localhost"
PORT = 3652
FRAME_SIZE = 512

#create server socket and listen on host:port
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Web server running on http://localhost:{PORT}...")

def client_handler(client_conn):
    try:
        request = client_conn.recv(1024).decode("utf-8")
        if not request:
            client_conn.close()
            return

        #parse request
        lines = request.split("\n")
        request_line = lines[0].split()
        if len(request_line) < 3:
            client_conn.close()
            return
        method, path, version = request_line
        headers = {l.split(": ")[0]: l.split(": ")[1] for l in lines[1:] if ": " in l} #make dictionary for easy access to hearer info

        #505 logic
        if version != "HTTP/1.1":
                client_conn.sendall(b"HTTP/1.1 505 HTTP Version Not Supported\n\n")
                client_conn.close()
                return
        
        filepath = path.strip("/")
        #404 logic
        if not os.path.exists(filepath):
            client_conn.sendall(b"HTTP/1.1 404 Not Found\n\n")
            client_conn.close()
            return
        
        #403 logic
        if filepath.startswith("private/") or not os.access(filepath, os.R_OK):
            #we couldn't zip a file with no read access for submission so we added a private/ dir at the servers main level that simulates restriction with this check
            client_conn.sendall(b"HTTP/1.1 403 Forbidden\n\n")
            client_conn.close()
            return
        
        #304 logic
        send_file = True
        if "If-Modified-Since" in headers:
            client_time = parsedate_to_datetime(headers["If-Modified-Since"]).timestamp()
            file_time = os.path.getmtime(filepath)
            if file_time <= client_time:
                # 304 Not Modified, no need to send file content
                client_conn.sendall(b"HTTP/1.1 304 Not Modified\n\n")
                with open(filepath, 'rb') as file:
                    while True:
                        chunk = file.read(FRAME_SIZE)
                        if not chunk:
                            break
                        client_conn.sendall(chunk)
                send_file = False

        #200 logic
        if send_file:
            client_conn.sendall(b"HTTP/1.1 200 OK\n\n")
            #hol fix
            with open(filepath, 'rb') as file:
                while True:
                    chunk = file.read(FRAME_SIZE)
                    if not chunk:
                        break
                    client_conn.sendall(chunk)
        
        client_conn.close()

    except Exception as e:
        print("Error:", e)
        client_conn.close()


while True:
    #accept connection and get client request
    client_conn, client_addr = server_socket.accept()

    new_thread = Thread(target=client_handler, args=(client_conn,))
    print("Thread created. ")
    new_thread.start()
