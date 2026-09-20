# sync_to_supabase.py - DEBUG VERSION
import requests
import json
import os
from datetime import datetime

SUPABASE_URL = "https://hzqrdwerkgfmfaufabjr.supabase.co"
SUPABASE_KEY = "sb_publishable_tnBOmCO7EFfIoXfNjEH_Tg_D7WX-zld"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Load local data from the app's actual stored source.
project_root = os.path.dirname(os.path.abspath(__file__))
data_file = os.path.join(project_root, 'offline_data.json')

products = []
orders = []

if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    products = data.get('products', []) or []
    orders = data.get('orders', []) or []
    if not products:
        print("⚠️ offline_data.json contains no products.")
    if not orders:
        print("⚠️ offline_data.json contains no orders.")
else:
    legacy_products_file = os.path.join(project_root, 'products.json')
    legacy_orders_file = os.path.join(project_root, 'orders.json')

    if os.path.exists(legacy_products_file):
        with open(legacy_products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
    else:
        print("⚠️ products.json not found. Looking for offline_data.json instead.")

    if os.path.exists(legacy_orders_file):
        with open(legacy_orders_file, 'r', encoding='utf-8') as f:
            orders = json.load(f)
    else:
        orders = []

print(f"📦 Found {len(products)} products and {len(orders)} orders to sync...")

# Sync Products (already done)
synced_products = 0
for product in products:
    try:
        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?id=eq.{product.get('id')}",
            headers=headers,
            timeout=5
        )
        if check.status_code == 200 and check.json():
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/products?id=eq.{product.get('id')}",
                headers=headers,
                json=product,
                timeout=5
            )
        else:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/products",
                headers=headers,
                json=product,
                timeout=5
            )
        if response.status_code in [200, 201, 204]:
            synced_products += 1
            print(f"✅ Synced product: {product.get('name')}")
    except Exception as e:
        print(f"❌ Error syncing product {product.get('name')}: {e}")

print(f"✅ Synced {synced_products}/{len(products)} products")

# Sync Orders with detailed debugging
if orders:
    synced_orders = 0
    for i, order in enumerate(orders):
        try:
            print(f"\n📝 Processing order {i+1}/{len(orders)}: {order.get('order_id', 'NO_ID')}")
            
            # Check what the order looks like
            print(f"   Order keys: {list(order.keys())}")
            
            # Format order for Supabase
            order_id = order.get('order_id')
            if not order_id:
                print(f"   ❌ No order_id found!")
                continue
            
            # Handle items
            items = order.get('items', [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except:
                    items = []
            print(f"   Items: {len(items)} items")
            
            # Handle customer
            customer = order.get('customer', {})
            if isinstance(customer, str):
                try:
                    customer = json.loads(customer)
                except:
                    customer = {'name': 'Unknown'}
            print(f"   Customer: {customer.get('name', 'Unknown')}")
            
            # Handle date
            created_at = order.get('created_at')
            if not created_at:
                created_at = datetime.utcnow().isoformat()
            
            supabase_order = {
                'order_id': str(order_id),
                'items': json.dumps(items),
                'subtotal': float(order.get('subtotal', 0)),
                'shipping': float(order.get('shipping', 0)),
                'total': float(order.get('total', 0)),
                'status': order.get('status', 'pending'),
                'source': order.get('source', 'web'),
                'created_at': created_at,
                'customer': json.dumps(customer)
            }
            
            print(f"   📤 Sending to Supabase: {supabase_order['order_id']}")
            
            # Try to insert
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/orders",
                headers=headers,
                json=supabase_order,
                timeout=10
            )
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                synced_orders += 1
                print(f"   ✅ Synced order: {order_id}")
            else:
                print(f"   ❌ Failed! Status: {response.status_code}")
                print(f"   Error response: {response.text[:200]}")
                
                # Try without items (just to test)
                if 'items' in supabase_order and 'items' not in order:
                    print(f"   🔄 Trying without items...")
                    test_order = {k: v for k, v in supabase_order.items() if k != 'items'}
                    response2 = requests.post(
                        f"{SUPABASE_URL}/rest/v1/orders",
                        headers=headers,
                        json=test_order,
                        timeout=10
                    )
                    print(f"   Without items status: {response2.status_code}")
                    if response2.status_code in [200, 201]:
                        print(f"   ✅ Order synced WITHOUT items!")
                        synced_orders += 1
                    else:
                        print(f"   ❌ Still failed: {response2.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Synced {synced_orders}/{len(orders)} orders")
else:
    print("⚠️ No orders to sync")

# Check final count
response = requests.get(
    f"{SUPABASE_URL}/rest/v1/orders?select=count",
    headers=headers
)
if response.status_code == 200:
    data = response.json()
    if isinstance(data, list):
        print(f"📊 Total orders in Supabase: {len(data)}")
    else:
        print(f"📊 Total orders in Supabase: {data}")
else:
    print(f"⚠️ Could not get count: {response.status_code}")