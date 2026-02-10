import sys
import os
from src.server.server_node import ServerNode
import uuid

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.main_server <port> [rooms]")
        sys.exit(1)

    # server_id = sys.argv[1]
    port = int(sys.argv[1])
    rooms = int(sys.argv[2]) if len(sys.argv) > 2 else 1 #Default 1 room

    server = ServerNode(
        server_id=os.getpid(), # It was os.getpid() uuid.uuid4()
        ip_address="0.0.0.0",
        port=port,
        number_of_rooms=rooms,
    )
    server.start()
