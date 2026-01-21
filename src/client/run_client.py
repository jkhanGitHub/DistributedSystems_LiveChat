from src.client.chat_client import ChatClient

if __name__ == "__main__":
    client = ChatClient(username="alice")
    client.start(ip="127.0.0.1", port=5001)

    client.join_room("room1")

    while True:
        msg = input("> ")
        client.send_message(msg, "room1")
