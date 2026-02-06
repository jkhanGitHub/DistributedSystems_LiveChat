from typing import Dict, Optional
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
from ..network.constants import DISCOVERY_PORT

@dataclass
class RingNeighbor:
    id: str
    ip: str
    port: int


class ServerNode:
    def __init__(self, server_id: str, ip_address: str, port: int):
        self.server_id = server_id
        self.ip_address = "127.0.0.1"
        self.port = port

        # logical state
        self.state = ServerState.LOOKING
        self.leader_id: Optional[str] = None

        # ring structure
        self.left_neighbor: Optional[RingNeighbor] = None
        self.right_neighbor: Optional[RingNeighbor] = None

        # rooms
        self.managed_rooms: Dict[str, Room] = {}

        # components
        self.connection_manager = ConnectionManager()
        self.udp_handler = UDPHandler()
        self.election_module = ElectionModule(self)
        self.failure_detector = FailureDetector(self)
        self.metadata_store = MetadataStore()
        self.multicast_handler = CausalMulticastHandler()

    # --------------------------------------------------
    # lifecycle
    # --------------------------------------------------

    def start(self):
        self.run()

    def run(self):
        # ---- TCP listener ----
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.bind((self.ip_address, self.port))
        tcp_socket.listen()

        print(
            f"[Server {self.server_id}] PID {os.getpid()} "
            f"listening on {self.ip_address}:{self.port}"
        )

        # ---- UDP listener (shared) ----
        self.udp_handler.listen(DISCOVERY_PORT, self._handle_udp_message)
        print(f"[Server {self.server_id}] UDP discovery listening on {self.port}")

        # ---- server gossip bootstrap ----
        self._broadcast_server_discovery()

        while True:
            sock, addr = tcp_socket.accept()
            self.handle_join(sock, addr)

    # UDP handling 
    def _handle_udp_message(self, msg: Message):
        print(f"[Server {self.server_id}] UDP received {msg.type}")
        if msg.sender_id == self.server_id:
            return

        match msg.type:
            # -------- server ↔ server gossip --------
            case MessageType.SERVER_DISCOVERY:
                self._handle_server_discovery(msg)

            case MessageType.METADATA_UPDATE:
                self.metadata_store.handle_message(msg, self.connection_manager)

            # -------- client → server discovery --------
            case MessageType.DISCOVERY_REQUEST:
                self._handle_client_discovery(msg)

            case MessageType.DISCOVERY_RESPONSE:
                return

    # server ↔ server discovery

    def _broadcast_server_discovery(self):
        print(f"[Server {self.server_id}] broadcasting SERVER_DISCOVERY")
        msg = Message(
            type=MessageType.SERVER_DISCOVERY,
            sender_id=self.server_id,
        )
        self.udp_handler.broadcast(msg, DISCOVERY_PORT)

    def _handle_server_discovery(self, msg: Message):
        print(
            f"[Server {self.server_id}] discovered peer server {msg.sender_id}"
        )

        response = Message(
            type=MessageType.METADATA_UPDATE,
            sender_id=self.server_id,
            content=json.dumps({
                "ip": self.ip_address,
                "port": self.port,
            }),
        )

        print(
        f"[Server {self.server_id}] sending METADATA_UPDATE "
        f"ip={self.ip_address} port={self.port}"
)

        self.udp_handler.broadcast(response, DISCOVERY_PORT)

    # client → server discovery 

    def _handle_client_discovery(self, msg: Message):
        print(f"[Server {self.server_id}] replying to client discovery")
        client_ip = msg.sender_addr[0]
        response = Message(
            type=MessageType.DISCOVERY_RESPONSE,
            sender_id=self.server_id,
            content=json.dumps({
                "ip": self.ip_address,
                "port": self.port,
            }),
        )
        print(
            f"[Server {self.server_id}] responding to client "
            f"{msg.sender_id} at {msg.sender_addr}"
        )
        
        self.udp_handler.send_to(response, msg.sender_addr)

    # TCP join handling

    def handle_join(self, sock: socket.socket, addr):
        conn = self.connection_manager.wrap_socket(
            sock, ip=addr[0], port=addr[1]
        )
        msg = conn.receive()

        if msg.type == MessageType.CLIENT_JOIN:
            self._handle_client_join(msg, conn)

        elif msg.type == MessageType.SERVER_JOIN:
            self._handle_server_join(msg, conn)

    def _handle_client_join(self, msg: Message, conn):
        self.connection_manager.active_connections_server_to_client[msg.sender_id] = conn
        print(f"[Server {self.server_id}] client joined: {msg.sender_id}")

        self.connection_manager.listen_to_connection(conn, self.process_message)

    def _handle_server_join(self, msg: Message, conn):
        self.connection_manager.active_connections_peer_to_peer[msg.sender_id] = conn
        print(f"[Server {self.server_id}] peer joined: {msg.sender_id}")

        self.connection_manager.listen_to_connection(conn, self.process_message)

    # chat / control plane

    def _handle_join_room(self, msg: Message):
        room_id = msg.room_id
        client_id = msg.sender_id

        if room_id not in self.managed_rooms:
            self.managed_rooms[room_id] = Room(room_id)
            print(f"[Server {self.server_id}] created room {room_id}")

        self.managed_rooms[room_id].add_client(client_id)

        print(
            f"[Server {self.server_id}] client {client_id} joined room {room_id}"
        )

    def update_neighbour_id(self, msg: Message):
        if self.left_neighbor and msg.sender_id == self.left_neighbor.id:
            self.left_neighbor.id = msg.content
        elif self.right_neighbor and msg.sender_id == self.right_neighbor.id:
            self.right_neighbor.id = msg.content

    def process_message(self, msg: Message):
        match msg.type:
            case MessageType.CHAT:
                if msg.room_id in self.managed_rooms:
                    room = self.managed_rooms[msg.room_id]
                    self.multicast_handler.handle_chat_message(msg, room)
                else:
                    print(
                        f"[Server {self.server_id}] "
                        f"room {msg.room_id} not found"
                    )

            case MessageType.ELECTION:
                self.election_module.handle_message(msg)

            case MessageType.HEARTBEAT:
                self.failure_detector.handle_heartbeat(msg)

            case MessageType.JOIN_ROOM:
                self._handle_join_room(msg)

            case MessageType.UPDATE_NEIGHBOUR:
                self.update_neighbour_id(msg)

            case _:
                print(
                    f"[Server {self.server_id}] "
                    f"unknown message type: {msg.type}"
                )
