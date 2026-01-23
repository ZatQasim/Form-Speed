# Form Project Architecture

**Version:** 0.1.0  
**Date:** 2026-01-23

---

## Overview

Form is a modular, multi-layered network optimization and security system.  
It consists of the following layers:

1. **Configuration Layer (`form_config/`)**  
   Centralized configuration files for devices, servers, and analytics.

2. **Device Client Layer (`device_client/`)**  
   Monitors network, manages VPN, routing, speed sharing, and security.

3. **Routing Server Layer (`routing_server/`)**  
   Optimizes routing using AI, handles device communications, load balancing, and firewall/security.

4. **Shared Library Layer (`shared_libs/`)**  
   Reusable crypto, network, and AI helper libraries across layers.

5. **Mesh Network Layer (`mesh_network/`)**  
   Enables local device-to-device routing for speed and redundancy.

6. **Analytics Dashboard Layer (`analytics_dashboard/`)**  
   Visualizes metrics, bandwidth, and routing efficiency.

7. **Documentation Layer (`docs/`)**  
   Architecture, API references, and roadmap.

---

## Data Flow

1. Device collects network metrics (`device_client/core/network_monitor.rs`).  
2. Metrics are cached locally (`cache/metrics_cache.json`).  
3. Device requests optimal routes from routing server (`routing_server/core/node_comm.go`).  
4. Server evaluates routes using AI optimizer (`ai_optimizer.py`) and load balancer (`load_balancer.go`).  
5. Device applies route and optionally shares speed (`speed_sharing.rs`).  
6. Mesh network layer extends routing locally between devices (`mesh_network/mesh_manager.py`).  
7. Analytics dashboard visualizes network performance (`analytics_dashboard/`).

---

## Technology Stack

- **Rust**: Core routing, device client, mesh logic, low-level utilities  
- **C++**: VPN, packet handling, network monitoring  
- **Go**: Routing server, concurrency  
- **Python**: AI, orchestration, dashboard backend  
- **Kotlin / Swift**: Mobile device integration  
- **JavaScript / HTML / CSS**: Dashboard frontend