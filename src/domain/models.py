from enum import Enum, auto
from typing import Dict, List, Optional
import uuid
import json
from dataclasses import dataclass, field, asdict

class MessageType(Enum):
    CHAT = "CHAT"
    DISCOVERY = "DISCOVERY"
    ELECTION = "ELECTION"
    HEARTBEAT = "HEARTBEAT"
    SYNC = "SYNC"
    METADATA_UPDATE = "METADATA_UPDATE"

@dataclass
class VectorClock:
    timestamps: Dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str):
        self.timestamps[node_id] = self.timestamps.get(node_id, 0) + 1

    def merge(self, other: 'VectorClock'):
        for node, count in other.timestamps.items():
            self.timestamps[node] = max(self.timestamps.get(node, 0), count)

    def compare(self, other: 'VectorClock') -> int:
        """
        Returns:
            -1 if self < other
             1 if self > other
             0 if concurrent or equal (simplified for now, usually needs more states for concurrent)
             Note: Strict vector clock comparison usually returns 'concurrent' as a separate state.
             Here we might implement a simple check.
             For now, let's implement standard partial ordering check logic if needed, 
             but the prompt asks for skeleton. I'll stick to a basic structure.
        """
        # Skeleton implementation
        pass

    def is_causally_ready(self, other: 'VectorClock') -> bool:
        # Skeleton implementation
        return True

@dataclass
class Message:
    type: MessageType
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    sender_id: str = ""
    room_id: str = ""
    vector_clock: VectorClock = field(default_factory=VectorClock)

    def serialize(self) -> str:
        # Skeleton implementation
        return json.dumps({
            "type": self.type.value,
            "message_id": self.message_id,
            "content": self.content,
            "sender_id": self.sender_id,
            "room_id": self.room_id,
            "vector_clock": self.vector_clock.timestamps
        })

    @staticmethod
    def deserialize(data: str) -> 'Message':
        # Skeleton implementation
        pass

@dataclass
class Room:
    room_id: str
    client_ids: List[str] = field(default_factory=list)
    message_history: List[Message] = field(default_factory=list)

    def add_client(self, client_id: str):
        if client_id not in self.client_ids:
            self.client_ids.append(client_id)

    def remove_client(self, client_id: str):
        if client_id in self.client_ids:
            self.client_ids.remove(client_id)

    def add_message(self, msg: Message):
        self.message_history.append(msg)
