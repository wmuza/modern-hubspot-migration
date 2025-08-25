#!/usr/bin/env python
"""
Deal Property Migration Script
Creates all custom deal properties from production in sandbox before migrating deal data
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
import time
import json
from datetime import datetime

def get_all_deal_properties(token):
    """Get all deal properties from a HubSpot portal"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/deals'
    
    success, data = make_hubspot_request('GET', url, headers)
    if success:
        return data.get('results', [])
    else:
        print(f"❌ Error fetching deal properties: {data}")
        return []

def create_deal_property(token, property_definition):
    """Create a deal property in the target portal"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/deals'
    
    # Clean the property definition for creation
    clean_def = {
        'name': property_definition['name'],
        'label': property_definition.get('label', property_definition['name']),
        'type': property_definition['type'],
        'fieldType': property_definition['fieldType']
    }
    
    # Add optional fields if present
    if 'description' in property_definition:
        clean_def['description'] = property_definition['description']
    
    if 'groupName' in property_definition:
        clean_def['groupName'] = property_definition['groupName']
    
    if 'options' in property_definition and property_definition['options']:
        clean_def['options'] = property_definition['options']
    
    if 'displayOrder' in property_definition:
        clean_def['displayOrder'] = property_definition['displayOrder']
    
    # Handle special deal property fields
    if 'referencedObjectType' in property_definition:
        clean_def['referencedObjectType'] = property_definition['referencedObjectType']
    
    if 'externalOptions' in property_definition:
        clean_def['externalOptions'] = property_definition['externalOptions']
    
    success, data = make_hubspot_request('POST', url, headers, json_data=clean_def)
    return success, data

def get_deal_property_groups(token):
    """Get deal property groups"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/deals/groups'
    
    success, data = make_hubspot_request('GET', url, headers)
    if success:
        return data.get('results', [])
    else:
        print(f"❌ Error fetching deal property groups: {data}")
        return []

def create_deal_property_group(token, group_definition):
    """Create a deal property group in the target portal"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/deals/groups'
    
    # Clean the group definition
    clean_def = {
        'name': group_definition['name'],
        'label': group_definition.get('label', group_definition['name']),
        'displayOrder': group_definition.get('displayOrder', 0)
    }
    
    success, data = make_hubspot_request('POST', url, headers, json_data=clean_def)
    return success, data

def migrate_deal_properties():
    """Main function to migrate deal properties from production to sandbox"""
    print("💼 Deal Property Migration")
    print("=" * 50)
    
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    if not prod_token or not sandbox_token:
        print("❌ Error: API tokens not found in .env file")
        return False
    
    # Get properties from production
    print("📥 Fetching deal properties from production...")
    prod_properties = get_all_deal_properties(prod_token)
    
    if not prod_properties:
        print("❌ Failed to get production properties")
        return False
    
    print(f"✅ Found {len(prod_properties)} properties in production")
    
    # Get properties from sandbox
    print("📥 Fetching deal properties from sandbox...")
    sandbox_properties = get_all_deal_properties(sandbox_token)
    sandbox_prop_names = {prop['name'] for prop in sandbox_properties}
    
    print(f"✅ Found {len(sandbox_properties)} properties in sandbox")
    
    # Get property groups from production
    print("📥 Fetching deal property groups from production...")
    prod_groups = get_deal_property_groups(prod_token)
    sandbox_groups = get_deal_property_groups(sandbox_token)
    sandbox_group_names = {group['name'] for group in sandbox_groups}
    
    # Filter properties that need to be created
    properties_to_create = []
    groups_to_create = []
    
    # First, identify groups that need to be created
    for group in prod_groups:
        group_name = group.get('name', '')
        
        # Skip if already exists in sandbox
        if group_name in sandbox_group_names:
            continue
            
        # Skip HubSpot defined groups
        if group_name.startswith('deal') and group.get('hubspotDefined', False):
            continue
            
        groups_to_create.append(group)
    
    # Then, identify properties that need to be created
    for prop in prod_properties:
        prop_name = prop.get('name', '')
        
        # Skip if already exists in sandbox
        if prop_name in sandbox_prop_names:
            continue
            
        # Skip HubSpot defined properties (can't be recreated)
        if prop.get('hubspotDefined', False):
            continue
            
        # Skip calculated properties
        if prop.get('calculated', False):
            continue
            
        # Skip readonly properties
        if prop.get('readOnlyValue', False):
            continue
            
        # Skip system properties
        if prop_name.lower().startswith(('hs_', 'hubspot_')):
            continue
        
        properties_to_create.append(prop)
    
    print(f"🔄 Need to create {len(groups_to_create)} property groups")
    print(f"🔄 Need to create {len(properties_to_create)} custom properties")
    
    if not groups_to_create and not properties_to_create:
        print("✅ All custom properties and groups already exist in sandbox")
        return True
    
    print()
    
    # Create property groups first
    group_created = 0
    group_failed = 0
    
    if groups_to_create:
        print(f"📁 Creating {len(groups_to_create)} property groups...")
        for i, group in enumerate(groups_to_create, 1):
            group_name = group['name']
            
            print(f"  [{i}/{len(groups_to_create)}] Creating group: {group_name}")
            
            success, result = create_deal_property_group(sandbox_token, group)
            
            if success:
                group_created += 1
                print(f"    ✅ Created successfully")
            else:
                group_failed += 1
                error_msg = result.get('error', str(result)) if isinstance(result, dict) else str(result)
                print(f"    ❌ Failed: {str(error_msg)[:80]}...")
            
            # Rate limiting
            time.sleep(0.1)
        
        print(f"📁 Groups: {group_created} created, {group_failed} failed")
        print()
    
    # Create properties
    created = 0
    failed = 0
    
    print(f"🔧 Creating {len(properties_to_create)} custom properties...")
    for i, prop in enumerate(properties_to_create, 1):
        prop_name = prop['name']
        prop_type = prop['type']
        
        print(f"  [{i}/{len(properties_to_create)}] Creating: {prop_name} ({prop_type})")
        
        success, result = create_deal_property(sandbox_token, prop)
        
        if success:
            created += 1
            print(f"    ✅ Created successfully")
        else:
            failed += 1
            error_msg = result.get('error', str(result)) if isinstance(result, dict) else str(result)
            print(f"    ❌ Failed: {str(error_msg)[:80]}...")
        
        # Rate limiting
        time.sleep(0.1)
        
        if i % 20 == 0:
            print(f"  📊 Progress: {i}/{len(properties_to_create)} processed")
            print()
    
    # Summary
    print()
    print("=" * 50)
    print("📊 DEAL PROPERTY MIGRATION SUMMARY")
    print("=" * 50)
    print(f"📁 Property groups created: {group_created}")
    if group_failed > 0:
        print(f"❌ Property groups failed: {group_failed}")
    print(f"✅ Properties created: {created}")
    if failed > 0:
        print(f"❌ Properties failed: {failed}")
    print(f"📝 Total processed: {len(properties_to_create)} properties, {len(groups_to_create)} groups")
    print("=" * 50)
    
    # Save detailed report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = {
        'timestamp': timestamp,
        'migration_date': datetime.now().isoformat(),
        'summary': {
            'groups_created': group_created,
            'groups_failed': group_failed,
            'properties_created': created,
            'properties_failed': failed,
            'total_groups_processed': len(groups_to_create),
            'total_properties_processed': len(properties_to_create)
        },
        'created_groups': [group['name'] for group in groups_to_create[:group_created]],
        'created_properties': [prop['name'] for prop in properties_to_create[:created]]
    }
    
    os.makedirs('reports', exist_ok=True)
    report_file = f'reports/deal_property_migration_{timestamp}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Detailed report saved: {report_file}")
    
    if failed == 0 and group_failed == 0:
        print("🎉 All deal properties migrated successfully!")
        print("💡 Ready for deal data migration")
        return True
    else:
        print("⚠️  Some properties failed to create - check errors above")
        return False

if __name__ == "__main__":
    success = migrate_deal_properties()
    exit(0 if success else 1)