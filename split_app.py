# split_app.py - Run this once to split your app
import os
import shutil

# Create folders
folders = ['routes', 'models', 'utils']
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, '__init__.py'), 'w') as f:
        f.write('# Package initialization\n')

print("✅ Folders created")

# Create the files with basic content
# You'll copy your code into these files
files = {
    'routes/main.py': '''# routes/main.py
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from models.product import load_products, get_product
from models.order import load_orders, save_order
from utils.helpers import get_cart, get_category_icon, get_all_categories, format_price

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Your index code here
    products = load_products()
    return render_template('shop.html', products=products)

# Add your other routes here
''',
    'routes/admin.py': '''# routes/admin.py
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from models.product import load_products, add_product, delete_product, update_product_stock
from models.order import load_orders, update_order_status
from utils.analytics import get_sales_analytics
from utils.helpers import get_cart

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def dashboard():
    # Your admin dashboard code here
    products = load_products()
    orders = load_orders()
    return render_template('admin.html', products=products, orders=orders)

# Add your other admin routes here
''',
    'routes/api.py': '''# routes/api.py
from flask import Blueprint, jsonify
from models.product import load_products, get_product
from models.order import load_orders

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/status')
def status():
    # Your status API here
    products = load_products()
    orders = load_orders()
    return jsonify({'products': len(products), 'orders': len(orders)})

# Add your other API routes here
''',
    'models/product.py': '''# models/product.py
import requests
import json
from flask import current_app

def load_products():
    """Load products from Supabase"""
    try:
        response = requests.get(
            f"{current_app.config['SUPABASE_URL']}/rest/v1/products?select=*",
            headers=current_app.config['SUPABASE_HEADERS'],
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
        return []
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

def get_product(product_id):
    """Get single product by ID"""
    products = load_products()
    for p in products:
        if str(p.get('id')) == str(product_id):
            return p
    return None

def update_product_stock(product_id, new_stock):
    """Update product stock in Supabase"""
    try:
        response = requests.patch(
            f"{current_app.config['SUPABASE_URL']}/rest/v1/products?id=eq.{product_id}",
            headers=current_app.config['SUPABASE_HEADERS'],
            json={'stock': int(new_stock)},
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Error updating stock: {e}")
        return False
''',
    'models/order.py': '''# models/order.py
import requests
import json
from datetime import datetime
from flask import current_app

def load_orders():
    """Load orders from Supabase"""
    try:
        response = requests.get(
            f"{current_app.config['SUPABASE_URL']}/rest/v1/orders?select=*&order=created_at.desc",
            headers=current_app.config['SUPABASE_HEADERS'],
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
                return data
        return []
    except Exception as e:
        print(f"Error loading orders: {e}")
        return []

def save_order(order_data):
    """Save order to Supabase"""
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
            f"{current_app.config['SUPABASE_URL']}/rest/v1/orders",
            headers=current_app.config['SUPABASE_HEADERS'],
            json=supabase_order,
            timeout=10
        )
        return response.status_code in [200, 201, 204]
    except Exception as e:
        print(f"Error saving order: {e}")
        return False
''',
    'utils/helpers.py': '''# utils/helpers.py
from flask import session

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
''',
    'utils/analytics.py': '''# utils/analytics.py
from models.product import load_products
from models.order import load_orders
import json
from datetime import datetime

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
'''
}

for filepath, content in files.items():
    # Create directories if needed
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"✅ Created {filepath}")

print("\n✅ All files created!")
print("\n📝 Next steps:")
print("1. Copy your code from app.py into the new files")
print("2. Replace the placeholder functions with your actual code")
print("3. Update app.py with the new version")