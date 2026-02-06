# src/client/run_client.py
import sys
import time
from src.client.chat_client import ChatClient

DISCOVERY_TIMEOUT = 5 # seconds

if __name__ == "__main__":
    client = ChatClient(username="user")

    if len(sys.argv) == 3:
        ip = sys.argv[1]
        port = int(sys.argv[2])
        print("[Client] connecting manually...")
        client.start(ip, port)
    else:
        print("[Client] discovering server...")
        client.discover_server()

        start_time = time.time()
        while client.server_connection is None:
            if time.time() - start_time > DISCOVERY_TIMEOUT:
                print("[Client] No server discovered")
                sys.exit(1)
            time.sleep(0.1)

    client.join_room("room1")

    try:
        while True:
            msg = input("> ")
            client.send_message(msg, "room1")
    except KeyboardInterrupt:
        print("\n[Client] shutting down")