#!/usr/bin/env python
"""
Fix JSON sync status - Mark all orders as synced
Run: python fix_json_sync.py
"""

import json
import os
from datetime import datetime

# Project root
project_root = os.path.dirname(os.path.abspath(__file__))
json_file = os.path.join(project_root, 'offline_data.json')

print("=" * 60)
print("🔧 FIXING JSON SYNC STATUS")
print("=" * 60)

try:
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    orders = data.get('orders', [])
    print(f"\n📊 Found {len(orders)} orders in JSON file")
    
    # Count currently unsynced
    unsynced = [o for o in orders if not o.get('synced', False)]
    print(f"📡 Unsynced orders before fix: {len(unsynced)}")
    
    if not unsynced:
        print("\n✅ All orders are already marked as synced!")
        print("   No action needed.")
        exit(0)
    
    # Mark all as synced
    fixed_count = 0
    for order in orders:
        if not order.get('synced', False):
            order['synced'] = True
            order['synced_at'] = datetime.now().isoformat()
            fixed_count += 1
    
    # Save back
    data['orders'] = orders
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n✅ Marked {fixed_count} orders as synced")
    print("📁 Updated offline_data.json")
    
    # Verify
    with open(json_file, 'r') as f:
        data = json.load(f)
    remaining = [o for o in data.get('orders', []) if not o.get('synced', False)]
    print(f"📡 Remaining unsynced orders: {len(remaining)}")
    
    if remaining:
        print("\n⚠️ Still have unsynced orders:")
        for o in remaining[:5]:
            print(f"   - {o.get('order_id')} | {o.get('customer_name', 'N/A')}")
    else:
        print("\n✅ All orders are now synced!")
    
except FileNotFoundError:
    print(f"❌ File not found: {json_file}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)