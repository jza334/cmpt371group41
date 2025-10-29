import socket
import os
from email.utils import parsedate_to_datetime

HOST = "localhost"
PORT = 3652

#create server socket and listen on host:port
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"Web server running on http://localhost:{PORT}...")

while True:
    #accept connection and get client request
    client_conn, client_addr = server_socket.accept()
    request = client_conn.recv(1024).decode("utf-8")
    if not request:
        client_conn.close()
        continue

    #parse request
    lines = request.split("\n")
    request_line = lines[0].split()
    if len(request_line) < 3:
        client_conn.close()
        continue
    method, path, version = request_line
    headers = {l.split(": ")[0]: l.split(": ")[1] for l in lines[1:] if ": " in l} #make dictionary for easy access to hearer info

    #505 logic
    if version != "HTTP/1.1":
        response = "HTTP/1.1 505 HTTP Version Not Supported\n\n"
    else:
        filepath = path.strip("/")
        #404 logic
        if not os.path.exists(filepath):
            response = "HTTP/1.1 404 Not Found\n\n"
        #403 logic
        elif filepath.startswith("private/") or not os.access(filepath, os.R_OK): 
            #we couldn't zip a file with no read access for submission so we added a private/ dir at the servers main level that simulates restriction with this check
            response = "HTTP/1.1 403 Forbidden\n\n"
        #304 logic
        elif "If-Modified-Since" in headers:
            client_time = parsedate_to_datetime(headers["If-Modified-Since"]).timestamp()
            file_time = os.path.getmtime(filepath)
            if file_time <= client_time:
                response = "HTTP/1.1 304 Not Modified\n\n"
            # 200 
            else:
                with open(filepath, 'r') as file:
                    content = file.read()
                response = "HTTP/1.1 200 OK\n\n" + content
        #200 if nothing else
        else:
            with open(filepath, 'r') as file:
                content = file.read()
            response = "HTTP/1.1 200 OK\n\n" + content

    if isinstance(response, str):
        response = response.encode("utf-8")
    client_conn.sendall(response)
    client_conn.close()