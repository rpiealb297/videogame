import socket

class Socket:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port

    def init(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen()
        
        print(f"[SERVER] Corriendo en {self.host}:{self.port}")

    def waitConnection(self):
        return self.server.accept()
