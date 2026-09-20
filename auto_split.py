# auto_split.py - Run this to automatically split your app.py
import os
import re
import shutil

def read_app_py():
    """Read the original app.py file"""
    try:
        with open('app.py', 'r') as f:
            return f.read()
    except FileNotFoundError:
        print("❌ app.py not found! Make sure you're in the right directory.")
        return None

def find_functions(content, function_names):
    """Find specific functions in the content"""
    functions = {}
    for name in function_names:
        # Find function definition
        pattern = rf'def {name}\(.*?\):.*?(?=\ndef |\nclass |\n@app\.route|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            functions[name] = match.group(0)
    return functions

def find_routes(content, route_prefix=''):
    """Find all route functions"""
    route_pattern = r'@app\.route\([\'"](.*?)[\'"](.*?)\).*?def (.*?)\(.*?\):.*?(?=@app\.route|\ndef |\nclass |\Z)'
    routes = re.findall(route_pattern, content, re.DOTALL)
    return routes

def create_models_py(content):
    """Create models/product.py and models/order.py"""
    
    # Create models folder
    os.makedirs('models', exist_ok=True)
    
    # Create __init__.py
    with open('models/__init__.py', 'w') as f:
        f.write('# Package initialization\n')
    
    # Find product-related functions
    product_functions = ['load_products', 'load_bundles', 'update_product_stock', 'get_product']
    product_funcs = find_functions(content, product_functions)
    
    # Find order-related functions
    order_functions = ['load_orders', 'save_order_to_supabase', 'save_order']
    order_funcs = find_functions(content, order_functions)
    
    # Write models/product.py
    product_content = '''# models/product.py
import requests
import json
import uuid
from flask import current_app

'''
    for name, func in product_funcs.items():
        product_content += func + '\n\n'
    
    with open('models/product.py', 'w') as f:
        f.write(product_content)
    print("✅ Created models/product.py")
    
    # Write models/order.py
    order_content = '''# models/order.py
import requests
import json
from datetime import datetime
from flask import current_app

'''
    for name, func in order_funcs.items():
        order_content += func + '\n\n'
    
    with open('models/order.py', 'w') as f:
        f.write(order_content)
    print("✅ Created models/order.py")

def create_utils_py(content):
    """Create utils/helpers.py and utils/analytics.py"""
    
    os.makedirs('utils', exist_ok=True)
    
    with open('utils/__init__.py', 'w') as f:
        f.write('# Package initialization\n')
    
    # Helper functions
    helper_functions = ['get_cart', 'get_category_icon', 'get_all_categories', 'allowed_file']
    helper_funcs = find_functions(content, helper_functions)
    
    helper_content = '''# utils/helpers.py
from flask import session

'''
    for name, func in helper_funcs.items():
        helper_content += func + '\n\n'
    
    with open('utils/helpers.py', 'w') as f:
        f.write(helper_content)
    print("✅ Created utils/helpers.py")
    
    # Analytics function
    analytics_func = find_functions(content, ['get_sales_analytics'])
    
    analytics_content = '''# utils/analytics.py
from models.product import load_products
from models.order import load_orders
import json
from datetime import datetime

'''
    for name, func in analytics_func.items():
        analytics_content += func + '\n\n'
    
    with open('utils/analytics.py', 'w') as f:
        f.write(analytics_content)
    print("✅ Created utils/analytics.py")

def create_routes_py(content):
    """Create routes/main.py, routes/admin.py, routes/api.py"""
    
    os.makedirs('routes', exist_ok=True)
    
    with open('routes/__init__.py', 'w') as f:
        f.write('# Package initialization\n')
    
    # Find all routes
    route_pattern = r'@app\.route\([\'"](.*?)[\'"](.*?)\).*?def (.*?)\(.*?\):.*?(?=@app\.route|\ndef |\nclass |\Z)'
    all_routes = re.findall(route_pattern, content, re.DOTALL)
    
    # Categorize routes
    main_routes = []
    admin_routes = []
    api_routes = []
    
    for route_url, route_options, func_name in all_routes:
        route_code = f'''@main_bp.route('{route_url}'{route_options})
def {func_name}():
{content[content.index(func_name):].split('def ')[0]}
'''
        if '/admin' in route_url:
            admin_routes.append((route_url, route_options, func_name))
        elif '/api' in route_url:
            api_routes.append((route_url, route_options, func_name))
        else:
            main_routes.append((route_url, route_options, func_name))
    
    # Find the actual function bodies
    def get_function_body(func_name):
        pattern = rf'def {func_name}\(.*?\):.*?(?=\ndef |\nclass |\n@app\.route|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(0) if match else ''
    
    # Write routes/main.py
    main_content = '''# routes/main.py
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from models.product import load_products, load_bundles, update_product_stock
from models.order import load_orders, save_order_to_supabase
from utils.helpers import get_cart, get_category_icon, get_all_categories

main_bp = Blueprint('main', __name__)

'''
    for route_url, route_options, func_name in main_routes:
        func_body = get_function_body(func_name)
        if func_body:
            # Replace @app.route with @main_bp.route
            func_body = func_body.replace(f"@app.route('{route_url}'", f"@main_bp.route('{route_url}'")
            main_content += func_body + '\n\n'
    
    with open('routes/main.py', 'w') as f:
        f.write(main_content)
    print(f"✅ Created routes/main.py ({len(main_routes)} routes)")
    
    # Write routes/admin.py
    admin_content = '''# routes/admin.py
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from models.product import load_products, load_bundles, update_product_stock
from models.order import load_orders, save_order_to_supabase, update_order_status
from utils.analytics import get_sales_analytics
from utils.helpers import get_cart
import uuid
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

'''
    for route_url, route_options, func_name in admin_routes:
        func_body = get_function_body(func_name)
        if func_body:
            # Replace @app.route with @admin_bp.route
            func_body = func_body.replace(f"@app.route('{route_url}'", f"@admin_bp.route('{route_url}'")
            admin_content += func_body + '\n\n'
    
    with open('routes/admin.py', 'w') as f:
        f.write(admin_content)
    print(f"✅ Created routes/admin.py ({len(admin_routes)} routes)")
    
    # Write routes/api.py
    api_content = '''# routes/api.py
from flask import Blueprint, jsonify
from models.product import load_products
from models.order import load_orders
from utils.helpers import get_cart
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')

'''
    for route_url, route_options, func_name in api_routes:
        func_body = get_function_body(func_name)
        if func_body:
            # Replace @app.route with @api_bp.route
            func_body = func_body.replace(f"@app.route('{route_url}'", f"@api_bp.route('{route_url}'")
            api_content += func_body + '\n\n'
    
    with open('routes/api.py', 'w') as f:
        f.write(api_content)
    print(f"✅ Created routes/api.py ({len(api_routes)} routes)")

def create_new_app_py():
    """Create the new app.py"""
    
    new_app_py = '''# app.py - NEW VERSION (Split)
from flask import Flask, request, jsonify, render_template, traceback
from datetime import timedelta
import os
import uuid

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

def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = 'allison-electronics-secret-2026'
    app.permanent_session_lifetime = timedelta(days=7)
    
    # Store config in app for other modules
    app.config['SUPABASE_URL'] = SUPABASE_URL
    app.config['SUPABASE_KEY'] = SUPABASE_KEY
    app.config['SUPABASE_HEADERS'] = SUPABASE_HEADERS
    app.config['IS_VERCEL'] = IS_VERCEL
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
    
    # Template filter
    @app.template_filter('format_number')
    def format_number_filter(value):
        """Format number with commas"""
        try:
            if value is None:
                return "0"
            return f"{int(float(value)):,}"
        except (ValueError, TypeError):
            return "0"
    
    # Error handlers
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
    
    # Register blueprints
    from routes.main import main_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    
    # Make folders
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(STATIC_FOLDER, exist_ok=True)
    except:
        pass
    
    return app

# Create app instance
app = create_app()

# For Vercel
application = app

if __name__ == '__main__':
    from models.product import load_products
    from models.order import load_orders
    
    print("\\n" + "="*60)
    print("📱 PRICE POINT - Premium Electronics Shop")
    print("="*60)
    print(f"🌍 Environment: {'Vercel' if IS_VERCEL else 'Local'}")
    
    orders = load_orders()
    products = load_products()
    print(f"\\n📊 Products: {len(products) if products else 0}")
    print(f"📊 Orders: {len(orders) if orders else 0}")
    print("="*60)
    
    print("\\n🚀 Starting server...")
    print("📍 http://localhost:5000")
    print("🔑 Login: admin / electronics2026")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
'''
    
    # Backup original app.py
    if os.path.exists('app.py'):
        shutil.copy('app.py', 'app.py.backup')
        print("✅ Backup created: app.py.backup")
    
    with open('app.py', 'w') as f:
        f.write(new_app_py)
    print("✅ Created new app.py")

def main():
    print("🚀 Auto-Splitting your Flask App...")
    print("="*50)
    
    content = read_app_py()
    if not content:
        return
    
    # Create all files
    create_models_py(content)
    create_utils_py(content)
    create_routes_py(content)
    create_new_app_py()
    
    print("="*50)
    print("✅ DONE! Your app is now split into multiple files.")
    print("📝 Next steps:")
    print("1. Check the new files for any missing imports")
    print("2. Run: python app.py")
    print("3. If you get import errors, add the missing imports")
    print("4. Your original app.py is backed up as app.py.backup")

if __name__ == '__main__':
    main()