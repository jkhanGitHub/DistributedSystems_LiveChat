from typing import Optional
from ..domain.models import VectorClock, Message
from ..network.transport import TCPConnection, UDPHandler, ConnectionManager

class ChatClient:
    def __init__(self, client_id: str, username: str):
        self.client_id = client_id
        self.username = username
        self.server_connection: Optional[TCPConnection] = None
        self.client_clock = VectorClock()
        self.udp_handler = UDPHandler()
        self.connection_manager = ConnectionManager() # using connection manager to handle connection logic if needed

    def start(self):
        # Skeleton implementation
        pass

    def discover_server(self):
        # Skeleton implementation
        pass

    def join_room(self, room_id: str):
        # Skeleton implementation
        pass

    def send_message(self, content: str):
        # Skeleton implementation
        pass

    def receive_message(self, msg: Message):
        # Skeleton implementation
        pass
