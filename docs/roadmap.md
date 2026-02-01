# Form Speed API Reference

**Version:** 0.1.0  
**Date:** 2026-01-23

---

## Device Client ↔ Routing Server API

### 1. `/api/metrics` (GET)
Returns the current device metrics cache.
```json
{
    "latency_ms": 22,
    "download_mbps": 95,
    "upload_mbps": 18,
    "packet_loss_percent": 0.2
}