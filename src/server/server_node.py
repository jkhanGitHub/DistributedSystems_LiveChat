import socket
import os
from multiprocessing import Process
from typing import Tuple
from enum import Enum, auto
from typing import Dict, Optional, Any
from dataclasses import dataclass

from ..domain.models import Room, Message
from ..network.transport import ConnectionManager, UDPHandler
from .election import ElectionModule
from .failure_detector import FailureDetector
from .metadata import MetadataStore
from .multicast import CausalMulticastHandler

class ServerState(Enum):
    LOOKING = "LOOKING"
    FOLLOWER = "FOLLOWER"
    LEADER = "LEADER"
    ELECTION_IN_PROGRESS = "ELECTION_IN_PROGRESS"

@dataclass
class RingNeighbor:
    id: str
    ip: str
    port: int

class ServerNode:
    def __init__(self, server_id: str, ip_address: str, port: int):
        self.server_id = server_id
        self.ip_address = ip_address
        self.port = port
        self.state = ServerState.LOOKING
        self.leader_id: Optional[str] = None
        
        self.left_neighbor: Optional[RingNeighbor] = None
        self.right_neighbor: Optional[RingNeighbor] = None
        
        self.managed_rooms: Dict[str, Room] = {}
        
        # Components
        self.connection_manager = ConnectionManager()
        self.udp_handler = UDPHandler()
        self.election_module = ElectionModule(candidate_id=server_id)
        self.failure_detector = FailureDetector()
        self.metadata_store = MetadataStore()
        self.multicast_handler = CausalMulticastHandler()

    def start(self):
        # Skeleton implementation
        pass

    def handle_discovery(self):
        # Skeleton implementation
        pass

    def handle_join(self):
        # Skeleton implementation
        pass

    from ..domain.models import MessageType

    def process_message(self, msg: Message):
        match msg.type:
            case MessageType.CHAT:
                if msg.room_id in self.managed_rooms:
                    room = self.managed_rooms[msg.room_id]
                    self.multicast_handler.handle_chat_message(msg, room)
                else:
                    print(f"[Server] Error: Room {msg.room_id} not found.")
            case MessageType.DISCOVERY:
                self.handle_discovery()
            case MessageType.ELECTION:
                # self.election_module.handle_election(msg)
                pass
            case _:
                print(f"[Server] Unknown message type: {msg.type}")
