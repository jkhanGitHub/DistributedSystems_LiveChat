import socket

def form_ring(members):
    sorted_binary_ring = sorted(socket.inet_aton(m) for m in members)
    return [socket.inet_ntoa(node) for node in sorted_binary_ring]

def get_neighbour(ring, current_node_ip, direction="left"):
    if current_node_ip not in ring:
        return None

    idx = ring.index(current_node_ip)

    if direction == "left":
        return ring[(idx + 1) % len(ring)]
    else:
        return ring[(idx - 1) % len(ring)]
