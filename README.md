
README.md

# Form

**Owner:** ZatQasim (Mohamed Mohamed Diriye)  
**Version:** 0.1.0  
**License:** Apache-2.0  

---

## Overview

Form is a modular, multi-layered network optimization and security system that allows users to:

- Automatically find the fastest and most secure network routes.
- Protect devices from backdoors, intrusions, and malware.
- Share bandwidth and network features with other users (Speed Sharing).
- Extend routing locally through Mesh Networking.
- Visualize network performance through an optional Analytics Dashboard.

Form supports **all network types** — local, regional, and global — and works across **desktop, Android, and iOS devices**.

---

## Features

1. **Adaptive Routing** – Optimizes your network path using AI predictions.  
2. **VPN Integration** – Full encryption and secure routing.  
3. **Speed Sharing** – Share your bandwidth with other trusted Form users.  
4. **Mesh Networking** – Device-to-device routing for local speed improvements.  
5. **Security Agent** – Local firewall, malware detection, and intrusion prevention.  
6. **Analytics Dashboard** – Visualizations of latency, bandwidth, and route efficiency.  

---

## Architecture

Form is organized into **7 modular layers**:

1. **Configuration Layer (`form_config/`)** – Centralized configuration files for devices, servers, and dashboards.  
2. **Device Client Layer (`device_client/`)** – Network monitoring, routing, VPN, ARN, Speed Sharing.  
3. **Routing Server Layer (`routing_server/`)** – Route optimization, AI predictions, load balancing, firewall/security.  
4. **Shared Library Layer (`shared_libs/`)** – Crypto, network tools, AI helpers, and low-level utilities.  
5. **Mesh Network Layer (`mesh_network/`)** – Device-to-device routing for speed and redundancy.  
6. **Analytics Dashboard Layer (`analytics_dashboard/`)** – Visualizes metrics and routing efficiency.  
7. **Documentation Layer (`docs/`)** – Architecture, API references, and roadmap.  

For a complete blueprint, refer to `docs/architecture.md`.

---

## Supported Platforms

- **Desktop:** Windows, Linux, macOS  
- **Mobile:** Android (Kotlin), iOS (Swift)  
- **Languages Used:** Rust, C++, Go, Python, Kotlin, Swift, JavaScript, HTML/CSS  

---

## Installation

**Device Client**:

```bash
# Rust dependencies
cargo build --release

# Python dependencies for orchestration and optional UI
pip install -r requirements.txt

Routing Server:

# Go server
go build -o routing_server ./core/main_server.go

# Python AI helpers
pip install -r requirements.txt

Mesh Network:

# Rust
cargo build --release

# Python orchestration
python mesh_manager.py


---

Usage

1. Configure form_config/global_settings.json and device/server defaults.


2. Start Routing Server first:

./routing_server


3. Start Device Client:

cargo run --release --bin device_client


4. Optional: Run Analytics Dashboard:

python analytics_dashboard/backend/dashboard.py


5. Optional: Enable Mesh Network for local routing:

python mesh_network/mesh_manager.py




---

Logging

Device Client: device_client/logs/device_activity.log, device_client/logs/vpn.log

Routing Server: routing_server/logs/server_activity.log, routing_server/logs/node_status.log

Mesh Network: mesh_network/logs/mesh_activity.log

Dashboard: analytics_dashboard/logs/dashboard_activity.log



---

Contribution

Fork the repository, create feature branches, and submit pull requests.

All contributions are under Apache-2.0 License.

Use docs/roadmap.md as guidance for planned features and milestones.



---

Contact

Owner: ZatQasim (Mohamed Mohamed Diriye)
Email: [formatui.software@gmail.com]
Project: Form
License: Apache-2.0