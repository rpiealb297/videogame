from core import Socket
from server import GameState

class GameServer:
    def __init__(self):
        self.socket = Socket.Socket()
        self.socket.init()

        self.server = GameState.GameState()    
        self.server.start()    

    def start(self):
        while True:
            conn, addr = self.socket.waitConnection()
            self.server.acceptNewPlayer(conn, addr)

if __name__ == "__main__":
    GameServer().start()