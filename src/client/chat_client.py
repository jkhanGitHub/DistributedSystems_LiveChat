from typing import Optional
from ..domain.models import VectorClock, Message, NodeId, generate_node_id
from ..network.transport import TCPConnection, UDPHandler, ConnectionManager

class ChatClient:
    def __init__(self, username: str, client_id: Optional[NodeId] = None):
        self.client_id = client_id or generate_node_id()
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

    def send_message(self, content: str, room_id: str):
        # 1. Increment local clock
        self.client_clock.increment(self.client_id)
        
        # 2. Create message with COPY of clock
        # Note: In a real implementation we might deepcopy, but here a simple dict copy is enough
        # assuming timestamps are ints.
        msg_clock = VectorClock(timestamps=self.client_clock.timestamps.copy())
        
        msg = Message(
            type=MessageType.CHAT,
            content=content,
            sender_id=self.client_id,
            room_id=room_id,
            vector_clock=msg_clock
        )
        
        # 3. Send to server
        if self.server_connection:
            self.server_connection.send(msg.serialize())
        else:
            print(f"[Client] Mock Send: {msg.serialize()}")

    def receive_message(self, msg: Message):
        # Skeleton implementation
        pass
