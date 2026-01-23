from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
import json
import random
import hashlib
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
METRICS_PATH = 'device_client/cache/metrics_cache.json'
USER_STATE_PATH = 'device_client/cache/user_states.json'

def load_pro_config():
    try:
        with open(PRO_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"pro_users": [], "subscription": {"price_usd": 5, "trial_days": 7}}

def load_metrics():
    try:
        with open(METRICS_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"device_metrics": {"latency_ms": 22, "download_mbps": 95, "upload_mbps": 18, "jitter_ms": 4, "packet_loss_percent": 0.2, "network_type": "LTE", "signal_strength": -82}}

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

def get_user_state(user_id):
    states = load_user_states()
    return states.get(str(user_id), {
        'vpn_enabled': False,
        'vpn_server': None,
        'speed_sharing_enabled': False,
        'security_enabled': False,
        'route_optimization_enabled': False,
        'shared_bandwidth_mbps': 0,
        'protected_since': None,
        'threats_blocked': 0
    })

def update_user_state(user_id, updates):
    states = load_user_states()
    user_state = states.get(str(user_id), {})
    user_state.update(updates)
    states[str(user_id)] = user_state
    save_user_states(states)
    return user_state

VPN_SERVERS = [
    {'id': 'us-east', 'name': 'US East', 'location': 'New York', 'ip': '10.0.1.1', 'capacity': 85, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'us-west', 'name': 'US West', 'location': 'Los Angeles', 'ip': '10.0.2.1', 'capacity': 72, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'europe', 'name': 'Europe', 'location': 'Amsterdam', 'ip': '10.0.3.1', 'capacity': 65, 'protocols': ['WireGuard', 'OpenVPN', 'IKEv2']},
    {'id': 'asia', 'name': 'Asia Pacific', 'location': 'Tokyo', 'ip': '10.0.4.1', 'capacity': 78, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'uk', 'name': 'United Kingdom', 'location': 'London', 'ip': '10.0.5.1', 'capacity': 68, 'protocols': ['WireGuard', 'OpenVPN']},
    {'id': 'germany', 'name': 'Germany', 'location': 'Frankfurt', 'ip': '10.0.6.1', 'capacity': 82, 'protocols': ['WireGuard', 'OpenVPN', 'IKEv2']}
]

THREAT_TYPES = ['Malware', 'Phishing', 'Tracking', 'DNS Leak', 'IP Leak', 'Suspicious Connection']

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
        if self.email in pro_config.get('pro_users', []) or self.username in pro_config.get('pro_users', []):
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
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
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
    
    flash('Welcome to Form Pro! Your 7-day free trial has started. All features are now unlocked!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    metrics = load_metrics()
    user_state = get_user_state(current_user.id)
    benefits = current_user.get_benefits()
    return render_template('dashboard.html', 
                          metrics=metrics.get('device_metrics', {}),
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
    metrics = load_metrics()
    user_state = get_user_state(current_user.id)
    return render_template('speed_sharing.html', metrics=metrics.get('device_metrics', {}), user_state=user_state)

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
    metrics = load_metrics()
    user_state = get_user_state(current_user.id)
    return render_template('analytics.html', 
                          metrics=metrics.get('device_metrics', {}),
                          history=metrics.get('history', []),
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
    metrics = load_metrics()
    user_state = get_user_state(current_user.id)
    
    if user_state.get('vpn_enabled') and user_state.get('route_optimization_enabled'):
        device_metrics = metrics.get('device_metrics', {})
        device_metrics['latency_ms'] = max(5, device_metrics.get('latency_ms', 22) - 8)
        device_metrics['download_mbps'] = device_metrics.get('download_mbps', 95) * 1.15
        device_metrics['jitter_ms'] = max(1, device_metrics.get('jitter_ms', 4) - 2)
        metrics['device_metrics'] = device_metrics
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
        latency = random.randint(15, 150)
        servers_with_latency.append({**server, 'latency': latency})
    
    servers_with_latency.sort(key=lambda x: x['latency'])
    
    return jsonify({
        'connected': user_state.get('vpn_enabled', False),
        'current_server': user_state.get('vpn_server'),
        'route_optimization': user_state.get('route_optimization_enabled', False),
        'security_enabled': user_state.get('security_enabled', False),
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
    
    user_state = update_user_state(current_user.id, {
        'vpn_enabled': True,
        'vpn_server': server,
        'connected_at': datetime.utcnow().isoformat(),
        'route_optimization_enabled': True,
        'security_enabled': True
    })
    
    assigned_ip = f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    
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
    
    update_user_state(current_user.id, {
        'vpn_enabled': False,
        'vpn_server': None,
        'route_optimization_enabled': False
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
    
    metrics = load_metrics()
    original_latency = metrics.get('device_metrics', {}).get('latency_ms', 22)
    optimized_latency = max(5, original_latency - random.randint(5, 15))
    
    original_speed = metrics.get('device_metrics', {}).get('download_mbps', 95)
    optimized_speed = original_speed * (1 + random.uniform(0.1, 0.25))
    
    update_user_state(current_user.id, {
        'route_optimization_enabled': True,
        'last_optimization': datetime.utcnow().isoformat()
    })
    
    return jsonify({
        'success': True,
        'message': 'Route optimized for best performance',
        'improvements': {
            'latency': {'before': original_latency, 'after': optimized_latency, 'improvement': f'-{original_latency - optimized_latency}ms'},
            'speed': {'before': round(original_speed, 1), 'after': round(optimized_speed, 1), 'improvement': f'+{round((optimized_speed - original_speed) / original_speed * 100, 1)}%'}
        },
        'route_path': ['Your Device', 'Form Edge Node', user_state.get('vpn_server', {}).get('location', 'Optimal Server'), 'Destination']
    })

@app.route('/api/speed-sharing/status')
@login_required
def speed_sharing_status():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    user_state = get_user_state(current_user.id)
    metrics = load_metrics()
    
    peers = [
        {'device_id': f'peer_{hashlib.md5(str(i).encode()).hexdigest()[:8]}', 
         'shared_bandwidth_mbps': round(random.uniform(5, 35), 1), 
         'status': random.choice(['active', 'active', 'idle']),
         'carrier': random.choice(['Verizon', 'AT&T', 'T-Mobile', 'Sprint']),
         'contribution': round(random.uniform(10, 50), 1)}
        for i in range(random.randint(2, 6))
    ]
    
    total_shared = sum(p['shared_bandwidth_mbps'] for p in peers)
    your_contribution = user_state.get('shared_bandwidth_mbps', 0)
    
    return jsonify({
        'enabled': user_state.get('speed_sharing_enabled', False),
        'your_bandwidth': {
            'download': metrics.get('device_metrics', {}).get('download_mbps', 95),
            'upload': metrics.get('device_metrics', {}).get('upload_mbps', 18)
        },
        'sharing_percentage': 30,
        'your_contribution': your_contribution,
        'peers': peers,
        'total_shared': round(total_shared, 1),
        'network_boost': round(total_shared * 0.3, 1)
    })

@app.route('/api/speed-sharing/toggle', methods=['POST'])
@login_required
def toggle_speed_sharing():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    data = request.get_json()
    enabled = data.get('enabled', False)
    
    metrics = load_metrics()
    upload_speed = metrics.get('device_metrics', {}).get('upload_mbps', 18)
    shared_amount = round(upload_speed * 0.3, 1) if enabled else 0
    
    update_user_state(current_user.id, {
        'speed_sharing_enabled': enabled,
        'shared_bandwidth_mbps': shared_amount,
        'sharing_started': datetime.utcnow().isoformat() if enabled else None
    })
    
    return jsonify({
        'success': True,
        'enabled': enabled,
        'shared_bandwidth_mbps': shared_amount,
        'message': f'Speed sharing {"enabled" if enabled else "disabled"}. {"You are now contributing " + str(shared_amount) + " Mbps to the network." if enabled else ""}'
    })

@app.route('/api/security/status')
@login_required
def security_status():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    
    user_state = get_user_state(current_user.id)
    
    threats_blocked = user_state.get('threats_blocked', 0)
    if user_state.get('security_enabled'):
        threats_blocked += random.randint(0, 3)
        update_user_state(current_user.id, {'threats_blocked': threats_blocked})
    
    recent_threats = [
        {'type': random.choice(THREAT_TYPES), 
         'blocked_at': (datetime.utcnow() - timedelta(minutes=random.randint(1, 120))).isoformat(),
         'source': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
         'severity': random.choice(['Low', 'Medium', 'High'])}
        for _ in range(min(5, threats_blocked))
    ]
    
    return jsonify({
        'enabled': user_state.get('security_enabled', False),
        'protected_since': user_state.get('protected_since'),
        'threats_blocked': threats_blocked,
        'recent_threats': recent_threats,
        'protection_features': {
            'malware_protection': True,
            'phishing_protection': True,
            'dns_leak_protection': True,
            'ip_leak_protection': True,
            'tracker_blocking': True,
            'ad_blocking': True
        },
        'encryption': 'AES-256-GCM',
        'dns_servers': ['Form Secure DNS 1', 'Form Secure DNS 2']
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
    return jsonify({
        'peers': [
            {'device_id': 'device_001', 'shared_bandwidth_mbps': 25.5, 'status': 'active'},
            {'device_id': 'device_002', 'shared_bandwidth_mbps': 18.2, 'status': 'active'},
            {'device_id': 'device_003', 'shared_bandwidth_mbps': 32.1, 'status': 'idle'}
        ],
        'total_shared': 75.8
    })

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
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
