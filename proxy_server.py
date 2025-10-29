from socket import *
import os
from email.utils import parsedate_to_datetime

PROXY_HOST = "localhost"
PROXY_PORT = 1234
SERVER_HOST = "localhost"
SERVER_PORT = 3652

#create server socket and listen on host:port
proxy_socket = socket(AF_INET, SOCK_STREAM)
proxy_socket.bind((PROXY_HOST, PROXY_PORT))
proxy_socket.listen()
print(f"Web server running on http://localhost:{PROXY_PORT}...")

# This class acts like a cache for the proxy server. 
class Cache:
    def __init__(self, max_size):
        self.max_size = max_size
        self.cache = dict()
        self.keyNum = 0

    # This function takes in a request, and searches to see if the request is in the cache. If 
    # the request is in the cache, the LRU indicator is updated, then the content is returned.
    # Otherwise, None is returned.
    def check_cache(self, target):
        for key, value in self.cache.items():
            request, content = value
            if target == request:
                print("Cache hit!\n")
                self._replace(key, request, content)
                return content
        print("Cache Miss!\n")
        return None
    
    # This functions takes in a request and a content, and stores it in the cache. If the cache
    # is full, the least recently used element is evicted. 
    def set(self, request, content):
        if (len(self.cache) >= self.max_size):
            self._evict()    
        self.cache[self.keyNum] = (request, content)
        self.keyNum += 1

    def _evict(self):
        keys = self.cache.keys()
        min_key = min(keys)
        self.cache.pop(min_key)

    # This function takes a key, request and content, and updates the LRU value for the entry.
    def _replace(self, key, request, content):
        request, content = self.cache.pop(key)
        self.set(request, content)

    # This function takes in a target request, and searches through the cache to try and find a 
    # request that is *matching*. In this context, matching refers to having the same values 
    # without the headers. If a match is found, the LRU value is updated. Otherwise, the request
    # is added to the cache. 
    def replace304(self, target, tContent):
        replaced = False
        for key, value in cache.cache.items():
            request, content = value
            stripped = request.split("\n")[0]
            if stripped == target:
                self._replace(key, target, content)
                replaced = True
                break
        if replaced == False:
            self.set(target, tContent)

    # for debugging
    def print(self):
        print(f"Cache size: {len(self.cache)}")
        for key, value in self.cache.items():
            if isinstance(value, tuple) and len(value) == 2:
                request, content = value
                print(f"{key}: \n{request} \n{content} \n")
            else:
                print(f"Unexpected value format for key {key}: {len(value)}")

def getServerResponse(request):
    proxy_to_server_socket = socket(AF_INET, SOCK_STREAM)
    proxy_to_server_socket.connect((SERVER_HOST, SERVER_PORT))
    proxy_to_server_socket.send(request)
    response = proxy_to_server_socket.recv(1024)
    proxy_to_server_socket.close()
    return response

cache = Cache(2)

while True:
    #accept connection and get client request
    client_conn, client_addr = proxy_socket.accept()
    request = client_conn.recv(1024)

    if not request:
        client_conn.close()
        continue

    # Convert byte form
    request_string = request.decode("utf-8")

    # parse request
    lines = request_string.split("\n")
    request_line = lines[0].split()
    if len(request_line) < 3:
        client_conn.close()
        continue
    method, path, version = request_line
    headers = {l.split(": ")[0]: l.split(": ")[1] for l in lines[1:] if ": " in l} #make dictionary for easy access to hearer info

    # 505 logic
    if version != "HTTP/1.1":
        response = "HTTP/1.1 505 HTTP Version Not Supported\n\n"
    elif "If-Modified-Since" in headers:
        response = getServerResponse(request)
        response_string = response.decode("utf-8")

        target = request_string.split("\n")[0]
        content = response_string.split("\n\n",1)[1]
        
        cache.replace304(target, content)
    else:
        response_content = cache.check_cache(request_string)
        if response_content:
            if isinstance(response_content, str):
                response_string = "HTTP/1.1 200 OK\n\n" + response_content
        else:
            response = getServerResponse(request)

            response_string = response.decode("utf-8")
            response_code = response_string.split("\n")[0].split(" ")[1]

            if response_code in ["403", "404", "505"]:
                pass
            elif response_code == "200":
                content = response_string.split("\n\n",1)[1]
                cache.set(request_string, content)

    
    if isinstance(response, str):
        response = response.encode("utf-8")
    
    client_conn.sendall(response)
    client_conn.close()
    
