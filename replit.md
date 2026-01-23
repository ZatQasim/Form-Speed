# Form Network Application

## Overview

Form is a network optimization and security platform that provides VPN access, speed sharing between peers, mesh networking, and network analytics. The application features a Flask-based web interface with user authentication, Stripe subscription payments for Pro features, and a modular architecture designed for cross-platform deployment (desktop, Android, iOS).

The core value proposition is a $5/month Pro subscription that unlocks VPN access, peer-to-peer bandwidth sharing, mesh network participation, priority routing, and advanced analytics with a 7-day free trial.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Application Layer
- **Framework**: Flask with Jinja2 templating
- **Authentication**: Flask-Login with password hashing via Werkzeug
- **Database**: SQLAlchemy ORM with SQLite default, PostgreSQL-ready via `psycopg2-binary`
- **Payments**: Stripe integration for subscription management with checkout sessions and webhooks

### User & Subscription Model
- Users have email, username, password hash, and subscription status
- Pro status determined by `is_pro` flag, active Stripe subscription, or valid trial period
- Trial system provides 7-day free access before payment required
- Pro user whitelist maintained in `pro.json` for manual overrides

### Frontend Architecture
- Server-rendered HTML templates with CSS styling
- Dark theme with cyan/green accent colors
- Dashboard layout with sidebar navigation
- Protected routes require authentication; Pro features require active subscription

### Configuration System
- Centralized JSON configs in `form_config/` for global settings, device defaults, server defaults
- Separate dashboard settings for analytics display
- Node registry for VPN server locations with capacity and protocol support

### Network Metrics
- Metrics cached in `device_client/cache/metrics_cache.json`
- Tracks latency, jitter, packet loss, bandwidth, network type, signal strength
- Analytics dashboard generates matplotlib charts for visualization

### Planned Multi-Language Architecture
The codebase references Rust for core routing/device client, Go for server communication, and Python for AI/mesh management, though the current implementation is primarily Python/Flask.

## External Dependencies

### Payment Processing
- **Stripe**: Subscription billing, checkout sessions, customer management
- Requires `STRIPE_KEY` environment variable
- Price ID configured in `pro.json`

### Database
- **SQLite**: Default local database (`form.db`)
- **PostgreSQL**: Production-ready via `DATABASE_URL` environment variable

### Python Packages
- `flask`, `flask-login`, `flask-sqlalchemy`: Web framework and auth
- `stripe`: Payment processing
- `matplotlib`: Chart generation for analytics
- `psycopg2-binary`: PostgreSQL driver
- `werkzeug`: Password hashing and utilities

### Environment Variables
- `SESSION_SECRET`: Flask session encryption key
- `DATABASE_URL`: Database connection string (optional, defaults to SQLite)
- `STRIPE_KEY`: Stripe API secret key

## Recent Changes (January 23, 2026)

### New Dashboard Pages
- **Network Diagnostics** (`/dashboard/diagnostics`): Real-time speed tests, ping tests, traceroute functionality, and quick diagnostic checks
- **Account & Billing** (`/dashboard/account`): Subscription status, billing history, and account management
- **Connection History** (`/dashboard/history`): Event logging for VPN connections, security alerts, speed tests, and device activity with filtering
- **Device Management** (`/dashboard/devices`): Add/remove devices, supports up to 5 devices per Pro account

### API Endpoints Added
- `/api/diagnostics/speedtest` - Real-time download/upload speed measurement
- `/api/diagnostics/ping` - Ping test with statistics (avg/min/max latency, packet loss)
- `/api/diagnostics/traceroute` - Trace network path to destination
- `/api/history` - Get connection history events
- `/api/history/clear` - Clear user's connection history
- `/api/devices` - Get registered devices
- `/api/devices/add` - Register new device (max 5)
- `/api/devices/<id>` - Remove device

### Functional Features (Live Data, No Mocks)
- **VPN connections log events** to connection history (connect/disconnect with server details)
- **Speed tests save results** to metrics history for analytics
- **Device data persisted** in `device_client/cache/devices.json`
- **Connection history stored** in `device_client/cache/connection_history.json`
- **Real latency measurement**: Measures actual network latency to servers using socket connections
- **Persistent VPN state**: VPN stays connected until user manually disconnects
- **Real peer network**: Speed sharing peers are stored and tracked

### UI Updates
- Expanded sidebar navigation to 10 items (Overview, VPN, Speed Sharing, Security, Diagnostics, Analytics, History, Devices, Account, Settings)
- New CSS styles for diagnostics cards, account pages, history timeline, device grid, and modals
- Pro feature gating on new pages (require active subscription)

### Previous Changes
- Complete CSS overhaul with modern Google/AT&T-style design
- Light theme with white backgrounds, subtle shadows, and professional typography
- Cancel Subscription page with Stripe integration
- Flask web application with authentication, Stripe payments, and dashboard

## Dashboard Pages

| Route | Description | Access |
|-------|-------------|--------|
| `/` | Landing page with features and pricing | Public |
| `/signup` | User registration | Public |
| `/login` | User login | Public |
| `/subscribe` | Stripe checkout for Pro subscription | Authenticated |
| `/dashboard` | Main dashboard with metrics overview | Authenticated |
| `/dashboard/vpn` | VPN server selection and connection | Pro only |
| `/dashboard/speed-sharing` | Peer bandwidth sharing management | Pro only |
| `/dashboard/analytics` | Detailed network analytics | Authenticated |
| `/dashboard/settings` | Account and preference settings | Authenticated |