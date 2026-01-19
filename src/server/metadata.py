from typing import Dict, Any

class MetadataStore:
    def __init__(self):
        self.room_locations: Dict[str, str] = {}
        # using Dict[str, Any] for ClientInfo as it wasn't strictly defined in models yet
        self.active_clients: Dict[str, Any] = {}

    def sync_with_leader(self):
        # Skeleton implementation
        pass

    def update_metadata(self):
        # Skeleton implementation
        pass
