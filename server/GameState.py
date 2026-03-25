import socket
import threading
import json

class GameState:
    def __init__(self):
        self.clients = {} 
        self.players_data = {} 
    
    def start(self):
        try:
            with open('data/mapa.json', 'r') as f:
                self.map_data = json.load(f)
        except:
            self.map_data = {"width": 800, "height": 600, "objects": []}

    def acceptNewPlayer(self,conn, addr):
        threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

    def broadcast(self, message_dict):
        payload = (json.dumps(message_dict) + "\n").encode()
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.send(payload)
            except:
                self.remove_client(client_socket)

    def remove_client(self, conn):
        if conn in self.clients:
            pid = self.clients[conn]
            print(f"[DESCONECTADO] {pid} salió.")
            if pid in self.players_data: del self.players_data[pid]
            del self.clients[conn]
            conn.close()

    def handle_client(self, conn, addr):
        player_id = f"User_{addr[1]}"
        self.clients[conn] = player_id
        
        # INICIALIZACIÓN COMPLETA
        self.players_data[player_id] = {
            "pos": {"x": 100, "y": 100}, 
            "anim_state": "idle", 
            "direction": 0
        }
        
        conn.send((json.dumps({"type": "init", "map": self.map_data, "id": player_id}) + "\n").encode())

        while True:
            try:
                data = conn.recv(2048).decode()
                if not data: break
                
                messages = data.strip().split('\n')
                for m in messages:
                    if not m: continue
                    msg = json.loads(m)
                    
                    if msg["type"] == "update":
                        if player_id in self.players_data:
                            self.players_data[player_id].update({
                                "pos": msg["pos"],
                                "anim_state": msg.get("anim_state", "idle"),
                                "direction": msg.get("direction", 0)
                            })
                        # Responder con el estado de TODOS
                        conn.send((json.dumps({"type": "sync", "players": self.players_data}) + "\n").encode())
                    
                    elif msg["type"] == "chat":
                        self.broadcast({"type": "chat", "user": player_id, "text": msg["text"]})
            except: break
        self.remove_client(conn)    
