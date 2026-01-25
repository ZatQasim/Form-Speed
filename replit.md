# Form Network Optimization System

## Overview

Form is a modular network optimization and security platform that provides VPN protection, speed sharing, mesh networking, and analytics capabilities. The system allows users to optimize network routes, share bandwidth with trusted peers, and protect devices from security threats. It features a Flask-based web dashboard for user management, subscription handling via Stripe, and network monitoring.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Application Layer
- **Framework**: Flask with SQLAlchemy ORM and Flask-Login for authentication
- **Database**: PostgreSQL (via `psycopg2-binary`) with SQLite fallback for development
- **Template Engine**: Jinja2 templates in `templates/` directory
- **Static Assets**: CSS and images in `static/` folder

### Authentication & Authorization
- User authentication via Flask-Login with session management
- Two-factor authentication (2FA) using TOTP with `pyotp` library
- QR code generation for 2FA setup
- Password hashing with Werkzeug security utilities

### Subscription & Payments
- Stripe integration for subscription management
- Pro user whitelist maintained in `pro.json`
- Subscription features: VPN, Speed Sharing, Mesh Network, Advanced Analytics
- 7-day free trial with $5/month pricing

### State Management
- User states stored in JSON files under `device_client/cache/`
- Network metrics, connection history, and device data cached locally
- Per-user state tracking for VPN connections, speed sharing, and security settings

### Configuration Architecture
- Global settings in `form_config/` for servers, devices, and dashboard
- Nodes registry for VPN server definitions
- Modular configuration approach separating concerns

### Analytics Dashboard
- Separate Flask backend in `analytics_dashboard/backend/`
- Matplotlib-based visualization generation
- Frontend with real-time metrics polling via JavaScript

### Planned Multi-Language Architecture
The documentation references future components in:
- **Rust**: Core routing, device client, mesh networking
- **Go**: Server-side routing, load balancing
- **Python**: AI optimization, mesh management, web dashboard
- **C++**: Low-level encryption and packet forwarding

Currently, only Python components are implemented.

## External Dependencies

### Payment Processing
- **Stripe**: Subscription billing and checkout session management

### Database
- **PostgreSQL**: Primary database (requires `DATABASE_URL` environment variable)
- **SQLite**: Fallback for local development

### Authentication
- **pyotp**: TOTP-based two-factor authentication
- **qrcode**: QR code generation for 2FA setup

### Visualization
- **Matplotlib**: Network metrics chart generation

### Environment Variables
- `SESSION_SECRET`: Flask session encryption key
- `DATABASE_URL`: PostgreSQL connection string
- `STRIPE_KEY`: Stripe API secret key

### Data Storage
- JSON file-based caching for user states, devices, metrics, and connection history
- Files stored in `device_client/cache/` directory