import socket
import threading
from typing import Callable, Dict, Optional

from ..domain.models import Message

# UDP TRANSPORT
class UDPHandler:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def broadcast(self, msg: Message, port: int):
        data = msg.serialize()
        self.socket.sendto(data, ("<broadcast>", port))

    def listen(self, port: int, callback: Callable[[Message], None]):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Added resusddr
        self.socket.bind(("", port))

        def loop():
            while True:
                data, _ = self.socket.recvfrom(4096)
                msg = Message.deserialize(data)
                callback(msg)

        threading.Thread(target=loop, daemon=True).start()

# TCP CONNECTION
class TCPConnection:
    def __init__(self, sock: socket.socket, ip = '127.0.0.1', port = 5001):
        self.socket = sock
        self.ip = ip
        self.port = port

    def send(self, msg: Message):
        payload = msg.serialize()
        length = len(payload).to_bytes(4, "big")
        self.socket.sendall(length + payload)

    def receive(self) -> Optional[Message]:
        length_bytes = self._recv_exact(4)
        if not length_bytes:
            return None

        length = int.from_bytes(length_bytes, "big")
        payload = self._recv_exact(length)
        if payload is None:
            return None

        return Message.deserialize(payload)

    def _recv_exact(self, size: int) -> Optional[bytes]:
        data = b""
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def close(self):
        self.socket.close()

    def stringify(self):
        return str(self.ip) + ' ' + str(self.port)


# CONNECTION MANAGER
class ConnectionManager:
    def __init__(self):
        self.active_connections_peer_to_peer: Dict[str, TCPConnection] = {}
        self.active_connections_server_to_client: Dict[str, TCPConnection] = {}

    # stringify to transmit the object to other peers
    def stringify(self):
        modified = {}
        for i in self.active_connections_peer_to_peer.keys():
            modified[i] = self.active_connections_peer_to_peer[i].stringify()
        return json.dumps(modified)

    # ---------- connection helpers ----------



    def wrap_socket(self, sock: socket.socket, ip = '127.0.0.1'. port = 5001) -> TCPConnection:
        return TCPConnection(sock,ip,port)

    # ---------- async receive ----------

    def listen_to_connection(
        self,
        conn: TCPConnection,
        callback: Callable[[Message], None],
    ):
        def loop():
            while True:
                msg = conn.receive()
                if msg is None:
                    break
                callback(msg)

        threading.Thread(target=loop, daemon=True).start()

    # ---------- messaging ----------

    def send_to_node(self, node_id: str, msg: Message):
        conn = self.active_connections_peer_to_peer.get(node_id)
        if conn:
            conn.send(msg)

    def broadcast_to_all(self, msg: Message):
        for conn in self.active_connections_peer_to_peer.values():
            conn.send(msg)
