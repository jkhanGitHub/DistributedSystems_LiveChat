import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    print("Importing domain models...")
    from src.domain.models import Message, VectorClock, Room, MessageType
    print("Domain models imported successfully.")

    print("Importing network layer...")
    from src.network.transport import UDPHandler, TCPConnection, ConnectionManager
    print("Network layer imported successfully.")

    print("Importing server modules...")
    from src.server.election import ElectionModule
    from src.server.failure_detector import FailureDetector
    from src.server.metadata import MetadataStore
    from src.server.multicast import CausalMulticastHandler
    from src.server.server_node import ServerNode
    print("Server modules imported successfully.")

    print("Importing client modules...")
    from src.client.chat_client import ChatClient
    print("Client modules imported successfully.")

    print("All imports successful!")

except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
