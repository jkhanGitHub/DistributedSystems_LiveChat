from typing import Dict, Any
from enum import Enum
from ..domain.models import Message, MessageType
from ..network.transport import ConnectionManager
from .server_state import ServerState
from .election import ElectionModule
import timeit


class FailureDetector:
    Node = None
    type = 'server'
    PERIOD = 2
    timers = {}
    def __init__(self, Node = None, type = 'server'):
        self.Node = Node
        self.type = type

    def handle_heartbeat(self, message):
        if message.content == 'Server Heartbeat':
            self.resetTimer(message.sender_id, 'server')
        elif message.content == 'Client Heartbeat':
            self.resetTimer(message.sender_id, 'client')

    #sends the heartbeat. and if it is the leader, it also sends the new metadata to all other servers
    def send_heartbeat(self, ConnectionManagerObject, MetadataStoreObject):
        me = self.Node
        if self.type == 'server':
            m = Message(content = 'Server Heartbeat', sender_id = me.server_id, type = MessageType.HEARTBEAT)
            if me.state != ServerState.LEADER:
                ConnectionManagerObject.send_to_node(me.right_neighbor.id,m)
                ConnectionManagerObject.send_to_node(me.left_neighbor.id,m)
                ConnectionManagerObject.send_to_node(me.leader_id,m)
                print('Sent heartbeats to neighbors')
            else:
                for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                    if i != int(me.leader_id):
                        ConnectionManagerObject.active_connections_peer_to_peer[i].send(m)
                        #MetadataStoreObject.sync_with_leader(ConnectionManagerObject.active_connections_peer_to_peer[i], me.server_id, ConnectionManagerObject)
                        print('Sent heartbeats to every node')
        else:
            m = Message(content = 'Client Heartbeat', sender_id = me.client_id, type = MessageType.HEARTBEAT)
            me.server_connection.send(m)
        #print('Sent heartbeats')

    #Monitors both client and server
    #To be initialized in the init phase of the server node.
    def start_monitoring(self, ConnectionManagerObject):
        me = self.Node
        self.timers = {}
        #Start the monitoring for the clients
        for i in me.managed_rooms.keys():
            for j in me.managed_rooms[i].client_ids:
                self.timers[('client',j)] = timeit.default_timer()

        #Start the monitoring for the servers
        if me.state != ServerState.LEADER:
            #Start the timers
            if me.right_neighbor.id!='0' and str(me.right_neighbor.id) != str(me.server_id):
                self.timers[('server',str(me.right_neighbor.id))] = timeit.default_timer()
            if me.left_neighbor.id!='0' and str(me.left_neighbor.id) != str(me.server_id):
                self.timers[('server',str(me.left_neighbor.id))]= timeit.default_timer()
            if me.leader_id!='0':
                print('leader', me.leader_id)
                self.timers[('server',str(me.leader_id))] = timeit.default_timer()
        else:
            #If leader, start the timer for all the other servers
            for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                if i != me.server_id:
                    print('Starting timer for all others')
                    self.timers[('server',str(i))] = timeit.default_timer()
        print(self.timers)

    #To be called whenever a heartbeat is received for a particular server
    def resetTimer(self, id, type):
        id = str(id)
        for i in self.timers.keys():
            if i[1] == id:
                if type == 'server':
                    print('Resetting timer for server ', id)
                    self.timers[('server',id)] = timeit.default_timer()
                    return
                elif type == 'client':
                    #print('Resetting timer for client ', id)
                    self.timers[('client',id)] = timeit.default_timer()
                    return
        return

    #If the leader is the failed node, initiate elections
    def on_failure_detected(self, typeid, ConnectionManagerObject):
        me = self.Node
        type = typeid[0]
        id = int(typeid[1])
        #self.timers.pop(typeid, None)
        if type == 'server':
            if id == int(me.leader_id):
                #spawn a new process here. So that there is failure detection during elections
                #Test them individually first. Then make it concurrent
                if id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                    ConnectionManagerObject.active_connections_peer_to_peer.pop(id)
                    print('left ', me.left_neighbor.id)
                    print('right ', me.right_neighbor.id)
                    me.election_module.start_election(ConnectionManagerObject)
            else:
                #Consider what happens when only a few servers are available
                if id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                    ConnectionManagerObject.active_connections_peer_to_peer.pop(id)
                    #Fix the ring
                    #Elections are to be triggered newly after ring formation
                    print('Server ' + str(id) + ' has crashed!')
                    if me.state == ServerState.LEADER:
                        print("Sending update neighbor command")
                        crashed = me.ring.index(id)
                        if int(me.leader_id) in me.ring:
                            me.ring.remove(int(me.leader_id))
                        leftOfCrashed = me.ring[((crashed + 1)%len(me.ring))]
                        rightOfCrashed = me.ring[((crashed - 1)%len(me.ring))]
                        print('The left and right of crashed are ' + str(leftOfCrashed) + ' ' + str(rightOfCrashed))
                        right = Message(content = 'left ' + str(leftOfCrashed),sender_id = me.server_id, type = MessageType.UPDATE_NEIGHBOUR)
                        left = Message(content = 'right ' + str(rightOfCrashed),sender_id = me.server_id, type = MessageType.UPDATE_NEIGHBOUR)
                        ConnectionManagerObject.send_to_node(int(rightOfCrashed), right)
                        ConnectionManagerObject.send_to_node(int(leftOfCrashed), left)
                    """me._recompute_ring()
                    me.election_module.start_election(ConnectionManagerObject)"""
                    """
                    if id == me.right_neighbor:
                        me.right_neighbor = me.right_neighbor.right_neighbor
                    elif id == me.left_neighbor:
                        me.left_neighbor = me.left_neighbor.left_neighbor
                    """
        elif type == 'client':
            if id in ConnectionManagerObject.active_connections_server_to_client.keys():
                ConnectionManagerObject.active_connections_server_to_client.pop(id)

    #A ServerNodeObject checks the timeouts of its connections and additionally the clients to check if they are active.
    def check_timeouts(self, ConnectionManagerObject):
        #print('Checking timeouts')
        for i in self.timers.keys():
            if timeit.default_timer() - self.timers[i] > 2*(self.PERIOD):
                #print('failure ' + str(i))
                self.on_failure_detected(i, ConnectionManagerObject)
