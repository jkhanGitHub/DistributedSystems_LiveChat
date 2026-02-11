from typing import Dict, Any
from ..domain.models import Message, MessageType
from ..network.transport import ConnectionManager
from .server_state import ServerState
import ast
import json
import socket
class MetadataStore:
    #room_locations = {}

    def __init__(self, room_locations = {}):
        self.room_locations = room_locations or {}

    #To be called by the process_message method if the message type is METADATA_UPDATE
    def handle_message(self,message, ConnectionManagerObject):
        m = message.content

        if "Update" in m:
            if 'Room' in m:
                m = m.split()
                room_id = m[2]
                self.room_locations[room_id] = message.sender_id
            elif 'Connections' in m:
                m = m.split()
                server_id = m[2]
                ip = m[2]
                port = m[3]
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ConnectionManagerObject.active_connections_peer_to_peer[server_id] = ConnectionManagerObject.wrap_socket(sock,ip,port)
            #print(self.room_locations)
        elif "Sync " in m:
            if "Room" in m:
                m = m[9:]
                incoming = ast.literal_eval(m)
                self.room_locations.update(incoming)
            elif "Connections" in m:
                m = m[16:]
                ConnectionManagerObject.active_connections_peer_to_peer = json.loads(m)
                for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                    ipport = ConnectionManagerObject.active_connections_peer_to_peer[i].split()
                    ip = ipport[0]
                    port = ipport[1]
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    #Store it as a TCPConnection object instead of ip and port
                    ConnectionManagerObject.active_connections_peer_to_peer[i] = ConnectionManagerObject.wrap_socket(sock,ip,port)

            #print(self.room_locations)
            #print(ConnectionManagerObject.active_connections_peer_to_peer)

    #send the new room that is added to the leader
    #To be called when a new room is added by the server. Through Discovery.
    def update_metadata(self, room_id, server, ConnectionManagerObject):
        #Update within the server instance first. Will be also done redundantly with the sync_with_leader() function
        self.room_locations[room_id] = server.server_id
        if server.state != ServerState.LEADER:
            m = Message(content = "Update Room " + str(room_id), sender_id = server.server_id, type = MessageType.METADATA_UPDATE)
            ConnectionManagerObject.send_to_node(server.leader_id, m)

    def update_globalview(self, ConnectionManagerObject, server, server_id):
        if server.state != ServerState.LEADER:
            m = Message(content = "Update Connections " + str(server_id) + ' ' + ConnectionManagerObject.active_connections_peer_to_peer[server_id].stringify(), sender_id = server.server_id, type = MessageType.METADATA_UPDATE)
            ConnectionManagerObject.send_to_node(server.leader_id, m)

    #To be called by the leader server
    def sync_with_leader(self, peer, id, ConnectionManagerObject):
        m = Message(content = "Sync Room" + str(self.room_locations), sender_id = id, type = MessageType.METADATA_UPDATE)
        peer.send(m)
        #m = Message(content = "Sync Connections" + ConnectionManagerObject.stringify(), sender_id = id, type = MessageType.METADATA_UPDATE)
        #peer.send(m)
