import unittest
import json
import time
import threading
from unittest.mock import patch, MagicMock
from src.server.server_node import ServerNode
from src.domain.models import Message, MessageType, generate_node_id
from src.server.server_state import ServerState

class TestDiscoveryRequestLookingBlock(unittest.TestCase):
    def setUp(self):
        # Patch create_room because it hits metadata_store.update_metadata which needs leader_id
        # leader_id isn't initialized in __init__ because it's just a type annotation
        with patch('src.server.server_node.ServerNode.create_room'):
            self.server = ServerNode("server-1", "127.0.0.1", 5000, 0)
        
        # Manually set leader_id and other requirements
        self.server.leader_id = "server-1" 
        self.server.state = ServerState.LOOKING
        
        # Mock connection manager and udp handler to avoid network side effects
        self.server.connection_manager.send_to_node = MagicMock()
        self.server.udp_handler.send_to = MagicMock()

        # Now we can create rooms safely
        for _ in range(5):
            self.server.create_room(generate_node_id())

        # set metadata for one specific room
        self.server.metadata_store.update_metadata("room-1", self.server, self.server.connection_manager)   

    def set_server_state(self, state: ServerState):
        self.server.state = state

    def test_discovery_request_looking_block(self):
        # Create a discovery request message
        msg = Message(
            type=MessageType.DISCOVERY_REQUEST,
            sender_id="client-1",
            content=json.dumps({
                "ip": "127.0.0.1",
                "port": 5001
            }),
            sender_addr=("127.0.0.1", 5001)
        )

        # The handler blocks while in LOOKING state, so we run it in a thread
        thread = threading.Thread(target=self.server._handle_client_discovery, args=(msg,))
        thread.start()

        # Give it a moment to enter the while loop
        time.sleep(0.5)

        # Verify that the server is still in LOOKING state and thread is waiting
        self.assertTrue(thread.is_alive(), "Handler should be blocked while in LOOKING state")
        self.assertEqual(self.server.state, ServerState.LOOKING)
        print(f"State before: {self.server.state}, should be LOOKING")
        
        # Wait a bit more to simulate "election time"
        time.sleep(1)

        # Change state to trigger the end of the loop
        self.set_server_state(ServerState.FOLLOWER)
        print(f"Set state to: {self.server.state}")

        # Wait for thread to finish correctly
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive(), "Handler should have unblocked after state change")
        
        # Verify that it tried to forward the request to the leader
        self.server.connection_manager.send_to_node.assert_called()
        print(f"State after: {self.server.state}, should be FOLLOWER")

if __name__ == "__main__":
    unittest.main()