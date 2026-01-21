from ..domain.models import Message, MessageType
from .server_state import ServerState
import ast

class ElectionModule:
    Node = None
    k = 0
    reply_counter = 0
    def __init__(self,Node=None):
        self.Node = Node

    def ConstructElectionMessage(self, id, k, d):
        dec = {'k' : k, 'd' : d, 'type' : 'Election'}
        m = Message(content = str(dec), sender_id = id, type = MessageType.ELECTION.value)
        return m

    def ConstructReplyMessage(self, id, k):
        #Dummy d
        dec = {'k' : k, 'd' : 0, 'type' : 'Reply'}
        m = Message(content = str(dec),sender_id = id, type = MessageType.ELECTION.value)
        return m

    def ConstructLeaderAnnoucementMessage(self, id):
        dec = {'k' : 0, 'd' : 0, 'type' : 'Leader Announcement'}
        m = Message(content = str(dec),sender_id = id, type = MessageType.ELECTION.value)
        return m

    def ParseMessage(self, message):
        stringlit = message.content
        dec = ast.literal_eval(stringlit)
        dec['mid'] = message.sender_id
        return dec

    def handle_message(self, message, ConnectionManagerObject):
        dec = self.ParseMessage(message)
        me = self.Node
        #Convert it to switch case
        if dec['type'] == 'Election':
            print('received election')
            if me.server_id < dec['mid'] and dec['d'] < 2**dec['k']:
                m = self.ConstructElectionMessage(dec['mid'], dec['k'], dec['d'] + 1)
                #Send it forward
                if dec['mid'] == me.right_neighbor.id:
                    if me.left_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                        left = ConnectionManagerObject.active_connections_peer_to_peer[me.left_neighbor.id]
                        left.send(m)
                elif dec['mid'] == me.left_neighbor.id:
                    if me.right_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                        right = ConnectionManagerObject.active_connections_peer_to_peer[me.right_neighbor.id]
                        right.send(m)
            elif me.server_id < dec['mid'] and dec['d'] == 2**dec['k']:
                m = self.ConstructReplyMessage(dec['mid'], dec['k'])
                #Send it back
                if dec['mid'] == me.left_neighbor.id:
                    if me.left_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                        left = ConnectionManagerObject.active_connections_peer_to_peer[me.left_neighbor.id]
                    left.send(m)
                elif dec['mid'] == me.right_neighbor.id:
                    if me.right_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                        right = ConnectionManagerObject.active_connections_peer_to_peer[me.right_neighbor.id]
                        right.send(m)
            elif me.server_id == dec['mid']:
                m = self.ConstructLeaderAnnoucementMessage(me.server_id)
                me.leader_id = me.server_id
                me.state = ServerState.LEADER.value
                self.k = 0
                for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                    if i != me.server_id:
                        active_connections_peer_to_peer[i].send(m)
        elif dec['type'] == 'Reply':
            print('received reply')
            if me.server_id != dec['mid']:
                if dec['mid'] == me.right_neighbor.id:
                    if me.left_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                        left = ConnectionManagerObject.active_connections_peer_to_peer[me.left_neighbor.id]
                        left.send(message)
                elif dec['mid'] == me.left_neighbor.id:
                    if me.right_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                        right = ConnectionManagerObject.active_connections_peer_to_peer[me.right_neighbor.id]
                        right.send(message)
            else:
                self.reply_counter += 1
                if reply_counter == 2:
                    self.k = self.k+1
                    self.start_election(ConnectionManagerObject)
        #Also handle the Leader Announcement message
        elif dec['type'] == 'Leader Announcement':
            print('received leader announcement')
            me.leader_id = dec['mid']
            me.state = ServerState.FOLLOWER.value
            self.k = 0



    def start_election(self, ConnectionManagerObject):
        self.Node.state = ServerState.ELECTION_IN_PROGRESS.value
        self.reply_counter = 0
        self.Node.leader_id = 0
        me = self.Node
        message = self.ConstructElectionMessage(self.Node.server_id, self.k, 2**self.k)
        if me.right_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
            right = ConnectionManagerObject.active_connections_peer_to_peer[me.right_neighbor.id]
            right.send(message)
        if me.left_neighbor.id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
            left = ConnectionManagerObject.active_connections_peer_to_peer[me.left_neighbor.id]
            left.send(message)
