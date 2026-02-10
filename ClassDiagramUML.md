class Message {
        +String message_id
        +String content
        +String sender_id
        +String room_id
        +serialize() String
        +deserialize(String data)$ Message
    }

    class MessageType {
        <<enumeration>>
        CLIENT_JOIN
        JOIN_ROOM
        LEAVE_ROOM
        CHAT
        DISCOVERY
        ELECTION
        HEARTBEAT
        SYNC
        METADATA_UPDATE
    }

    class VectorClock {
        +Map~String, int~ timestamps
        +copy() VectorClock
        +increment(String node_id)
        +merge(VectorClock other)
        +compare(VectorClock other) int
        +is_causally_ready(VectorClock other, String sender_id) bool
    }

    class Room {
        +String room_id
        +List~String~ client_ids
        +List~Message~ message_history
        +List~Message~ hold_back_queue
        +ServerNode host
        +copy() Room
        +add_client(String client_id)
        +remove_client(String client_id)
        +add_message(Message msg)
    }

    class UDPHandler {
        +Socket socket
        +broadcast(Message msg, int port)
        +listen(int port, callback)
    }

    class TCPConnection {
        +Socket socket
        +send(Message msg)
        +receive() Message
        +close()
        -_recv_exact(int size) bytes
    }

    class ConnectionManager {
        +Map~String, TCPConnection~ active_connections_peer_to_peer
        +Map~String, TCPConnection~ active_connections_server_to_client
        +connect_to(String ip, int port) TCPConnection
        +wrap_socket(Socket sock) TCPConnection
        +listen_to_connection(TCPConnection conn, callback)
        +send_to_node(String node_id, Message msg)
        +broadcast_to_all(Message msg)
    }

    class ServerNode {
        +String server_id
        +String ip_address
        +int port
        +String leader_id
        +RingNeighbor left_neighbor
        +RingNeighbor right_neighbor
        +int number_of_rooms
        +Map~String, dict~ servers
        +Map~String, Room~ managed_rooms 
        +start()
        +StartFailureDetection()
        +run()
        +create_room(String room_id) Room
        +handle_join(Socket sock, Addr addr)
        +process_message(Message msg)
        -_broadcast_server_discovery()
        -_handle_udp_message(Message msg)
        -_handle_server_discovery(Message msg)
        -_handle_client_discovery(Message msg)
        -_send_rooms_to_client(Addr addr)
        -_recompute_ring()
        -_handle_join_room(Message msg)
        +get_neighbors(String my_id)
        +update_neighbour_id(Message msg)
    }

    class ServerState {
        <<enumeration>>
        LOOKING
        FOLLOWER
        LEADER
        ELECTION_IN_PROGRESS
    }

    class ElectionModule {
        +ServerNode Node
        +int k
        +int reply_counter
        +ConstructElectionMessage(id, k, d)
        +ConstructReplyMessage(id, k)
        +ConstructLeaderAnnoucementMessage(id)
        +ParseMessage(Message msg)
        +handle_message(Message msg, ConnectionManager cm)
        +start_election(ConnectionManager cm)
    }

    class FailureDetector {
        +ServerNode Node
        +String type
        +Map timers
        +send_heartbeat(ConnectionManager cm, MetadataStore ms)
        +start_monitoring(ConnectionManager cm)
        +resetTimer(id, type)
        +on_failure_detected(typeid, ConnectionManager cm)
        +check_timeouts(ConnectionManager cm)
    }

    class MetadataStore {
        +Map~String, String~ room_locations
        +handle_message(Message msg)
        +update_metadata(String room_id, ServerNode server, ConnectionManager cm)
        +sync_with_leader(TCPConnection peer, String id)
    }

    class CausalMulticastHandler {
        +handle_chat_message(Message msg, Room room)
        -deliver_and_multicast(Message msg, Room room)
        -check_queue_recursively(Room room)
        +multicast(Message msg, Room room)
    }

    class ChatClient {
        +String client_id
        +String username
        +TCPConnection server_connection
        +start(String ip, int port)
        +discover_server(int port, callback)
        +join_room(String room_id)
        +send_message(String content, String room_id)
        +receive_message(Message msg)
    }

    Message *-- VectorClock
    Message *-- MessageType
    
    Room *-- VectorClock
    Room o-- Message
    
    ServerNode *-- ConnectionManager
    ServerNode *-- ElectionModule
    ServerNode *-- FailureDetector
    ServerNode *-- MetadataStore
    ServerNode *-- CausalMulticastHandler
    ServerNode o-- Room
    ServerNode *-- UDPHandler
    ServerNode o-- ServerState
    
    ConnectionManager o-- TCPConnection

    ChatClient *-- ConnectionManager
    ChatClient *-- VectorClock
    ChatClient *-- UDPHandler
    
    CausalMulticastHandler ..> Room : modifies