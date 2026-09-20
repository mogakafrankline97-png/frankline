#!/usr/bin/env python
"""
Supabase Database Connection Checker
Run: python check_db_connection.py
"""

import os
import sys
import json
import socket
from datetime import datetime

# ===== FIX: Get the correct project root =====
# The script is in the routes folder, so we need to go up one level
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Go up one level from routes/

print(f"📁 Script location: {script_dir}")
print(f"📁 Project root: {project_root}")

# Add project root to path
sys.path.insert(0, project_root)

# Also try to add the routes folder
sys.path.insert(0, script_dir)

try:
    from config import Config
    print("✅ Config loaded successfully from project root")
except ImportError as e:
    print(f"⚠️  Could not load config from project root: {e}")
    
    # Try to find config.py by searching
    config_path = None
    for root, dirs, files in os.walk(project_root):
        if 'config.py' in files:
            config_path = root
            break
    
    if config_path:
        print(f"✅ Found config.py in: {config_path}")
        sys.path.insert(0, config_path)
        try:
            from config import Config
            print("✅ Config loaded successfully")
        except ImportError as e2:
            print(f"❌ Still couldn't load config: {e2}")
            sys.exit(1)
    else:
        print("❌ config.py not found anywhere!")
        sys.exit(1)

try:
    import requests
    print("✅ Requests module loaded")
except ImportError as e:
    print(f"❌ Requests module not installed: {e}")
    print("   Run: pip install requests")
    sys.exit(1)


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_supabase_connection():
    """Check all aspects of Supabase connection"""
    
    print_section("🔍 SUPABASE CONNECTION CHECK")
    
    results = {
        'config': {},
        'dns': {},
        'network': {},
        'auth': {},
        'database': {},
        'tables': {}
    }
    
    # ===== 1. CHECK CONFIG =====
    print("\n📋 1. CONFIGURATION")
    print("-" * 40)
    
    try:
        supabase_url = Config.SUPABASE_URL
        supabase_key = Config.SUPABASE_KEY
        
        # Mask the key for security
        key_preview = supabase_key[:20] + "..." + supabase_key[-10:] if len(supabase_key) > 30 else supabase_key
        key_type = "service_role" if supabase_key.startswith('eyJ') else "publishable" if supabase_key.startswith('sb_publishable') else "unknown"
        
        print(f"   SUPABASE_URL: {supabase_url}")
        print(f"   SUPABASE_KEY: {key_preview}")
        print(f"   KEY TYPE: {key_type}")
        print(f"   KEY LENGTH: {len(supabase_key)} chars")
        
        results['config'] = {
            'url': supabase_url,
            'key_type': key_type,
            'key_length': len(supabase_key)
        }
        
        if key_type == 'publishable':
            print("   ⚠️  WARNING: Using publishable key! Use service_role key for backend operations.")
        
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        results['config']['error'] = str(e)
        return results
    
    # ===== 2. CHECK DNS =====
    print("\n🌐 2. DNS RESOLUTION")
    print("-" * 40)
    
    try:
        # Extract host from URL
        host = supabase_url.replace('https://', '').replace('http://', '').split('/')[0]
        print(f"   Resolving: {host}")
        
        ip = socket.gethostbyname(host)
        print(f"   ✅ DNS resolved: {host} → {ip}")
        results['dns'] = {'host': host, 'ip': ip, 'success': True}
        
    except Exception as e:
        print(f"   ❌ DNS resolution failed: {e}")
        results['dns'] = {'error': str(e), 'success': False}
        return results
    
    # ===== 3. CHECK NETWORK CONNECTION =====
    print("\n🌐 3. NETWORK CONNECTION")
    print("-" * 40)
    
    try:
        print(f"   Testing connection to: {supabase_url}")
        
        # Try HEAD request first (faster)
        try:
            response = requests.head(
                f"{supabase_url}/rest/v1/",
                headers=Config.SUPABASE_HEADERS,
                timeout=5
            )
            print(f"   ✅ HEAD request: Status {response.status_code}")
        except:
            print("   ⚠️  HEAD request failed, trying GET...")
            response = requests.get(
                f"{supabase_url}/rest/v1/",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            print(f"   ✅ GET request: Status {response.status_code}")
        
        results['network'] = {
            'status_code': response.status_code,
            'success': response.status_code < 500
        }
        
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error: {e}")
        results['network'] = {'error': 'ConnectionError', 'success': False}
        return results
    except requests.exceptions.Timeout as e:
        print(f"   ❌ Timeout error: {e}")
        results['network'] = {'error': 'Timeout', 'success': False}
        return results
    except Exception as e:
        print(f"   ❌ Network error: {e}")
        results['network'] = {'error': str(e), 'success': False}
        return results
    
    # ===== 4. CHECK AUTHENTICATION =====
    print("\n🔐 4. AUTHENTICATION")
    print("-" * 40)
    
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/products",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            print("   ✅ Authentication successful!")
            print(f"      Response: {response.status_code} OK")
            results['auth'] = {'success': True, 'status_code': response.status_code}
        elif response.status_code == 401:
            print("   ❌ Authentication failed (401)")
            print("      Invalid API key or missing permissions")
            results['auth'] = {'success': False, 'status_code': 401, 'error': 'Invalid API key'}
            return results
        elif response.status_code == 403:
            print("   ❌ Authorization failed (403)")
            print("      API key doesn't have permission")
            print("      Make sure you're using the SERVICE ROLE key")
            results['auth'] = {'success': False, 'status_code': 403, 'error': 'Forbidden - use service role key'}
            return results
        else:
            print(f"   ⚠️  Unexpected response: {response.status_code}")
            results['auth'] = {'success': False, 'status_code': response.status_code, 'error': f'Status {response.status_code}'}
            
    except Exception as e:
        print(f"   ❌ Auth test error: {e}")
        results['auth'] = {'error': str(e), 'success': False}
        return results
    
    # ===== 5. CHECK DATABASE TABLES =====
    print("\n📊 5. DATABASE TABLES")
    print("-" * 40)
    
    tables_to_check = ['products', 'orders', 'customers']
    
    for table in tables_to_check:
        try:
            response = requests.get(
                f"{supabase_url}/rest/v1/{table}?limit=1",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                count = len(data)
                print(f"   ✅ {table}: {count} rows (accessible)")
                results['tables'][table] = {'exists': True, 'count': count}
            elif response.status_code == 404:
                print(f"   ❌ {table}: Table not found")
                results['tables'][table] = {'exists': False, 'error': 'Table not found'}
            else:
                print(f"   ⚠️  {table}: Status {response.status_code}")
                results['tables'][table] = {'exists': False, 'error': f'Status {response.status_code}'}
                
        except Exception as e:
            print(f"   ❌ {table}: Error - {str(e)}")
            results['tables'][table] = {'exists': False, 'error': str(e)}
    
    # ===== 6. CHECK ORDER COUNT =====
    print("\n📦 6. ORDER STATISTICS")
    print("-" * 40)
    
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/orders",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            orders = response.json()
            total_orders = len(orders)
            
            # Count synced vs unsynced
            synced = sum(1 for o in orders if o.get('synced', True))
            unsynced = sum(1 for o in orders if not o.get('synced', False))
            
            print(f"   Total orders: {total_orders}")
            print(f"   Synced orders: {synced}")
            print(f"   Unsynced orders: {unsynced}")
            
            # Calculate revenue
            total_revenue = sum(float(o.get('total', 0)) for o in orders)
            print(f"   Total revenue: KSh {total_revenue:,.2f}")
            
            results['database'] = {
                'total_orders': total_orders,
                'synced': synced,
                'unsynced': unsynced,
                'total_revenue': total_revenue
            }
            
            # Show recent orders
            if orders:
                print("\n   Recent orders:")
                recent = sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
                for o in recent:
                    print(f"     • {o.get('order_id')} | {o.get('customer_name', 'N/A')} | KSh {o.get('total', 0):,.2f} | synced: {o.get('synced', True)}")
                    
        else:
            print(f"   ❌ Failed to fetch orders: {response.status_code}")
            results['database'] = {'error': f'Status {response.status_code}'}
            
    except Exception as e:
        print(f"   ❌ Error fetching orders: {e}")
        results['database'] = {'error': str(e)}
    
    # ===== 7. CHECK JSON OFFLINE DATA =====
    print("\n💾 7. OFFLINE JSON DATA")
    print("-" * 40)
    
    try:
        # Try to import storage
        try:
            # Add utils to path
            utils_path = os.path.join(project_root, 'utils')
            sys.path.insert(0, utils_path)
            
            from utils.storage import load_json_data
            json_data = load_json_data()
            json_orders = json_data.get('orders', [])
            json_products = json_data.get('products', [])
            
            print(f"   JSON orders: {len(json_orders)}")
            print(f"   JSON products: {len(json_products)}")
            
            # Count unsynced in JSON
            json_unsynced = sum(1 for o in json_orders if not o.get('synced', False))
            print(f"   JSON unsynced orders: {json_unsynced}")
            
            results['offline'] = {
                'total_orders': len(json_orders),
                'total_products': len(json_products),
                'unsynced': json_unsynced
            }
            
        except ImportError as e:
            print(f"   ⚠️  Could not import utils.storage: {e}")
            print("   Checking for offline_data.json directly...")
            
            # Try to read offline_data.json directly
            json_file = os.path.join(project_root, 'offline_data.json')
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    json_orders = data.get('orders', [])
                    json_products = data.get('products', [])
                    print(f"   JSON orders: {len(json_orders)}")
                    print(f"   JSON products: {len(json_products)}")
                    json_unsynced = sum(1 for o in json_orders if not o.get('synced', False))
                    print(f"   JSON unsynced orders: {json_unsynced}")
                    results['offline'] = {
                        'total_orders': len(json_orders),
                        'total_products': len(json_products),
                        'unsynced': json_unsynced
                    }
            else:
                print(f"   ❌ offline_data.json not found at: {json_file}")
                results['offline'] = {'error': 'File not found'}
                
    except Exception as e:
        print(f"   ❌ Error reading JSON: {e}")
        results['offline'] = {'error': str(e)}
    
    # ===== SUMMARY =====
    print_section("📊 CONNECTION SUMMARY")
    
    all_ok = all([
        results.get('dns', {}).get('success', False),
        results.get('network', {}).get('success', False),
        results.get('auth', {}).get('success', False)
    ])
    
    if all_ok:
        print("\n✅ Supabase connection is WORKING!")
        print("   • DNS resolution: OK")
        print("   • Network connection: OK")
        print("   • Authentication: OK")
        print("   • Tables accessible: YES")
    else:
        print("\n❌ Supabase connection has ISSUES:")
        if not results.get('dns', {}).get('success', False):
            print("   • DNS resolution failed - check your internet")
        if not results.get('network', {}).get('success', False):
            print("   • Network connection failed - check URL/internet")
        if not results.get('auth', {}).get('success', False):
            print("   • Authentication failed - check your API key")
    
    # Show recommendations
    if results.get('config', {}).get('key_type') == 'publishable':
        print("\n⚠️  RECOMMENDATION: Use SERVICE ROLE key instead of publishable key")
        print("   Get it from: Supabase Dashboard → Settings → API → service_role")
    
    # Show JSON vs Supabase sync status
    offline_unsynced = results.get('offline', {}).get('unsynced', 0)
    if offline_unsynced > 0:
        print(f"\n📡 You have {offline_unsynced} offline orders in JSON that need syncing!")
        print("   Run this in browser console (F12):")
        print("   fetch('/admin/api/force-sync', { method: 'POST' }).then(r => r.json()).then(console.log)")
    
    print("\n" + "=" * 60)
    
    return results


def main():
    """Main function"""
    print("\n🚀 Supabase Connection Checker")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   Press Ctrl+C to cancel\n")
    
    try:
        results = check_supabase_connection()
        return 0 if results.get('auth', {}).get('success', False) else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())