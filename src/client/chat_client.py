from typing import Optional
import time
import json
from ..domain.models import (
    VectorClock,
    Message,
    MessageType,
    NodeId,
    generate_node_id,
)
from ..network.transport import TCPConnection, UDPHandler, ConnectionManager
from ..network.constants import (DISCOVERY_PORT,DISCOVERY_INTERVAL,DISCOVERY_RETRIES)
class ChatClient:
    def __init__(self, username: str, client_id: Optional[NodeId] = None):
        self.client_id = client_id or generate_node_id()
        self.username = username
        self.discovery_active = False

        self.server_connection: Optional[TCPConnection] = None
        self.client_clock = VectorClock()

        self.udp_handler = UDPHandler()
        self.connection_manager = ConnectionManager()

        self.current_room = None
        self.discovered_servers = {}

    # Lifecycle
    def start(self, ip: str, port: int):
        # Connect to server and start receiving messages.
        
        try:
            self.server_connection = self.connection_manager.connect_to(ip, port)
        except Exception as e:
            print("[Client] Failed to connect:", e)
            self.discovery_active = False
            return

        # Send JOIN message so server can register us
        join_msg = Message(
            type=MessageType.CLIENT_JOIN,
            sender_id=self.client_id,
        )
        self.server_connection.send(join_msg)

        # Start async receive loop
        self.connection_manager.listen_to_connection(
            self.server_connection,
            self.receive_message,
        )

        print(f"[Client {self.client_id}] connected to {ip}:{port}")

    # Discovery
    def discover_server(self, discovery_port: int):
         # Discover servers via UDP.
        
        if self.discovery_active:
            return
        
        self.discovery_active = True

        self.udp_handler.listen(0, self.on_server_discovered)

        discovery_msg = Message(
            type=MessageType.DISCOVERY_REQUEST,
            sender_id=self.client_id,
        )

        for _ in range(DISCOVERY_RETRIES):
            if not self.discovery_active:
                break

            print("[Client] sending discovery broadcast")
            self.udp_handler.broadcast(discovery_msg, discovery_port)
            time.sleep(DISCOVERY_INTERVAL)

    def on_server_discovered(self, msg: Message):
        if not self.discovery_active:
            return
        
        if self.server_connection is not None:
            return
        
        if msg.type == MessageType.AVAILABLE_ROOMS:
            self.discovery_active = False
            self._handle_available_rooms(msg)
        
    def _handle_available_rooms(self, msg: Message):
        data = json.loads(msg.content)
        rooms = data["rooms"]
        servers = data["servers"]

        room_list = list(rooms.items())

        if not room_list:
            print("\nNo rooms available yet.")
            print("Try again in a moment...")
            self.discovery_active = True
            return

        print("\nAvailable rooms:")
        for i, (room_id, server_id) in enumerate(room_list):
            print(f"{i}: {room_id} (server {server_id})")

        try:
            choice = int(input("Select room: "))
            room_id, server_id = room_list[choice]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return
        print(servers)
        ip = servers[server_id]["ip"]
        port = servers[server_id]["port"]

        self.start(ip, port)
        self.join_room(room_id)

        if room_id is not None:
            pass
        else:
            self.current_room = room_id
        print(f"[Client {self.client_id}] joined room {room_id}")


    # Chat protocol
    def join_room(self, room_id: str):
        # Join a chat room.
        
        if not self.server_connection:
            print("[Client] Not connected to server")
            return

        join_room_msg = Message(
            type=MessageType.JOIN_ROOM,
            sender_id=self.client_id,
            room_id=room_id,
        )
        self.server_connection.send(join_room_msg)

    def send_message(self, content: str, room_id: str):
        # Send a chat message.
        # Increment local clock
        self.client_clock.increment(self.client_id)

        msg_clock = VectorClock(
            timestamps=self.client_clock.timestamps.copy()
        )

        msg = Message(
            type=MessageType.CHAT,
            content=content,
            sender_id=self.client_id,
            room_id=room_id,
            vector_clock=msg_clock,
        )

        if self.server_connection:
            try:
                self.server_connection.send(msg)
            except:
                print("[Client] Not connected, Message not sent")
                self.client_clock.decrement(self.client_id)
                self.server_connection.close()
                self.handle_server_crash(server_id)
        #else case should never happen
        else:
            print("[Client] Not connected, Message not sent")
            self.client_clock.decrement(self.client_id)
            self.server_connection.close()
            self.handle_server_crash(server_id)

    # Receive
    def receive_message(self, msg: Message):
        # Handle incoming messages from server.
        self.client_clock.merge(msg.vector_clock)
        print(
            f"[Room {msg.room_id}] "
            f"[Client {msg.sender_id}]: {msg.content}" 
        )

    def handle_server_crash(self):
        self.discover_server(DISCOVERY_PORT)