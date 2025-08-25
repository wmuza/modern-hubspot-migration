#!/usr/bin/env python
"""
HubSpot Property Synchronization Script (2025 API Compatible)
Syncs custom properties from production to sandbox environment
"""

import time
from typing import List, Dict, Any
from utils import load_env_config, get_api_headers, make_hubspot_request, print_progress_bar

def get_contact_properties(token: str) -> List[Dict[str, Any]]:
    """Get all contact properties from HubSpot"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/contacts'
    
    success, data = make_hubspot_request('GET', url, headers)
    
    if success:
        return data.get('results', [])
    else:
        print(f"❌ Error fetching properties: {data}")
        return []

def create_property(token: str, property_data: Dict[str, Any]) -> tuple[bool, str]:
    """Create a custom property in HubSpot"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/contacts'
    
    # Skip system properties that can't be created
    if property_data.get('hubspotDefined', False):
        return True, "System property - skipped"
    
    # Prepare property payload
    payload = {
        'name': property_data['name'],
        'label': property_data['label'],
        'type': property_data['type'],
        'fieldType': property_data['fieldType']
    }
    
    # Add optional fields if they exist
    optional_fields = ['description', 'groupName', 'options', 'displayOrder']
    for field in optional_fields:
        if field in property_data and property_data[field]:
            payload[field] = property_data[field]
    
    success, data = make_hubspot_request('POST', url, headers, json_data=payload)
    
    if success:
        return True, "Created successfully"
    elif isinstance(data, dict) and data.get('status_code') == 409:
        return True, "Already exists"
    else:
        error_msg = data.get('error', str(data)) if isinstance(data, dict) else str(data)
        return False, f"Error: {error_msg}"

def sync_properties(prod_token: str, sandbox_token: str) -> Dict[str, int]:
    """
    Sync all properties from production to sandbox
    
    Returns:
        Dictionary with counts: created, skipped, failed, total
    """
    print("🔄 Starting property synchronization...")
    print("=" * 60)
    
    # Get properties from both environments
    print("📥 Fetching properties from production...")
    prod_properties = get_contact_properties(prod_token)
    
    if not prod_properties:
        print("❌ Failed to get production properties")
        return {'created': 0, 'skipped': 0, 'failed': 0, 'total': 0}
    
    print("📥 Fetching properties from sandbox...")
    sandbox_properties = get_contact_properties(sandbox_token)
    
    if not sandbox_properties:
        print("❌ Failed to get sandbox properties")
        return {'created': 0, 'skipped': 0, 'failed': 0, 'total': 0}
    
    # Create set of existing property names in sandbox
    sandbox_property_names = {prop['name'] for prop in sandbox_properties}
    
    print(f"✅ Production properties: {len(prod_properties)}")
    print(f"✅ Sandbox properties: {len(sandbox_properties)}")
    
    # Find properties that need to be created
    missing_properties = [
        prop for prop in prod_properties 
        if prop['name'] not in sandbox_property_names
    ]
    
    if not missing_properties:
        print("✅ All properties already exist in sandbox!")
        return {'created': 0, 'skipped': len(prod_properties), 'failed': 0, 'total': len(prod_properties)}
    
    print(f"🔧 Creating {len(missing_properties)} missing properties...")
    print()
    
    # Create missing properties
    counts = {'created': 0, 'skipped': 0, 'failed': 0, 'total': len(missing_properties)}
    
    for i, prop in enumerate(missing_properties, 1):
        prop_name = prop['name']
        prop_label = prop.get('label', prop_name)
        
        print_progress_bar(i-1, len(missing_properties), "Creating properties")
        
        success, message = create_property(sandbox_token, prop)
        
        if success:
            if "Created successfully" in message:
                counts['created'] += 1
                status = "✅"
            else:
                counts['skipped'] += 1
                status = "⏭️ "
        else:
            counts['failed'] += 1
            status = "❌"
        
        print(f"  {status} {prop_name} ({prop_label}) - {message}")
        
        # Rate limiting to avoid API limits
        time.sleep(0.1)
    
    print_progress_bar(len(missing_properties), len(missing_properties), "Creating properties")
    
    return counts

def main():
    """Main execution function"""
    print("🚀 HubSpot Property Synchronization (2025)")
    print("=" * 60)
    
    # Load configuration
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    if not prod_token or not sandbox_token:
        print("❌ Error: Missing API keys in .env file")
        print("   Please configure HUBSPOT_PROD_API_KEY and HUBSPOT_SANDBOX_API_KEY")
        return
    
    if prod_token.startswith('your_') or sandbox_token.startswith('your_'):
        print("❌ Error: Please replace placeholder API keys with actual values")
        return
    
    # Sync properties
    results = sync_properties(prod_token, sandbox_token)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 PROPERTY SYNC SUMMARY")
    print("=" * 60)
    print(f"✅ Created: {results['created']}")
    print(f"⏭️  Skipped: {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📝 Total: {results['total']}")
    print("=" * 60)
    
    if results['failed'] == 0:
        print("🎉 Property synchronization completed successfully!")
        print("💡 Your sandbox now has all properties from production")
    else:
        print("⚠️  Some properties failed to sync - check errors above")
    
    print("\n🔄 Next step: Run contact_migration.py to migrate contact data")

if __name__ == "__main__":
    main()