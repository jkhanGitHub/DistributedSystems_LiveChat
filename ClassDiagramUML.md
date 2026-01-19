    class Message {
        +UUID message_id
        +String content
        +String sender_id
        +String room_id
        +VectorClock vector_clock
        +MessageType type
        +serialize()
        +deserialize()
    }

    class MessageType {
        <<enumeration>>
        CHAT
        DISCOVERY
        ELECTION
        HEARTBEAT
        SYNC
        METADATA_UPDATE
    }

    class VectorClock {
        +Map~String, Integer~ timestamps
        +increment(String node_id)
        +merge(VectorClock other)
        +compare(VectorClock other) int
        +is_causally_ready(VectorClock other) bool
    }

    class Room {
        +String room_id
        +List~String~ client_ids
        +List~Message~ message_history
        +add_client(String client_id)
        +remove_client(String client_id)
        +add_message(Message msg)
    }


    class UDPHandler {
        +broadcast(Message msg, int port)
        +listen(int port, callback)
    }

    class TCPConnection {
        +Socket socket
        +send(Message msg)
        +receive() Message
        +close()
    }

    class ConnectionManager {
        +Map~String, TCPConnection~ active_connections_peer_to_peer
        +Map~String, TCPConnection~ active_connections_server_to_client
        +connect_to(String ip, int port)
        +listen_for_connections(int port)
        +send_to_node(String node_id, Message msg)
        +broadcast_to_all(Message msg)
    }

  
    class ServerNode {
        +String server_id
        +String ip_address
        +int port
        +ServerState state
        +String leader_id
        +RingNeighbor left_neighbor
        +RingNeighbor right_neighbor
        +Map~String, Room~ managed_rooms
        --
        +start()
        +handle_discovery()
        +handle_join()
        +process_message(Message msg)
    }

    class ServerState {
        <<enumeration>>
        LOOKING
        FOLLOWER
        LEADER
        ELECTION_IN_PROGRESS
    }

    class ElectionModule {
        +String candidate_id
        +start_election()
        +handle_election_message(Message msg)
        -hirschberg_sinclair_algo()
    }

    class FailureDetector {
        +start_monitoring(Map~String, Node~ nodes)
        +send_heartbeat()
        +check_timeouts()
        +on_failure_detected(String failed_node_id)
    }

    class MetadataStore {
        +Map~String, String~ room_locations
        +Map~String, ClientInfo~ active_clients
        +sync_with_leader()
        +update_metadata()
    }

    class CausalMulticastHandler {
        +VectorClock local_clock
        +List~Message~ hold_back_queue
        +deliver_message(Message msg)
        +multicast(Message msg)
        -check_delivery_condition()
    }

    class ChatClient {
        +String client_id
        +String username
        +TCPConnection server_connection
        +VectorClock client_clock
        +start()
        +discover_server()
        +join_room(String room_id)
        +send_message(String content)
        +receive_message(Message msg)
    }


    Message *-- VectorClock
    Message *-- MessageType
    
    ServerNode *-- ConnectionManager
    ServerNode *-- ElectionModule
    ServerNode *-- FailureDetector
    ServerNode *-- MetadataStore
    ServerNode *-- CausalMulticastHandler
    ServerNode o-- Room
    ServerNode --> UDPHandler : uses

    ChatClient *-- ConnectionManager
    ChatClient --> UDPHandler : uses
    
    ElectionModule ..> ConnectionManager : sends votes
    CausalMulticastHandler ..> ConnectionManager : sends chats