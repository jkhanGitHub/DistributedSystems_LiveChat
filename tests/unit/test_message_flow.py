import unittest
from unittest.mock import MagicMock
from src.domain.models import Room, Message, MessageType, VectorClock, generate_node_id
from src.server.multicast import CausalMulticastHandler
from src.server.server_node import ServerNode

class TestMessageFlow(unittest.TestCase):
    def setUp(self):
        self.handler = CausalMulticastHandler()
        self.room_id = "test_room"
        self.room = Room(room_id=self.room_id)
        
        # Mock multicast to verifying output
        self.handler.multicast = MagicMock()
        
        self.client_a = generate_node_id()
        self.client_b = generate_node_id()
        
        # Initialize room knowledge of clients (implicitly starts at 0)
        self.room.add_client(self.client_a)
        self.room.add_client(self.client_b)

    def create_message(self, sender_id, clock_dict, content):
        vc = VectorClock()
        vc.timestamps = clock_dict
        return Message(
            type=MessageType.CHAT,
            content=content,
            sender_id=sender_id,
            room_id=self.room_id,
            vector_clock=vc
        )

    def test_basic_delivery(self):
        # Client A sends first message: {A:1}
        msg1 = self.create_message(self.client_a, {self.client_a: 1}, "Hello")
        
        self.handler.handle_chat_message(msg1, self.room)
        
        # Should be delivered immediately
        self.handler.multicast.assert_called_with(msg1, self.room)
        self.assertEqual(self.room.vector_clock.timestamps[self.client_a], 1)
        self.assertEqual(len(self.room.hold_back_queue), 0)

    def test_holdback_and_recursive_delivery(self):
        # Scenario: Server receives M2 (A:2) before M1 (A:1)
        
        # M2 arrives first (Gap! We know A:0, need A:1, got A:2)
        msg2 = self.create_message(self.client_a, {self.client_a: 2}, "Second")
        
        self.handler.handle_chat_message(msg2, self.room)
        
        # Should NOT be delivered
        self.handler.multicast.assert_not_called()
        self.assertIn(msg2, self.room.hold_back_queue)
        
        # M1 arrives (Fills gap: A:1)
        msg1 = self.create_message(self.client_a, {self.client_a: 1}, "First")
        
        self.handler.handle_chat_message(msg1, self.room)
        
        # Verify M1 delivered
        # AND M2 delivered recursively
        self.assertEqual(self.handler.multicast.call_count, 2)
        
        # Verify call order
        calls = self.handler.multicast.call_args_list
        self.assertEqual(calls[0][0][0], msg1) # First call arg is msg1
        self.assertEqual(calls[1][0][0], msg2) # Second call arg is msg2
        
        # Verify room state
        self.assertEqual(self.room.vector_clock.timestamps[self.client_a], 2)
        self.assertEqual(len(self.room.hold_back_queue), 0)

if __name__ == '__main__':
    unittest.main()
