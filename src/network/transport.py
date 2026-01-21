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
        self.socket.bind(("", port))

        def loop():
            while True:
                data, _ = self.socket.recvfrom(4096)
                msg = Message.deserialize(data)
                callback(msg)

        threading.Thread(target=loop, daemon=True).start()


# TCP CONNECTION
class TCPConnection:
    def __init__(self, sock: socket.socket):
        self.socket = sock

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


# CONNECTION MANAGER
class ConnectionManager:
    def __init__(self):
        self.active_connections_peer_to_peer: Dict[str, TCPConnection] = {}
        self.active_connections_server_to_client: Dict[str, TCPConnection] = {}

    # ---------- connection helpers ----------

    def connect_to(self, ip: str, port: int) -> TCPConnection:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        return TCPConnection(sock)

    def wrap_socket(self, sock: socket.socket) -> TCPConnection:
        return TCPConnection(sock)

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
