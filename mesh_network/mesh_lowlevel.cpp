#include <iostream>
#include <string>
#include <vector>

struct MeshPacket {
    std::string source;
    std::string destination;
    std::vector<uint8_t> payload;
};

extern "C" void forward_packet(MeshPacket& packet) {
    // Example: simple log-forward
    std::cout << "[Mesh] Forwarding packet from " 
              << packet.source << " to " 
              << packet.destination 
              << " (" << packet.payload.size() << " bytes)" << std::endl;
}

extern "C" void encrypt_packet(MeshPacket& packet) {
    // Dummy encryption: XOR with 0xAA
    for(auto& b : packet.payload) b ^= 0xAA;
}