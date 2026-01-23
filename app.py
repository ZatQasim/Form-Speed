from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
import json
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
        return {"device_metrics": {"latency_ms": 0, "download_mbps": 0, "upload_mbps": 0}}

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
        except Exception as e:
            flash(f'Error processing subscription: {str(e)}', 'error')
    
    flash('Welcome to Form Pro! Your 7-day free trial has started.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    metrics = load_metrics()
    return render_template('dashboard.html', 
                          metrics=metrics.get('device_metrics', {}),
                          is_pro=current_user.has_active_subscription())

@app.route('/dashboard/vpn')
@login_required
def vpn_dashboard():
    if not current_user.has_active_subscription():
        flash('VPN requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    return render_template('vpn.html')

@app.route('/dashboard/speed-sharing')
@login_required
def speed_sharing_dashboard():
    if not current_user.has_active_subscription():
        flash('Speed Sharing requires a Pro subscription', 'warning')
        return redirect(url_for('subscribe'))
    metrics = load_metrics()
    return render_template('speed_sharing.html', metrics=metrics.get('device_metrics', {}))

@app.route('/dashboard/analytics')
@login_required
def analytics_dashboard():
    metrics = load_metrics()
    return render_template('analytics.html', 
                          metrics=metrics.get('device_metrics', {}),
                          history=metrics.get('history', []))

@app.route('/dashboard/settings')
@login_required
def settings_dashboard():
    return render_template('settings.html')

@app.route('/api/metrics')
@login_required
def api_metrics():
    metrics = load_metrics()
    return jsonify(metrics)

@app.route('/api/vpn/status')
@login_required
def vpn_status():
    if not current_user.has_active_subscription():
        return jsonify({'error': 'Pro subscription required'}), 403
    return jsonify({
        'connected': False,
        'servers': [
            {'name': 'US East', 'location': 'New York', 'latency': 22},
            {'name': 'US West', 'location': 'Los Angeles', 'latency': 45},
            {'name': 'Europe', 'location': 'Amsterdam', 'latency': 85},
            {'name': 'Asia', 'location': 'Tokyo', 'latency': 120}
        ]
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
    
    return 'OK', 200

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
