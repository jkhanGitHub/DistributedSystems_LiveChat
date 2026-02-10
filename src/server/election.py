from ..domain.models import Message, MessageType
from .server_state import ServerState
import ast
import time

class ElectionModule:
    Node = None
    reply_counter = 0
    def __init__(self,Node=None):
        self.Node = Node

    def ConstructElectionMessage(self, id, k, d):
        dec = {'k' : k, 'd' : d, 'type' : 'Election', 'mid' : id}
        m = Message(content = str(dec), sender_id = self.Node.server_id, type = MessageType.ELECTION)
        return m

    def ConstructReplyMessage(self, id, k):
        #Dummy d
        dec = {'k' : k, 'd' : 0, 'type' : 'Reply', 'mid' : id}
        m = Message(content = str(dec),sender_id = self.Node.server_id, type = MessageType.ELECTION)
        return m

    def ConstructLeaderAnnouncementMessage(self, id):
        dec = {'k' : 0, 'd' : 0, 'type' : 'Leader Announcement', 'mid' : id}
        m = Message(content = str(dec),sender_id = self.Node.server_id, type = MessageType.ELECTION)
        return m

    def ParseMessage(self, message):
        stringlit = message.content
        dec = ast.literal_eval(stringlit)
        return dec

    def handle_message(self, message, ConnectionManagerObject):
        dec = self.ParseMessage(message)
        me = self.Node
        #Convert it to switch case
        if dec['type'] == 'Election':
            #print('received election from ', dec['mid'])
            #print('Election params d , k', (dec['d'],dec['k']))
            if me.server_id < dec['mid'] and dec['d'] < 2**dec['k']:
                m = self.ConstructElectionMessage(dec['mid'], dec['k'], dec['d'] + 1)
                #Send it forward
                if message.sender_id == me.right_neighbor.id:
                    ConnectionManagerObject.send_to_node(me.left_neighbor.id, m)
                elif message.sender_id == me.left_neighbor.id:
                    ConnectionManagerObject.send_to_node(me.right_neighbor.id, m)
                #print('Sending it forward for ' + str(dec['mid']) + ' with k ' + str(dec['k']))
            elif me.server_id < dec['mid'] and dec['d'] == 2**dec['k']:
                m = self.ConstructReplyMessage(dec['mid'], dec['k'])
                #Send it back
                if message.sender_id == me.left_neighbor.id:
                    ConnectionManagerObject.send_to_node(me.left_neighbor.id, m)
                elif message.sender_id == me.right_neighbor.id:
                    ConnectionManagerObject.send_to_node(me.right_neighbor.id, m)
                #print('Sending reply for ' +str(dec['mid']) + ' back to ' +  str(message.sender_id))
            elif me.server_id == dec['mid']:
                if me.leader_id != me.server_id:
                    m = self.ConstructLeaderAnnouncementMessage(me.server_id)
                    me.leader_id = me.server_id
                    print('My connection manager has')
                    for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                        if i != int(me.server_id):
                            ConnectionManagerObject.active_connections_peer_to_peer[i].send(m)
                            print(i)
                    print('I am leader')
                    me.state = ServerState.LEADER

                    #Remove self from the ring
                    right = Message(content = str(me.left_neighbor.id),sender_id = me.server_id, type = MessageType.UPDATE_NEIGHBOUR)
                    left = Message(content = str(me.right_neighbor.id),sender_id = me.server_id, type = MessageType.UPDATE_NEIGHBOUR)
                    ConnectionManagerObject.send_to_node(me.left_neighbor.id, left)
                    ConnectionManagerObject.send_to_node(me.right_neighbor.id, right)
                    me.right_neighbor.id = 0
                    me.left_neighbor.id = 0
                    #To be handled in server_node

        elif dec['type'] == 'Reply':
            #print('received reply from ', message.sender_id)
            #print('Reply params d , k', (dec['d'],dec['k']))
            if me.server_id != dec['mid']:
                if message.sender_id == me.right_neighbor.id:
                    ConnectionManagerObject.send_to_node(me.left_neighbor.id, message)
                    #print('Sending reply for ' +str(dec['mid']) + ' to ' +  str(me.left_neighbor.id,))
                elif message.sender_id == me.left_neighbor.id:
                    ConnectionManagerObject.send_to_node(me.right_neighbor.id, message)
                    #print('Sending reply for ' +str(dec['mid']) + ' to ' +  str(me.right_neighbor.id,))
            else:
                self.reply_counter += 1
                if self.reply_counter == 2:
                    self.start_election(ConnectionManagerObject, dec['k'] + 1)

        #Also handle the Leader Announcement message
        elif dec['type'] == 'Leader Announcement':
            print('received leader announcement')
            me.leader_id = dec['mid']
            print('left ', me.left_neighbor.id)
            print('right ', me.right_neighbor.id)
            print('My connection manager has')
            for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                print(i)
            #me.state = ServerState.FOLLOWER



    def start_election(self, ConnectionManagerObject, k = 0):
        print('Starting Election ',k)
        self.Node.state = ServerState.ELECTION_IN_PROGRESS
        self.reply_counter = 0
        self.Node.leader_id = '0'
        me = self.Node
        message = self.ConstructElectionMessage(me.server_id, k, 1)
        ConnectionManagerObject.send_to_node(me.right_neighbor.id, message)
        ConnectionManagerObject.send_to_node(me.left_neighbor.id, message)
