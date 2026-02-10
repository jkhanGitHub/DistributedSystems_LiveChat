from typing import Dict, Optional
from dataclasses import dataclass
import socket
import os
import json
import threading
import time
import secrets
import string
import timeit

from ..domain.models import Room, Message, MessageType
from ..network.transport import ConnectionManager, UDPHandler
from .election import ElectionModule
from .failure_detector import FailureDetector
from .metadata import MetadataStore
from .multicast import CausalMulticastHandler
from .server_state import ServerState
from ..network.constants import DISCOVERY_PORT

@dataclass
class RingNeighbor:
    id: str
    ip: str
    port: int

class ServerNode:
    def __init__(self, server_id: str, ip_address: str, port: int, number_of_rooms: int):
        self.server_id = server_id
        self.ip_address = self._get_local_ip() # It was "127.0.0.1" force_loopback=True
        self.port = port
        self.servers: Dict[str, dict] = {}
        self.ring = []
        self.number_of_rooms = number_of_rooms
        self.servers[self.server_id] = {
            "ip": self.ip_address,
            "port": self.port,
        }

        # logical state
        self.state = ServerState.LEADER
        self.leader_id = '0'
        #self.leader_id = self.server_id # For simplicity, start as own leader. Election can be triggered later.

        # ring structure
        self.left_neighbor = RingNeighbor('0', '127.0.0.1', 5001)
        self.right_neighbor = RingNeighbor('0', '127.0.0.1', 5001)
        
        # rooms
        self.managed_rooms: Dict[str, Room] = {}

        # components
        self.connection_manager = ConnectionManager()
        self.udp_handler = UDPHandler()
        self.election_module = ElectionModule(self)
        self.failure_detector = FailureDetector(self)
        self.metadata_store = MetadataStore()
        self.multicast_handler = CausalMulticastHandler()

        # TODO: create room through server prompt, for now this works.
        # create a room in each server with name being a random 4 char string
        for i in range(self.number_of_rooms):
            random_id = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
            temp_room = self.create_room(random_id)
            #add room to managed rooms
            self.managed_rooms[random_id] = temp_room

    # lifecycle
    def start(self):
        self.run()

    def StartFailureDetection(self):
        start = 0
        init = 1
        self.failure_detector.start_monitoring(self.connection_manager)
        while(True):
            if self.state == ServerState.ELECTION_IN_PROGRESS or self.state == ServerState.LOOKING:
                init = 1
                start = timeit.default_timer()
            else:
                if init == 1:
                    self.failure_detector.start_monitoring(self.connection_manager)
                    init = 0
                if timeit.default_timer() - start > self.failure_detector.PERIOD:
                    self.failure_detector.send_heartbeat(self.connection_manager, self.metadata_store)
                    start = timeit.default_timer()

    def run(self):
        # ---- TCP listener ----
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.bind(("0.0.0.0", self.port)) # It was self.ip_address
        tcp_socket.listen()

        print(
            f"[Server {self.server_id}] PID {os.getpid()} "
            f"listening on {self.ip_address}:{self.port}"
        )

        # ---- UDP listener (shared) ----
        self.udp_handler.listen(DISCOVERY_PORT, self._handle_udp_message)
        print(f"[Server {self.server_id}] UDP discovery listening on {DISCOVERY_PORT}")

        time.sleep(0.5) # delay for clusters to start listeners
        # self._start_server_gossip()
        self._broadcast_server_discovery()

        def acceptTCP():
            while True:
                try:
                    sock, addr = tcp_socket.accept()
                    self.handle_join(sock, addr)
                except Exception as e:
                    print(f"[Server {self.server_id}] accept error:", e)
        
        t1 = threading.Thread(target=acceptTCP, daemon=True)
        t1.start()

        t2 = threading.Thread(target=self.StartFailureDetection, daemon=True)
        t2.start()
        t1.join()
    
    # UDP handling 
    def _handle_udp_message(self, msg: Message):
        if msg.type != MessageType.SERVER_DISCOVERY: # To reduce spam
            print(f"[Server {self.server_id}] UDP received {msg.type}")
        #if msg.sender_id == self.server_id:
        #    return

        match msg.type:
            # -------- server ↔ server discovery --------
            case MessageType.SERVER_DISCOVERY:
                self._handle_server_discovery(msg)

            # -------- client → server discovery --------
            case MessageType.DISCOVERY_REQUEST:
                #run handle client discovery inside of a thread to prevent responding when election is happening
                threading.Thread(target=self._handle_client_discovery, args=(msg,)).start()

            case MessageType.DISCOVERY_RESPONSE:
                return

    # server ↔ server discovery

    def _get_local_ip(self, force_loopback=True):
        #if force_loopback:
        #    return "127.0.0.1"

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    """ Gossip for server discovery used
    def _start_server_gossip(self):
        def loop():
            counter = 0
            while True:
                self._broadcast_server_discovery()
                counter += 1

                if counter % 5 == 0:
                    print(f"[Server {self.server_id}] gossip heartbeat")

                time.sleep(3)

        threading.Thread(target=loop, daemon=True).start()
    """

    def _broadcast_server_discovery(self):
        print(f"[Server {self.server_id}] broadcasting SERVER_DISCOVERY")
        msg = Message(
            type=MessageType.SERVER_DISCOVERY,
            sender_id=self.server_id,
            content=json.dumps({
            "ip": self.ip_address,
            "port": self.port
            }),
        )
        self.udp_handler.broadcast(msg, DISCOVERY_PORT)

    def _handle_server_discovery(self, msg: Message):

        if msg.sender_id == self.server_id: # 
            return

        if msg.sender_id in self.connection_manager.active_connections_peer_to_peer:
            return
        
        # Only higher-ID server connects to solve win10013 error
        #if str(self.server_id) < str(msg.sender_id):
        #    return
        
        print(f"[Server {self.server_id}] discovered peer server {msg.sender_id}")

        try:
            data = json.loads(msg.content)
            peer_ip = data["ip"]
            peer_port = data["port"]

            self.servers[msg.sender_id] = {
                "ip": peer_ip,
                "port": peer_port,
            }

            conn = self.connection_manager.connect_to(peer_ip, peer_port)

            self.connection_manager.active_connections_peer_to_peer[msg.sender_id] = conn

            print(
                f"[Server {self.server_id}] TCP connected to peer "
                f"{msg.sender_id} at {peer_ip}:{peer_port}"
            )

            join_msg = Message(
                type=MessageType.SERVER_JOIN,
                sender_id=self.server_id,
            )
            conn.send(join_msg)
            #self.connection_manager.listen_to_connection(conn, self.process_message)

            self._recompute_ring()
            #time.sleep(1)
            self.election_module.start_election(self.connection_manager)

        except Exception as e:
            print(f"[Server {self.server_id}] could not connect to peer:", e)


    # client → server discovery 

    def _handle_client_discovery(self, msg: Message):
        print(f"[Server {self.server_id}] client discovery from {msg.sender_id}")

        #block until election is done
        while self.state == ServerState.LOOKING:
            time.sleep(0.1)

        if self.state == ServerState.LEADER:
            self._send_rooms_to_client(msg.sender_addr)
            return

        forward = Message(
            type=MessageType.AVAILABLE_ROOMS,
            sender_id=self.server_id,
            content=json.dumps({
                "client_ip": msg.sender_addr[0],
                "client_port": msg.sender_addr[1],
            }),
        )

        self.connection_manager.send_to_node(self.leader_id, forward)

    # TCP join handling

    def handle_join(self, sock: socket.socket, addr):
        try:
            conn = self.connection_manager.wrap_socket(
                sock, ip=addr[0], port=addr[1]
            )
            msg = conn.receive()

            if msg.type == MessageType.CLIENT_JOIN:
                self._handle_client_join(msg, conn)

            elif msg.type == MessageType.SERVER_JOIN:
                self._handle_server_join(msg, conn)
                self._recompute_ring()
                self.election_module.start_election(self.connection_manager)
        
        except Exception as e:
            print(f"[Server {self.server_id}] join error:", e)

    def _handle_client_join(self, msg: Message, conn):
        self.connection_manager.active_connections_server_to_client[msg.sender_id] = conn
        print(f"[Server {self.server_id}] client joined: {msg.sender_id}")

        self.connection_manager.listen_to_connection(conn, self.process_message)

    def _handle_server_join(self, msg: Message, conn):
        self.connection_manager.active_connections_peer_to_peer[msg.sender_id] = conn
        print(f"[Server {self.server_id}] peer joined: {msg.sender_id}")

        self.connection_manager.listen_to_connection(conn, self.process_message)

    def _send_rooms_to_client(self, addr):
        response = Message(
            type=MessageType.AVAILABLE_ROOMS,
            sender_id=self.server_id,
            content=json.dumps({
                "rooms": self.metadata_store.room_locations,
                "servers": self.servers,
            }),
        )

        self.udp_handler.send_to(response, addr)

    #Neighbor lookup
    def get_neighbors(self, my_id):
        if not self.ring or my_id not in self.ring:
            return None, None

        idx = self.ring.index(my_id)

        left = self.ring[(idx + 1) % len(self.ring)]
        right = self.ring[(idx - 1) % len(self.ring)]

        return left, right

    # chat / control plane

    def create_room(self, room_id: str) -> Room:
        """Creates a new room with this node as the host."""
        if room_id not in self.managed_rooms:
            self.managed_rooms[room_id] = Room(host=self, room_id=room_id)
            print(f"[Server {self.server_id}] created room {room_id}")
            # self.metadata_store.room_locations[room_id] = self.server_id
            if self.leader_id is not None:
                self.metadata_store.update_metadata(room_id, self, self.connection_manager)

        return self.managed_rooms[room_id]

    def _handle_join_room(self, msg: Message):
        room_id = msg.room_id
        client_id = msg.sender_id

        if room_id not in self.managed_rooms:
            self.managed_rooms[room_id] = Room(self, room_id) # Added self
            print(f"[Server {self.server_id}] created room {room_id}")

        self.managed_rooms[room_id].add_client(client_id)

        print(
            f"[Server {self.server_id}] client {client_id} joined room {room_id}"
        )

    def _recompute_ring(self):
        members = [self.server_id]
        members.extend(self.connection_manager.active_connections_peer_to_peer.keys())

        new_ring = sorted(set(members))

        if new_ring == self.ring:
            return

        self.ring = new_ring

        idx = self.ring.index(self.server_id)
        left = self.ring[(idx + 1) % len(self.ring)]
        right = self.ring[(idx - 1) % len(self.ring)]

        self.right_neighbor = RingNeighbor(right, '127.0.0.1', 5001)
        self.left_neighbor = RingNeighbor(left,'127.0.0.1', 5001)

        print(f"[Server {self.server_id}] ring stabilized:")
        print(" members:", self.ring)
        print(" left:", left)
        print(" right:", right)

    def _handle_available_rooms(self, msg: Message):
        data = json.loads(msg.content)

        client_ip = data["client_ip"]
        client_port = data["client_port"]

        response = Message(
            type=MessageType.AVAILABLE_ROOMS,
            sender_id=self.server_id,
            content=json.dumps({
                "rooms": self.metadata_store.room_locations,
                "servers": self.servers,
            }),
        )

        self.udp_handler.send_to(response, (client_ip, client_port))


    def update_neighbour_id(self, msg: Message):
        if msg.sender_id == self.left_neighbor.id:
            self.left_neighbor.id = msg.content
            print('Updated my left to ', msg.content)
        elif msg.sender_id == self.right_neighbor.id:
            self.right_neighbor.id = msg.content
            print('Updated my right to ', msg.content)
        self.state = ServerState.FOLLOWER

    def process_message(self, msg: Message):
        match msg.type:
            case MessageType.CHAT:
                if msg.room_id in self.managed_rooms:
                    room = self.managed_rooms[msg.room_id]
                    self.multicast_handler.handle_chat_message(msg, room)
                else:
                    print(
                        f"[Server {self.server_id}] "
                        f"room {msg.room_id} not found"
                    )

            case MessageType.ELECTION:
                self.election_module.handle_message(msg, self.connection_manager)

            case MessageType.HEARTBEAT:
                self.failure_detector.handle_heartbeat(msg)

            case MessageType.JOIN_ROOM:
                self._handle_join_room(msg)

            case MessageType.UPDATE_NEIGHBOUR:
                self.update_neighbour_id(msg)

            case MessageType.AVAILABLE_ROOMS:
                if self.state == ServerState.LEADER:
                    self._handle_available_rooms(msg)

            case MessageType.METADATA_UPDATE:
                self.metadata_store.handle_message(msg, self.connection_manager)

            case _:
                print(
                    f"[Server {self.server_id}] "
                    f"unknown message type: {msg.type}"
                )
