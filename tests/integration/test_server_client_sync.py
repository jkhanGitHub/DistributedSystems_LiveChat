import unittest
from src.domain.models import VectorClock, Message, MessageType, Room
from src.client.chat_client import ChatClient
from src.server.multicast import CausalMulticastHandler
from unittest.mock import MagicMock

class TestServerClientSync(unittest.TestCase):
    def test_full_sync_cycle(self):
        """
        Tests the full lifecycle of a message and its vector clock:
        Client A -> Server (Merge) -> Client B (Merge)
        """
        # 1. Setup
        client_a = ChatClient(username="A", client_id="client_A")
        client_b = ChatClient(username="B", client_id="client_B")
        
        # Mock server environment
        server_node_mock = MagicMock()
        room = Room(host=server_node_mock, room_id="test_room")
        room.client_ids = ["client_A", "client_B"]
        
        multicast_handler = CausalMulticastHandler()
        # Mock the actual multicast network send
        multicast_handler.multicast = MagicMock()

        print("\n--- Server/Client Sync Test ---")
        print(f"Initial Client A clock: {client_a.client_clock.timestamps}")
        print(f"Initial Client B clock: {client_b.client_clock.timestamps}")
        print(f"Initial Server Room clock: {room.vector_clock.timestamps}")

        # 2. Client A sends a message
        # In reality, Client A increments its clock and sends to Server
        client_a.client_clock.increment("client_A")
        msg_from_a = Message(
            type=MessageType.CHAT,
            content="Hello from A",
            sender_id="client_A",
            room_id="test_room",
            vector_clock=client_a.client_clock.copy()
        )
        print(f"\nClient A sends message with clock: {msg_from_a.vector_clock.timestamps}")

        # 3. Server receives and processes message
        # Server uses the merge logic internally via handle_chat_message -> _deliver_and_multicast
        multicast_handler.handle_chat_message(msg_from_a, room)
        
        print(f"Server Room clock after merge: {room.vector_clock.timestamps}")
        self.assertEqual(room.vector_clock.timestamps["client_A"], 1)

        # 4. Server multicasts to Client B
        # Let's simulate Client B receiving the message that was "multicast"
        # In a real system, the server would send the message to Client B
        # Here we manually call receive_message on Client B
        client_b.receive_message(msg_from_a)
        
        print(f"Client B clock after receiving A's message: {client_b.client_clock.timestamps}")
        self.assertEqual(client_b.client_clock.timestamps["client_A"], 1)

        # 5. Client B replies
        client_b.client_clock.increment("client_B")
        msg_from_b = Message(
            type=MessageType.CHAT,
            content="Hi from B",
            sender_id="client_B",
            room_id="test_room",
            vector_clock=client_b.client_clock.copy()
        )
        print(f"\nClient B replies with clock: {msg_from_b.vector_clock.timestamps}")

        # 6. Server processes B's reply
        multicast_handler.handle_chat_message(msg_from_b, room)
        print(f"Server Room clock after merge: {room.vector_clock.timestamps}")
        self.assertEqual(room.vector_clock.timestamps["client_B"], 1)
        self.assertEqual(room.vector_clock.timestamps["client_A"], 1)

        # 7. Client A receives B's reply
        client_a.receive_message(msg_from_b)
        print(f"Client A clock after receiving B's reply: {client_a.client_clock.timestamps}")
        self.assertEqual(client_a.client_clock.timestamps["client_B"], 1)
        
        print("--- Sync Test Complete ---")

if __name__ == "__main__":
    unittest.main()
