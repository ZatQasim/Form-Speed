# Form Speed Network - Replit.md

## Overview

Form Speed is a multi-layered network optimization and security platform that provides VPN protection, speed sharing, mesh networking, and security features. The application is a Flask-based web service with a subscription model (Pro tier) that offers premium features including VPN access, bandwidth sharing between peers, mesh network routing, and advanced analytics.

The platform supports device management, two-factor authentication, cloud storage, password management, and various network diagnostic tools (WiFi analysis, port scanning, certificate scanning, traceroute mapping).

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python) with SQLAlchemy ORM
- **Authentication**: Flask-Login for session management with optional TOTP-based 2FA (pyotp)
- **Database**: SQLAlchemy with SQLite fallback, designed for PostgreSQL in production (`DATABASE_URL` environment variable)
- **Payment Processing**: Stripe integration for subscription billing

### Data Storage
- **User Data**: SQLAlchemy models in relational database
- **State Management**: JSON file-based caching in `device_client/cache/` directory for:
  - User states (`user_states.json`)
  - Network metrics (`network_data.json`, `metrics_cache.json`)
  - Device registry (`devices.json`)
  - Connection history (`connection_history.json`)
  - Invite/sharing codes (`invite_codes.json`)
- **Configuration**: JSON config files in `form_config/` for global settings, device defaults, server settings, and node registry

### Frontend Architecture
- **Templating**: Jinja2 templates with a base layout (`base.html`)
- **Styling**: Custom CSS with CSS variables for theming (Google-inspired design system)
- **JavaScript**: Inline scripts in templates for API interactions
- **Dashboard Structure**: Sidebar navigation with multiple feature sections (VPN, Speed Sharing, Security, Mesh, Tools, Cloud, Analytics, etc.)

### Feature Modules
1. **VPN System**: Server selection, connection state management, IP assignment
2. **Speed Sharing**: Peer-to-peer bandwidth sharing with invite codes and guest access
3. **Security**: Threat blocking, protection status tracking
4. **Mesh Network**: P2P routing (Python manager with planned Rust/C++ bindings)
5. **Analytics Dashboard**: Separate Flask app for metrics visualization using Matplotlib
6. **Network Tools**: WiFi analyzer, port scanner, certificate scanner, traceroute mapper, packet detector
7. **Password Manager**: Encrypted credential storage
8. **Cloud Storage**: File upload with Google Cloud Storage integration

### Subscription Model
- **Pro Users**: Managed via `pro.json` whitelist and Stripe subscriptions
- **Trial Period**: 7-day free trial at $5/month
- **Feature Gating**: Pro-only features locked for free users in dashboard

## External Dependencies

### Python Packages (requirements.txt)
- **flask, flask-login, flask-sqlalchemy**: Web framework and auth
- **stripe**: Payment processing
- **werkzeug**: Password hashing
- **pyotp, qrcode**: Two-factor authentication
- **matplotlib**: Chart generation for analytics
- **psycopg2-binary**: PostgreSQL database driver
- **openai, tenacity**: AI integration capabilities

### Node.js Packages (package.json)
- **@google-cloud/storage**: Cloud storage integration
- **@uppy/core, @uppy/dashboard, @uppy/aws-s3, @uppy/react**: File upload UI components
- **google-auth-library**: GCP authentication

### Third-Party Services
- **Stripe**: Subscription billing and payment processing (`STRIPE_KEY` env variable)
- **Google Cloud Storage**: Object storage via Replit integration (sidecar at `127.0.0.1:1106`)
- **Google Maps API**: Used in traceroute and packet detector visualization tools

### Environment Variables
- `SESSION_SECRET`: Flask session encryption key
- `DATABASE_URL`: PostgreSQL connection string
- `STRIPE_KEY`: Stripe API key for payments
- `PUBLIC_OBJECT_SEARCH_PATHS`: Cloud storage public paths configuration