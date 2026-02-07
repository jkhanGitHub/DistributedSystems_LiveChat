from typing import Dict, Any
from enum import Enum
from ..domain.models import Message, MessageType
from ..network.transport import ConnectionManager
from .server_state import ServerState
from .election import ElectionModule
import timeit


class FailureDetector:
    #Heartbeat mechanism for a particular server
    #What about heartbeats during elections
    #If failure detector and the election run in different processes, then it could work together.
    Node = None
    type = 'server'
    PERIOD = 2
    timers = {}
    def __init__(self, Node = None, type = 'server'):
        self.Node = Node
        self.type = type

    #sends the heartbeat. and if it is the leader, it also sends the new metadata to all other servers
    #Consider separating the functions too.
    def send_heartbeat(self, ConnectionManagerObject, MetadataStoreObject):
        me = self.Node
        if self.type == 'server':
            m = Message(content = 'Server Heartbeat', sender_id = me.server_id, type = MessageType.HEARTBEAT.value)
            #Ensures fault tolerance happens even during elections
            if me.state != ServerState.LEADER.value:
                ConnectionManagerObject.send_to_node(me.right_neighbor.id,m)
                ConnectionManagerObject.send_to_node(me.left_neighbor.id,m)
                ConnectionManagerObject.send_to_node(me.leader_id,m)
            else:
                for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                    if i != me.leader_id:
                        ConnectionManagerObject.active_connections_peer_to_peer[i].send(m)
                        MetadataStoreObject.sync_with_leader(active_connections_peers[i], me.server_id, ConnectionManagerObject)
        else:
            m = Message(content = 'Client Heartbeat', sender_id = me.client_id, type = MessageType.HEARTBEAT.value)
            me.server_connection.send(m)

    #Monitors both client and server
    #To be initialized in the init phase of the server node.
    def start_monitoring(self, ConnectionManagerObject):
        me = self.Node
        #Start the monitoring for the clients
        for i in me.managed_rooms.keys():
            for j in managed_rooms[i].client_ids:
                self.timers[('client',j)] = timeit.default_timer()

        #Start the monitoring for the servers
        if me.state != ServerState.LEADER.value:
            #Start the timers
            if me.right_neighbor.id!=0:
                self.timers[('server',me.right_neighbor.id)] = timeit.default_timer()
            if me.left_neighbor.id!=0:
                self.timers[('server',me.left_neighbor.id)]= timeit.default_timer()
            if me.leader_id!=0:
                self.timers[('server',me.leader_id)] = timeit.default_timer()
        else:
            #If leader, start the timer for all the other servers
            for i in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                if i != me.server_id:
                    self.timers[('server',i)] = timeit.default_timer()

    #To be called whenever a heartbeat is received for a particular server
    def resetTimer(self, id, type):
        for i in self.timers.keys():
            if i[1] == id:
                if type == 'server':
                    self.timers[('server',id)] = timeit.default_timer()
                    return
                elif type == 'client':
                    self.timers[('client',id)] = timeit.default_timer()
                    return
        return

    #If the leader is the failed node, initiate elections
    def on_failure_detected(self, typeid, ConnectionManagerObject):
        me = self.Node
        type = typeid[0]
        id = typeid[1]
        timers.pop(typeid, None)
        if type == 'server':
            if id == me.leader_id:
                #spawn a new process here. So that there is failure detection during elections
                #Test them individually first. Then make it concurrent
                ElectionModuleObject = self.Node.election_module
                ElectionModuleObject.start_election(ConnectionManagerObject)
            else:
                #Consider what happens when only a few servers are available
                if id in ConnectionManagerObject.active_connections_peer_to_peer.keys():
                    ConnectionManagerObject.active_connections_peer_to_peer.pop(id)
                    #Fix the ring
                    #Elections are to be triggered newly after ring formation
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
        for i in self.timers.keys():
            if timeit.default_timer() - self.timers[i] > 2*(self.PERIOD):
                print('failure ' + str(i))
                self.on_failure_detected(i, ConnectionManagerObject)
