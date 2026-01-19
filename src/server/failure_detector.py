from typing import Dict, Any

class FailureDetector:
    def start_monitoring(self, nodes: Dict[str, Any]):
        # Skeleton implementation
        pass

    def send_heartbeat(self):
        # Skeleton implementation
        pass

    def check_timeouts(self):
        # Skeleton implementation
        pass

    def on_failure_detected(self, failed_node_id: str):
        # Skeleton implementation
        pass
