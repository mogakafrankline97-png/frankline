from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from datetime import datetime, timedelta
import os
import uuid
import json
import requests
import traceback
import threading
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
application = app
app.secret_key = 'allison-electronics-secret-2026'
app.permanent_session_lifetime = timedelta(days=7)

# ================================================================
# ===== CONFIGURATION =====
# ================================================================

IS_VERCEL = 'VERCEL' in os.environ or 'NOW' in os.environ

if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/static/uploads'
    STATIC_FOLDER = '/tmp/static'
else:
    UPLOAD_FOLDER = 'static/uploads'
    STATIC_FOLDER = 'static'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(STATIC_FOLDER, exist_ok=True)
except:
    pass

app.static_folder = STATIC_FOLDER

# ===== TEMPLATE FILTERS =====
@app.template_filter('format_number')
def format_number_filter(value):
    """Format number with commas"""
    try:
        if value is None:
            return "0"
        return f"{int(float(value)):,}"
    except (ValueError, TypeError):
        return "0"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ================================================================
# ===== SUPABASE CONFIG =====
# ================================================================

SUPABASE_URL = "https://hzqrdwerkgfmfaufabjr.supabase.co"
SUPABASE_KEY = "sb_publishable_tnBOmCO7EFfIoXfNjEH_Tg_D7WX-zld"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ================================================================
# ===== OFFLINE JSON STORAGE =====
# ================================================================

DATA_FILE = 'offline_data.json'
products_cache = []
orders_cache = []
order_queue = []

def load_json_data():
    """Load data from JSON file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return {'products': [], 'orders': [], 'order_queue': []}
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return {'products': [], 'orders': [], 'order_queue': []}

def save_json_data(data):
    """Save data to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving JSON: {e}")
        return False

def has_internet():
    """Check if internet is available"""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

# Initialize JSON file if it doesn't exist
if not os.path.exists(DATA_FILE):
    save_json_data({'products': [], 'orders': [], 'order_queue': []})
    print("✅ JSON data file created")

# ================================================================
# ===== ERROR HANDLERS =====
# ================================================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/admin/') or request.path.startswith('/api/'):
        return jsonify({'error': 'Not found', 'message': 'The requested endpoint does not exist'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    print(f"Server error: {e}")
    traceback.print_exc()
    if request.path.startswith('/admin/') or request.path.startswith('/api/'):
        return jsonify({'error': 'Server error', 'message': str(e)}), 500
    return render_template('500.html'), 500

# ================================================================
# ===== DATA FUNCTIONS =====
# ================================================================

def load_orders():
    """Load orders from Supabase with JSON fallback"""
    try:
        if has_internet():
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/orders?select=*&order=created_at.desc",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for order in data:
                        if isinstance(order.get('customer'), list):
                            order['customer'] = order['customer'][0] if order['customer'] else {}
                        if isinstance(order.get('items'), str):
                            try:
                                order['items'] = json.loads(order['items'])
                            except:
                                order['items'] = []
                        if not isinstance(order.get('customer'), dict):
                            order['customer'] = {}
                        if not isinstance(order.get('items'), list):
                            order['items'] = []
                    # Cache orders locally
                    json_data = load_json_data()
                    json_data['orders'] = data
                    save_json_data(json_data)
                    return data
        
        # Return cached orders
        json_data = load_json_data()
        return json_data.get('orders', [])
    except Exception as e:
        print(f"Error loading orders: {e}")
        json_data = load_json_data()
        return json_data.get('orders', [])

def load_products():
    """Load products from Supabase with JSON cache"""
    global products_cache
    
    try:
        if has_internet():
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/products?select=*",
                headers=SUPABASE_HEADERS,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    products_cache = data
                    # Cache to JSON
                    json_data = load_json_data()
                    json_data['products'] = data
                    json_data['last_sync'] = datetime.utcnow().isoformat()
                    save_json_data(json_data)
                    print(f"☁️ Loaded {len(data)} products from Supabase")
                    return data
        
        # Return cached products
        if products_cache:
            print(f"📂 Using cached products ({len(products_cache)})")
            return products_cache
        
        json_data = load_json_data()
        products = json_data.get('products', [])
        if products:
            products_cache = products
            print(f"📂 Loaded {len(products)} products from JSON cache")
            return products
        
        # Ultimate fallback: Sample products
        print("⚠️ No products found - returning sample data")
        return get_sample_products()
    except Exception as e:
        print(f"Error loading products: {e}")
        return products_cache if products_cache else get_sample_products()

def get_sample_products():
    """Return hardcoded sample products"""
    return [
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
            'badge': 'Best Seller'
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
            'badge': 'New'
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
            'badge': 'Trending'
        },
        {
            'id': 'samsung_s24',
            'name': 'Samsung Galaxy S24 Ultra',
            'price': 165000.0,
            'cost_price': 115000.0,
            'category': 'Phones',
            'description': 'Flagship Android phone with advanced camera',
            'image': 'https://images.unsplash.com/photo-1511707267537-b85faf00021e?w=500',
            'stock': 20,
            'rating': 4.6,
            'reviews': 234
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
            'badge': 'New'
        }
    ]

def load_bundles():
    """Load bundles from Supabase"""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/bundles?select=*",
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
        return []
    except:
        return []

def save_order_to_supabase(order_data):
    """Save order - offline-first with JSON queue"""
    global order_queue
    
    # Always save to JSON first
    json_data = load_json_data()
    
    # Check if order already exists
    existing = [o for o in json_data.get('orders', []) if o.get('order_id') == order_data.get('order_id')]
    if not existing:
        json_data.setdefault('orders', []).append(order_data)
        save_json_data(json_data)
    
    # If online, try Supabase
    if has_internet():
        try:
            supabase_order = {
                'order_id': order_data.get('order_id'),
                'items': json.dumps(order_data.get('items', [])),
                'subtotal': float(order_data.get('subtotal', 0)),
                'shipping': float(order_data.get('shipping', 0)),
                'total': float(order_data.get('total', 0)),
                'status': order_data.get('status', 'pending'),
                'source': order_data.get('source', 'web'),
                'created_at': order_data.get('created_at', datetime.utcnow().isoformat()),
                'customer': json.dumps(order_data.get('customer', {}))
            }
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/orders",
                headers=SUPABASE_HEADERS,
                json=supabase_order,
                timeout=10
            )
            if response.status_code in [200, 201, 204]:
                # Mark as synced in JSON
                json_data = load_json_data()
                for order in json_data.get('orders', []):
                    if order.get('order_id') == order_data.get('order_id'):
                        order['synced'] = True
                        order['synced_at'] = datetime.utcnow().isoformat()
                save_json_data(json_data)
                print(f"✅ Order saved to Supabase: {order_data.get('order_id')}")
                return True
            else:
                print(f"⚠️ Failed to save to Supabase: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Supabase save failed: {e}")
    
    # If offline or failed, add to queue
    json_data = load_json_data()
    queue = json_data.get('order_queue', [])
    if order_data.get('order_id') not in [q.get('order_id') for q in queue]:
        queue.append({
            **order_data,
            'queued_at': datetime.utcnow().isoformat()
        })
        json_data['order_queue'] = queue
        save_json_data(json_data)
        print(f"📦 Order queued for later sync (queue: {len(queue)})")
    
    return True  # Always return True so user doesn't see error

def sync_queued_orders():
    """Sync queued orders from JSON when online"""
    if not has_internet():
        return
    
    json_data = load_json_data()
    queue = json_data.get('order_queue', [])
    
    if not queue:
        return
    
    print(f"🔄 Syncing {len(queue)} queued orders...")
    synced = []
    
    for order in queue:
        try:
            supabase_order = {
                'order_id': order.get('order_id'),
                'items': json.dumps(order.get('items', [])),
                'subtotal': float(order.get('subtotal', 0)),
                'shipping': float(order.get('shipping', 0)),
                'total': float(order.get('total', 0)),
                'status': order.get('status', 'pending'),
                'source': order.get('source', 'web'),
                'created_at': order.get('created_at', datetime.utcnow().isoformat()),
                'customer': json.dumps(order.get('customer', {}))
            }
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/orders",
                headers=SUPABASE_HEADERS,
                json=supabase_order,
                timeout=10
            )
            if response.status_code in [200, 201, 204]:
                synced.append(order)
                print(f"✅ Synced order: {order.get('order_id')}")
        except Exception as e:
            print(f"❌ Failed to sync order: {e}")
    
    # Remove synced orders from queue
    if synced:
        json_data = load_json_data()
        json_data['order_queue'] = [o for o in json_data.get('order_queue', []) if o.get('order_id') not in [s.get('order_id') for s in synced]]
        save_json_data(json_data)
        print(f"📊 Queue size: {len(json_data['order_queue'])}")

def sync_products_from_supabase():
    """Sync products from Supabase to JSON cache"""
    try:
        if not has_internet():
            return False
        
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?select=*",
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                json_data = load_json_data()
                json_data['products'] = data
                json_data['last_sync'] = datetime.utcnow().isoformat()
                save_json_data(json_data)
                print(f"✅ Synced {len(data)} products from Supabase")
                return True
        return False
    except Exception as e:
        print(f"Product sync error: {e}")
        return False

def update_product_stock(product_id, new_stock):
    """Update product stock in Supabase"""
    try:
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=SUPABASE_HEADERS,
            json={'stock': int(new_stock)},
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Error updating stock: {e}")
        return False

def get_cart():
    """Get cart from session"""
    try:
        cart = session.get('cart', {})
        if isinstance(cart, list):
            new_cart = {}
            for item_id in cart:
                new_cart[item_id] = new_cart.get(item_id, 0) + 1
            session['cart'] = new_cart
            session.modified = True
            return new_cart
        if not isinstance(cart, dict):
            session['cart'] = {}
            session.modified = True
            return {}
        return cart
    except Exception as e:
        print(f"Error getting cart: {e}")
        return {}

# ================================================================
# ===== BACKGROUND SYNC THREAD =====
# ================================================================

def background_sync():
    """Background thread to sync data when internet is available"""
    while True:
        try:
            if has_internet():
                print("🌐 Internet available - syncing...")
                sync_products_from_supabase()
                sync_queued_orders()
            else:
                print("📴 Offline mode - using local data")
            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            print(f"Background sync error: {e}")
            time.sleep(60)

def start_sync_thread():
    """Start background sync thread"""
    thread = threading.Thread(target=background_sync, daemon=True)
    thread.start()
    print("🔄 Background sync thread started")

# Start background sync
start_sync_thread()

# ================================================================
# ===== ANALYTICS =====
# ================================================================

def get_sales_analytics():
    """Calculate revenue, profit, and sales analytics"""
    try:
        orders = load_orders()
        products = load_products()
        
        if not orders:
            orders = []
        if not products:
            products = []
        
        product_lookup = {}
        for p in products:
            if p and p.get('id'):
                product_lookup[str(p.get('id'))] = p
        
        total_revenue = 0
        total_cost = 0
        total_profit = 0
        total_orders = len(orders)
        total_items_sold = 0
        pos_orders_count = 0
        web_orders_count = 0
        customer_data = {}
        monthly_data = {}
        product_sales = {}
        
        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            
            customer = order.get('customer', {})
            if isinstance(customer, str):
                try:
                    customer = json.loads(customer)
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
            
            source = order.get('source', 'web')
            if source == 'pos':
                pos_orders_count += 1
            else:
                web_orders_count += 1
            
            customer_name = customer.get('name', 'Unknown') if isinstance(customer, dict) else 'Unknown'
            if customer_name != 'Unknown':
                if customer_name not in customer_data:
                    customer_data[customer_name] = {
                        'name': customer_name,
                        'email': customer.get('email', ''),
                        'phone': customer.get('phone', ''),
                        'orders': 0,
                        'total_spent': 0
                    }
                customer_data[customer_name]['orders'] += 1
                customer_data[customer_name]['total_spent'] += float(order.get('total', 0))
            
            # Monthly tracking
            created_at = order.get('created_at', '')
            month = created_at[:7] if created_at else datetime.utcnow().strftime('%Y-%m')
            if month not in monthly_data:
                monthly_data[month] = {
                    'orders': 0,
                    'items': 0,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0
                }
            monthly_data[month]['orders'] += 1
            
            for item in items:
                product_id = str(item.get('product_id', ''))
                quantity = int(item.get('quantity', 1))
                price = float(item.get('price', 0))
                item_total = float(item.get('total', price * quantity))
                
                product = product_lookup.get(product_id, {})
                cost_price = float(product.get('cost_price', 0)) if product else 0
                item_cost = cost_price * quantity
                
                total_revenue += item_total
                total_cost += item_cost
                total_profit += (item_total - item_cost)
                total_items_sold += quantity
                
                monthly_data[month]['items'] += quantity
                monthly_data[month]['revenue'] += item_total
                monthly_data[month]['cost'] += item_cost
                monthly_data[month]['profit'] += (item_total - item_cost)
                
                product_name = item.get('name', 'Unknown Product')
                if product_name not in product_sales:
                    product_sales[product_name] = {
                        'quantity': 0,
                        'revenue': 0,
                        'cost': 0,
                        'profit': 0
                    }
                product_sales[product_name]['quantity'] += quantity
                product_sales[product_name]['revenue'] += item_total
                product_sales[product_name]['cost'] += item_cost
                product_sales[product_name]['profit'] += (item_total - item_cost)
        
        return {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_orders': total_orders,
            'total_items_sold': total_items_sold,
            'pos_orders_count': pos_orders_count,
            'web_orders_count': web_orders_count,
            'total_customers': len(customer_data),
            'monthly_data': monthly_data,
            'product_sales': product_sales,
            'customer_data': customer_data
        }
    except Exception as e:
        print(f"Error in analytics: {e}")
        traceback.print_exc()
        return {
            'total_revenue': 0,
            'total_cost': 0,
            'total_profit': 0,
            'total_orders': 0,
            'total_items_sold': 0,
            'pos_orders_count': 0,
            'web_orders_count': 0,
            'total_customers': 0,
            'monthly_data': {},
            'product_sales': {},
            'customer_data': {}
        }

# ================================================================
# ===== HELPER FUNCTIONS =====
# ================================================================

def get_category_icon(category):
    icons = {
        'Phones': 'fa-mobile-screen',
        'Laptops': 'fa-laptop',
        'Accessories': 'fa-headphones',
        'Wearables': 'fa-watch',
        'Audio': 'fa-music',
        'Televisions': 'fa-tv',
        'Gaming': 'fa-gamepad',
        'Tablets': 'fa-tablet'
    }
    return icons.get(category, 'fa-box')

def get_all_categories():
    return {
        'Phones': 'fa-mobile-screen',
        'Laptops': 'fa-laptop',
        'Accessories': 'fa-headphones',
        'Wearables': 'fa-watch',
        'Audio': 'fa-music',
        'Televisions': 'fa-tv',
        'Gaming': 'fa-gamepad',
        'Tablets': 'fa-tablet'
    }

# ================================================================
# ===== ROUTES =====
# ================================================================

@app.route('/')
def index():
    try:
        products_list = load_products()
        bundles_list = load_bundles()
        
        products_dict = {}
        for p in products_list:
            if p and 'id' in p:
                products_dict[str(p['id'])] = p
        
        bundles_dict = {}
        for b in bundles_list:
            if b and 'id' in b:
                bundles_dict[str(b['id'])] = b
        
        best_sellers = [p for p in products_list if p.get('badge') == 'Best Seller']
        new_arrivals = [p for p in products_list if p.get('badge') == 'New']
        trending = [p for p in products_list if p.get('badge') == 'Trending']
        
        categories = {}
        for p in products_list:
            cat = p.get('category', 'Other')
            if cat not in categories:
                categories[cat] = {
                    'name': cat,
                    'icon': get_category_icon(cat),
                    'count': 0
                }
            categories[cat]['count'] += 1
        
        return render_template('shop.html',
            products=products_dict,
            all_products=products_dict,
            bundles=bundles_dict,
            best_sellers=best_sellers,
            new_arrivals=new_arrivals,
            trending=trending,
            categories=categories,
            CATEGORIES=get_all_categories()
        )
    except Exception as e:
        print(f"Index error: {e}")
        return render_template('shop.html', products={}, all_products={}, bundles={}, best_sellers=[], new_arrivals=[], trending=[], categories={}, CATEGORIES=get_all_categories())

@app.route('/category/<category_name>')
def category_page(category_name):
    try:
        products = load_products()
        products_dict = {}
        for p in products:
            if p and 'id' in p and p.get('category') == category_name:
                products_dict[str(p['id'])] = p
        return render_template('category.html',
            products=products_dict,
            category_name=category_name,
            CATEGORIES=get_all_categories()
        )
    except Exception as e:
        print(f"Category error: {e}")
        flash('Error loading category', 'danger')
        return redirect(url_for('index'))

@app.route('/product/<product_id>')
def product_detail(product_id):
    try:
        products = load_products()
        product = None
        for p in products:
            if str(p.get('id')) == str(product_id):
                product = p
                break
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('index'))
        
        related = [p for p in products if p.get('category') == product.get('category') and str(p.get('id')) != product_id][:4]
        
        related_dict = {}
        for r in related:
            if r and 'id' in r:
                related_dict[str(r['id'])] = r
        
        return render_template('product.html',
            product=product,
            related=related_dict
        )
    except Exception as e:
        print(f"Product detail error: {e}")
        flash('Error loading product', 'danger')
        return redirect(url_for('index'))

@app.route('/cart')
def cart_page():
    try:
        cart = get_cart()
        cart_items = []
        subtotal = 0
        total_items = 0
        products = load_products()
        bundles = load_bundles()
        
        product_lookup = {str(p.get('id')): p for p in products if p and p.get('id')}
        bundle_lookup = {str(b.get('id')): b for b in bundles if b and b.get('id')}
        
        for item_id, quantity in cart.items():
            if quantity <= 0:
                continue
            
            product = product_lookup.get(str(item_id))
            if product:
                price = float(product.get('price', 0))
                item_total = price * quantity
                cart_items.append({
                    'id': str(item_id),
                    'name': str(product.get('name', 'Product')),
                    'price': price,
                    'image': str(product.get('image', '')),
                    'type': 'product',
                    'quantity': quantity,
                    'item_total': item_total,
                    'stock': int(product.get('stock', 0)),
                    'description': str(product.get('description', '')),
                    'specs': product.get('specs', [])
                })
                subtotal += item_total
                total_items += quantity
                continue
            
            bundle = bundle_lookup.get(str(item_id))
            if bundle:
                price = float(bundle.get('price', 0))
                item_total = price * quantity
                cart_items.append({
                    'id': str(item_id),
                    'name': str(bundle.get('name', 'Bundle')),
                    'price': price,
                    'image': str(bundle.get('image', '')),
                    'type': 'bundle',
                    'quantity': quantity,
                    'item_total': item_total,
                    'products': bundle.get('products', [])
                })
                subtotal += item_total
                total_items += quantity
        
        shipping = 0 if subtotal >= 50000 else 800
        total = subtotal + shipping
        
        return render_template('cart.html',
            cart_items=cart_items,
            subtotal=subtotal,
            shipping=shipping,
            total=total,
            total_items=total_items
        )
    except Exception as e:
        print(f"Cart error: {e}")
        traceback.print_exc()
        flash('Error loading cart', 'danger')
        return redirect(url_for('index'))

@app.route('/add-to-cart/<item_id>', methods=['POST'])
def add_to_cart(item_id):
    """Add item to cart - returns JSON"""
    try:
        cart = get_cart()
        products = load_products()
        bundles = load_bundles()
        
        product = None
        for p in products:
            if str(p.get('id')) == str(item_id):
                product = p
                break
        
        if product:
            current_qty = cart.get(item_id, 0)
            if current_qty >= product.get('stock', 0):
                return jsonify({
                    'success': False,
                    'message': 'Not enough stock available!'
                })
        
        bundle_exists = False
        for b in bundles:
            if str(b.get('id')) == str(item_id):
                bundle_exists = True
                break
        
        if not product and not bundle_exists:
            return jsonify({
                'success': False, 
                'message': 'Item not found'
            })
        
        cart[item_id] = cart.get(item_id, 0) + 1
        session['cart'] = cart
        session.modified = True
        
        total_items = sum(cart.values())
        
        return jsonify({
            'success': True,
            'message': 'Added to cart!',
            'count': total_items,
            'quantity': cart[item_id]
        })
        
    except Exception as e:
        print(f"Error adding to cart: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/update-cart/<item_id>/<action>', methods=['POST'])
def update_cart_item(item_id, action):
    try:
        cart = get_cart()
        products = load_products()
        bundles = load_bundles()
        
        product_lookup = {str(p.get('id')): p for p in products if p and p.get('id')}
        bundle_lookup = {str(b.get('id')): b for b in bundles if b and b.get('id')}
        
        if action == 'increase':
            product = product_lookup.get(str(item_id))
            if product:
                current = cart.get(item_id, 0)
                if current >= product.get('stock', 0):
                    return jsonify({
                        'success': False,
                        'message': 'Not enough stock available!'
                    })
            
            cart[item_id] = cart.get(item_id, 0) + 1
            
        elif action == 'decrease':
            if item_id in cart:
                if cart[item_id] <= 1:
                    del cart[item_id]
                else:
                    cart[item_id] -= 1
            else:
                return jsonify({'success': False, 'message': 'Item not in cart'})
        
        elif action == 'remove':
            if item_id in cart:
                del cart[item_id]
            else:
                return jsonify({'success': False, 'message': 'Item not in cart'})
        else:
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        session['cart'] = cart
        session.modified = True
        
        subtotal = 0
        for iid, qty in cart.items():
            product = product_lookup.get(str(iid))
            if product:
                subtotal += float(product.get('price', 0)) * qty
            else:
                bundle = bundle_lookup.get(str(iid))
                if bundle:
                    subtotal += float(bundle.get('price', 0)) * qty
        
        shipping = 0 if subtotal >= 50000 else 800
        total = subtotal + shipping
        
        item_price = 0
        product = product_lookup.get(str(item_id))
        if product:
            item_price = float(product.get('price', 0))
        else:
            bundle = bundle_lookup.get(str(item_id))
            if bundle:
                item_price = float(bundle.get('price', 0))
        
        return jsonify({
            'success': True,
            'quantity': cart.get(item_id, 0) if item_id in cart else 0,
            'subtotal': subtotal,
            'shipping': shipping,
            'total': total,
            'total_items': sum(cart.values()),
            'item_total': item_price * cart.get(item_id, 0) if item_id in cart else 0
        })
    except Exception as e:
        print(f"Error updating cart: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/remove-from-cart/<item_id>', methods=['POST'])
def remove_from_cart(item_id):
    try:
        cart = get_cart()
        if item_id in cart:
            del cart[item_id]
            session['cart'] = cart
            session.modified = True
            return jsonify({
                'success': True,
                'message': 'Removed from cart!',
                'count': sum(cart.values())
            })
        return jsonify({'success': False, 'message': 'Item not in cart'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/checkout')
def checkout_page():
    try:
        cart = get_cart()
        if not cart:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('index'))
        
        cart_items = []
        subtotal = 0
        total_items = 0
        products = load_products()
        bundles = load_bundles()
        
        product_lookup = {str(p.get('id')): p for p in products if p and p.get('id')}
        bundle_lookup = {str(b.get('id')): b for b in bundles if b and b.get('id')}
        
        for item_id, quantity in cart.items():
            if quantity <= 0:
                continue
            
            product = product_lookup.get(str(item_id))
            if product:
                price = float(product.get('price', 0))
                item_total = price * quantity
                cart_items.append({
                    'id': item_id,
                    'name': product.get('name', 'Product'),
                    'price': price,
                    'image': product.get('image', ''),
                    'type': 'product',
                    'quantity': quantity,
                    'item_total': item_total
                })
                subtotal += item_total
                total_items += quantity
                continue
            
            bundle = bundle_lookup.get(str(item_id))
            if bundle:
                price = float(bundle.get('price', 0))
                item_total = price * quantity
                cart_items.append({
                    'id': item_id,
                    'name': bundle.get('name', 'Bundle'),
                    'price': price,
                    'image': bundle.get('image', ''),
                    'type': 'bundle',
                    'quantity': quantity,
                    'item_total': item_total
                })
                subtotal += item_total
                total_items += quantity
        
        shipping = 0 if subtotal >= 50000 else 800
        total = subtotal + shipping
        
        return render_template('checkout.html',
            cart_items=cart_items,
            subtotal=subtotal,
            shipping=shipping,
            total=total,
            total_items=total_items
        )
    except Exception as e:
        print(f"Checkout error: {e}")
        traceback.print_exc()
        flash('Error loading checkout', 'danger')
        return redirect(url_for('index'))

@app.route('/place-order', methods=['POST'])
def place_order():
    try:
        cart = get_cart()
        if not cart:
            return jsonify({'success': False, 'message': 'Cart is empty'})
        
        if request.is_json:
            data = request.get_json()
        else:
            data = {
                'customer_name': request.form.get('customer_name', 'Customer'),
                'customer_email': request.form.get('customer_email', 'customer@example.com'),
                'customer_phone': request.form.get('customer_phone', 'N/A'),
                'customer_address': request.form.get('customer_address', 'N/A')
            }
        
        if not data.get('customer_name') or data.get('customer_name') == 'Customer':
            return jsonify({'success': False, 'message': 'Please enter your name'}), 400
        
        subtotal = 0
        products = load_products()
        bundles = load_bundles()
        product_lookup = {str(p.get('id')): p for p in products if p and p.get('id')}
        bundle_lookup = {str(b.get('id')): b for b in bundles if b and b.get('id')}
        order_items = []
        
        for item_id, quantity in cart.items():
            if quantity <= 0:
                continue
                
            product = product_lookup.get(str(item_id))
            if product:
                current_stock = int(product.get('stock', 0))
                if current_stock < quantity:
                    return jsonify({
                        'success': False,
                        'message': f'Not enough stock for {product.get("name")}. Available: {current_stock}'
                    }), 400
                
                price = float(product.get('price', 0))
                item_total = price * quantity
                subtotal += item_total
                order_items.append({
                    'product_id': item_id,
                    'name': product.get('name', 'Product'),
                    'price': price,
                    'quantity': quantity,
                    'total': item_total,
                    'type': 'product'
                })
                
                new_stock = max(0, current_stock - quantity)
                update_product_stock(item_id, new_stock)
                continue
            
            bundle = bundle_lookup.get(str(item_id))
            if bundle:
                price = float(bundle.get('price', 0))
                item_total = price * quantity
                subtotal += item_total
                order_items.append({
                    'product_id': item_id,
                    'name': bundle.get('name', 'Bundle'),
                    'price': price,
                    'quantity': quantity,
                    'total': item_total,
                    'type': 'bundle'
                })
        
        if not order_items:
            return jsonify({'success': False, 'message': 'No valid items in cart'}), 400
        
        shipping = 0 if subtotal >= 50000 else 800
        total = subtotal + shipping
        
        order_id = f"ELEC-{uuid.uuid4().hex[:8].upper()}"
        
        customer_name = data.get('customer_name', 'Customer').strip()
        customer_email = data.get('customer_email', 'customer@example.com').strip()
        customer_phone = data.get('customer_phone', 'N/A').strip()
        customer_address = data.get('customer_address', 'N/A').strip()
        
        order_data = {
            'order_id': order_id,
            'items': order_items,
            'subtotal': subtotal,
            'shipping': shipping,
            'total': total,
            'status': 'pending',
            'source': 'web',
            'created_at': datetime.utcnow().isoformat(),
            'customer': {
                'name': customer_name,
                'email': customer_email,
                'phone': customer_phone,
                'address': customer_address
            }
        }
        
        if save_order_to_supabase(order_data):
            session['cart'] = {}
            session.modified = True
            
            return jsonify({
                'success': True,
                'order_id': order_id,
                'total': total,
                'message': 'Order placed successfully!'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to save order. Please try again.'}), 500
            
    except Exception as e:
        print(f"Error placing order: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/order-confirmation/<order_id>')
def order_confirmation(order_id):
    return render_template('confirmation.html', order_id=order_id)

@app.route('/clear-cart', methods=['POST'])
def clear_cart():
    session['cart'] = {}
    session.modified = True
    return jsonify({'success': True, 'message': 'Cart cleared'})

# ================================================================
# ===== API ROUTES =====
# ================================================================

@app.route('/api/status')
def api_status():
    try:
        orders = load_orders()
        products = load_products()
        json_data = load_json_data()
        queue_size = len(json_data.get('order_queue', []))
        
        return jsonify({
            'success': True,
            'products': len(products),
            'orders': len(orders),
            'queue_size': queue_size,
            'is_online': has_internet(),
            'timestamp': datetime.utcnow().isoformat(),
            'environment': 'vercel' if IS_VERCEL else 'local'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/products')
def api_products():
    try:
        return jsonify(load_products())
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/products/<product_id>')
def api_product_detail(product_id):
    """Get single product by ID"""
    try:
        products = load_products()
        for p in products:
            if str(p.get('id')) == str(product_id):
                return jsonify(p)
        return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def api_orders():
    try:
        return jsonify(load_orders())
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/orders/<order_id>')
def api_order_detail(order_id):
    """Get single order by ID"""
    try:
        orders = load_orders()
        for o in orders:
            if str(o.get('order_id')) == str(order_id):
                return jsonify(o)
        return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cart-count', methods=['GET'])
def cart_count():
    try:
        cart = get_cart()
        count = sum(cart.values()) if cart and isinstance(cart, dict) else 0
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'count': 0})

# ================================================================
# ===== ADMIN ROUTES =====
# ================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'electronics2026':
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login first', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        products = load_products()
        orders = load_orders()
        bundles = load_bundles()
        cart = get_cart()
        analytics = get_sales_analytics()
        
        # Build customer list
        customer_list = {}
        pos_count = 0
        web_count = 0
        
        for order in orders:
            customer = order.get('customer', {})
            if isinstance(customer, str):
                try:
                    customer = json.loads(customer)
                except:
                    customer = {}
            if isinstance(customer, list):
                customer = customer[0] if customer else {}
            if not isinstance(customer, dict):
                customer = {}
            
            source = order.get('source', 'web')
            if source == 'pos':
                pos_count += 1
            else:
                web_count += 1
            
            name = customer.get('name', 'Unknown') if isinstance(customer, dict) else 'Unknown'
            if name and name != 'Unknown':
                if name not in customer_list:
                    customer_list[name] = {
                        'name': name,
                        'email': customer.get('email', '') if isinstance(customer, dict) else '',
                        'phone': customer.get('phone', '') if isinstance(customer, dict) else '',
                        'orders': 0,
                        'total_spent': 0
                    }
                customer_list[name]['orders'] += 1
                customer_list[name]['total_spent'] += float(order.get('total', 0))
        
        customers = list(customer_list.values())
        customers.sort(key=lambda x: x['orders'], reverse=True)
        
        json_data = load_json_data()
        queue_size = len(json_data.get('order_queue', []))
        
        stats = {
            'total_products': len(products),
            'total_bundles': len(bundles),
            'total_cart_items': sum(cart.values()) if cart else 0,
            'low_stock': len([p for p in products if p.get('stock', 0) < 10]),
            'total_orders': len(orders),
            'pending_orders': len([o for o in orders if o.get('status') == 'pending']),
            'pos_orders': pos_count,
            'web_orders': web_count,
            'total_revenue': analytics.get('total_revenue', 0),
            'total_profit': analytics.get('total_profit', 0),
            'total_items_sold': analytics.get('total_items_sold', 0),
            'total_customers': len(customers),
            'db_mode': 'online' if has_internet() else 'offline',
            'queue_size': queue_size
        }
        
        return render_template('admin.html',
            products=products,
            bundles=bundles,
            orders=orders,
            customers=customers,
            stats=stats,
            pos_count=pos_count,
            analytics=analytics,
            DB_CONNECTED=has_internet(),
            uuid=uuid
        )
        
    except Exception as e:
        print(f"Admin dashboard error: {e}")
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
                'total_profit': 0,
                'total_items_sold': 0,
                'total_customers': 0,
                'db_mode': 'offline'
            },
            DB_CONNECTED=False,
            uuid=uuid
        )

@app.route('/admin/pos')
def admin_pos():
    if not session.get('admin_logged_in'):
        flash('Please login first', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        products = load_products()
        
        # Ensure all products have required POS fields
        for product in products:
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
        
        orders = load_orders()
        customer_list = {}
        for order in orders:
            customer = order.get('customer', {})
            if isinstance(customer, str):
                try:
                    customer = json.loads(customer)
                except:
                    customer = {}
            if isinstance(customer, list):
                customer = customer[0] if customer else {}
            if not isinstance(customer, dict):
                customer = {}
            
            name = customer.get('name', 'Unknown') if isinstance(customer, dict) else 'Unknown'
            if name and name != 'Unknown':
                if name not in customer_list:
                    customer_list[name] = {
                        'name': name,
                        'email': customer.get('email', '') if isinstance(customer, dict) else '',
                        'phone': customer.get('phone', '') if isinstance(customer, dict) else '',
                        'orders': 0,
                        'total_spent': 0
                    }
                customer_list[name]['orders'] += 1
                customer_list[name]['total_spent'] += float(order.get('total', 0))
        
        customers = list(customer_list.values())
        customers.sort(key=lambda x: x['orders'], reverse=True)
        
        return render_template('pos.html',
            products=products,
            customers=customers,
            DB_CONNECTED=has_internet()
        )
    except Exception as e:
        print(f"POS error: {e}")
        flash('Error loading POS', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/pos/place-order', methods=['POST'])
def admin_pos_place_order():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        if not data or not data.get('items'):
            return jsonify({'success': False, 'message': 'No items in order'}), 400
        
        order_id = f"POS-{uuid.uuid4().hex[:8].upper()}"
        
        # Update stock for products (only if online)
        if has_internet():
            products = load_products()
            product_lookup = {str(p.get('id')): p for p in products}
            
            for item in data.get('items', []):
                product_id = str(item.get('product_id'))
                quantity = int(item.get('quantity', 1))
                product = product_lookup.get(product_id)
                if product:
                    current_stock = int(product.get('stock', 0))
                    if current_stock < quantity:
                        return jsonify({
                            'success': False,
                            'message': f'Not enough stock for {product.get("name")}. Available: {current_stock}'
                        }), 400
                    new_stock = max(0, current_stock - quantity)
                    update_product_stock(product_id, new_stock)
        
        order_data = {
            'order_id': order_id,
            'items': data.get('items', []),
            'subtotal': float(data.get('subtotal', 0)),
            'shipping': float(data.get('shipping', 0)),
            'total': float(data.get('total', 0)),
            'status': 'confirmed',
            'source': 'pos',
            'created_at': datetime.utcnow().isoformat(),
            'customer': {
                'name': data.get('customer_name', 'Walk-in Customer'),
                'email': data.get('customer_email', 'walkin@example.com'),
                'phone': data.get('customer_phone', 'N/A'),
                'address': data.get('customer_address', 'In-store purchase')
            }
        }
        
        if save_order_to_supabase(order_data):
            analytics = get_sales_analytics()
            
            return jsonify({
                'success': True,
                'order_id': order_id,
                'message': 'Order placed successfully!' + (' (Offline - will sync later)' if not has_internet() else ''),
                'offline': not has_internet(),
                'analytics': analytics,
                'stats': {
                    'total_revenue': analytics.get('total_revenue', 0),
                    'total_profit': analytics.get('total_profit', 0),
                    'total_orders': analytics.get('total_orders', 0),
                    'total_items_sold': analytics.get('total_items_sold', 0),
                    'pos_orders_count': analytics.get('pos_orders_count', 0),
                    'web_orders_count': analytics.get('web_orders_count', 0)
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to save order'}), 500
            
    except Exception as e:
        print(f"POS Order error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

# ================================================================
# ===== ADMIN API ROUTES =====
# ================================================================

@app.route('/admin/api/notifications')
def admin_api_notifications():
    """Get notifications for admin"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        orders = load_orders()
        pending = [o for o in orders if o.get('status') == 'pending']
        pending_count = len(pending)
        
        notifications = []
        if pending_count > 0:
            notifications.append({
                'icon': '📦',
                'title': f'{pending_count} pending orders',
                'time': 'Just now'
            })
        
        products = load_products()
        low_stock = [p for p in products if p.get('stock', 0) < 5]
        if low_stock:
            notifications.append({
                'icon': '⚠️',
                'title': f'{len(low_stock)} products low in stock',
                'time': 'Just now'
            })
        
        # Check for queued orders (offline)
        json_data = load_json_data()
        queue_size = len(json_data.get('order_queue', []))
        if queue_size > 0:
            notifications.append({
                'icon': '📴',
                'title': f'{queue_size} orders waiting to sync',
                'time': 'Queued offline'
            })
        
        return jsonify({
            'count': len(notifications),
            'notifications': notifications
        })
    except Exception as e:
        return jsonify({'count': 0, 'notifications': []})

@app.route('/admin/api/top-products')
def admin_api_top_products():
    """Get top selling products"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        orders = load_orders()
        product_sales = {}
        
        for order in orders:
            if order.get('status') == 'cancelled':
                continue
            
            items = order.get('items', [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except:
                    items = []
            if not isinstance(items, list):
                items = []
            
            for item in items:
                name = item.get('name', 'Unknown')
                revenue = float(item.get('total', 0))
                if name not in product_sales:
                    product_sales[name] = 0
                product_sales[name] += revenue
        
        sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return jsonify({
            'products': [{'rank': i+1, 'name': name, 'revenue': revenue} for i, (name, revenue) in enumerate(sorted_products)]
        })
    except Exception as e:
        return jsonify({'products': []})

@app.route('/admin/api/analytics')
def admin_api_analytics():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        analytics = get_sales_analytics()
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/revenue')
def admin_api_revenue():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        analytics = get_sales_analytics()
        return jsonify({
            'total_revenue': analytics.get('total_revenue', 0),
            'total_profit': analytics.get('total_profit', 0),
            'total_orders': analytics.get('total_orders', 0),
            'total_items_sold': analytics.get('total_items_sold', 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/upload-image', methods=['POST'])
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
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        image_url = f"/static/uploads/{filename}"
        return jsonify({
            'success': True, 
            'url': image_url,
            'message': 'Image uploaded successfully!'
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

@app.route('/admin/products', methods=['POST'])
def admin_products():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        product_data = {
            'id': request.form.get('id'),
            'name': request.form.get('name'),
            'price': float(request.form.get('price', 0)),
            'cost_price': float(request.form.get('cost_price', 0)) or 0,
            'image': request.form.get('image'),
            'category': request.form.get('category'),
            'description': request.form.get('description'),
            'rating': float(request.form.get('rating', 4.0)),
            'reviews': int(request.form.get('reviews', 0)),
            'badge': request.form.get('badge', ''),
            'stock': int(request.form.get('stock', 0)),
            'original_price': float(request.form.get('original_price', 0)) or None,
            'specs': request.form.get('specs', '').split(',') if request.form.get('specs') else []
        }
        
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/products",
            headers=SUPABASE_HEADERS,
            json=product_data,
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            # Update local cache
            products = load_products()
            json_data = load_json_data()
            json_data['products'] = products
            save_json_data(json_data)
            return jsonify({'success': True, 'message': 'Product saved successfully!', 'product': product_data})
        else:
            return jsonify({'success': False, 'message': 'Error saving product'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/products/<product_id>', methods=['DELETE'])
def admin_delete_product(product_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        response = requests.delete(
            f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=SUPABASE_HEADERS,
            timeout=5
        )
        if response.status_code in [200, 204]:
            # Update local cache
            products = load_products()
            json_data = load_json_data()
            json_data['products'] = products
            save_json_data(json_data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Failed to delete'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/orders/<order_id>/status', methods=['POST'])
def admin_update_order_status(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        new_status = request.json.get('status')
        if not new_status:
            return jsonify({'success': False, 'message': 'Status required'}), 400
        
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/orders?order_id=eq.{order_id}",
            headers=SUPABASE_HEADERS,
            json={'status': new_status},
            timeout=5
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Failed to update status'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ================================================================
# ===== SYNC STATUS ROUTES =====
# ================================================================

@app.route('/api/sync-status')
def sync_status():
    """Check sync status"""
    try:
        json_data = load_json_data()
        queue_size = len(json_data.get('order_queue', []))
        
        return jsonify({
            'has_internet': has_internet(),
            'queued_orders': queue_size,
            'is_offline': not has_internet(),
            'message': 'Working offline' if not has_internet() else 'Connected to Supabase'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/force-sync')
def force_sync():
    """Manually trigger sync"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        products_synced = sync_products_from_supabase()
        orders_synced = sync_queued_orders()
        
        return jsonify({
            'success': True,
            'products_synced': products_synced,
            'orders_synced': orders_synced,
            'message': 'Sync completed'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ================================================================
# ===== DEBUG ROUTES =====
# ================================================================

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Server is running',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/debug')
def debug():
    """Check data in Supabase"""
    try:
        orders = load_orders()
        products = load_products()
        bundles = load_bundles()
        json_data = load_json_data()
        
        return jsonify({
            'orders_count': len(orders),
            'products_count': len(products),
            'bundles_count': len(bundles),
            'queue_size': len(json_data.get('order_queue', [])),
            'is_online': has_internet(),
            'sample_order': orders[0] if orders else None,
            'sample_product': products[0] if products else None,
            'is_vercel': IS_VERCEL
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/test-data')
def test_data():
    """Test data loading"""
    try:
        orders = load_orders()
        products = load_products()
        analytics = get_sales_analytics()
        
        return jsonify({
            'success': True,
            'orders_count': len(orders),
            'products_count': len(products),
            'revenue': analytics.get('total_revenue', 0),
            'customers': analytics.get('total_customers', 0),
            'sample_order': orders[0] if orders else None
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/test-add-to-cart/<item_id>')
def test_add_to_cart(item_id):
    """Test the add to cart functionality"""
    try:
        cart = get_cart()
        products = load_products()
        
        product = None
        for p in products:
            if str(p.get('id')) == str(item_id):
                product = p
                break
        
        return jsonify({
            'item_id': item_id,
            'product_found': product is not None,
            'product': product,
            'current_cart': cart,
            'session_cart': session.get('cart', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/load-sample-data', methods=['GET', 'POST'])
def load_sample_data():
    """Load sample products into Supabase for testing"""
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
                'badge': 'Best Seller'
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
                'badge': 'New'
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
                'badge': 'Trending'
            },
            {
                'id': 'samsung_s24',
                'name': 'Samsung Galaxy S24 Ultra',
                'price': 165000.0,
                'cost_price': 115000.0,
                'category': 'Phones',
                'description': 'Flagship Android phone with advanced camera',
                'image': 'https://images.unsplash.com/photo-1511707267537-b85faf00021e?w=500',
                'stock': 20,
                'rating': 4.6,
                'reviews': 234
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
                'badge': 'New'
            }
        ]
        
        added = 0
        errors = []
        
        if has_internet():
            for product in sample_products:
                try:
                    response = requests.post(
                        f"{SUPABASE_URL}/rest/v1/products",
                        headers=SUPABASE_HEADERS,
                        json=product,
                        timeout=5
                    )
                    if response.status_code in [200, 201]:
                        added += 1
                    else:
                        errors.append(f"{product['name']}: {response.status_code}")
                except Exception as e:
                    errors.append(f"{product['name']}: {str(e)}")
            
            # Update cache
            if added > 0:
                sync_products_from_supabase()
        else:
            # Save to JSON directly (offline)
            json_data = load_json_data()
            json_data['products'] = sample_products
            save_json_data(json_data)
            added = len(sample_products)
        
        return jsonify({
            'success': True,
            'added': added,
            'total': len(sample_products),
            'errors': errors,
            'message': f'Loaded {added}/{len(sample_products)} sample products' + (' (offline)' if not has_internet() else '')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/debug-products')
def debug_products():
    """Show all products with detailed info"""
    try:
        products = load_products()
        
        if not products:
            return jsonify({
                'success': False,
                'error': 'No products loaded',
                'message': 'Database may be empty. Try /load-sample-data'
            })
        
        product_list = []
        for p in products:
            product_list.append({
                'id': p.get('id'),
                'name': p.get('name'),
                'price': p.get('price'),
                'stock': p.get('stock'),
                'category': p.get('category'),
                'has_image': bool(p.get('image'))
            })
        
        return jsonify({
            'success': True,
            'total_products': len(products),
            'products': product_list,
            'sample': products[0] if products else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ================================================================
# ===== RUN APP =====
# ================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("📱 PRICE POINT - Premium Electronics Shop")
    print("="*60)
    print(f"🌍 Environment: {'Vercel' if IS_VERCEL else 'Local'}")
    print(f"📶 Internet: {'Connected' if has_internet() else 'Offline'}")
    
    orders = load_orders()
    products = load_products()
    print(f"\n📊 Products: {len(products) if products else 0}")
    print(f"📊 Orders: {len(orders) if orders else 0}")
    
    json_data = load_json_data()
    queue_size = len(json_data.get('order_queue', []))
    if queue_size > 0:
        print(f"📦 Queued orders: {queue_size} (will sync when internet returns)")
    
    print("="*60)
    print("\n🚀 Starting server...")
    print("📍 http://localhost:5000")
    print("🔑 Login: admin / electronics2026")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)