from enum import Enum, auto
from typing import Dict, Optional, Any
from dataclasses import dataclass
import socket
import os
import json

from ..domain.models import Room, Message, MessageType
from ..network.transport import ConnectionManager, UDPHandler
from .election import ElectionModule
from .failure_detector import FailureDetector
from .metadata import MetadataStore
from .multicast import CausalMulticastHandler
from .server_state import ServerState

@dataclass
class RingNeighbor:
    id: str
    ip: str
    port: int

class ServerNode:
    def __init__(self, server_id: str, ip_address: str, port: int):
        super().__init__()
        self.server_id = server_id
        self.ip_address = ip_address
        self.port = port
        
        # logical state
        self.state = ServerState.LOOKING
        self.leader_id: Optional[str] = None
        
        # ring structure
        self.left_neighbor: Optional[RingNeighbor] = None
        self.right_neighbor: Optional[RingNeighbor] = None
        
        # room
        self.managed_rooms: Dict[str, Room] = {}
        
        # Components
        self.connection_manager = ConnectionManager()
        self.udp_handler = UDPHandler()
        self.election_module = ElectionModule(self)
        self.failure_detector = FailureDetector(self)
        self.metadata_store = MetadataStore()
        self.multicast_handler = CausalMulticastHandler()

    def start(self):
        self.run()

    def run(self):
        """
        Main server loop.
        Handles:
        - TCP connections (clients & servers)
        - UDP discovery
        """
        # ---- TCP listener ----
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Adding reuaseaddr
        tcp_socket.bind((self.ip_address, self.port))
        tcp_socket.listen()

        print(
            f"[Server {self.server_id}] PID {os.getpid()} "
            f"listening on {self.ip_address}:{self.port}"
        )

        # ---- UDP discovery listener ----
        self.udp_handler.listen(self.port, self._handle_udp_message)

        self.handle_discovery()

        while True:
            sock, addr = tcp_socket.accept()
            print("DEBUG handle_join signature:", self.handle_join)
            self.handle_join(sock, addr)

    def handle_discovery(self):
        # Broadcast discovery message to locate other servers
        discovery_msg = Message(
            type=MessageType.DISCOVERY,
            sender_id=self.server_id,
        )
        self.udp_handler.broadcast(discovery_msg, self.port)

    def _handle_udp_message(self, msg: Message):
        if msg.sender_id == self.server_id:
            return

        if msg.type == MessageType.DISCOVERY:
            print(
                f"[Server {self.server_id}] discovered server {msg.sender_id}"
            )

            response = Message(
                type=MessageType.METADATA_UPDATE,
                sender_id=self.server_id,
                content=json.dumps({
                    "ip": self.ip_address,
                    "port": self.port,
                }),
            )
            self.udp_handler.broadcast(response, self.port)

        """elif msg.type == MessageType.METADATA_UPDATE:
            data = json.loads(msg.content)
            self.metadata_store.sync_with_leader(
                msg.sender_id,
                data["ip"],
                data["port"]
            )"""

    def handle_join(self, sock: socket.socket, addr):
        # Handle a new TCP connection
        conn = self.connection_manager.wrap_socket(sock, ip = addr[0], port = addr[1])
        msg = conn.receive()

        if msg.type == MessageType.CLIENT_JOIN:
            self._handle_client_join(msg, conn)

        elif msg.type == MessageType.SERVER_JOIN:
            self._handle_server_join(msg, conn)

    def _handle_join_room(self, msg: Message):
        room_id = msg.room_id
        client_id = msg.sender_id

        # Create room if it doesn't exist
        if room_id not in self.managed_rooms:
            self.managed_rooms[room_id] = Room(room_id)
            print(f"[Server {self.server_id}] created room {room_id}")

        room = self.managed_rooms[room_id]
        room.add_client(client_id)

        print(
            f"[Server {self.server_id}] client {client_id} "
            f"joined room {room_id}"
        )
        
    def _handle_client_join(self, msg: Message, conn):
        """
        Register a new client.
        """
        self.connection_manager.active_connections_server_to_client[msg.sender_id] = conn
        print(f"[Server {self.server_id}] client joined: {msg.sender_id}")

        self.connection_manager.listen_to_connection(
            conn,
            self.process_message
        )

    def _handle_server_join(self, msg: Message, conn):
        """
        Register a new peer server.
        """
        self.connection_manager.active_connections_peer_to_peer[msg.sender_id] = conn
        print(f"[Server {self.server_id}] peer joined: {msg.sender_id}")

        self.connection_manager.listen_to_connection(
            conn,
            self.process_message
        )

    def update_neighbour_id(self, msg):
        if msg.sender_id == me.left_neighbor.id:
            me.left_neighbor.id = msg.content
        elif msg.sender_id == me.right_neighbor.id:
            me.right_neighbor.id = msg.content
        #Also update the IP Addresses if used.
    
    def process_message(self, msg: Message):
        match msg.type:
            case MessageType.CHAT:
                if msg.room_id in self.managed_rooms:
                    room = self.managed_rooms[msg.room_id]
                    self.multicast_handler.handle_chat_message(msg, room) # Currently this doesn't work. 
                else:
                    print(
                        f"[Server {self.server_id}] "
                        f"room {msg.room_id} not found"
                    )

            case MessageType.DISCOVERY:
                self.handle_discovery()

            case MessageType.ELECTION:
                self.election_module.handle_message(msg)

            case MessageType.HEARTBEAT:
                self.failure_detector.handle_heartbeat(msg)

            case MessageType.METADATA_UPDATE:
                self.metadata_store.handle_message(msg)

            case MessageType.JOIN_ROOM:
                self._handle_join_room(msg)

            case MessageType.UPDATE_NEIGHBOUR:
                self.update_neighbour_id(msg)

            case _:
                print(
                    f"[Server {self.server_id}] "
                    f"unknown message type: {msg.type}"
                )
