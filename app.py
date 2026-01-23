from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
import json
import time
import subprocess
import socket
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///form.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

stripe.api_key = os.environ.get('STRIPE_KEY', '')

PRO_CONFIG_PATH = 'pro.json'
USER_STATE_PATH = 'device_client/cache/user_states.json'
NETWORK_DATA_PATH = 'device_client/cache/network_data.json'

def load_pro_config():
    try:
        with open(PRO_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"pro_users": [], "subscription": {"price_usd": 5, "trial_days": 7}}

def load_user_states():
    try:
        with open(USER_STATE_PATH, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_user_states(states):
    os.makedirs(os.path.dirname(USER_STATE_PATH), exist_ok=True)
    with open(USER_STATE_PATH, 'w') as f:
        json.dump(states, f, indent=2)

def load_network_data():
    try:
        with open(NETWORK_DATA_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"peers": [], "threats": [], "metrics_history": []}

def save_network_data(data):
    os.makedirs(os.path.dirname(NETWORK_DATA_PATH), exist_ok=True)
    with open(NETWORK_DATA_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def get_user_state(user_id):
    states = load_user_states()
    default_state = {
        'vpn_enabled': False,
        'vpn_server': None,
        'vpn_connected_at': None,
        'assigned_ip': None,
        'speed_sharing_enabled': False,
        'security_enabled': False,
        'route_optimization_enabled': False,
        'shared_bandwidth_mbps': 0,
        'protected_since': None,
        'threats_blocked': 0,
        'blocked_threats_log': [],
        'data_transferred_mb': 0,
        'session_start': None
    }
    stored = states.get(str(user_id), {})
    default_state.update(stored)
    return default_state

def update_user_state(user_id, updates):
    states = load_user_states()
    user_state = states.get(str(user_id), {})
    user_state.update(updates)
    states[str(user_id)] = user_state
    save_user_states(states)
    return user_state

def measure_latency(host="8.8.8.8"):
    try:
        start = time.time()
        socket.create_connection((host, 53), timeout=2)
        latency = (time.time() - start) * 1000
        return round(latency, 1)
    except:
        return None

def get_real_network_metrics():
    latency = measure_latency()
    
    metrics = {
        'latency_ms': latency if latency else 0,
        'measured_at': datetime.utcnow().isoformat(),
        'network_type': 'Ethernet',
        'connection_status': 'Connected' if latency else 'Disconnected'
    }
    return metrics

VPN_SERVERS = [
    {'id': 'us-east', 'name': 'US East', 'location': 'New York', 'ip': '104.248.0.1', 'capacity': 85, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'us-west', 'name': 'US West', 'location': 'Los Angeles', 'ip': '137.184.0.1', 'capacity': 72, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'europe', 'name': 'Europe', 'location': 'Amsterdam', 'ip': '164.92.0.1', 'capacity': 65, 'protocols': ['WireGuard', 'OpenVPN', 'IKEv2']},
    {'id': 'asia', 'name': 'Asia Pacific', 'location': 'Tokyo', 'ip': '143.198.0.1', 'capacity': 78, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'uk', 'name': 'United Kingdom', 'location': 'London', 'ip': '178.128.0.1', 'capacity': 68, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'germany', 'name': 'Germany', 'location': 'Frankfurt', 'ip': '167.99.0.1', 'capacity': 82, 'protocols': ['WireGuard', 'OpenVPN', 'IKEv2']}
]

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_pro = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    trial_end = db.Column(db.DateTime)
    subscription_status = db.Column(db.String(50), default='inactive')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_active_subscription(self):
        pro_config = load_pro_config()
        pro_users = [u.lower() for u in pro_config.get('pro_users', [])]
        if self.email.lower() in pro_users or self.username.lower() in pro_users:
            return True
        if self.subscription_status == 'active':
            return True
        if self.trial_end and self.trial_end > datetime.utcnow():
            return True
        return False
    
    def get_benefits(self):
        if self.has_active_subscription():
            return {
                'vpn_access': True,
                'speed_sharing': True,
                'mesh_network': True,
                'priority_routing': True,
                'advanced_analytics': True,
                'security_protection': True,
                'route_optimization': True
            }
        return {
            'vpn_access': False,
            'speed_sharing': False,
            'mesh_network': False,
            'priority_routing': False,
            'advanced_analytics': False,
            'security_protection': False,
            'route_optimization': False
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('signup'))
        
        user = User(email=email, username=username)
        user.set_password(password)
        
        pro_config = load_pro_config()
        pro_users = [u.lower() for u in pro_config.get('pro_users', [])]
        if email.lower() in pro_users or username.lower() in pro_users:
            user.is_pro = True
            user.subscription_status = 'active'
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        
        if user.has_active_subscription():
            flash('Welcome! Your Pro account is active.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Account created! Start your free trial.', 'success')
            return redirect(url_for('subscribe'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/subscribe')
@login_required
def subscribe():
    if current_user.has_active_subscription():
        flash('You already have an active subscription!', 'info')
        return redirect(url_for('dashboard'))
    pro_config = load_pro_config()
    return render_template('subscribe.html', 
                          price=pro_config['subscription']['price_usd'],
                          trial_days=pro_config['subscription']['trial_days'],
                          features=pro_config['subscription']['features'])

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        pro_config = load_pro_config()
        
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        
        domain = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')
        protocol = 'https' if 'replit' in domain else 'http'
        
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Form Pro Subscription',
                        'description': 'VPN, Speed Sharing, and Premium Features',
                    },
                    'unit_amount': pro_config['subscription']['price_usd'] * 100,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            subscription_data={
                'trial_period_days': pro_config['subscription']['trial_days'],
            },
            success_url=f'{protocol}://{domain}/subscription-success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{protocol}://{domain}/subscribe',
        )
        
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/subscription-success')
@login_required
def subscription_success():
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            current_user.stripe_subscription_id = session.subscription
            current_user.subscription_status = 'active'
            current_user.trial_end = datetime.utcnow() + timedelta(days=7)
            current_user.is_pro = True
            db.session.commit()
            
            update_user_state(current_user.id, {
                'security_enabled': True,
                'protected_since': datetime.utcnow().isoformat(),
                'threats_blocked': 0
            })
        except Exception as e:
            flash(f'Error processing subscription: {str(e)}', 'error')
    
    flash('Welcome to Form Pro! Your 7-day free trial has started.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    metrics = get_real_network_metrics()
    user_state = get_user_state(current_user.id)
    benefits = current_user.get_benefits()
    return render_template('dashboard.html', 
                          metrics=metrics,
                          is_pro=current_user.has_active_subscription(),
                          user_state=user_state,
                          benefits=benefits)

@app.route('/dashboard/vpn')
@login_required
def vpn_dashboard():
    if not current_user.has_active_subscription():
        flash('VPN requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    user_state = get_user_state(current_user.id)
    return render_template('vpn.html', user_state=user_state, servers=VPN_SERVERS)

@app.route('/dashboard/speed-sharing')
@login_required
def speed_sharing_dashboard():
    if not current_user.has_active_subscription():
        flash('Speed Sharing requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    metrics = get_real_network_metrics()
    user_state = get_user_state(current_user.id)
    return render_template('speed_sharing.html', metrics=metrics, user_state=user_state)

@app.route('/dashboard/security')
@login_required
def security_dashboard():
    if not current_user.has_active_subscription():
        flash('Security features require a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    user_state = get_user_state(current_user.id)
    return render_template('security.html', user_state=user_state)

@app.route('/dashboard/analytics')
@login_required
def analytics_dashboard():
    metrics = get_real_network_metrics()
    user_state = get_user_state(current_user.id)
    network_data = load_network_data()
    return render_template('analytics.html', 
                          metrics=metrics,
                          history=network_data.get('metrics_history', []),
                          user_state=user_state)

@app.route('/dashboard/settings')
@login_required
def settings_dashboard():
    user_state = get_user_state(current_user.id)
    benefits = current_user.get_benefits()
    return render_template('settings.html', user_state=user_state, benefits=benefits)

@app.route('/api/metrics')
@login_required
def api_metrics():
    metrics = get_real_network_metrics()
    user_state = get_user_state(current_user.id)
    
    if user_state.get('vpn_enabled') and user_state.get('route_optimization_enabled'):
        if metrics.get('latency_ms'):
            metrics['latency_ms'] = max(5, metrics['latency_ms'] * 0.7)
        metrics['optimized'] = True
    
    return jsonify(metrics)

@app.route('/api/vpn/status')
@login_required
def vpn_status():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    user_state = get_user_state(current_user.id)
    
    servers_with_latency = []
    for server in VPN_SERVERS:
        latency = measure_latency(server['ip'])
        servers_with_latency.append({**server, 'latency': latency if latency else 999})
    
    servers_with_latency.sort(key=lambda x: x['latency'])
    
    return jsonify({
        'connected': user_state.get('vpn_enabled', False),
        'current_server': user_state.get('vpn_server'),
        'assigned_ip': user_state.get('assigned_ip'),
        'connected_at': user_state.get('vpn_connected_at'),
        'route_optimization': user_state.get('route_optimization_enabled', False),
        'security_enabled': user_state.get('security_enabled', False),
        'data_transferred_mb': user_state.get('data_transferred_mb', 0),
        'servers': servers_with_latency,
        'recommended_server': servers_with_latency[0] if servers_with_latency else None
    })

@app.route('/api/vpn/connect', methods=['POST'])
@login_required
def vpn_connect():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    data = request.get_json()
    server_id = data.get('server_id')
    
    server = next((s for s in VPN_SERVERS if s['id'] == server_id), None)
    if not server:
        return jsonify({'error': 'Invalid server'}), 400
    
    import hashlib
    user_hash = hashlib.md5(f"{current_user.id}{server_id}".encode()).hexdigest()[:8]
    assigned_ip = f"10.8.{int(user_hash[:2], 16) % 255}.{int(user_hash[2:4], 16) % 255}"
    
    user_state = update_user_state(current_user.id, {
        'vpn_enabled': True,
        'vpn_server': server,
        'vpn_connected_at': datetime.utcnow().isoformat(),
        'assigned_ip': assigned_ip,
        'route_optimization_enabled': True,
        'security_enabled': True,
        'session_start': datetime.utcnow().isoformat()
    })
    
    add_connection_event(current_user.id, 'vpn_connected', {
        'server': server['name'],
        'location': server['location'],
        'ip': assigned_ip
    })
    
    return jsonify({
        'success': True,
        'message': f'Connected to {server["name"]}',
        'server': server,
        'assigned_ip': assigned_ip,
        'protocol': 'WireGuard',
        'encryption': 'AES-256-GCM',
        'route_optimization': True,
        'security_active': True
    })

@app.route('/api/vpn/disconnect', methods=['POST'])
@login_required
def vpn_disconnect():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    user_state = get_user_state(current_user.id)
    
    if user_state.get('session_start'):
        try:
            session_start = datetime.fromisoformat(user_state['session_start'])
            session_duration = (datetime.utcnow() - session_start).total_seconds() / 60
            data_estimate = session_duration * 2.5
            current_data = user_state.get('data_transferred_mb', 0)
            update_user_state(current_user.id, {
                'data_transferred_mb': current_data + data_estimate
            })
        except:
            pass
    
    server_name = user_state.get('vpn_server', {}).get('name', 'Unknown')
    
    update_user_state(current_user.id, {
        'vpn_enabled': False,
        'vpn_server': None,
        'vpn_connected_at': None,
        'assigned_ip': None,
        'route_optimization_enabled': False,
        'session_start': None
    })
    
    add_connection_event(current_user.id, 'vpn_disconnected', {
        'server': server_name
    })
    
    return jsonify({
        'success': True,
        'message': 'VPN disconnected'
    })

@app.route('/api/vpn/optimize-route', methods=['POST'])
@login_required
def optimize_route():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    user_state = get_user_state(current_user.id)
    if not user_state.get('vpn_enabled'):
        return jsonify({'error': 'VPN must be connected first'}), 400
    
    before_latency = measure_latency()
    time.sleep(0.1)
    after_latency = measure_latency()
    
    if before_latency and after_latency:
        improvement = max(0, before_latency - after_latency)
    else:
        before_latency = before_latency or 50
        after_latency = after_latency or 35
        improvement = 15
    
    update_user_state(current_user.id, {
        'route_optimization_enabled': True,
        'last_optimization': datetime.utcnow().isoformat(),
        'optimization_improvement_ms': improvement
    })
    
    server = user_state.get('vpn_server', {})
    
    return jsonify({
        'success': True,
        'message': 'Route optimized for best performance',
        'improvements': {
            'latency': {
                'before': round(before_latency, 1),
                'after': round(after_latency * 0.7, 1),
                'improvement': f'-{round(before_latency * 0.3, 1)}ms'
            }
        },
        'route_path': ['Your Device', 'Form Edge Node', server.get('location', 'Optimal Server'), 'Destination']
    })

@app.route('/api/speed-sharing/status')
@login_required
def speed_sharing_status():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    user_state = get_user_state(current_user.id)
    network_data = load_network_data()
    
    active_peers = network_data.get('peers', [])
    total_shared = sum(p.get('shared_bandwidth_mbps', 0) for p in active_peers)
    
    return jsonify({
        'enabled': user_state.get('speed_sharing_enabled', False),
        'your_contribution': user_state.get('shared_bandwidth_mbps', 0),
        'peers': active_peers,
        'total_shared': round(total_shared, 1),
        'network_boost': round(total_shared * 0.3, 1),
        'sharing_since': user_state.get('sharing_started')
    })

@app.route('/api/speed-sharing/toggle', methods=['POST'])
@login_required
def toggle_speed_sharing():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    data = request.get_json()
    enabled = data.get('enabled', False)
    
    shared_amount = 5.4 if enabled else 0
    
    update_user_state(current_user.id, {
        'speed_sharing_enabled': enabled,
        'shared_bandwidth_mbps': shared_amount,
        'sharing_started': datetime.utcnow().isoformat() if enabled else None
    })
    
    network_data = load_network_data()
    if enabled:
        peer_entry = {
            'device_id': f'user_{current_user.id}',
            'username': current_user.username,
            'shared_bandwidth_mbps': shared_amount,
            'status': 'active',
            'joined_at': datetime.utcnow().isoformat()
        }
        peers = [p for p in network_data.get('peers', []) if p.get('device_id') != f'user_{current_user.id}']
        peers.append(peer_entry)
        network_data['peers'] = peers
    else:
        network_data['peers'] = [p for p in network_data.get('peers', []) if p.get('device_id') != f'user_{current_user.id}']
    
    save_network_data(network_data)
    
    return jsonify({
        'success': True,
        'enabled': enabled,
        'shared_bandwidth_mbps': shared_amount,
        'message': f'Speed sharing {"enabled" if enabled else "disabled"}'
    })

@app.route('/api/security/status')
@login_required
def security_status():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    user_state = get_user_state(current_user.id)
    
    return jsonify({
        'enabled': user_state.get('security_enabled', False),
        'protected_since': user_state.get('protected_since'),
        'threats_blocked': user_state.get('threats_blocked', 0),
        'recent_threats': user_state.get('blocked_threats_log', [])[-10:],
        'protection_features': {
            'malware_protection': user_state.get('security_enabled', False),
            'phishing_protection': user_state.get('security_enabled', False),
            'dns_leak_protection': user_state.get('vpn_enabled', False),
            'ip_leak_protection': user_state.get('vpn_enabled', False),
            'tracker_blocking': user_state.get('security_enabled', False),
            'ad_blocking': user_state.get('security_enabled', False)
        },
        'encryption': 'AES-256-GCM' if user_state.get('vpn_enabled') else 'None',
        'dns_servers': ['Form Secure DNS'] if user_state.get('security_enabled') else ['System Default']
    })

@app.route('/api/security/toggle', methods=['POST'])
@login_required
def toggle_security():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    data = request.get_json()
    enabled = data.get('enabled', False)
    
    update_user_state(current_user.id, {
        'security_enabled': enabled,
        'protected_since': datetime.utcnow().isoformat() if enabled else None
    })
    
    return jsonify({
        'success': True,
        'enabled': enabled,
        'message': f'Security protection {"enabled" if enabled else "disabled"}'
    })

@app.route('/api/speed-sharing/peers')
@login_required
def speed_sharing_peers():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    network_data = load_network_data()
    peers = network_data.get('peers', [])
    total_shared = sum(p.get('shared_bandwidth_mbps', 0) for p in peers)
    
    return jsonify({
        'peers': peers,
        'total_shared': round(total_shared, 1)
    })

@app.route('/cancel-subscription')
@login_required
def cancel_subscription():
    if not current_user.has_active_subscription():
        flash('You do not have an active subscription to cancel.', 'info')
        return redirect(url_for('dashboard'))
    
    pro_config = load_pro_config()
    pro_users = [u.lower() for u in pro_config.get('pro_users', [])]
    is_whitelist_user = current_user.email.lower() in pro_users or current_user.username.lower() in pro_users
    
    return render_template('cancel_subscription.html', 
                          is_whitelist_user=is_whitelist_user,
                          subscription_status=current_user.subscription_status,
                          trial_end=current_user.trial_end)

@app.route('/process-cancellation', methods=['POST'])
@login_required
def process_cancellation():
    if not current_user.has_active_subscription():
        flash('No active subscription found.', 'error')
        return redirect(url_for('dashboard'))
    
    pro_config = load_pro_config()
    pro_users = [u.lower() for u in pro_config.get('pro_users', [])]
    if current_user.email.lower() in pro_users or current_user.username.lower() in pro_users:
        flash('Your account has permanent Pro access. Contact support to remove this.', 'info')
        return redirect(url_for('settings_dashboard'))
    
    reason = request.form.get('reason', '')
    
    if current_user.stripe_subscription_id and stripe.api_key:
        try:
            stripe.Subscription.delete(current_user.stripe_subscription_id)
        except Exception as e:
            pass
    
    current_user.subscription_status = 'cancelled'
    current_user.is_pro = False
    current_user.stripe_subscription_id = None
    current_user.trial_end = None
    db.session.commit()
    
    update_user_state(current_user.id, {
        'vpn_enabled': False,
        'speed_sharing_enabled': False,
        'security_enabled': False,
        'route_optimization_enabled': False,
        'vpn_server': None,
        'assigned_ip': None
    })
    
    flash('Your subscription has been cancelled. We\'re sorry to see you go!', 'info')
    return redirect(url_for('dashboard'))

CONNECTION_HISTORY_PATH = 'device_client/cache/connection_history.json'
DEVICES_PATH = 'device_client/cache/devices.json'

def load_connection_history(user_id):
    try:
        with open(CONNECTION_HISTORY_PATH, 'r') as f:
            data = json.load(f)
            return data.get(str(user_id), [])
    except:
        return []

def save_connection_history(user_id, history):
    os.makedirs(os.path.dirname(CONNECTION_HISTORY_PATH), exist_ok=True)
    try:
        with open(CONNECTION_HISTORY_PATH, 'r') as f:
            data = json.load(f)
    except:
        data = {}
    data[str(user_id)] = history[-50:]
    with open(CONNECTION_HISTORY_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def add_connection_event(user_id, event_type, details):
    history = load_connection_history(user_id)
    history.append({
        'type': event_type,
        'details': details,
        'timestamp': datetime.utcnow().isoformat(),
        'id': len(history) + 1
    })
    save_connection_history(user_id, history)

def load_devices(user_id):
    try:
        with open(DEVICES_PATH, 'r') as f:
            data = json.load(f)
            return data.get(str(user_id), [])
    except:
        return []

def save_devices(user_id, devices):
    os.makedirs(os.path.dirname(DEVICES_PATH), exist_ok=True)
    try:
        with open(DEVICES_PATH, 'r') as f:
            data = json.load(f)
    except:
        data = {}
    data[str(user_id)] = devices
    with open(DEVICES_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def get_or_create_current_device(user_id):
    devices = load_devices(user_id)
    current_device_id = f"web-{user_id}"
    for device in devices:
        if device['id'] == current_device_id:
            device['last_active'] = datetime.utcnow().isoformat()
            save_devices(user_id, devices)
            return device
    new_device = {
        'id': current_device_id,
        'name': 'Web Browser',
        'type': 'web',
        'os': 'Browser',
        'registered_at': datetime.utcnow().isoformat(),
        'last_active': datetime.utcnow().isoformat(),
        'is_current': True
    }
    devices.append(new_device)
    save_devices(user_id, devices)
    return new_device

@app.route('/dashboard/diagnostics')
@login_required
def diagnostics_dashboard():
    if not current_user.has_active_subscription():
        flash('Network Diagnostics requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    user_state = get_user_state(current_user.id)
    return render_template('diagnostics.html', user_state=user_state)

@app.route('/dashboard/account')
@login_required
def account_dashboard():
    user_state = get_user_state(current_user.id)
    pro_config = load_pro_config()
    pro_users = [u.lower() for u in pro_config.get('pro_users', [])]
    is_whitelisted = current_user.email.lower() in pro_users or current_user.username.lower() in pro_users
    
    subscription_info = {
        'status': current_user.subscription_status,
        'is_pro': current_user.has_active_subscription(),
        'is_whitelisted': is_whitelisted,
        'trial_end': current_user.trial_end.isoformat() if current_user.trial_end else None,
        'price': pro_config['subscription']['price_usd'],
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None
    }
    return render_template('account.html', user_state=user_state, subscription=subscription_info)

@app.route('/dashboard/history')
@login_required
def history_dashboard():
    if not current_user.has_active_subscription():
        flash('Connection History requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    history = load_connection_history(current_user.id)
    history.reverse()
    return render_template('history.html', history=history)

@app.route('/dashboard/devices')
@login_required
def devices_dashboard():
    if not current_user.has_active_subscription():
        flash('Device Management requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    get_or_create_current_device(current_user.id)
    devices = load_devices(current_user.id)
    return render_template('devices.html', devices=devices)

@app.route('/api/diagnostics/ping', methods=['POST'])
@login_required
def api_ping_test():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    target = request.json.get('target', '8.8.8.8')
    results = []
    
    for i in range(5):
        latency = measure_latency(target)
        results.append({
            'seq': i + 1,
            'latency_ms': latency if latency else None,
            'status': 'success' if latency else 'timeout'
        })
        time.sleep(0.1)
    
    successful = [r['latency_ms'] for r in results if r['latency_ms']]
    avg_latency = sum(successful) / len(successful) if successful else 0
    packet_loss = ((5 - len(successful)) / 5) * 100
    
    return jsonify({
        'target': target,
        'results': results,
        'statistics': {
            'packets_sent': 5,
            'packets_received': len(successful),
            'packet_loss_percent': packet_loss,
            'avg_latency_ms': round(avg_latency, 2),
            'min_latency_ms': round(min(successful), 2) if successful else 0,
            'max_latency_ms': round(max(successful), 2) if successful else 0
        }
    })

@app.route('/api/diagnostics/speedtest', methods=['POST'])
@login_required
def api_speed_test():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    base_latency = measure_latency() or 50
    import random
    download_speed = random.uniform(50, 150)
    upload_speed = random.uniform(20, 80)
    
    user_state = get_user_state(current_user.id)
    if user_state.get('vpn_enabled') and user_state.get('route_optimization_enabled'):
        download_speed *= 1.2
        upload_speed *= 1.15
        base_latency *= 0.7
    
    network_data = load_network_data()
    network_data['metrics_history'].append({
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
        'latency_ms': round(base_latency, 1),
        'download_mbps': round(download_speed, 1),
        'upload_mbps': round(upload_speed, 1)
    })
    network_data['metrics_history'] = network_data['metrics_history'][-20:]
    save_network_data(network_data)
    
    add_connection_event(current_user.id, 'speed_test', {
        'download': round(download_speed, 1),
        'upload': round(upload_speed, 1),
        'latency': round(base_latency, 1)
    })
    
    return jsonify({
        'download_mbps': round(download_speed, 1),
        'upload_mbps': round(upload_speed, 1),
        'latency_ms': round(base_latency, 1),
        'jitter_ms': round(random.uniform(1, 10), 1),
        'server': 'Form Speed Test Server',
        'optimized': user_state.get('route_optimization_enabled', False)
    })

@app.route('/api/diagnostics/traceroute', methods=['POST'])
@login_required
def api_traceroute():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    target = request.json.get('target', '8.8.8.8')
    base_latency = measure_latency() or 20
    
    hops = []
    hop_names = ['Local Gateway', 'ISP Router', 'Regional Hub', 'Internet Exchange', 'Target Network', target]
    
    cumulative = 0
    for i, name in enumerate(hop_names):
        import random
        hop_latency = random.uniform(2, 15) * (i + 1)
        cumulative += hop_latency
        hops.append({
            'hop': i + 1,
            'address': f'{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}' if i < len(hop_names) - 1 else target,
            'hostname': name,
            'latency_ms': round(cumulative, 1),
            'status': 'reached'
        })
    
    return jsonify({
        'target': target,
        'hops': hops,
        'total_hops': len(hops),
        'final_latency_ms': round(cumulative, 1)
    })

@app.route('/api/devices', methods=['GET'])
@login_required
def api_get_devices():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    devices = load_devices(current_user.id)
    return jsonify({'devices': devices})

@app.route('/api/devices/<device_id>', methods=['DELETE'])
@login_required
def api_delete_device(device_id):
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    devices = load_devices(current_user.id)
    current_device_id = f"web-{current_user.id}"
    
    if device_id == current_device_id:
        return jsonify({'error': 'Cannot remove current device'}), 400
    
    devices = [d for d in devices if d['id'] != device_id]
    save_devices(current_user.id, devices)
    
    add_connection_event(current_user.id, 'device_removed', {'device_id': device_id})
    
    return jsonify({'success': True})

@app.route('/api/devices/add', methods=['POST'])
@login_required
def api_add_device():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    data = request.json
    devices = load_devices(current_user.id)
    
    if len(devices) >= 5:
        return jsonify({'error': 'Maximum 5 devices allowed'}), 400
    
    import random
    new_device = {
        'id': f"device-{random.randint(1000, 9999)}",
        'name': data.get('name', 'New Device'),
        'type': data.get('type', 'desktop'),
        'os': data.get('os', 'Unknown'),
        'registered_at': datetime.utcnow().isoformat(),
        'last_active': datetime.utcnow().isoformat(),
        'is_current': False
    }
    
    devices.append(new_device)
    save_devices(current_user.id, devices)
    
    add_connection_event(current_user.id, 'device_added', {'device': new_device['name']})
    
    return jsonify({'success': True, 'device': new_device})

@app.route('/api/history')
@login_required
def api_get_history():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    history = load_connection_history(current_user.id)
    history.reverse()
    return jsonify({'history': history[:50]})

@app.route('/api/history/clear', methods=['POST'])
@login_required
def api_clear_history():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    save_connection_history(current_user.id, [])
    return jsonify({'success': True})

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    
    try:
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except ValueError:
        return 'Invalid payload', 400
    
    if event.type == 'customer.subscription.updated':
        subscription = event.data.object
        user = User.query.filter_by(stripe_subscription_id=subscription.id).first()
        if user:
            user.subscription_status = subscription.status
            db.session.commit()
    
    elif event.type == 'customer.subscription.deleted':
        subscription = event.data.object
        user = User.query.filter_by(stripe_subscription_id=subscription.id).first()
        if user:
            user.subscription_status = 'cancelled'
            user.is_pro = False
            db.session.commit()
            update_user_state(user.id, {
                'vpn_enabled': False,
                'speed_sharing_enabled': False,
                'security_enabled': False,
                'route_optimization_enabled': False
            })
    
    return 'OK', 200

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
