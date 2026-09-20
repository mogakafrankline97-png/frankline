from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, send_from_directory
from datetime import datetime
import json
import os
import traceback
import sys

print("=" * 60)
print("🚀 ACACIAMART Starting...")
print("=" * 60)

# ============================================================
# TRY EACH IMPORT SEPARATELY TO FIND THE ERROR
# ============================================================

try:
    print("1. Loading config...")
    from config import Config
    print("   ✅ Config loaded")
except Exception as e:
    print(f"   ❌ Config error: {e}")
    traceback.print_exc()
    raise

try:
    print("2. Loading routes.shop...")
    from routes.shop import shop_bp
    print("   ✅ Shop routes loaded")
except Exception as e:
    print(f"   ❌ Shop routes error: {e}")
    traceback.print_exc()
    raise

try:
    print("3. Loading routes.api...")
    from routes.api import api_bp
    print("   ✅ API routes loaded")
except Exception as e:
    print(f"   ❌ API routes error: {e}")
    traceback.print_exc()
    raise

try:
    print("4. Loading routes.admin...")
    from routes.admin import admin_bp
    print("   ✅ Admin routes loaded")
except Exception as e:
    print(f"   ❌ Admin routes error: {e}")
    traceback.print_exc()
    raise

try:
    print("5. Loading utils.data...")
    from utils.data import load_orders, load_products, load_bundles, sync_products_from_supabase, sync_pending_data_if_possible
    print("   ✅ Utils.data loaded")
except Exception as e:
    print(f"   ❌ Utils.data error: {e}")
    traceback.print_exc()
    raise

print("=" * 60)
print("✅ ALL IMPORTS SUCCESSFUL!")
print("=" * 60)

# ============================================================
# CREATE APP
# ============================================================
app = Flask(__name__)
application = app
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.permanent_session_lifetime = Config.PERMANENT_SESSION_LIFETIME
app.template_folder = 'templates'
app.static_folder = Config.STATIC_FOLDER

# ---------- REGISTER M-PESA TEST BLUEPRINT (debug only) ----------
try:
    from mpesa_test import mpesa_test_bp
    app.register_blueprint(mpesa_test_bp)
    print("✅ M-Pesa test blueprint registered at /mpesa/test-stk")
except Exception as e:
    print(f"⚠️ M-Pesa test blueprint not loaded: {e}")
# ---------- END DEBUG ----------

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


@app.template_filter('format_number')
def format_number_filter(value):
    try:
        if value is None:
            return '0'
        return f"{int(float(value)):,}"
    except (ValueError, TypeError):
        return '0'


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/admin/') or request.path.startswith('/api/'):
        return jsonify({'error': 'Not found', 'message': 'The requested endpoint does not exist'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    print(f'Server error: {error}')
    traceback.print_exc()
    if request.path.startswith('/admin/') or request.path.startswith('/api/'):
        return jsonify({'error': 'Server error', 'message': str(error)}), 500
    return render_template('500.html'), 500


app.register_blueprint(shop_bp)
app.register_blueprint(api_bp)
app.register_blueprint(admin_bp)


# ============================================================
# PWA ROUTES
# ============================================================

@app.route('/manifest.json')
def manifest_root():
    """Serve manifest from root URL for PWA"""
    try:
        return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')
    except Exception as e:
        print(f"❌ Error serving manifest: {e}")
        return "Manifest not found", 404


@app.route('/sw.js')
def service_worker_root():
    """Serve service worker from root URL for PWA"""
    try:
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    except Exception as e:
        print(f"❌ Error serving sw.js: {e}")
        return "Service Worker not found", 404


@app.route('/offline.html')
def offline_page_root():
    """Serve offline page"""
    try:
        return render_template('offline.html')
    except Exception as e:
        print(f"❌ Error serving offline.html: {e}")
        return "Offline page not found", 404


@app.route('/favicon.ico')
def favicon_root():
    """Serve favicon"""
    try:
        return send_from_directory('static/icons', 'favicon.ico', mimetype='image/x-icon')
    except Exception as e:
        print(f"⚠️ Favicon not found: {e}")
        return "", 204


@app.route('/static/<path:filename>')
def static_files_root(filename):
    """Serve static files"""
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        print(f"❌ Error serving static file: {e}")
        return "File not found", 404


# ============================================================
# POS ROUTE - MAIN POS PAGE (FIXED)
# ============================================================

@app.route('/pos')
def pos_page():
    """Main POS page - Entry point for PWA"""
    try:
        # Check if user is logged in
        if 'user' not in session:
            return redirect(url_for('user_login'))
        
        # Load products
        try:
            products = load_products()
        except Exception as e:
            print(f"⚠️ Error loading products: {e}")
            products = []
        
        # Load customers with fallback
        customers = []
        try:
            from utils.data import load_customers
            customers = load_customers()
        except ImportError:
            print("⚠️ load_customers not found, using fallback")
            customers = [
                {'name': 'Walk-in Customer', 'email': 'walkin@example.com', 'phone': 'N/A'},
                {'name': 'John Doe', 'email': 'john@example.com', 'phone': '+254 700 000 000'},
                {'name': 'Jane Smith', 'email': 'jane@example.com', 'phone': '+254 711 111 111'}
            ]
        except Exception as e:
            print(f"⚠️ Error loading customers: {e}")
            customers = [
                {'name': 'Walk-in Customer', 'email': 'walkin@example.com', 'phone': 'N/A'}
            ]

        credit_customers = []
        try:
            from utils.credit import get_all_credit_customers
            credit_customers = get_all_credit_customers() or []
        except Exception as e:
            print(f"⚠️ Error loading credit customers for POS seed: {e}")
            credit_customers = []

        if not credit_customers:
            try:
                pos_orders_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pos_orders.json')
                if os.path.exists(pos_orders_path):
                    with open(pos_orders_path, 'r', encoding='utf-8') as f:
                        orders = json.load(f)

                    seen = {}
                    for order in orders or []:
                        customer_id = order.get('customer_id') or order.get('customer', {}).get('id')
                        customer_name = order.get('customer_name') or order.get('customer', {}).get('name') or 'Credit Customer'
                        if customer_id and customer_name and customer_id not in seen:
                            seen[customer_id] = {
                                'customer_id': customer_id,
                                'full_name': customer_name,
                                'phone': order.get('customer_phone') or order.get('customer', {}).get('phone') or '',
                                'email': order.get('customer_email') or order.get('customer', {}).get('email') or '',
                                'current_balance': order.get('balance_after', 0) or 0,
                                'credit_limit': order.get('credit_limit', 0) or 0,
                                'account_status': 'active'
                            }
                    credit_customers = list(seen.values())
            except Exception as e:
                print(f"⚠️ Error loading local order-based credit customer seed: {e}")
                credit_customers = []
        
        if not products:
            products = []
        if not customers:
            customers = [
                {'name': 'Walk-in Customer', 'email': 'walkin@example.com', 'phone': 'N/A'}
            ]
        
        return render_template('pos.html', 
                             products=products, 
                             customers=customers,
                             credit_customers=credit_customers,
                             session=session)
    except Exception as e:
        print(f'❌ Error in /pos: {e}')
        traceback.print_exc()
        # Return error page
        return render_template('pos.html', 
                             products=[], 
                             customers=[],
                             credit_customers=[],
                             session=session)


# ============================================================
# END PWA ROUTES
# ============================================================


@app.before_request
def maybe_sync_pending_orders():
    if request.path.startswith('/static/') or request.path.startswith('/favicon.ico'):
        return None
    try:
        sync_pending_data_if_possible()
    except Exception as e:
        print(f"⚠️ Sync error (ignored): {e}")
    return None


# ============================================================
# HOME & LOGIN ROUTES
# ============================================================

@app.route('/')
def home():
    """Redirect to login or dashboard"""
    if 'user' in session:
        if session['user'].get('role') == 'admin':
            return redirect('/admin')
        return redirect('/pos')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    """Unified login with database authentication"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Please enter both email and password', 'danger')
            return render_template('admin_login.html')
        
        # ============================================================
        # DATABASE AUTHENTICATION - PRIMARY METHOD
        # ============================================================
        try:
            from models.user import User
            user, error = User.authenticate(email, password)
            
            if user:
                session['user'] = {
                    'id': user.id,
                    'email': user.email,
                    'name': user.full_name,
                    'role': user.role
                }
                
                # Log the login
                try:
                    import requests
                    requests.post(
                        f"{Config.SUPABASE_URL}/rest/v1/user_logs",
                        headers=Config.SUPABASE_HEADERS,
                        json={
                            'user_id': user.id,
                            'action': 'login',
                            'details': {'method': 'web'},
                            'ip_address': request.remote_addr,
                            'created_at': datetime.utcnow().isoformat()
                        },
                        timeout=5
                    )
                except:
                    pass
                
                if user.role == 'admin':
                    flash('Welcome back, ' + user.full_name + '!', 'success')
                    return redirect('/admin')
                else:
                    flash('Welcome, ' + user.full_name + '!', 'success')
                    return redirect('/pos')
                    
        except Exception as e:
            print(f"DB auth error: {e}")
            # Fall through to legacy auth
        
        # ============================================================
        # LEGACY AUTHENTICATION - FALLBACK
        # ============================================================
        users = {
            'admin@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'Admin User',
                'role': 'admin',
                'redirect': '/admin'
            },
            'user@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'John Doe',
                'role': 'user',
                'redirect': '/pos'
            },
            'pos@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'POS Operator',
                'role': 'pos',
                'redirect': '/pos'
            },
            'manager@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'Store Manager',
                'role': 'manager',
                'redirect': '/pos'
            }
        }
        
        if email in users and users[email]['password'] == password:
            session['user'] = {
                'email': email,
                'name': users[email]['name'],
                'role': users[email]['role'],
                'id': 'legacy_' + email
            }
            flash('Welcome, ' + users[email]['name'] + '!', 'success')
            return redirect(users[email]['redirect'])
        else:
            flash('Invalid email or password', 'danger')
            return render_template('admin_login.html')
    
    return render_template('admin_login.html')


@app.route('/logout')
def user_logout():
    """Logout user"""
    user_id = session.get('user', {}).get('id')
    
    # Log the logout
    if user_id and not str(user_id).startswith('legacy_'):
        try:
            import requests
            requests.post(
                f"{Config.SUPABASE_URL}/rest/v1/user_logs",
                headers=Config.SUPABASE_HEADERS,
                json={
                    'user_id': user_id,
                    'action': 'logout',
                    'ip_address': request.remote_addr,
                    'created_at': datetime.utcnow().isoformat()
                },
                timeout=5
            )
        except:
            pass
    
    session.pop('user', None)
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('user_login'))


# ============================================================
# HEALTH & DEBUG ROUTES
# ============================================================

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Server is running', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/debug')
def debug():
    try:
        orders = load_orders()
        products = load_products()
        bundles = load_bundles()
        return jsonify({
            'orders_count': len(orders),
            'products_count': len(products),
            'bundles_count': len(bundles),
            'sample_order': orders[0] if orders else None,
            'sample_product': products[0] if products else None,
            'is_vercel': Config.IS_VERCEL,
        })
    except Exception as exc:
        return jsonify({'error': str(exc)})


@app.route('/load-sample-data', methods=['GET', 'POST'])
def load_sample_data():
    try:
        sample_products = [
            {
                'id': 'iphone_15',
                'name': 'iPhone 15 Pro Max',
                'price': 245000.0,
                'cost_price': 180000.0,
                'category': 'Phones',
                'description': 'Latest Apple flagship with A17 Pro chip',
                'image': 'https://images.unsplash.com/photo-1592286927505-1def25e4c479?w=500',
                'stock': 15,
                'rating': 4.9,
                'reviews': 245,
                'badge': 'Best Seller',
            },
            {
                'id': 'macbook_pro',
                'name': 'MacBook Pro 16"',
                'price': 450000.0,
                'cost_price': 350000.0,
                'category': 'Laptops',
                'description': 'Professional laptop with M3 Max chip',
                'image': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500',
                'stock': 8,
                'rating': 4.8,
                'reviews': 156,
                'badge': 'New',
            },
            {
                'id': 'airpods_pro',
                'name': 'AirPods Pro 2',
                'price': 35000.0,
                'cost_price': 22000.0,
                'category': 'Accessories',
                'description': 'Premium wireless earbuds with ANC',
                'image': 'https://images.unsplash.com/photo-1606841838e0-bf1baf2dc3e9?w=500',
                'stock': 25,
                'rating': 4.7,
                'reviews': 389,
                'badge': 'Trending',
            },
            {
                'id': 'samsung_s24',
                'name': 'Samsung Galaxy S24 Ultra',
                'price': 225000.0,
                'cost_price': 115000.0,
                'category': 'Phones',
                'description': 'Flagship Android phone with advanced camera',
                'image': 'https://images.unsplash.com/photo-1511707267537-b85faf00021e?w=500',
                'stock': 23,
                'rating': 4.6,
                'reviews': 234,
            },
            {
                'id': 'ipad_pro',
                'name': 'iPad Pro 12.9"',
                'price': 185000.0,
                'cost_price': 140000.0,
                'category': 'Tablets',
                'description': 'Powerful tablet with M2 chip',
                'image': 'https://images.unsplash.com/photo-1561070791-2526d30994b5?w=500',
                'stock': 12,
                'rating': 4.7,
                'reviews': 198,
                'badge': 'New',
            },
            {
                'id': 'hp_spectre',
                'name': 'HP Spectre x360',
                'price': 125000.0,
                'cost_price': 90000.0,
                'category': 'Laptops',
                'description': 'Convertible premium laptop',
                'image': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=500',
                'stock': 18,
                'rating': 4.5,
                'reviews': 112,
            },
            {
                'id': 'watch_9',
                'name': 'Apple Watch Series 9',
                'price': 62000.0,
                'cost_price': 45000.0,
                'category': 'Wearables',
                'description': 'Smartwatch with fitness tracking',
                'image': 'https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500',
                'stock': 26,
                'rating': 4.8,
                'reviews': 173,
            },
            {
                'id': 'usb_c_cable',
                'name': 'USB-C Fast Charging Cable',
                'price': 1200.0,
                'cost_price': 700.0,
                'category': 'Accessories',
                'description': 'Fast charging cable',
                'image': 'https://images.unsplash.com/photo-1583394838336-acd977736f90?w=500',
                'stock': 98,
                'rating': 4.4,
                'reviews': 67,
            },
            {
                'id': 'dell_xps',
                'name': 'Dell XPS 15',
                'price': 165000.0,
                'cost_price': 120000.0,
                'category': 'Laptops',
                'description': 'Thin and powerful productivity laptop',
                'image': 'https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=500',
                'stock': 4,
                'rating': 4.6,
                'reviews': 99,
            },
            {
                'id': 'power_bank',
                'name': 'Anker 20000mAh Power Bank',
                'price': 8500.0,
                'cost_price': 5000.0,
                'category': 'Accessories',
                'description': 'Portable charger for travel',
                'image': 'https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=500',
                'stock': 57,
                'rating': 4.7,
                'reviews': 88,
            },
            {
                'id': 'buds_2',
                'name': 'Samsung Galaxy Buds 2',
                'price': 18000.0,
                'cost_price': 12000.0,
                'category': 'Audio',
                'description': 'Noise-cancelling earbuds',
                'image': 'https://images.unsplash.com/photo-1606225457115-9b0de873c5e1?w=500',
                'stock': 45,
                'rating': 4.5,
                'reviews': 74,
            },
        ]

        import requests
        added = 0
        errors = []
        for product in sample_products:
            try:
                response = requests.post(
                    f"{Config.SUPABASE_URL}/rest/v1/products",
                    headers=Config.SUPABASE_HEADERS,
                    json=product,
                    timeout=5,
                )
                if response.status_code in [200, 201]:
                    added += 1
                else:
                    errors.append(f"{product['name']}: {response.status_code}")
            except Exception as exc:
                errors.append(f"{product['name']}: {str(exc)}")
        
        if added > 0:
            sync_products_from_supabase()

        return jsonify({'success': True, 'added': added, 'total': len(sample_products), 'errors': errors, 'message': f'Loaded {added}/{len(sample_products)} sample products'})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


# ============================================================
# FOR VERCEL
# ============================================================
def handler(request, context):
    return app(request, context)


if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('📱 PRICE POINT - Premium Electronics Shop')
    print('=' * 60)
    print(f"🌍 Environment: {'Vercel' if Config.IS_VERCEL else 'Local'}")
    print(f"\n📊 Products: {len(load_products())}")
    print(f"📊 Orders: {len(load_orders())}")
    print('=' * 60)
    print('\n🚀 Starting server...')
    print('📍 http://localhost:5000')
    print('🔑 Login: admin@pricepoint.com / electronics2026')
    print('👥 Users: admin, manager, pos, user (all with same password)')
    print('=' * 60)
    app.run(debug=not Config.IS_VERCEL, host='0.0.0.0', port=5000)
