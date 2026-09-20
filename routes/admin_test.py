import sys
import os
import json

# Add the project root to Python path so config can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import traceback
import uuid
from datetime import datetime, timedelta
from functools import wraps

import requests
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
from utils.data import get_cart, get_sales_analytics, load_bundles, load_orders, load_products, update_product_stock

admin_bp = Blueprint('admin', __name__)

# ============================================================
# DETECT VERCEL ENVIRONMENT
# ============================================================
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW_REGION') is not None
print(f"🚀 Running on: {'Vercel' if IS_VERCEL else 'Local'}")

# On Vercel, we can only write to /tmp
DATA_FILE = os.path.join('/tmp', 'data.json') if IS_VERCEL else 'data.json'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def is_admin():
    user = session.get('user', {})
    return user.get('role') == 'admin' or session.get('admin_logged_in')


def is_logged_in():
    return 'user' in session or session.get('admin_logged_in')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Admin access required', 'danger')
            return redirect(url_for('admin.user_login'))
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please login first', 'danger')
            return redirect(url_for('admin.user_login'))
        return f(*args, **kwargs)
    return decorated_function


def seed_demo_products():
    demo_products = [
        {'id': 'PROD_1', 'name': 'Wireless Headphones', 'price': 2999, 'stock': 45, 'category': 'Electronics', 'image': '', 'description': 'Premium wireless headphones'},
        {'id': 'PROD_2', 'name': 'USB-C Cable', 'price': 499, 'stock': 120, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_3', 'name': 'Bluetooth Speaker', 'price': 1499, 'stock': 30, 'category': 'Electronics', 'image': ''},
        {'id': 'PROD_4', 'name': 'Laptop Stand', 'price': 899, 'stock': 25, 'category': 'Furniture', 'image': ''},
        {'id': 'PROD_5', 'name': 'Wireless Mouse', 'price': 699, 'stock': 60, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_6', 'name': 'Mechanical Keyboard', 'price': 2499, 'stock': 15, 'category': 'Electronics', 'image': ''},
        {'id': 'PROD_7', 'name': 'HDMI Cable', 'price': 299, 'stock': 80, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_8', 'name': 'USB Hub', 'price': 1299, 'stock': 20, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_9', 'name': 'Monitor 24"', 'price': 14999, 'stock': 8, 'category': 'Electronics', 'image': ''},
        {'id': 'PROD_10', 'name': 'Desk Lamp', 'price': 599, 'stock': 35, 'category': 'Furniture', 'image': ''},
    ]
    return demo_products


def get_default_users():
    return [
        {'id': 'admin_1', 'email': 'admin@pricepoint.com', 'password': 'electronics2026', 'name': 'Admin User', 'role': 'admin'},
        {'id': 'manager_1', 'email': 'manager@pricepoint.com', 'password': 'electronics2026', 'name': 'Store Manager', 'role': 'manager'},
        {'id': 'pos_1', 'email': 'pos@pricepoint.com', 'password': 'electronics2026', 'name': 'POS Operator', 'role': 'pos'},
        {'id': 'user_1', 'email': 'user@pricepoint.com', 'password': 'electronics2026', 'name': 'Regular User', 'role': 'user'}
    ]


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@admin_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please enter both email and password', 'danger')
            return render_template('admin_login.html')

        users_legacy = {
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
                'redirect': '/admin/pos'
            },
            'pos@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'POS Operator',
                'role': 'pos',
                'redirect': '/admin/pos'
            },
            'manager@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'Store Manager',
                'role': 'manager',
                'redirect': '/admin/pos'
            }
        }

        username = request.form.get('username', '').strip()
        if username == 'admin' and password == 'electronics2026':
            session['admin_logged_in'] = True
            session['user'] = {
                'email': 'admin@pricepoint.com',
                'name': 'Admin User',
                'role': 'admin',
                'id': 'legacy_admin'
            }
            flash('Welcome back, Admin!', 'success')
            return redirect('/admin')

        if email in users_legacy and users_legacy[email]['password'] == password:
            session['user'] = {
                'email': email,
                'name': users_legacy[email]['name'],
                'role': users_legacy[email]['role'],
                'id': 'legacy_' + email
            }
            session['admin_logged_in'] = True
            flash('Welcome, ' + users_legacy[email]['name'] + '!', 'success')
            return redirect(users_legacy[email]['redirect'])
        else:
            flash('Invalid email or password', 'danger')
            return render_template('admin_login.html')

    return render_template('admin_login.html')


@admin_bp.route('/logout')
def user_logout():
    session.pop('user', None)
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin.user_login'))


@admin_bp.route('/admin/login')
def admin_login_redirect():
    return redirect(url_for('admin.user_login'))


@admin_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out', 'success')
    return redirect(url_for('admin.user_login'))


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    if not is_admin():
        flash('Admin access required', 'danger')
        return redirect(url_for('admin.user_login'))

    try:
        import utils.data
        utils.data.orders_cache = []

        user = session.get('user', {})
        user_name = user.get('name', 'Admin User')
        user_role = user.get('role', 'admin')

        all_products = load_products()
        all_orders = load_orders()
        
        # ============================================================
        # SAFELY CLEAN PRODUCTS - Fix any None values
        # ============================================================
        cleaned_products = []
        for p in all_products:
            clean_p = dict(p)
            # Fix stock
            if clean_p.get('stock') is None:
                clean_p['stock'] = 0
            # Fix price
            if clean_p.get('price') is None:
                clean_p['price'] = 0
            # Fix name
            if clean_p.get('name') is None:
                clean_p['name'] = 'Unnamed Product'
            # Fix category
            if clean_p.get('category') is None:
                clean_p['category'] = 'Uncategorized'
            # Fix image
            if clean_p.get('image') is None:
                clean_p['image'] = ''
            # Fix description
            if clean_p.get('description') is None:
                clean_p['description'] = ''
            # Fix cost_price
            if clean_p.get('cost_price') is None:
                clean_p['cost_price'] = 0
            # Fix badge
            if clean_p.get('badge') is None:
                clean_p['badge'] = ''
            cleaned_products.append(clean_p)
        
        all_products = cleaned_products
        
        print(f"📡 Loaded: {len(all_products)} products, {len(all_orders)} orders")

        if not all_products:
            all_products = seed_demo_products()
            # Clean demo products too
            for p in all_products:
                if p.get('stock') is None:
                    p['stock'] = 0
                if p.get('price') is None:
                    p['price'] = 0
                if p.get('name') is None:
                    p['name'] = 'Unnamed Product'
                if p.get('category') is None:
                    p['category'] = 'Uncategorized'
            try:
                for product in all_products:
                    requests.post(
                        f"{Config.SUPABASE_URL}/rest/v1/products",
                        headers=Config.SUPABASE_HEADERS,
                        json=product,
                        timeout=10
                    )
                print("🌱 Demo products seeded to Supabase")
            except Exception as e:
                print(f"⚠️ Could not seed demo products: {e}")

        bundles = load_bundles()
        cart = get_cart()
        analytics = get_sales_analytics()

        per_page = 10

        products_page = request.args.get('products_page', 1, type=int)
        orders_page = request.args.get('orders_page', 1, type=int)
        customers_page = request.args.get('customers_page', 1, type=int)

        customer_dict = {}
        pos_count = 0
        web_count = 0

        for order in all_orders:
            name = None
            email = None
            phone = None

            if order.get('customer_name'):
                name = order.get('customer_name')

            if not name:
                customer = order.get('customer', {})
                if isinstance(customer, dict):
                    name = customer.get('name')
                    if not email:
                        email = customer.get('email')
                    if not phone:
                        phone = customer.get('phone')
                elif isinstance(customer, str):
                    try:
                        customer_obj = json.loads(customer)
                        name = customer_obj.get('name')
                        if not email:
                            email = customer_obj.get('email')
                        if not phone:
                            phone = customer_obj.get('phone')
                    except:
                        pass

            if not name:
                email = order.get('customer_email', '')
                if email and '@' in email:
                    name = email.split('@')[0].replace('.', ' ').title()

            if not name or name in ['Walk-in Customer', 'Web Customer', 'Customer', 'Unknown', '']:
                continue

            if not email or email == 'N/A':
                email = order.get('customer_email', 'N/A')
                if (not email or email == 'N/A') and isinstance(order.get('customer'), dict):
                    email = order.get('customer', {}).get('email', 'N/A')

            if not phone or phone == 'N/A':
                phone = order.get('customer_phone', 'N/A')
                if (not phone or phone == 'N/A') and isinstance(order.get('customer'), dict):
                    phone = order.get('customer', {}).get('phone', 'N/A')

            if order.get('source') == 'pos':
                pos_count += 1
            else:
                web_count += 1

            if name not in customer_dict:
                customer_dict[name] = {
                    'name': name,
                    'email': email if email else 'N/A',
                    'phone': phone if phone else 'N/A',
                    'orders': 0,
                    'total_spent': 0
                }
            customer_dict[name]['orders'] += 1
            customer_dict[name]['total_spent'] += order.get('total', 0)

        customers = list(customer_dict.values())
        customers.sort(key=lambda x: x['orders'], reverse=True)
        total_customers = len(customers)

        total_orders = len([o for o in all_orders if o.get('status') != 'cancelled'])
        total_revenue = sum(o.get('total', 0) for o in all_orders if o.get('status') != 'cancelled')
        pending_orders = len([o for o in all_orders if o.get('status') == 'pending'])
        
        # Safe low stock calculation
        low_stock_items = 0
        for p in all_products:
            stock = p.get('stock', 0)
            if stock is None:
                stock = 0
            if stock < 10:
                low_stock_items += 1

        now = datetime.utcnow()
        today = now.date()
        first_day_this_month = today.replace(day=1)

        today_revenue = 0
        today_orders = 0
        yesterday_revenue = 0
        month_revenue = 0
        month_orders = 0
        last_month_revenue = 0

        if today.month == 1:
            last_month_year = today.year - 1
            last_month_month = 12
        else:
            last_month_year = today.year
            last_month_month = today.month - 1

        first_day_last_month = datetime(last_month_year, last_month_month, 1).date()
        if today.month == 1:
            last_day_last_month = datetime(last_month_year, 12, 31).date()
        else:
            last_day_last_month = datetime(today.year, today.month, 1).date() - timedelta(days=1)

        for order in all_orders:
            total = order.get('total', 0)
            if isinstance(total, str):
                try:
                    total = float(total.replace(',', ''))
                except:
                    total = 0
            total = float(total or 0)

            if order.get('status') == 'cancelled':
                continue

            created_at = order.get('created_at', '')
            if not created_at:
                continue

            try:
                if isinstance(created_at, datetime):
                    order_date = created_at.date()
                elif isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            order_date = datetime.fromisoformat(clean).date()
                        else:
                            order_date = datetime.strptime(clean[:10], '%Y-%m-%d').date()
                    elif ' ' in created_at:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                    else:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                else:
                    continue
            except Exception as e:
                print(f"Date parse error: {e}")
                continue

            if order_date == today:
                today_revenue += total
                today_orders += 1

            if order_date == today - timedelta(days=1):
                yesterday_revenue += total

            if order_date >= first_day_this_month:
                month_revenue += total
                month_orders += 1

            if first_day_last_month <= order_date <= last_day_last_month:
                last_month_revenue += total

        if yesterday_revenue > 0:
            today_growth = round(((today_revenue - yesterday_revenue) / yesterday_revenue) * 100, 1)
        else:
            today_growth = 100.0 if today_revenue > 0 else 0

        if last_month_revenue > 0:
            month_growth = round(((month_revenue - last_month_revenue) / last_month_revenue) * 100, 1)
        else:
            month_growth = 100.0 if month_revenue > 0 else 0

        total_customer_pages = (total_customers + per_page - 1) // per_page if total_customers > 0 else 1
        if customers_page < 1:
            customers_page = 1
        elif customers_page > total_customer_pages and total_customer_pages > 0:
            customers_page = total_customer_pages

        customers_start = (customers_page - 1) * per_page
        customers_end = customers_start + per_page
        paginated_customers = customers[customers_start:customers_end] if customers else []

        total_products = len(all_products)
        total_product_pages = (total_products + per_page - 1) // per_page if total_products > 0 else 1
        if products_page < 1:
            products_page = 1
        elif products_page > total_product_pages and total_product_pages > 0:
            products_page = total_product_pages

        products_start = (products_page - 1) * per_page
        products_end = products_start + per_page
        paginated_products = all_products[products_start:products_end] if all_products else []

        sorted_orders = sorted(all_orders, key=lambda x: x.get('created_at', ''), reverse=True)
        total_order_pages = (total_orders + per_page - 1) // per_page if total_orders > 0 else 1
        if orders_page < 1:
            orders_page = 1
        elif orders_page > total_order_pages and total_order_pages > 0:
            orders_page = total_order_pages

        orders_start = (orders_page - 1) * per_page
        orders_end = orders_start + per_page
        paginated_orders = sorted_orders[orders_start:orders_end] if sorted_orders else []

        recent_orders = sorted_orders[:3] if sorted_orders else []

        stats = {
            'total_products': total_products,
            'total_bundles': len(bundles),
            'total_cart_items': sum(cart.values()) if cart else 0,
            'low_stock': low_stock_items,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'pos_orders': pos_count,
            'web_orders': web_count,
            'total_revenue': total_revenue,
            'total_cost': analytics.get('total_cost', 0),
            'total_profit': analytics.get('total_profit', 0),
            'total_items_sold': analytics.get('total_items_sold', 0),
            'total_customers': total_customers,
            'today_revenue': today_revenue,
            'today_orders': today_orders,
            'yesterday_revenue': yesterday_revenue,
            'month_revenue': month_revenue,
            'month_orders': month_orders,
            'last_month_revenue': last_month_revenue,
            'today_growth_pct': today_growth,
            'month_growth_pct': month_growth,
            'db_mode': 'online',
        }

        return render_template('admin.html',
            products=paginated_products,
            all_products=all_products,
            total_products=total_products,
            product_page=products_page,
            total_product_pages=total_product_pages,
            orders=paginated_orders,
            recent_orders=recent_orders,
            total_orders=total_orders,
            orders_page=orders_page,
            total_order_pages=total_order_pages,
            customers=paginated_customers,
            total_customers=total_customers,
            customers_page=customers_page,
            total_customer_pages=total_customer_pages,
            per_page=per_page,
            bundles=bundles,
            stats=stats,
            pos_count=pos_count,
            analytics=analytics,
            DB_CONNECTED=True
        )

    except Exception as exc:
        print(f'Admin dashboard error: {exc}')
        traceback.print_exc()
        flash('Error loading admin dashboard', 'danger')
        return render_template('admin.html',
            products=[],
            bundles=[],
            orders=[],
            customers=[],
            pos_count=0,
            analytics={},
            stats={
                'total_products': 0,
                'total_bundles': 0,
                'total_cart_items': 0,
                'low_stock': 0,
                'total_orders': 0,
                'pending_orders': 0,
                'pos_orders': 0,
                'web_orders': 0,
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'total_items_sold': 0,
                'total_customers': 0,
                'today_revenue': 0,
                'today_orders': 0,
                'yesterday_revenue': 0,
                'month_revenue': 0,
                'month_orders': 0,
                'last_month_revenue': 0,
                'today_growth_pct': 0,
                'month_growth_pct': 0,
                'db_mode': 'offline',
            },
            total_products=0,
            total_product_pages=1,
            product_page=1,
            total_orders=0,
            total_order_pages=1,
            orders_page=1,
            total_customers=0,
            total_customer_pages=1,
            customers_page=1,
            per_page=10,
            recent_orders=[],
            DB_CONNECTED=False
        )


# ============================================================
# ============================================================
# TEST ROUTES - ADDED FOR VERCEL DEBUGGING
# ============================================================
# ============================================================

@admin_bp.route('/test')
def test():
    """Simple test to verify Flask is working on Vercel"""
    return jsonify({
        'status': '✅ Flask is working on Vercel!',
        'vercel': os.environ.get('VERCEL') == '1',
        'now_region': os.environ.get('NOW_REGION'),
        'supabase_url': Config.SUPABASE_URL,
        'has_key': bool(Config.SUPABASE_KEY),
        'key_preview': Config.SUPABASE_KEY[:20] + '...' if Config.SUPABASE_KEY else 'None'
    })


@admin_bp.route('/test-env')
def test_env():
    """Test environment variables"""
    return jsonify({
        'VERCEL': os.environ.get('VERCEL'),
        'NOW_REGION': os.environ.get('NOW_REGION'),
        'SUPABASE_URL_from_os': os.environ.get('SUPABASE_URL'),
        'SUPABASE_KEY_from_os': os.environ.get('SUPABASE_KEY')[:20] + '...' if os.environ.get('SUPABASE_KEY') else 'None',
        'SUPABASE_URL_from_config': Config.SUPABASE_URL,
        'SUPABASE_KEY_from_config': Config.SUPABASE_KEY[:20] + '...' if Config.SUPABASE_KEY else 'None',
        'has_key': bool(Config.SUPABASE_KEY)
    })


@admin_bp.route('/test-supabase')
def test_supabase():
    """Test Supabase connection directly"""
    result = {
        'supabase_url': Config.SUPABASE_URL,
        'has_key': bool(Config.SUPABASE_KEY),
        'key_preview': Config.SUPABASE_KEY[:20] + '...' if Config.SUPABASE_KEY else 'None'
    }
    
    try:
        print("🔗 Testing Supabase connection...")
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/products?limit=1",
            headers=Config.SUPABASE_HEADERS,
            timeout=5
        )
        result['status_code'] = response.status_code
        result['success'] = response.status_code == 200
        if response.status_code == 200:
            data = response.json()
            result['count'] = len(data)
            print(f"✅ Connected! Found {len(data)} products")
        else:
            result['error'] = response.text[:200]
            print(f"❌ Failed with status {response.status_code}")
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ Error: {e}")
    
    return jsonify(result)


@admin_bp.route('/test-data')
def test_data():
    """Test data loading"""
    result = {}
    try:
        from utils.data import load_products, load_orders
        products = load_products()
        orders = load_orders()
        result['products'] = len(products)
        result['orders'] = len(orders)
        if products and len(products) > 0:
            result['sample_product'] = {
                'id': products[0].get('id'),
                'name': products[0].get('name'),
                'price': products[0].get('price'),
                'stock': products[0].get('stock')
            }
        result['success'] = True
    except Exception as e:
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        result['success'] = False
    return jsonify(result)


# ============================================================
# POS ROUTE
# ============================================================

@admin_bp.route('/admin/pos')
def admin_pos():
    if not session.get('admin_logged_in'):
        flash('Please login first', 'danger')
        return redirect(url_for('admin.user_login'))

    all_products = load_products()
    for product in all_products:
        if 'price' not in product or product['price'] is None:
            product['price'] = 0
        if 'stock' not in product or product['stock'] is None:
            product['stock'] = 0
        if 'image' not in product:
            product['image'] = ''
        if 'name' not in product:
            product['name'] = 'Product'
        if 'id' not in product:
            product['id'] = str(uuid.uuid4())

    customers = []
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/customers",
            headers=Config.SUPABASE_HEADERS,
            timeout=10,
        )
        if response.status_code == 200:
            customers_from_db = response.json()
            for c in customers_from_db:
                customers.append({
                    'name': c.get('name', ''),
                    'email': c.get('email', ''),
                    'phone': c.get('phone', ''),
                    'orders': 0,
                    'total_spent': 0
                })
    except Exception as e:
        print(f"⚠️ Error loading customers: {e}")

    customers.sort(key=lambda x: x['name'])

    return render_template('pos.html',
        products=all_products,
        customers=customers,
        DB_CONNECTED=True
    )


# ============================================================
# POS ORDER ROUTE - ONLINE (WORKS PERFECTLY)
# ============================================================

@admin_bp.route('/admin/pos/place-order', methods=['POST'])
def admin_pos_place_order():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'success': False, 'message': 'No items in order'}), 400

        user = session.get('user', {})
        user_id = user.get('id', 'unknown')
        user_name = user.get('name', 'Unknown User')
        user_role = user.get('role', 'user')

        order_id = data.get('order_id', f'POS-{uuid.uuid4().hex[:8].upper()}')
        items = data.get('items', [])
        
        print(f"📦 Received order: {order_id}")
        print(f"📦 Items: {len(items)}")
        
        for item in items:
            print(f"  - {item.get('name')} x{item.get('quantity')}")

        print("📦 DEDUCTING STOCK...")
        
        stock_updated = []
        stock_failed = []
        
        for item in items:
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 1))
            
            if not product_id:
                print(f"⚠️ No product_id for item: {item.get('name')}")
                stock_failed.append({'name': item.get('name'), 'reason': 'No product_id'})
                continue
            
            try:
                print(f"🔍 Fetching product: {product_id}")
                response = requests.get(
                    f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                    headers=Config.SUPABASE_HEADERS,
                    timeout=10
                )
                
                if response.status_code == 200:
                    products = response.json()
                    if products and len(products) > 0:
                        product = products[0]
                        current_stock = product.get('stock', 0)
                        new_stock = max(0, current_stock - quantity)
                        
                        print(f"📦 {product.get('name')}: {current_stock} → {new_stock}")
                        
                        update_response = requests.patch(
                            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                            headers=Config.SUPABASE_HEADERS,
                            json={'stock': new_stock},
                            timeout=10
                        )
                        
                        if update_response.status_code in [200, 204]:
                            print(f"✅ Stock updated: {product.get('name')}")
                            stock_updated.append({
                                'name': product.get('name'),
                                'old_stock': current_stock,
                                'new_stock': new_stock
                            })
                        else:
                            print(f"❌ Failed to update stock: {update_response.status_code}")
                            stock_failed.append({
                                'name': product.get('name'),
                                'reason': f'HTTP {update_response.status_code}'
                            })
                    else:
                        print(f"⚠️ Product not found: {product_id}")
                        stock_failed.append({
                            'name': item.get('name'),
                            'reason': 'Product not found'
                        })
                else:
                    print(f"❌ Failed to fetch product: {response.status_code}")
                    stock_failed.append({
                        'name': item.get('name'),
                        'reason': f'Fetch error: {response.status_code}'
                    })
                    
            except Exception as e:
                print(f"❌ Stock deduction error for {product_id}: {e}")
                stock_failed.append({
                    'name': item.get('name'),
                    'reason': str(e)
                })

        print(f"📊 Stock updated: {len(stock_updated)} items")
        for s in stock_updated:
            print(f"  ✅ {s['name']}: {s['old_stock']} → {s['new_stock']}")
        
        if stock_failed:
            print(f"❌ Stock failed: {len(stock_failed)} items")
            for s in stock_failed:
                print(f"  ❌ {s['name']}: {s['reason']}")

        subtotal = float(data.get('subtotal', 0))
        shipping = float(data.get('shipping', 0))
        total = float(data.get('total', subtotal + shipping))

        customer_name = data.get('customer_name', 'Walk-in Customer')
        customer_email = data.get('customer_email', 'walkin@example.com')
        customer_phone = data.get('customer_phone', 'N/A')
        customer_address = data.get('customer_address', 'In-store purchase')

        order_data = {
            'order_id': order_id,
            'items': items,
            'subtotal': subtotal,
            'shipping': shipping,
            'total': total,
            'status': 'confirmed',
            'source': 'pos',
            'created_at': datetime.utcnow().isoformat(),
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'customer_address': customer_address,
            'customer': {
                'name': customer_name,
                'email': customer_email,
                'phone': customer_phone,
                'address': customer_address,
            },
            'user_id': str(user_id),
            'user_name': user_name,
            'user_role': user_role,
            'staff_name': user_name
        }

        print(f"💰 Total: KSh {total}")

        try:
            response = requests.post(
                f"{Config.SUPABASE_URL}/rest/v1/orders",
                headers=Config.SUPABASE_HEADERS,
                json=order_data,
                timeout=15
            )

            if response.status_code in [200, 201]:
                print(f"✅ Order saved to Supabase: {order_id}")
                
                import utils.data
                utils.data.orders_cache = []
                utils.data.products_cache = []

                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'order': order_data,
                    'synced': True,
                    'stock_updated': stock_updated,
                    'stock_failed': stock_failed,
                    'message': f'✅ Order #{order_id} placed! Stock deducted: {len(stock_updated)} items.',
                    'total': total
                })
            else:
                print(f"❌ Failed to save order: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
                return jsonify({
                    'success': False,
                    'message': f'Failed to save order: {response.status_code}',
                    'supabase_error': response.text[:500]
                }), 500
                
        except Exception as e:
            print(f"❌ Order save error: {e}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Error saving order: {str(e)}'
            }), 500

    except Exception as exc:
        print(f'❌ POS Order error: {exc}')
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Error: {str(exc)[:100]}'
        }), 500


# ============================================================
# SYNC QUEUED ORDERS - FIXED WITH STOCK DEDUCTION/RESTOCK
# ============================================================

@admin_bp.route('/admin/api/sync-queue', methods=['POST'])
def api_sync_queue():
    try:
        # Check Supabase availability
        try:
            response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/products?limit=1",
                headers=Config.SUPABASE_HEADERS,
                timeout=5
            )
            if response.status_code not in [200, 401, 403]:
                return jsonify({
                    'success': True,
                    'synced': 0,
                    'failed': 0,
                    'offline': True,
                    'message': 'Supabase offline - orders will sync when online'
                }), 200
        except:
            return jsonify({
                'success': True,
                'synced': 0,
                'failed': 0,
                'offline': True,
                'message': 'Supabase offline - orders will sync when online'
            }), 200        data = request.get_json()
        if not data or not data.get('orders'):
            return jsonify({
                'success': True,
                'synced': 0,
                'failed': 0,
                'message': 'No orders provided to sync'
            })

        orders_to_sync = data.get('orders', [])

        print(f"🔄 Received {len(orders_to_sync)} items to sync from IndexedDB")

        synced = 0
        failed = 0
        stock_errors = []

        for order in orders_to_sync:
            try:
                order_id = order.get('order_id', f'OFF-{uuid.uuid4().hex[:8].upper()}')
                
                # ============================================================
                # CHECK IF THIS IS A RETURN
                # ============================================================
                is_return = order.get('is_return', False)
                return_type = "RETURN" if is_return else "ORDER"
                
                print(f"📦 Processing {return_type}: {order_id}")
                
                # Check if order already exists
                check_response = requests.get(
                    f"{Config.SUPABASE_URL}/rest/v1/orders?order_id=eq.{order_id}",
                    headers=Config.SUPABASE_HEADERS,
                    timeout=10
                )

                if check_response.status_code == 200 and check_response.json():
                    print(f"⏭️ {return_type} {order_id} already exists, skipping")
                    synced += 1
                    continue

                # ============================================================
                # BUILD ORDER DATA
                # ============================================================
                order_data = {
                    'order_id': order_id,
                    'items': order.get('items', []),
                    'subtotal': float(order.get('subtotal', 0)),
                    'shipping': float(order.get('shipping', 0)),
                    'total': float(order.get('total', 0)),
                    'status': order.get('status', 'confirmed'),
                    'source': order.get('source', 'pos'),
                    'created_at': order.get('created_at', datetime.utcnow().isoformat()),
                    'customer_name': order.get('customer_name', 'Walk-in Customer'),
                    'customer_email': order.get('customer_email', 'walkin@example.com'),
                    'customer_phone': order.get('customer_phone', 'N/A'),
                    'customer_address': order.get('customer_address', 'In-store purchase'),
                    'customer': order.get('customer', {
                        'name': order.get('customer_name', 'Walk-in Customer'),
                        'email': order.get('customer_email', 'walkin@example.com'),
                        'phone': order.get('customer_phone', 'N/A'),
                        'address': order.get('customer_address', 'In-store purchase')
                    }),
                    'user_id': order.get('user_id', 'unknown'),
                    'user_name': order.get('user_name', 'Unknown User'),
                    'user_role': order.get('user_role', 'user'),
                    'staff_name': order.get('staff_name', order.get('user_name', 'Unknown User'))
                }

                # ============================================================
                # ADD RETURN-SPECIFIC FIELDS
                # ============================================================
                if is_return:
                    order_data['is_return'] = True
                    order_data['return_reason'] = order.get('return_reason', 'Customer return')
                    order_data['return_amount'] = float(order.get('return_amount', 0))
                    order_data['original_items'] = order.get('original_items', [])
                    if order_data['total'] > 0:
                        order_data['total'] = -order_data['total']

                # Ensure items is a list and has required fields
                if not isinstance(order_data['items'], list):
                    order_data['items'] = []

                for item in order_data['items']:
                    if not isinstance(item, dict):
                        continue
                    if 'product_id' not in item:
                        item['product_id'] = str(uuid.uuid4())
                    if 'quantity' not in item:
                        item['quantity'] = 1
                    if 'price' not in item:
                        item['price'] = 0
                    if 'name' not in item:
                        item['name'] = 'Unknown Product'
                    if 'total' not in item:
                        item['total'] = float(item.get('price', 0)) * float(item.get('quantity', 1))

                # ============================================================
                # STOCK ADJUSTMENT - THE CRITICAL FIX!
                # ============================================================
                if is_return:
                    # ============================================================
                    # RETURN: RESTOCK ITEMS (add stock back)
                    # ============================================================
                    print(f"📦 RESTOCKING ITEMS FOR RETURN: {order_id}")
                    
                    for item in order_data['items']:
                        product_id = item.get('product_id')
                        quantity = int(item.get('quantity', 1))

                        if not product_id:
                            print(f"⚠️ No product_id for item: {item.get('name')}")
                            continue

                        try:
                            # Get current product from Supabase
                            stock_response = requests.get(
                                f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                                headers=Config.SUPABASE_HEADERS,
                                timeout=10
                            )
                            
                            if stock_response.status_code == 200:
                                stock_products = stock_response.json()
                                if stock_products and len(stock_products) > 0:
                                    product = stock_products[0]
                                    current_stock = product.get('stock', 0)
                                    new_stock = current_stock + quantity  # ADD stock back for returns
                                    
                                    print(f"📦 RESTOCK: {product.get('name')}: {current_stock} → {new_stock} (+{quantity})")
                                    
                                    # Update stock in Supabase
                                    update_response = requests.patch(
                                        f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                                        headers=Config.SUPABASE_HEADERS,
                                        json={'stock': new_stock},
                                        timeout=10
                                    )
                                    
                                    if update_response.status_code in [200, 204]:
                                        print(f"✅ Stock restocked for return: {product.get('name')}")
                                    else:
                                        print(f"❌ Failed to restock during return: {update_response.status_code}")
                                        stock_errors.append({
                                            'product': product.get('name'),
                                            'error': f'HTTP {update_response.status_code}'
                                        })
                                else:
                                    print(f"⚠️ Product not found for restock: {product_id}")
                            else:
                                print(f"❌ Failed to fetch product for restock: {product_id} - {stock_response.status_code}")
                                
                        except Exception as e:
                            print(f"❌ Restock error during return sync for {product_id}: {e}")
                            stock_errors.append({
                                'product': item.get('name'),
                                'error': str(e)
                            })
                else:
                    # ============================================================
                    # ORDER: DEDUCT STOCK
                    # ============================================================
                    print(f"📦 DEDUCTING STOCK FOR SYNCED ORDER: {order_id}")
                    
                    for item in order_data['items']:
                        product_id = item.get('product_id')
                        quantity = int(item.get('quantity', 1))

                        if not product_id:
                            print(f"⚠️ No product_id for item: {item.get('name')}")
                            continue

                        try:
                            # Get current product from Supabase
                            stock_response = requests.get(
                                f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                                headers=Config.SUPABASE_HEADERS,
                                timeout=10
                            )
                            
                            if stock_response.status_code == 200:
                                stock_products = stock_response.json()
                                if stock_products and len(stock_products) > 0:
                                    product = stock_products[0]
                                    current_stock = product.get('stock', 0)
                                    new_stock = max(0, current_stock - quantity)  # DEDUCT stock for orders
                                    
                                    print(f"📦 DEDUCT: {product.get('name')}: {current_stock} → {new_stock}")
                                    
                                    # Update stock in Supabase
                                    update_response = requests.patch(
                                        f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                                        headers=Config.SUPABASE_HEADERS,
                                        json={'stock': new_stock},
                                        timeout=10
                                    )
                                    
                                    if update_response.status_code in [200, 204]:
                                        print(f"✅ Stock updated for sync: {product.get('name')}")
                                    else:
                                        print(f"❌ Failed to update stock during sync: {update_response.status_code}")
                                        stock_errors.append({
                                            'product': product.get('name'),
                                            'error': f'HTTP {update_response.status_code}'
                                        })
                                else:
                                    print(f"⚠️ Product not found for stock deduction: {product_id}")
                            else:
                                print(f"❌ Failed to fetch product for stock deduction: {product_id} - {stock_response.status_code}")
                                
                        except Exception as e:
                            print(f"❌ Stock deduction error during sync for {product_id}: {e}")
                            stock_errors.append({
                                'product': item.get('name'),
                                'error': str(e)
                            })

                # ============================================================
                # SAVE ORDER TO SUPABASE
                # ============================================================
                response = requests.post(
                    f"{Config.SUPABASE_URL}/rest/v1/orders",
                    headers=Config.SUPABASE_HEADERS,
                    json=order_data,
                    timeout=15
                )

                if response.status_code in [200, 201]:
                    print(f"✅ {return_type} synced: {order_id}")
                    synced += 1
                else:
                    print(f"❌ Failed to sync {return_type}: {order_id} - {response.status_code}")
                    print(f"Response: {response.text[:200]}")
                    failed += 1

            except Exception as e:
                failed += 1
                print(f"❌ Sync error for {order.get('order_id', 'unknown')}: {e}")
                traceback.print_exc()

        # Clear caches after successful sync
        if synced > 0:
            import utils.data
            utils.data.orders_cache = []
            utils.data.products_cache = []  # CRITICAL: Clear products cache to reflect stock updates

        # Log summary
        print(f"📊 Sync summary: {synced} synced, {failed} failed")
        if stock_errors:
            print(f"⚠️ Stock errors: {len(stock_errors)}")
            for err in stock_errors:
                print(f"  - {err}")

        return jsonify({
            'success': True,
            'synced': synced,
            'failed': failed,
            'stock_errors': stock_errors,
            'message': f"Synced {synced} items, {failed} failed"
        })

    except Exception as e:
        print(f"❌ Sync queue error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# PROCESS RETURN - ONLINE (WORKS PERFECTLY)
# ============================================================

@admin_bp.route('/admin/api/process-return', methods=['POST'])
def api_process_return():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        items_to_return = data.get('items', [])
        refund_total = data.get('refund_total', 0)
        customer_name = data.get('customer_name', 'Customer')
        reason = data.get('reason', 'Customer return')

        if not items_to_return:
            return jsonify({'success': False, 'message': 'No items to return'}), 400

        return_items = []
        for item in items_to_return:
            item_price = float(item.get('price', 0))
            item_qty = int(item.get('quantity', 1))
            return_items.append({
                'product_id': str(item.get('id', '')),
                'name': item.get('name', 'Product'),
                'price': item_price,
                'quantity': item_qty,
                'total': item_price * item_qty,
                'type': 'return'
            })

        return_order_id = data.get('return_order_id', f'RET-{uuid.uuid4().hex[:8].upper()}')

        return_order_data = {
            'order_id': return_order_id,
            'items': return_items,
            'subtotal': refund_total,
            'shipping': 0,
            'total': -refund_total,
            'status': 'returned',
            'source': 'pos',
            'created_at': datetime.utcnow().isoformat(),
            'customer': {
                'name': customer_name,
                'email': 'return@example.com',
                'phone': 'N/A',
                'address': 'Return'
            },
            'customer_name': customer_name,
            'customer_email': 'return@example.com',
            'customer_phone': 'N/A',
            'customer_address': 'Return',
            'return_reason': reason,
            'return_amount': refund_total,
            'is_return': True
        }

        # Restock products
        for item in items_to_return:
            product_id = str(item.get('id', ''))
            quantity = int(item.get('quantity', 1))
            if product_id:
                try:
                    products = load_products()
                    for p in products:
                        if str(p.get('id')) == product_id:
                            current_stock = int(p.get('stock', 0))
                            new_stock = current_stock + quantity
                            requests.patch(
                                f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                                headers=Config.SUPABASE_HEADERS,
                                json={'stock': new_stock},
                                timeout=10
                            )
                            break
                except Exception as e:
                    print(f"⚠️ Error restocking product {product_id}: {e}")

        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/orders",
            headers=Config.SUPABASE_HEADERS,
            json=return_order_data,
            timeout=10,
        )

        if response.status_code in [200, 201]:
            import utils.data
            utils.data.orders_cache = []
            utils.data.products_cache = []

            return jsonify({
                'success': True,
                'order_id': return_order_id,
                'message': f'Return processed! Refund: KSh {refund_total:,.2f}',
                'refund_total': refund_total,
                'revenue_deducted': refund_total
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to process return: {response.status_code}'
            }), 500

    except Exception as e:
        print(f'❌ Return error: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# SYNC SINGLE ORDER
# ============================================================

@admin_bp.route('/admin/api/sync-order', methods=['POST'])
def api_sync_order():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        if not data or not data.get('order_id'):
            return jsonify({'success': False, 'message': 'No order data provided'}), 400

        order_id = data.get('order_id')
        print(f"🔄 Syncing order from IndexedDB: {order_id}")

        check_response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/orders?order_id=eq.{order_id}",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )

        if check_response.status_code == 200 and check_response.json():
            return jsonify({'success': True, 'message': 'Order already exists'})

        order_data = {
            'order_id': data.get('order_id'),
            'items': data.get('items', []),
            'subtotal': float(data.get('subtotal', 0)),
            'shipping': float(data.get('shipping', 0)),
            'total': float(data.get('total', 0)),
            'status': data.get('status', 'confirmed'),
            'source': data.get('source', 'pos'),
            'created_at': data.get('created_at', datetime.utcnow().isoformat()),
            'customer_name': data.get('customer_name', 'Walk-in Customer'),
            'customer_email': data.get('customer_email', 'walkin@example.com'),
            'customer_phone': data.get('customer_phone', 'N/A'),
            'customer_address': data.get('customer_address', 'In-store purchase'),
            'customer': data.get('customer', {
                'name': data.get('customer_name', 'Walk-in Customer'),
                'email': data.get('customer_email', 'walkin@example.com'),
                'phone': data.get('customer_phone', 'N/A'),
                'address': data.get('customer_address', 'In-store purchase')
            }),
            'user_id': data.get('user_id', 'unknown'),
            'user_name': data.get('user_name', 'Unknown User'),
            'user_role': data.get('user_role', 'user'),
            'staff_name': data.get('staff_name', data.get('user_name', 'Unknown User'))
        }

        if not isinstance(order_data['items'], list):
            order_data['items'] = []

        for item in order_data['items']:
            if not isinstance(item, dict):
                continue
            if 'product_id' not in item:
                item['product_id'] = str(uuid.uuid4())
            if 'quantity' not in item:
                item['quantity'] = 1
            if 'price' not in item:
                item['price'] = 0
            if 'name' not in item:
                item['name'] = 'Unknown Product'
            if 'total' not in item:
                item['total'] = float(item.get('price', 0)) * float(item.get('quantity', 1))

        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/orders",
            headers=Config.SUPABASE_HEADERS,
            json=order_data,
            timeout=15
        )

        if response.status_code in [200, 201]:
            print(f"✅ Order synced to Supabase: {order_id}")
            import utils.data
            utils.data.orders_cache = []
            return jsonify({'success': True, 'message': 'Order synced successfully'})
        else:
            print(f"❌ Sync failed: {response.status_code} - {response.text[:200]}")
            return jsonify({
                'success': False,
                'message': f'Sync failed: {response.status_code}',
                'supabase_error': response.text[:500]
            }), 500

    except Exception as e:
        print(f'❌ Sync order error: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# UNSYNCED ORDERS COUNT
# ============================================================

@admin_bp.route('/admin/api/unsynced-count', methods=['GET'])
def api_unsynced_count():
    try:
        return jsonify({
            'success': True,
            'count': 0,
            'orders': [],
            'message': 'Check IndexedDB for unsynced orders'
        })
    except Exception as e:
        print(f"❌ Unsynced count error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# GET OFFLINE ORDERS
# ============================================================

@admin_bp.route('/admin/api/offline-orders', methods=['GET'])
def api_offline_orders():
    try:
        return jsonify({
            'success': True,
            'message': 'Send offline orders via POST to /admin/api/sync-queue'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# USER SALES STATS
# ============================================================

@admin_bp.route('/admin/api/user-stats', methods=['GET'])
@login_required
def api_user_stats():
    try:
        user = session.get('user', {})
        user_id = user.get('id', 'unknown')
        user_name = user.get('name', 'Unknown User')

        all_orders = load_orders()

        user_orders = []
        for order in all_orders:
            order_user_id = order.get('user_id', '')
            order_user_name = order.get('user_name', '')
            order_staff_name = order.get('staff_name', '')

            if (str(order_user_id) == str(user_id) or
                order_user_name == user_name or
                order_staff_name == user_name):
                user_orders.append(order)

        today = datetime.utcnow().date()
        today_revenue = 0
        today_orders = 0
        total_revenue = 0

        for order in user_orders:
            if order.get('status') == 'cancelled':
                continue
            total_revenue += order.get('total', 0)

            created_at = order.get('created_at', '')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        if 'T' in created_at:
                            order_date = datetime.fromisoformat(created_at.replace('Z', '').replace('+00:00', '')).date()
                        else:
                            order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                    elif isinstance(created_at, datetime):
                        order_date = created_at.date()
                    else:
                        continue

                    if order_date == today:
                        today_revenue += order.get('total', 0)
                        today_orders += 1
                except:
                    pass

        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'name': user_name
            },
            'today_revenue': today_revenue,
            'today_orders': today_orders,
            'total_revenue': total_revenue,
            'total_orders': len(user_orders)
        })
    except Exception as e:
        print(f"❌ User stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API ROUTES
# ============================================================

@admin_bp.route('/admin/api/analytics')
def admin_api_analytics():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    orders = load_orders()
    analytics = calculate_analytics_from_orders(orders)
    return jsonify(analytics)


@admin_bp.route('/admin/api/revenue')
def admin_api_revenue():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        orders = load_orders()

        now = datetime.utcnow()
        today = now.date()
        first_day_this_month = today.replace(day=1)

        if today.month == 1:
            last_month_year = today.year - 1
            last_month_month = 12
        else:
            last_month_year = today.year
            last_month_month = today.month - 1

        first_day_last_month = datetime(last_month_year, last_month_month, 1).date()
        if today.month == 1:
            last_day_last_month = datetime(last_month_year, 12, 31).date()
        else:
            last_day_last_month = datetime(today.year, today.month, 1).date() - timedelta(days=1)

        today_revenue = 0
        today_orders = 0
        yesterday_revenue = 0
        month_revenue = 0
        month_orders = 0
        last_month_revenue = 0

        for order in orders:
            total = order.get('total', 0)
            if isinstance(total, str):
                try:
                    total = float(total.replace(',', ''))
                except:
                    total = 0
            total = float(total or 0)

            if order.get('status') == 'cancelled':
                continue

            created_at = order.get('created_at', '')
            if not created_at:
                continue

            try:
                if isinstance(created_at, datetime):
                    order_date = created_at.date()
                elif isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            order_date = datetime.fromisoformat(clean).date()
                        else:
                            order_date = datetime.strptime(clean[:10], '%Y-%m-%d').date()
                    elif ' ' in created_at:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                    else:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                else:
                    continue
            except Exception as e:
                print(f"Date parse error: {e}")
                continue

            if order_date == today:
                today_revenue += total
                today_orders += 1

            if order_date == today - timedelta(days=1):
                yesterday_revenue += total

            if order_date >= first_day_this_month:
                month_revenue += total
                month_orders += 1

            if first_day_last_month <= order_date <= last_day_last_month:
                last_month_revenue += total

        if yesterday_revenue > 0:
            today_growth = round(((today_revenue - yesterday_revenue) / yesterday_revenue) * 100, 1)
        else:
            today_growth = 100.0 if today_revenue > 0 else 0

        if last_month_revenue > 0:
            month_growth = round(((month_revenue - last_month_revenue) / last_month_revenue) * 100, 1)
        else:
            month_growth = 100.0 if month_revenue > 0 else 0

        total_revenue = sum(order.get('total', 0) for order in orders if order.get('status') != 'cancelled')

        return jsonify({
            "total_revenue": total_revenue,
            "total_cost": 0,
            "total_profit": 0,
            "total_orders": len(orders),
            "total_items_sold": 0,
            "today_revenue": today_revenue,
            "today_orders": today_orders,
            "yesterday_revenue": yesterday_revenue,
            "month_revenue": month_revenue,
            "month_orders": month_orders,
            "last_month_revenue": last_month_revenue,
            "today_growth_pct": today_growth,
            "month_growth_pct": month_growth
        })

    except Exception as exc:
        print(f'❌ Revenue API error: {exc}')
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


# ============================================================
# CALCULATE ANALYTICS
# ============================================================

def calculate_analytics_from_orders(orders):
    if not orders:
        return {
            'total_revenue': 0,
            'total_cost': 0,
            'total_profit': 0,
            'total_orders': 0,
            'total_items_sold': 0,
            'pos_orders_count': 0,
            'web_orders_count': 0,
            'product_sales': {},
            'category_sales': {},
            'monthly_data': {}
        }

    products = load_products()
    product_lookup = {str(p.get('id')): p for p in products if p and p.get('id')}

    total_revenue = 0
    total_cost = 0
    total_profit = 0
    total_items_sold = 0
    pos_orders_count = 0
    web_orders_count = 0
    product_sales = {}
    category_sales = {}
    monthly_data = {}

    for order in orders:
        if order.get('status') == 'cancelled':
            continue

        if order.get('source') == 'pos':
            pos_orders_count += 1
        else:
            web_orders_count += 1

        created_at = order.get('created_at', '')
        month_key = 'Unknown'
        if created_at:
            try:
                if isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            dt = datetime.fromisoformat(clean)
                        else:
                            dt = datetime.strptime(clean[:10], '%Y-%m-%d')
                    elif ' ' in created_at:
                        dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
                    else:
                        dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
                elif isinstance(created_at, datetime):
                    dt = created_at
                else:
                    dt = datetime.utcnow()
                month_key = dt.strftime('%b %Y')
            except:
                month_key = 'Unknown'

        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'orders': 0,
                'items': 0,
                'revenue': 0,
                'cost': 0,
                'profit': 0,
                'margin': 0
            }
        monthly_data[month_key]['orders'] += 1

        order_total = 0
        order_cost = 0
        order_items = 0

        for item in order.get('items', []):
            quantity = item.get('quantity', 1)
            price = float(item.get('price', 0) or 0)
            total_items_sold += quantity
            order_items += quantity

            item_total = price * quantity
            order_total += item_total
            total_revenue += item_total

            cost_price = 0

            if 'cost_price' in item:
                try:
                    cost_price = float(item.get('cost_price', 0) or 0)
                except (ValueError, TypeError):
                    cost_price = 0

            if cost_price == 0:
                product_id = item.get('product_id', '')
                if product_id:
                    product = product_lookup.get(product_id, {})
                    if product:
                        cost_price = float(product.get('cost_price', 0) or 0)

            if cost_price == 0 and price > 0:
                cost_price = price * 0.7

            item_cost = cost_price * quantity
            order_cost += item_cost
            total_cost += item_cost
            total_profit += (item_total - item_cost)

            product_id = item.get('product_id', '')
            category = 'Uncategorized'
            if product_id:
                product = product_lookup.get(product_id, {})
                if product and product.get('category'):
                    category = product.get('category')

            product_name = item.get('name', 'Unknown Product')
            if product_name not in product_sales:
                product_sales[product_name] = {
                    'quantity': 0,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0,
                    'margin': 0
                }
            product_sales[product_name]['quantity'] += quantity
            product_sales[product_name]['revenue'] += item_total
            product_sales[product_name]['cost'] += item_cost
            product_sales[product_name]['profit'] += (item_total - item_cost)

            if category not in category_sales:
                category_sales[category] = {
                    'quantity': 0,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0,
                    'margin': 0
                }
            category_sales[category]['quantity'] += quantity
            category_sales[category]['revenue'] += item_total
            category_sales[category]['cost'] += item_cost
            category_sales[category]['profit'] += (item_total - item_cost)

        monthly_data[month_key]['items'] += order_items
        monthly_data[month_key]['revenue'] += order_total
        monthly_data[month_key]['cost'] += order_cost
        monthly_data[month_key]['profit'] += (order_total - order_cost)

    for product in product_sales.values():
        if product['revenue'] > 0:
            product['margin'] = round((product['profit'] / product['revenue']) * 100, 1)

    for category in category_sales.values():
        if category['revenue'] > 0:
            category['margin'] = round((category['profit'] / category['revenue']) * 100, 1)

    for month in monthly_data.values():
        if month['revenue'] > 0:
            month['margin'] = round((month['profit'] / month['revenue']) * 100, 1)

    sorted_products = sorted(
        product_sales.items(),
        key=lambda x: x[1]['profit'],
        reverse=True
    )
    product_sales = dict(sorted_products)

    return {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'total_orders': len(orders),
        'total_items_sold': total_items_sold,
        'pos_orders_count': pos_orders_count,
        'web_orders_count': web_orders_count,
        'product_sales': product_sales,
        'category_sales': category_sales,
        'monthly_data': monthly_data
    }


@admin_bp.route('/api/products/<product_id>', methods=['GET'])
def api_get_product(product_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        products = load_products()
        for product in products:
            if str(product.get('id')) == str(product_id):
                return jsonify(product)
        return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/orders/<order_id>', methods=['GET'])
def api_get_order(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        orders = load_orders()

        for order in orders:
            if str(order.get('order_id')) == str(order_id):
                customer = order.get('customer', {})
                if isinstance(customer, str):
                    try:
                        customer = json.loads(customer) if customer else {}
                    except:
                        customer = {}
                if isinstance(customer, list):
                    customer = customer[0] if customer else {}
                if not isinstance(customer, dict):
                    customer = {}

                items = order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                if not isinstance(items, list):
                    items = []

                formatted_items = []
                for item in items:
                    if isinstance(item, dict):
                        formatted_items.append({
                            'name': item.get('name', 'Product'),
                            'quantity': item.get('quantity', 1),
                            'price': item.get('price', 0),
                            'total': item.get('total', item.get('price', 0) * item.get('quantity', 1))
                        })

                return jsonify({
                    'order_id': order.get('order_id', 'N/A'),
                    'customer': {
                        'name': customer.get('name', order.get('customer_name', 'Customer')),
                        'email': customer.get('email', order.get('customer_email', 'N/A')),
                        'phone': customer.get('phone', order.get('customer_phone', 'N/A')),
                        'address': customer.get('address', order.get('customer_address', 'N/A')),
                    },
                    'items': formatted_items,
                    'subtotal': order.get('subtotal', 0),
                    'shipping': order.get('shipping', 0),
                    'total': order.get('total', 0),
                    'status': order.get('status', 'pending'),
                    'created_at': order.get('created_at', ''),
                    'source': order.get('source', 'web'),
                })
        return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/upload-image', methods=['POST'])
def upload_image():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    if file and allowed_file(file.filename):
        filename = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        image_url = f"/static/uploads/{filename}"
        return jsonify({'success': True, 'url': image_url, 'message': 'Image uploaded successfully!'})
    return jsonify({'success': False, 'message': 'Invalid file type'}), 400


@admin_bp.route('/admin/products', methods=['POST'])
def admin_products():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = {
                'id': request.form.get('id', '').strip(),
                'name': request.form.get('name', '').strip(),
                'price': float(request.form.get('price', 0) or 0),
                'cost_price': float(request.form.get('cost_price', 0) or 0),
                'image': request.form.get('image', '').strip(),
                'category': request.form.get('category', '').strip(),
                'description': request.form.get('description', '').strip(),
                'rating': float(request.form.get('rating', 4.0) or 4.0),
                'reviews': int(request.form.get('reviews', 0) or 0),
                'badge': request.form.get('badge', '').strip(),
                'stock': int(request.form.get('stock', 0) or 0),
                'original_price': float(request.form.get('original_price', 0) or 0) or None,
                'specs': [s.strip() for s in request.form.get('specs', '').split(',') if s.strip()]
            }

        product_id = data.get('id', '').strip()
        if not product_id:
            return jsonify({'success': False, 'message': 'Product ID is required'}), 400

        existing_products = load_products()
        product_exists = False
        for p in existing_products:
            if p.get('id') == product_id:
                product_exists = True
                break

        if product_exists:
            response = requests.patch(
                f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                headers=Config.SUPABASE_HEADERS,
                json=data,
                timeout=10,
            )
            if response.status_code in [200, 204]:
                import utils.data
                utils.data.products_cache = []
                return jsonify({'success': True, 'message': 'Product updated successfully!', 'product': data})
            else:
                return jsonify({'success': False, 'message': f'Error updating product: {response.status_code}'}), 500

        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/products",
            headers=Config.SUPABASE_HEADERS,
            json=data,
            timeout=10,
        )

        if response.status_code in [200, 201]:
            import utils.data
            utils.data.products_cache = []
            return jsonify({'success': True, 'message': 'Product saved successfully!', 'product': data})
        else:
            return jsonify({'success': False, 'message': f'Error saving product: {response.status_code}'}), 500

    except Exception as exc:
        print(f'Product save error: {exc}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(exc)}), 500


@admin_bp.route('/admin/products/<product_id>', methods=['DELETE'])
def admin_delete_product(product_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        response = requests.delete(
            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=Config.SUPABASE_HEADERS,
            timeout=5,
        )
        if response.status_code in [200, 204]:
            import utils.data
            utils.data.products_cache = []
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Failed to delete'})
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)})


@admin_bp.route('/admin/orders/<order_id>/status', methods=['POST'])
def admin_update_order_status(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        new_status = request.json.get('status')
        if not new_status:
            return jsonify({'success': False, 'message': 'Status required'}), 400
        response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/orders?order_id=eq.{order_id}",
            headers=Config.SUPABASE_HEADERS,
            json={'status': new_status},
            timeout=5,
        )
        if response.status_code in [200, 204]:
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Failed to update status'})
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 500


@admin_bp.route('/api/customers', methods=['GET'])
def api_customers():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/customers",
            headers=Config.SUPABASE_HEADERS,
            timeout=10,
        )

        if response.status_code == 200:
            customers_from_db = response.json()
            if customers_from_db:
                result = []
                for c in customers_from_db:
                    result.append({
                        'name': c.get('name', ''),
                        'email': c.get('email', 'N/A'),
                        'phone': c.get('phone', 'N/A'),
                        'orders': 0,
                        'total_spent': 0
                    })
                return jsonify(result)

        orders = load_orders()
        customer_dict = {}

        for order in orders:
            name = None

            if order.get('customer_name'):
                name = order.get('customer_name')

            if not name:
                customer = order.get('customer', {})
                if isinstance(customer, dict):
                    name = customer.get('name')
                elif isinstance(customer, str):
                    try:
                        customer_obj = json.loads(customer)
                        name = customer_obj.get('name')
                    except:
                        pass

            if not name or name in ['Walk-in Customer', 'Web Customer', 'Customer', '']:
                continue

            email = order.get('customer_email', 'N/A')
            phone = order.get('customer_phone', 'N/A')

            if name not in customer_dict:
                customer_dict[name] = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'orders': 0,
                    'total_spent': 0
                }
            customer_dict[name]['orders'] += 1
            customer_dict[name]['total_spent'] += order.get('total', 0)

        return jsonify(list(customer_dict.values()))

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/sales-stats', methods=['GET'])
def api_sales_stats():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        orders = load_orders()
        products = load_products()
        today = datetime.utcnow().date()

        today_revenue = 0
        today_orders = 0
        today_returns = 0
        today_return_amount = 0
        all_customers = set()

        for order in orders:
            created_at = order.get('created_at', '')
            if not created_at:
                continue

            try:
                order_date = None
                if isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            order_date = datetime.fromisoformat(clean).date()
                        else:
                            order_date = datetime.strptime(clean[:10], '%Y-%m-%d').date()
                    elif ' ' in created_at:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                    else:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                elif isinstance(created_at, datetime):
                    order_date = created_at.date()
                else:
                    continue

                customer = order.get('customer', {})
                customer_name = None
                if isinstance(customer, dict):
                    customer_name = customer.get('name', '')
                elif isinstance(customer, str):
                    try:
                        c = json.loads(customer)
                        customer_name = c.get('name', '')
                    except:
                        pass

                if customer_name and customer_name not in ['Walk-in Customer', 'Web Customer', '']:
                    all_customers.add(customer_name)

                if order_date == today:
                    status = order.get('status', '')
                    total = float(order.get('total', 0))

                    if status == 'returned':
                        today_returns += 1
                        today_return_amount += abs(total)
                        today_revenue += total
                    elif status != 'cancelled':
                        today_revenue += total
                        today_orders += 1

            except Exception as e:
                print(f"Error processing order: {e}")
                continue

        total_products = len(products)

        return jsonify({
            'success': True,
            'today_revenue': today_revenue,
            'today_orders': today_orders,
            'today_returns': today_returns,
            'today_return_amount': today_return_amount,
            'total_customers': len(all_customers),
            'total_products': total_products
        })
    except Exception as e:
        print(f"❌ Sales stats error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# AJAX PAGINATION API ENDPOINTS
# ============================================================

@admin_bp.route('/admin/api/products', methods=['GET'])
@admin_required
def api_products_paginated():
    """Get paginated products for AJAX"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        all_products = load_products()
        
        total = len(all_products)
        start = (page - 1) * per_page
        end = start + per_page
        products = all_products[start:end]
        
        return jsonify({
            'success': True,
            'products': products,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'start': start + 1 if products else 0,
            'end': min(end, total)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/orders', methods=['GET'])
@admin_required
def api_orders_paginated():
    """Get paginated orders for AJAX"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        all_orders = load_orders()
        all_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        total = len(all_orders)
        start = (page - 1) * per_page
        end = start + per_page
        orders = all_orders[start:end]
        
        return jsonify({
            'success': True,
            'orders': orders,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'start': start + 1 if orders else 0,
            'end': min(end, total)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/customers', methods=['GET'])
@admin_required
def api_customers_paginated():
    """Get paginated customers for AJAX"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        all_orders = load_orders()
        
        customer_dict = {}
        for order in all_orders:
            if order.get('status') == 'cancelled':
                continue
                
            name = order.get('customer_name')
            if not name:
                customer = order.get('customer', {})
                if isinstance(customer, dict):
                    name = customer.get('name')
                elif isinstance(customer, str):
                    try:
                        name = json.loads(customer).get('name')
                    except:
                        pass
            
            if not name or name in ['Walk-in Customer', 'Web Customer', 'Customer', 'Unknown', '']:
                continue
            
            if name not in customer_dict:
                customer_dict[name] = {
                    'name': name,
                    'email': order.get('customer_email', 'N/A'),
                    'phone': order.get('customer_phone', 'N/A'),
                    'orders': 0,
                    'total_spent': 0
                }
            customer_dict[name]['orders'] += 1
            customer_dict[name]['total_spent'] += order.get('total', 0)
        
        customers = list(customer_dict.values())
        customers.sort(key=lambda x: x['orders'], reverse=True)
        
        total = len(customers)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = customers[start:end]
        
        return jsonify({
            'success': True,
            'customers': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'start': start + 1 if paginated else 0,
            'end': min(end, total)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/order/<order_id>', methods=['GET'])
@admin_required
def api_get_order_details(order_id):
    """Get single order details for modal"""
    try:
        all_orders = load_orders()
        
        for order in all_orders:
            if str(order.get('order_id')) == str(order_id):
                items = order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                
                customer = order.get('customer', {})
                if isinstance(customer, str):
                    try:
                        customer = json.loads(customer)
                    except:
                        customer = {}
                
                return jsonify({
                    'success': True,
                    'order': {
                        'order_id': order.get('order_id'),
                        'items': items,
                        'subtotal': order.get('subtotal', 0),
                        'shipping': order.get('shipping', 0),
                        'total': order.get('total', 0),
                        'status': order.get('status', 'pending'),
                        'source': order.get('source', 'web'),
                        'created_at': order.get('created_at', ''),
                        'customer_name': order.get('customer_name', 'Customer'),
                        'customer_email': order.get('customer_email', ''),
                        'customer_phone': order.get('customer_phone', ''),
                        'customer_address': order.get('customer_address', ''),
                        'customer': customer
                    }
                })
        
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/product/<product_id>', methods=['GET'])
@admin_required
def api_get_product_details(product_id):
    """Get single product details for editing"""
    try:
        all_products = load_products()
        
        for product in all_products:
            if str(product.get('id')) == str(product_id):
                return jsonify({'success': True, 'product': product})
        
        return jsonify({'success': False, 'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/api/product/<product_id>', methods=['PUT'])
@admin_required
def api_update_product(product_id):
    """Update a product"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        try:
            requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/",
                headers=Config.SUPABASE_HEADERS,
                timeout=3
            )
        except:
            return jsonify({
                'success': False, 
                'message': 'You are offline. Please connect to the internet to update products.',
                'offline': True
            }), 503
        
        response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=Config.SUPABASE_HEADERS,
            json=data,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            import utils.data
            utils.data.products_cache = []
            return jsonify({'success': True, 'message': 'Product updated successfully'})
        else:
            return jsonify({'success': False, 'message': f'Failed to update: {response.status_code}'}), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False, 
            'message': 'You are offline. Please connect to the internet to update products.',
            'offline': True
        }), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/admin/api/product/<product_id>', methods=['DELETE'])
@admin_required
def api_delete_product(product_id):
    """Delete a product"""
    try:
        try:
            requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/",
                headers=Config.SUPABASE_HEADERS,
                timeout=3
            )
        except:
            return jsonify({
                'success': False, 
                'message': 'You are offline. Please connect to the internet to delete products.',
                'offline': True
            }), 503
        
        response = requests.delete(
            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            import utils.data
            utils.data.products_cache = []
            return jsonify({'success': True, 'message': 'Product deleted successfully'})
        else:
            return jsonify({'success': False, 'message': f'Failed to delete: {response.status_code}'}), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False, 
            'message': 'You are offline. Please connect to the internet to delete products.',
            'offline': True
        }), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# PWA ROUTES - PUBLIC
# ============================================================

@admin_bp.route('/offline.html')
def offline_page():
    try:
        return render_template('offline.html')
    except Exception as e:
        print(f"❌ Error serving offline.html: {e}")
        return "Offline page not found", 404


@admin_bp.route('/sw.js')
def service_worker():
    try:
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    except Exception as e:
        print(f"❌ Error serving sw.js: {e}")
        return "Service Worker not found", 404


@admin_bp.route('/manifest.json')
def manifest():
    try:
        return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')
    except Exception as e:
        print(f"❌ Error serving manifest.json: {e}")
        return "Manifest not found", 404


@admin_bp.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory('static/icons', 'favicon.ico', mimetype='image/x-icon')
    except Exception as e:
        print(f"⚠️ Favicon not found: {e}")
        return "", 204


@admin_bp.route('/static/<path:filename>')
def static_files(filename):
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        print(f"❌ Error serving static file: {e}")
        return "File not found", 404
