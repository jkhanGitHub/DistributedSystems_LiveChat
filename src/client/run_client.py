# src/client/run_client.py
import sys
from src.client.chat_client import ChatClient

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m src.client.run_client <ip> <port>")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2])

    client = ChatClient(username="user")
    client.start(ip=ip, port=port)
    client.join_room("room1")

    while True:
        msg = input("> ")
        client.send_message(msg, "room1")

