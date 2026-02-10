# src/client/run_client.py
import sys
import time
from src.client.chat_client import ChatClient

DISCOVERY_PORT = 6000
DISCOVERY_TIMEOUT = 5 # seconds

if __name__ == "__main__":
    client = ChatClient(username="user")

    if len(sys.argv) == 3:
        ip = sys.argv[1]
        port = int(sys.argv[2])
        print("[Client] connecting manually...")
        client.start(ip, port)
    else:
        print("[Client] discovering rooms...")
        client.discover_server(DISCOVERY_PORT)

    try:
        while True:
            msg = input("> ")
            client.send_message(msg, client.current_room)
    except KeyboardInterrupt:
        print("\n[Client] shutting down")
