import unittest
from unittest.mock import MagicMock
from src.server.multicast import CausalMulticastHandler
from src.domain.models import Room, Message, MessageType, VectorClock

class TestMulticastRedistribution(unittest.TestCase):
    def test_multicast_redistribution(self):
        """
        Verifies that CausalMulticastHandler.multicast() correctly sends
        the message to all connected clients in the room via TCP.
        """
        # 1. Setup - Mock Server and Connection Manager
        server_mock = MagicMock()
        connection_manager_mock = MagicMock()
        server_mock.connection_manager = connection_manager_mock
        
        # Mock active connections dictionary
        # { client_id: connection_mock }
        client_a_conn = MagicMock()
        client_b_conn = MagicMock()
        client_c_conn = MagicMock()
        
        connection_manager_mock.active_connections_server_to_client = {
            "client_A": client_a_conn,
            "client_B": client_b_conn,
            "client_C": client_c_conn
        }

        # 2. Setup - Room and Handler
        room = Room(host=server_mock, room_id="redist_room")
        # Only A and B are in this room, C is connected but not in room
        room.client_ids = ["client_A", "client_B"] 
        
        handler = CausalMulticastHandler()

        # 3. Create Message
        msg = Message(
            type=MessageType.CHAT,
            content="Broadcast Message",
            sender_id="client_A",
            room_id="redist_room",
            vector_clock=VectorClock(timestamps={"client_A": 1})
        )

        print("\n--- Multicast Redistribution Test ---")
        print(f"Room Members: {room.client_ids}")
        print(f"Connected Clients: {list(connection_manager_mock.active_connections_server_to_client.keys())}")
        
        # 4. Execute Multicast
        print("Executing multicast...")
        handler.multicast(msg, room)

        # 5. Verify
        # Client A (sender) is in room, so it should receive it (echo)
        # In this implementation, the server echoes back to the sender too (implied by loop over room.client_ids)
        print("Verifying Client A received message...")
        client_a_conn.send.assert_called_with(msg)
        
        print("Verifying Client B received message...")
        client_b_conn.send.assert_called_with(msg)
        
        print("Verifying Client C did NOT receive message (not in room)...")
        client_c_conn.send.assert_not_called()
        
        print("--- Multicast Redistribution Test Passed ---")

if __name__ == "__main__":
    unittest.main()
