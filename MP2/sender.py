from socket import *
from threading import *
import os
from email.utils import parsedate_to_datetime

HOST = "localhost"
APP_PORT = 1234
FRAME_SIZE = 512

#create server socket and listen on host:port
sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sender_socket.bind((HOST, PORT))
sender_socket.listen()
print(f"Sender running on http://localhost:{PORT}...")

class Sender:
    def __init__(self):
        self.app_socket = socket(AF_INET, SOCK_STREAM)
        self.send_socket = socket(AF_INET, SOCK_STREAM)
    
    def initial_state(self):
        self.app_socket.bind((HOST, APP_PORT))
        self.app_socket.listen()
        print(f"Sender waiting for application layer on http://localhost:{APP_PORT}...")

        while True:
            #accept connection and get data from application layer
            client_conn, client_addr = self.app_socket.accept()

            new_thread = Thread(target=client_handler, args=(client_conn,))
            print("Thread created. ")
            new_thread.start()

