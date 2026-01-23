import time
from mesh_core import MeshNetwork, Node  # assume bindings via PyO3
from mesh_lowlevel import forward_packet, encrypt_packet  # via C++ FFI

mesh = MeshNetwork()
mesh.monitor_nodes()

def add_device(node_id, ip, latency=50):
    node = Node(id=node_id, ip=ip, latency_ms=latency)
    mesh.add_node(node)

def route_packet(source_id, dest_id, payload):
    node = mesh.select_best_node()
    if node:
        packet = {'source': source_id, 'destination': dest_id, 'payload': payload}
        encrypt_packet(packet)  # C++ low-level encryption
        forward_packet(packet)
        print(f"[Python] Routed via node {node.id}")

# Example usage
if __name__ == "__main__":
    add_device("node1", "192.168.1.2")
    add_device("node2", "192.168.1.3")
    
    while True:
        route_packet("me", "node1", b"Hello Mesh!")
        time.sleep(5)