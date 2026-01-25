from typing import Dict, Any
from ..domain.models import Message, MessageType
from ..network.transport import ConnectionManager
from .server_state import ServerState
import ast

class MetadataStore:
    room_locations = {}

    def __init__(self, room_locations = {}):
        self.room_locations = room_locations

    #To be called by the process_message method if the message type is METADATA_UPDATE
    def handle_message(self,message):
        m = message.content
        if "Update" in m:
            m = m.split()
            room_id = m[1]
            self.room_locations[room_id] = message.sender_id
            #print(self.room_locations)
        elif "Sync " in m:
            m = m[5:]
            self.room_locations = ast.literal_eval(m)
            #print(self.room_locations)

    #send the new room that is added to the leader
    #To be called when a new room is added by the server. Through Discovery.
    def update_metadata(self, room_id, server, ConnectionManagerObject):
        #Update within the server instance first. Will be also done redundantly with the sync_with_leader() function
        self.room_locations[room_id] = server.server_id
        if server.state != ServerState.LEADER.value:
            m = Message(content = "Update " + str(room_id), sender_id = server.server_id, type = MessageType.METADATA_UPDATE.value)
            if server.leader_id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                leader = ConnectionManagerObject.active_connections_peer_to_peer[server.leader_id]
                leader.send(m)

    #To be called by the leader server
    def sync_with_leader(self, peer, id):
        m = Message(content = "Sync " + str(self.room_locations), sender_id = id, type = MessageType.METADATA_UPDATE.value)
        peer.send(m)
