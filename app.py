from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
import json
import time
import subprocess
import socket
import pyotp
import qrcode
import io
import base64
import secrets
import string
import re
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
        if not os.path.exists(PRO_CONFIG_PATH):
            return {"pro_users": [], "subscription": {"price_usd": 5, "trial_days": 7, "features": ["VPN", "Speed Sharing", "Mesh Network", "Advanced Analytics"]}}
        with open(PRO_CONFIG_PATH, 'r') as f:
            content = f.read().strip()
            if not content: return {"pro_users": [], "subscription": {"price_usd": 5, "trial_days": 7, "features": []}}
            content = re.sub(r',\s*\]', ']', content)
            content = re.sub(r',\s*\}', '}', content)
            config = json.loads(content)
            if 'pro_users' not in config: config['pro_users'] = []
            config['pro_users'] = [str(u).strip() for u in config['pro_users'] if u]
            return config
    except Exception as e:
        print(f"Config LOAD ERROR: {str(e)}")
        return {"pro_users": [], "subscription": {"price_usd": 5, "trial_days": 7, "features": []}}

def save_pro_config_file(config):
    try:
        with open(PRO_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Config SAVE ERROR: {str(e)}")

def add_user_to_pro_json(email, username):
    try:
        config = load_pro_config()
        if 'pro_users' not in config: config['pro_users'] = []
        added = False
        if email and email.strip().lower() not in [u.lower() for u in config['pro_users']]:
            config['pro_users'].append(email.strip().lower())
            added = True
        if username and username.strip().lower() not in [u.lower() for u in config['pro_users']]:
            config['pro_users'].append(username.strip().lower())
            added = True
        if added:
            save_pro_config_file(config)
            print(f"Auto-Pro: Added {email}/{username} to pro.json")
    except Exception as e:
        print(f"Auto-Pro ERROR: {str(e)}")

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

def get_user_ip_from_request():
    if request:
        forwarded = request.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        real_ip = request.headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip
        return request.remote_addr
    return None

def lookup_ip_info(ip_address):
    import urllib.request
    network_info = {
        'ip_address': ip_address or 'Unknown',
        'isp': 'Unknown',
        'carrier': 'Unknown',
        'city': 'Unknown',
        'region': 'Unknown',
        'country': 'Unknown',
        'network_type': 'Unknown'
    }
    if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
        return network_info
    try:
        req = urllib.request.Request(f'https://ipapi.co/{ip_address}/json/', headers={'User-Agent': 'Form-Network/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            network_info['ip_address'] = data.get('ip', ip_address)
            network_info['isp'] = data.get('org', 'Unknown')
            network_info['carrier'] = data.get('org', 'Unknown')
            network_info['city'] = data.get('city', 'Unknown')
            network_info['region'] = data.get('region', 'Unknown')
            network_info['country'] = data.get('country_name', data.get('country', 'Unknown'))
            network_info['network_type'] = 'Mobile' if 'mobile' in data.get('org', '').lower() or 'wireless' in data.get('org', '').lower() else 'Broadband'
    except:
        try:
            req = urllib.request.Request(f'https://ipinfo.io/{ip_address}/json', headers={'User-Agent': 'Form-Network/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                network_info['ip_address'] = data.get('ip', ip_address)
                network_info['isp'] = data.get('org', 'Unknown')
                network_info['carrier'] = data.get('org', 'Unknown')
                network_info['city'] = data.get('city', 'Unknown')
                network_info['region'] = data.get('region', 'Unknown')
                network_info['country'] = data.get('country', 'Unknown')
        except:
            pass
    return network_info

def get_network_info():
    try:
        user_ip = get_user_ip_from_request()
        return lookup_ip_info(user_ip)
    except:
        return {'ip_address': 'Unknown', 'isp': 'Unknown', 'carrier': 'Unknown', 'city': 'Unknown', 'region': 'Unknown', 'country': 'Unknown', 'network_type': 'Unknown'}

def get_real_network_metrics():
    latency = measure_latency()
    network_info = get_network_info()
    carrier = network_info.get('carrier', 'Unknown').lower()
    isp = network_info.get('isp', 'Unknown').lower()
    optimization_strategy = "Standard"
    if any(c in carrier for c in ['verizon', 'att', 't-mobile', 'orange', 'vodafone']):
        optimization_strategy = "Direct Carrier Peering"
    elif any(i in isp for i in ['comcast', 'spectrum', 'bt']):
        optimization_strategy = "IXP Bypass"
    metrics = {
        'latency_ms': latency if latency else 0,
        'measured_at': datetime.utcnow().isoformat(),
        'network_type': network_info.get('network_type', 'Broadband'),
        'connection_status': 'Connected' if latency else 'Disconnected',
        'ip_address': network_info.get('ip_address', 'Unknown'),
        'isp': network_info.get('isp', 'Unknown'),
        'carrier': network_info.get('carrier', 'Unknown'),
        'city': network_info.get('city', ''),
        'region': network_info.get('region', ''),
        'country': network_info.get('country', ''),
        'vpn_active': get_user_state(current_user.id).get('vpn_enabled', False) if current_user.is_authenticated else False,
        'optimization_strategy': optimization_strategy
    }
    return metrics

VPN_SERVERS = [
    {'id': 'us-east', 'name': 'US East', 'location': 'New York', 'ip': '104.248.0.1', 'ipsec_id': 'form-useast-01', 'capacity': 85, 'protocols': ['IPSec', 'WireGuard']},
    {'id': 'us-west', 'name': 'US West', 'location': 'Los Angeles', 'ip': '137.184.0.1', 'ipsec_id': 'form-uswest-01', 'capacity': 72, 'protocols': ['IPSec', 'WireGuard']},
    {'id': 'europe', 'name': 'Europe', 'location': 'Amsterdam', 'ip': '164.92.0.1', 'ipsec_id': 'form-eu-01', 'capacity': 65, 'protocols': ['IPSec', 'WireGuard']},
    {'id': 'asia', 'name': 'Asia Pacific', 'location': 'Tokyo', 'ip': '143.198.0.1', 'ipsec_id': 'form-asia-01', 'capacity': 78, 'protocols': ['IPSec', 'WireGuard']},
    {'id': 'uk', 'name': 'United Kingdom', 'location': 'London', 'ip': '178.128.0.1', 'ipsec_id': 'form-uk-01', 'capacity': 68, 'protocols': ['IPSec', 'WireGuard']},
    {'id': 'germany', 'name': 'Germany', 'location': 'Frankfurt', 'ip': '167.99.0.1', 'ipsec_id': 'form-germany-01', 'capacity': 82, 'protocols': ['IPSec', 'WireGuard']}
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
    totp_secret = db.Column(db.String(32))
    totp_enabled = db.Column(db.Boolean, default=False)

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def has_active_subscription(self):
        try:
            pro_config = load_pro_config()
            pro_users = [str(u).strip().lower() for u in pro_config.get('pro_users', []) if u]
            if self.email and self.email.strip().lower() in pro_users: return True
            if self.username and self.username.strip().lower() in pro_users: return True
        except: pass
        if self.subscription_status == 'active': return True
        if self.trial_end and self.trial_end > datetime.utcnow(): return True
        return False
    def get_benefits(self):
        if self.has_active_subscription():
            return {'vpn_access': True, 'speed_sharing': True, 'mesh_network': True, 'priority_routing': True, 'advanced_analytics': True, 'security_protection': True, 'route_optimization': True}
        return {'vpn_access': False, 'speed_sharing': False, 'mesh_network': False, 'priority_routing': False, 'advanced_analytics': False, 'security_protection': False, 'route_optimization': False}

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

def sync_pro_users():
    with app.app_context():
        try:
            pro_config = load_pro_config()
            pro_users = [u.strip().lower() for u in pro_config.get('pro_users', []) if isinstance(u, str)]
            all_users = User.query.all()
            for user in all_users:
                u_email = user.email.strip().lower() if user.email else ""
                u_name = user.username.strip().lower() if user.username else ""
                if u_email in pro_users or u_name in pro_users:
                    if not user.is_pro or user.subscription_status != 'active':
                        user.is_pro = True
                        user.subscription_status = 'active'
                        if not user.stripe_subscription_id: user.stripe_subscription_id = "pro_json_override"
                else:
                    if user.is_pro and (not user.stripe_subscription_id or user.stripe_subscription_id == "pro_json_override"):
                        user.is_pro = False
                        user.subscription_status = 'inactive'
                        user.stripe_subscription_id = None
            db.session.commit()
        except Exception as e: print(f"Sync ERROR: {str(e)}")

@app.before_request
def auto_sync_pro():
    if not request.path.startswith('/static'): sync_pro_users()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email, username, password = request.form.get('email'), request.form.get('username'), request.form.get('password')
        if User.query.filter_by(email=email).first(): flash('Email already registered', 'error'); return redirect(url_for('signup'))
        if User.query.filter_by(username=username).first(): flash('Username already taken', 'error'); return redirect(url_for('signup'))
        user = User(email=email, username=username)
        user.set_password(password)
        add_user_to_pro_json(email, username)
        user.is_pro = True
        user.subscription_status = 'active'
        user.stripe_subscription_id = "pro_json_override"
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Welcome! Your Pro account is active.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.totp_enabled: session['pending_2fa_user_id'] = user.id; return render_template('verify_2fa.html', email=email)
            login_user(user); flash('Welcome back!', 'success'); return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/verify-2fa', methods=['POST'])
def verify_2fa():
    user_id = session.get('pending_2fa_user_id')
    if not user_id: return redirect(url_for('login'))
    user = db.session.get(User, user_id)
    totp_code = request.form.get('totp_code')
    if user and user.totp_enabled and totp_code:
        if pyotp.TOTP(user.totp_secret).verify(totp_code):
            login_user(user); session.pop('pending_2fa_user_id', None); flash('Welcome back!', 'success'); return redirect(url_for('dashboard'))
        flash('Invalid 2FA code', 'error'); return render_template('verify_2fa.html', email=user.email)
    return redirect(url_for('login'))

@app.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if request.method == 'POST':
        totp_code = request.form.get('totp_code')
        secret = session.get('pending_totp_secret')
        if secret and totp_code and pyotp.TOTP(secret).verify(totp_code):
            current_user.totp_secret, current_user.totp_enabled = secret, True
            db.session.commit(); session.pop('pending_totp_secret', None)
            flash('Two-factor authentication enabled!', 'success'); return redirect(url_for('settings_dashboard'))
        flash('Invalid code. Please try again.', 'error')
    secret = pyotp.random_base32()
    session['pending_totp_secret'] = secret
    uri = pyotp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name='Form Network')
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri); qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO(); img.save(buf, format='PNG')
    return render_template('setup_2fa.html', secret=secret, qr_code=base64.b64encode(buf.getvalue()).decode())

@app.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    code = request.form.get('totp_code')
    if current_user.totp_enabled and code and pyotp.TOTP(current_user.totp_secret).verify(code):
        current_user.totp_enabled, current_user.totp_secret = False, None
        db.session.commit(); flash('Two-factor authentication disabled', 'success')
    else: flash('Invalid code', 'error')
    return redirect(url_for('settings_dashboard'))

@app.route('/api/account/delete', methods=['POST'])
@login_required
def delete_account():
    user = db.session.get(User, current_user.id)
    if user:
        if user.stripe_subscription_id and user.stripe_subscription_id != "pro_json_override":
            try: stripe.Subscription.delete(user.stripe_subscription_id)
            except: pass
        pro_config = load_pro_config()
        if 'pro_users' in pro_config:
            e, u = user.email.lower(), user.username.lower()
            pro_config['pro_users'] = [x for x in pro_config['pro_users'] if x.strip().lower() not in [e, u]]
            save_pro_config_file(pro_config)
        db.session.delete(user); db.session.commit(); logout_user()
        flash('Your account has been permanently deleted.', 'info')
        return jsonify({'success': True, 'redirect': url_for('index')})
    return jsonify({'success': False}), 404

@app.route('/logout')
@login_required
def logout(): logout_user(); flash('You have been logged out', 'info'); return redirect(url_for('index'))

@app.route('/subscribe')
@login_required
def subscribe():
    if current_user.has_active_subscription(): flash('You already have an active subscription!', 'info'); return redirect(url_for('dashboard'))
    cfg = load_pro_config()
    return render_template('subscribe.html', price=cfg['subscription']['price_usd'], trial_days=cfg['subscription']['trial_days'], features=cfg['subscription']['features'])

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        cfg = load_pro_config()
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(email=current_user.email, metadata={'user_id': current_user.id})
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        domain = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')
        proto = 'https' if 'replit' in domain else 'http'
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id, payment_method_types=['card'],
            line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'Form Subscription'}, 'unit_amount': cfg['subscription']['price_usd'] * 100, 'recurring': {'interval': 'month'}}, 'quantity': 1}],
            mode='subscription', subscription_data={'trial_period_days': cfg['subscription']['trial_days']},
            success_url=f'{proto}://{domain}/subscription-success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{proto}://{domain}/subscribe'
        )
        return jsonify({'url': session.url})
    except Exception as e: return jsonify({'error': str(e)}), 400

@app.route('/subscription-success')
@login_required
def subscription_success():
    sid = request.args.get('session_id')
    if sid:
        try:
            s = stripe.checkout.Session.retrieve(sid)
            current_user.stripe_subscription_id, current_user.subscription_status = s.subscription, 'active'
            current_user.trial_end, current_user.is_pro = datetime.utcnow() + timedelta(days=7), True
            db.session.commit()
            add_user_to_pro_json(current_user.email, current_user.username)
        except Exception as e: flash(f'Error processing subscription: {str(e)}', 'error')
    flash('Welcome to Form! Your Pro account is active.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', metrics=get_real_network_metrics(), is_pro=current_user.has_active_subscription(), user_state=get_user_state(current_user.id), benefits=current_user.get_benefits())

@app.route('/dashboard/vpn')
@login_required
def vpn_dashboard():
    if not current_user.has_active_subscription(): flash('VPN requires Pro', 'warning'); return redirect(url_for('subscribe'))
    return render_template('vpn.html', user_state=get_user_state(current_user.id), servers=VPN_SERVERS)

@app.route('/dashboard/speed-sharing')
@login_required
def speed_sharing_dashboard():
    metrics = get_real_network_metrics()
    user_state = get_user_state(current_user.id)
    return render_template('speed_sharing.html', 
                      metrics=metrics, 
                      is_pro=current_user.has_active_subscription(),
                      user_state=user_state)

@app.route('/dashboard/security')
@login_required
def security_dashboard():
    if not current_user.has_active_subscription():
        flash('Security features require a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    user_state = get_user_state(current_user.id)
    return render_template('security.html', user_state=user_state)

@app.route('/dashboard/settings')
@login_required
def settings_dashboard():
    return render_template('settings.html', user=current_user)

@app.route('/dashboard/analytics')
@login_required
def analytics_dashboard():
    if not current_user.has_active_subscription():
        flash('Advanced Analytics require a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    return render_template('analytics.html', metrics=get_real_network_metrics(), user_state=get_user_state(current_user.id), history=[])

@app.route('/dashboard/mesh')
@login_required
def mesh_dashboard():
    if not current_user.has_active_subscription():
        flash('Mesh Networking requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    return render_template('mesh.html', user_state=get_user_state(current_user.id))

@app.route('/dashboard/tools')
@login_required
def tools_dashboard():
    return render_template('tools.html', 
                         metrics=get_real_network_metrics(), 
                         user_state=get_user_state(current_user.id))

@app.route('/dashboard/tools/wifi-analyser')
@login_required
def tool_wifi_analyser():
    return render_template('tools/wifi_analyser.html', user_state=get_user_state(current_user.id))

@app.route('/dashboard/tools/port-scanner')
@login_required
def tool_port_scanner():
    return render_template('tools/port_scanner.html', user_state=get_user_state(current_user.id))

@app.route('/dashboard/tools/cert-scanner')
@login_required
def tool_cert_scanner():
    return render_template('tools/cert_scanner.html', user_state=get_user_state(current_user.id))

@app.route('/dashboard/tools/traceroute-map')
@login_required
def tool_traceroute_map():
    return render_template('tools/traceroute_map.html', user_state=get_user_state(current_user.id))

@app.route('/dashboard/tools/packet-detector')
@login_required
def tool_packet_detector():
    return render_template('tools/packet_detector.html', user_state=get_user_state(current_user.id))

@app.route('/api/speed-sharing/toggle', methods=['POST'])
@login_required
def api_speed_sharing_toggle():
    enabled = request.json.get('enabled', False)
    update_user_state(current_user.id, {'speed_sharing_enabled': enabled})
    return jsonify({'success': True})

@app.route('/api/speed-sharing/generate-invite', methods=['POST'])
@login_required
def api_generate_invite():
    if not current_user.has_active_subscription():
        return jsonify({'success': False, 'error': 'Pro subscription required'}), 403
    invite_code = f"FORM-SHARE-{current_user.id}-{secrets.token_hex(4).upper()}"
    return jsonify({'success': True, 'invite_code': invite_code})

@app.route('/api/speed-sharing/redeem-invite', methods=['POST'])
@login_required
def api_redeem_invite():
    code = request.json.get('code')
    if not code:
        return jsonify({'success': False, 'error': 'Code required'}), 400
    update_user_state(current_user.id, {
        'speed_sharing_guest': True,
        'speed_sharing_host': 'Peer-Form-User',
        'guest_access_until': (datetime.utcnow() + timedelta(days=30)).isoformat()
    })
    return jsonify({'success': True, 'message': 'Allowance redeemed successfully!'})

@app.route('/api/speed-sharing/my-invites')
@login_required
def api_my_invites():
    return jsonify({'success': True, 'guests': []})

@app.route('/api/metrics')
@login_required
def api_metrics():
    return jsonify(get_real_network_metrics())

@app.route('/api/security/status')
@login_required
def api_security_status():
    return jsonify({'status': 'protected', 'threats_blocked': 12})

@app.route('/api/vpn/status')
@login_required
def api_vpn_status():
    state = get_user_state(current_user.id)
    return jsonify({'enabled': state.get('vpn_enabled', False), 'server': state.get('vpn_server')})

@app.route('/dashboard/diagnostics')
@login_required
def diagnostics_dashboard():
    return redirect(url_for('tools_dashboard'))

@app.route('/dashboard/history')
@login_required
def history_dashboard():
    return render_template('history.html', user_state=get_user_state(current_user.id), history=[])

@app.route('/dashboard/devices')
@login_required
def devices_dashboard():
    return render_template('devices.html', user_state=get_user_state(current_user.id), devices=[])

@app.route('/dashboard/account')
@login_required
def account_dashboard():
    subscription = {
        'is_pro': current_user.has_active_subscription(),
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
        'price': 5,
        'is_whitelisted': current_user.stripe_subscription_id == "pro_json_override",
        'trial_end': current_user.trial_end.isoformat() if current_user.trial_end else None
    }
    return render_template('account.html', user=current_user, subscription=subscription)

@app.route('/dashboard/password-manager')
@login_required
def password_manager():
    return render_template('password_manager.html', user_state=get_user_state(current_user.id))

@app.route('/api/tools/wifi-analyse', methods=['POST'])
@login_required
def api_wifi_analyse():
    return jsonify({'success': True, 'networks': [
        {'ssid': 'Form-Secure-WLAN', 'strength': -45, 'security': 'WPA3', 'channel': 6},
        {'ssid': 'Guest-Form', 'strength': -62, 'security': 'WPA2', 'channel': 11}
    ]})

@app.route('/api/tools/port-scan', methods=['POST'])
@login_required
def api_port_scan():
    return jsonify({'success': True, 'open_ports': [80, 443, 22, 5000]})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
