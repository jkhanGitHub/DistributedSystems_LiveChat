import unittest
from src.client.chat_client import ChatClient
from src.domain.models import Message, MessageType, VectorClock, NodeId

class TestClientCausalCheck(unittest.TestCase):
    def setUp(self):
        self.client = ChatClient(username="test_user", client_id="client_A")
        self.client_id = "client_A"
        self.other_id = "client_B"

    def test_causal_ready_delivery(self):
        """Test that a message in causal order is delivered immediately."""
        # Current clock: {client_A: 0}
        # Incoming msg from B: {client_B: 1}
        msg_vc = VectorClock(timestamps={self.other_id: 1})
        msg = Message(
            type=MessageType.CHAT,
            content="Hello",
            sender_id=self.other_id,
            vector_clock=msg_vc
        )
        
        self.client.receive_message(msg)
        
        self.assertEqual(self.client.client_clock.timestamps.get(self.other_id), 1)
        self.assertEqual(len(self.client.hold_back_queue), 0)

    def test_hold_back_delivery(self):
        """Test that an out-of-order message is held back and then delivered."""
        # Current clock: {client_A: 0}
        
        # 1. Message from B with clock {client_B: 2} (missing {client_B: 1})
        msg_vc_2 = VectorClock(timestamps={self.other_id: 2})
        msg_2 = Message(
            type=MessageType.CHAT,
            content="Future Message",
            sender_id=self.other_id,
            vector_clock=msg_vc_2
        )
        
        self.client.receive_message(msg_2)
        
        # Should be in queue
        self.assertEqual(len(self.client.hold_back_queue), 1)
        self.assertEqual(self.client.client_clock.timestamps.get(self.other_id, 0), 0)

        # 2. Correct message arrives: {client_B: 1}
        msg_vc_1 = VectorClock(timestamps={self.other_id: 1})
        msg_1 = Message(
            type=MessageType.CHAT,
            content="First Message",
            sender_id=self.other_id,
            vector_clock=msg_vc_1
        )
        
        self.client.receive_message(msg_1)
        
        # Both should be delivered now
        self.assertEqual(self.client.client_clock.timestamps.get(self.other_id), 2)
        self.assertEqual(len(self.client.hold_back_queue), 0)

    def test_self_message_echo(self):
        """Test that the client's own messages are delivered immediately (skipping check)."""
        # Client sends a message
        self.client.send_message("My Message", "room1")
        # Clock is now {client_A: 1}
        
        self.assertEqual(self.client.client_clock.timestamps.get(self.client_id), 1)
        
        # Server echoes it back
        msg_vc = VectorClock(timestamps={self.client_id: 1})
        echo_msg = Message(
            type=MessageType.CHAT,
            content="My Message",
            sender_id=self.client_id,
            vector_clock=msg_vc
        )
        
        # This would fail is_causally_ready because clock[client_A] is already 1
        # But we skip the check for self-messages.
        self.client.receive_message(echo_msg)
        
        self.assertEqual(self.client.client_clock.timestamps.get(self.client_id), 1)
        self.assertEqual(len(self.client.hold_back_queue), 0)

if __name__ == '__main__':
    unittest.main()
