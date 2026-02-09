import unittest
from src.server.server_node import ServerNode
from src.domain.models import Room

class TestServerRoom(unittest.TestCase):
    def setUp(self):
        # We need a valid port and IP
        self.server = ServerNode("server-1", "127.0.0.1", 5000)

    def test_create_room(self):
        room_id = "test-room"
        room = self.server.create_room(room_id)
        
        self.assertIn(room_id, self.server.managed_rooms)
        self.assertIsInstance(room, Room)
        self.assertEqual(room.room_id, room_id)
        self.assertEqual(room.host, self.server)
        
        # Verify defaults are assigned
        self.assertEqual(room.client_ids, [])
        self.assertEqual(room.message_history, [])
        self.assertIsNotNone(room.vector_clock)
        self.assertEqual(room.hold_back_queue, [])

    def test_random_room_on_init(self):
        # ServerNode.__init__ should create one random room
        self.assertEqual(len(self.server.managed_rooms), 1)
        for room_id, room in self.server.managed_rooms.items():
            self.assertEqual(len(room_id), 4)
            self.assertEqual(room.host, self.server)

if __name__ == "__main__":
    unittest.main()
