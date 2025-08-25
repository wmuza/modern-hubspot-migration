#!/usr/bin/env python
"""
Company Property Migration Script
Creates all custom company properties from production in sandbox before migrating data
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
from core.field_filters import HubSpotFieldFilter
import time

def get_all_company_properties(token):
    """Get all company properties from a HubSpot portal"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/companies'
    
    success, data = make_hubspot_request('GET', url, headers)
    if success:
        return data.get('results', [])
    else:
        print(f"❌ Error fetching company properties: {data}")
        return []

def create_company_property(token, property_definition):
    """Create a company property in the target portal"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/companies'
    
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
    
    success, data = make_hubspot_request('POST', url, headers, json_data=clean_def)
    return success, data

def migrate_company_properties(prod_token=None, sandbox_token=None):
    """Main function to migrate company properties from production to sandbox"""
    print("🏢 Company Property Migration")
    print("=" * 50)
    
    # Use provided tokens or load from config
    if not prod_token or not sandbox_token:
        config = load_env_config()
        prod_token = prod_token or config.get('HUBSPOT_PROD_API_KEY')
        sandbox_token = sandbox_token or config.get('HUBSPOT_SANDBOX_API_KEY')
    
    # Get properties from production
    print("📥 Fetching company properties from production...")
    prod_properties = get_all_company_properties(prod_token)
    
    if not prod_properties:
        print("❌ Failed to get production properties")
        return
    
    print(f"✅ Found {len(prod_properties)} properties in production")
    
    # Get properties from sandbox
    print("📥 Fetching company properties from sandbox...")
    sandbox_properties = get_all_company_properties(sandbox_token)
    sandbox_prop_names = {prop['name'] for prop in sandbox_properties}
    
    print(f"✅ Found {len(sandbox_properties)} properties in sandbox")
    
    # Filter properties that need to be created
    filter_system = HubSpotFieldFilter()
    properties_to_create = []
    
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
    
    if not properties_to_create:
        print("✅ All custom properties already exist in sandbox")
        return
    
    print(f"🔄 Need to create {len(properties_to_create)} custom properties in sandbox")
    print()
    
    # Create properties in sandbox
    created = 0
    failed = 0
    
    for i, prop in enumerate(properties_to_create, 1):
        prop_name = prop['name']
        prop_type = prop['type']
        
        print(f"  [{i}/{len(properties_to_create)}] Creating: {prop_name} ({prop_type})")
        
        success, result = create_company_property(sandbox_token, prop)
        
        if success:
            created += 1
            print(f"    ✅ Created successfully")
        else:
            failed += 1
            error_msg = result.get('error', str(result)) if isinstance(result, dict) else str(result)
            print(f"    ❌ Failed: {str(error_msg)[:80]}...")
        
        # Rate limiting
        time.sleep(0.1)
        
        if i % 10 == 0:
            print(f"  📊 Progress: {i}/{len(properties_to_create)} processed")
            print()
    
    # Summary
    print()
    print("=" * 50)
    print("📊 PROPERTY MIGRATION SUMMARY")
    print("=" * 50)
    print(f"✅ Successfully created: {created} properties")
    if failed > 0:
        print(f"❌ Failed to create: {failed} properties")
    print(f"📝 Total processed: {len(properties_to_create)} properties")
    print("=" * 50)
    
    if failed == 0:
        print("🎉 All custom company properties migrated successfully!")
        print("💡 You can now run the association migrator to sync property values")
    else:
        print("⚠️  Some properties failed to create - check errors above")

if __name__ == "__main__":
    migrate_company_properties()