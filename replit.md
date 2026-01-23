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

### UI Redesign - Modern Google/AT&T Style
- Complete CSS overhaul with clean, minimalist design
- Light theme with white backgrounds, subtle shadows, and professional typography
- Google Sans font family for consistent modern look
- CSS variables for consistent theming (primary blue #1a73e8, secondary green #34a853)
- Rounded corners, subtle borders, and smooth transitions throughout

### Cancel Subscription Feature
- New Cancel Subscription page at `/cancel-subscription`
- Backend route `/process-cancellation` handles Stripe subscription cancellation
- Whitelist users (pro.json) cannot cancel through self-service
- Form collects cancellation reason for feedback

### Previous Changes
- Created main Flask web application (`app.py`) with full authentication and dashboard
- Added `pro.json` configuration for Pro user management and Stripe settings
- Implemented Signup/Login pages with password hashing
- Integrated Stripe subscription with $5/month pricing and 7-day free trial
- Created multiple dashboard pages:
  - Overview (main dashboard with network metrics)
  - VPN (server selection and connection with persistent state)
  - Speed Sharing (peer management and bandwidth sharing)
  - Security (threat protection and monitoring)
  - Analytics (real-time network performance metrics)
  - Settings (user account and preferences)
- Added Form logo to static assets
- Dark theme UI with cyan/green accent colors

### Live Data Features (No Mock Data)
- **Real latency measurement**: Measures actual network latency to servers using socket connections
- **Persistent VPN state**: VPN stays connected until user manually disconnects (stored in user_states.json)
- **Real peer network**: Speed sharing peers are stored and tracked in network_data.json
- **Case-insensitive pro.json matching**: Usernames and emails in pro.json work regardless of case
- **Automatic Pro assignment**: Users matching pro.json get Pro status immediately on signup

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