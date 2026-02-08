from src.server.server_node import ServerNode 
from enum import Enum, auto
from typing import Dict, List, Optional
import uuid
import json
from dataclasses import dataclass, field, asdict
class MessageType(Enum):
    CLIENT_JOIN = "CLIENT_JOIN"
    SERVER_JOIN = "SERVER_JOIN"
    JOIN_ROOM = "JOIN_ROOM"
    LEAVE_ROOM = "LEAVE_ROOM"
    CHAT = "CHAT"
    DISCOVERY_REQUEST = "DISCOVERY_REQUEST"
    DISCOVERY_RESPONSE = "DISCOVERY_RESPONSE"
    SERVER_DISCOVERY = "SERVER_DISCOVERY"
    ELECTION = "ELECTION"
    HEARTBEAT = "HEARTBEAT"
    SYNC = "SYNC"
    METADATA_UPDATE = "METADATA_UPDATE"
    UPDATE_NEIGHBOUR = "UPDATE_NEIGHBOUR"


NodeId = str

def generate_node_id() -> NodeId:
    return str(uuid.uuid4())

@dataclass
class VectorClock:
    timestamps: Dict[NodeId, int] = field(default_factory=dict)

    def increment(self, node_id: NodeId):
        self.timestamps[node_id] = self.timestamps.get(node_id, 0) + 1

    def decrement(self, node_id: NodeId):
        self.timestamps[node_id] = self.timestamps.get(node_id, 0) - 1

    def merge(self, other: 'VectorClock'):
        for node, count in other.timestamps.items():
            self.timestamps[node] = max(self.timestamps.get(node, 0), count)

    def compare(self, other: 'VectorClock') -> int:
        """
        Returns:
            -1 if self < other (self happened before other)
             1 if self > other (other happened before self)
             0 if concurrent or equal
        """
        keys = set(self.timestamps.keys()) | set(other.timestamps.keys())
        greater = False
        smaller = False
        
        for key in keys:
            v1 = self.timestamps.get(key, 0)
            v2 = other.timestamps.get(key, 0)
            
            if v1 > v2:
                greater = True
            elif v1 < v2:
                smaller = True
        
        if greater and not smaller:
            return 1
        if smaller and not greater:
            return -1
        return 0 # Equal or Concurrent

    def is_causally_ready(self, message_clock: 'VectorClock', sender_id: NodeId) -> bool:
        """
        Checks if a message with `message_clock` from `sender_id` can be delivered
        given the current local `self` clock.
        
        Conditions:
        1. message_clock[sender_id] == self[sender_id] + 1 (Next message from sender)
        2. for all k != sender_id: message_clock[k] <= self[k] (We have seen all messages seen by sender)
        """
        # Condition 1: Check sender sequence
        sender_msg_time = message_clock.timestamps.get(sender_id, 0)
        local_sender_time = self.timestamps.get(sender_id, 0)
        
        if sender_msg_time != local_sender_time + 1:
            return False
            
        # Condition 2: Check causality for all other nodes
        other_nodes = set(self.timestamps.keys()) | set(message_clock.timestamps.keys())
        other_nodes.discard(sender_id)
        
        for node in other_nodes:
            if message_clock.timestamps.get(node, 0) > self.timestamps.get(node, 0):
                return False
                
        return True

@dataclass
class Message:
    type: MessageType
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    sender_id: NodeId = ""
    room_id: str = ""
    vector_clock: VectorClock = field(default_factory=VectorClock)
    sender_addr: Optional[tuple[str,int]] = None

    def serialize(self) -> str:
        # Skeleton implementation
        return json.dumps({
            "type": self.type.value,
            "message_id": self.message_id,
            "content": self.content,
            "sender_id": self.sender_id,
            "room_id": self.room_id,
            "vector_clock": self.vector_clock.timestamps
        }).encode("utf-8")

    @staticmethod
    def deserialize(data: str) -> 'Message':
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        obj = json.loads(data)

        return Message(
            type=MessageType(obj["type"]),
            message_id=obj["message_id"],
            content=obj.get("content", ""),
            sender_id=obj.get("sender_id", ""),
            room_id=obj.get("room_id", ""),
            vector_clock=VectorClock(
                timestamps=obj.get("vector_clock", {})
        )
    )

@dataclass
class Room:
    host: ServerNode
    room_id: str
    client_ids: List[NodeId] = field(default_factory=list)
    message_history: List[Message] = field(default_factory=list)
    vector_clock: VectorClock = field(default_factory=VectorClock)
    hold_back_queue: List[Message] = field(default_factory=list)

    def add_client(self, client_id: NodeId):
        if client_id not in self.client_ids:
            self.client_ids.append(client_id)

    def remove_client(self, client_id: NodeId):
        if client_id in self.client_ids:
            self.client_ids.remove(client_id)

    def add_message(self, msg: Message):
        self.message_history.append(msg)
