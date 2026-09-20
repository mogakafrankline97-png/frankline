# schema_tool.py - All-in-One Schema Tool
import sys
import json
from config import Config
from SupabaseSchemaViewer import SupabaseSchemaViewer

def main():
    viewer = SupabaseSchemaViewer()
    
    print("\n🔍 SCHEMA TOOL")
    print("=" * 40)
    print("1. View schema")
    print("2. Export as JSON")
    print("3. Export as Markdown")
    print("4. Show summary")
    print("5. All of the above")
    print("=" * 40)
    
    choice = input("Choose option (1-5): ")
    
    if choice == '1':
        viewer.get_all_schemas()
        viewer.display_schema()
    
    elif choice == '2':
        viewer.get_all_schemas()
        filename = viewer.export_schema_json()
        print(f"✅ Exported to: {filename}")
    
    elif choice == '3':
        from schema_markdown import export_schema_markdown
        filename = export_schema_markdown()
        print(f"✅ Exported to: {filename}")
    
    elif choice == '4':
        viewer.get_all_schemas()
        print("\n📊 SUMMARY:")
        print("-" * 40)
        for item in viewer.get_schema_summary():
            print(f"  {item['table']:20} {item['records']:6} records, {item['columns']:3} columns")
    
    elif choice == '5':
        viewer.get_all_schemas()
        viewer.display_schema()
        viewer.export_schema_json()
        from schema_markdown import export_schema_markdown
        export_schema_markdown()
        print("\n✅ All exports complete!")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
