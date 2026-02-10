from typing import List
from ..domain.models import VectorClock, Message, Room

class CausalMulticastHandler:
    def __init__(self):
        # State is now held in the Room objects passed to methods
        pass

    def handle_chat_message(self, msg: Message, room: Room):
        """
        Main entry point for handling a CHAT message.
        Checks for causal readiness and either multicasts or holds back.
        """
        # 1. Check if causally ready
        if room.vector_clock.is_causally_ready(msg.vector_clock, msg.sender_id):
            self._deliver_and_multicast(msg, room)
            
            # 2. Check hold back queue for any now-ready messages
            self._check_queue_recursively(room)
        else:
            print(f"[Server] Holding back message {msg.message_id} from {msg.sender_id}")
            room.hold_back_queue.append(msg)

    def _deliver_and_multicast(self, msg: Message, room: Room):
        """
        Delivers the message by updating the room clock and multicasting.
        """
        # Update Room Clock (Merge)
        room.vector_clock.merge(msg.vector_clock)
        
        # Add to history
        room.add_message(msg)
        
        # Multicast
        self.multicast(msg, room)

    def _check_queue_recursively(self, room: Room):
        """
        Checks the hold back queue for any messages that are now ready.
        Repeats until no more messages can be delivered.
        """
        progress = True
        while progress:
            progress = False
            # Iterate through a copy of the list to allow modification
            for msg in room.hold_back_queue[:]:
                if room.vector_clock.is_causally_ready(msg.vector_clock, msg.sender_id):
                    room.hold_back_queue.remove(msg)
                    self._deliver_and_multicast(msg, room)
                    progress = True
                    # Break inner loop to restart iteration on modified list (safer)
                    break 

    def multicast(self, msg: Message, room: Room):
        """
        Sends the message to all clients in the room.
        """
        # use TCP connection to send the message to all participant of the room
        for client_id in room.client_ids:
            room.host.connection_manager.active_connections_server_to_client[client_id].send(msg)

