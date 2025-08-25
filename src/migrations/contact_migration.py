#!/usr/bin/env python
"""
HubSpot Contact Migration Script (2025 API Compatible)
Migrates contacts with all writable properties from production to sandbox
"""

import time
from typing import List, Dict, Any, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import (
    load_env_config, get_api_headers, make_hubspot_request, print_progress_bar
)
from core.field_filters import HubSpotFieldFilter

def _verify_contact_properties(sandbox_token: str, sandbox_contact_id: str, original_contact: Dict[str, Any], filter_system: HubSpotFieldFilter) -> bool:
    """Verify all properties were transferred correctly and fix missing ones"""
    headers = get_api_headers(sandbox_token)
    sandbox_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{sandbox_contact_id}'
    
    # Get writable properties list
    props_url = 'https://api.hubapi.com/crm/v3/properties/contacts'
    props_success, props_data = make_hubspot_request('GET', props_url, headers)
    
    if not props_success:
        return False
        
    properties = props_data.get('results', [])
    safe_props = filter_system.get_safe_properties_list(properties)
    
    params = {
        'properties': ','.join(safe_props)
    }
    
    success, sandbox_data = make_hubspot_request('GET', sandbox_url, headers, params=params)
    
    if not success:
        return False
    
    # Compare properties
    original_props = original_contact.get('properties', {})
    sandbox_props = sandbox_data.get('properties', {})
    
    missing_props = {}
    key_properties = ['phone', 'mobilephone', 'company', 'jobtitle', 'website', 'city', 'state', 'country']
    
    for prop_name, prop_value in original_props.items():
        if prop_name in safe_props and prop_value and prop_name in key_properties:  # Only check key properties
            sandbox_value = sandbox_props.get(prop_name)
            
            if not sandbox_value:
                missing_props[prop_name] = prop_value
    
    # Fix missing properties
    if missing_props:
        print(f"    🔧 Fixing {len(missing_props)} missing key properties...")
        
        # Filter the missing properties through the field filter
        filtered_missing = filter_system.filter_contact_properties(missing_props, is_update=True)
        
        if filtered_missing:
            update_payload = {'properties': filtered_missing}
            update_success, update_result = make_hubspot_request('PATCH', sandbox_url, headers, json_data=update_payload)
            
            if update_success:
                print(f"    ✅ Updated {len(filtered_missing)} properties")
                return True
            else:
                print(f"    ⚠️  Property update failed")
                return False
        
    return True

def get_writable_properties(token: str, filter_system: HubSpotFieldFilter) -> List[str]:
    """Get list of writable contact property names"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/contacts'
    
    success, data = make_hubspot_request('GET', url, headers)
    
    if not success:
        print(f"❌ Error fetching properties: {data}")
        return []
    
    properties = data.get('results', [])
    return filter_system.get_safe_properties_list(properties)

def get_contacts_from_production(token: str, properties: List[str], limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch contacts with specified properties from production ordered by creation date DESC (newest first)"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/objects/contacts'
    
    params = {
        'limit': limit,
        'properties': ','.join(properties),
        'sorts': 'createdate:desc'  # Order by creation date descending (newest first)
    }
    
    success, data = make_hubspot_request('GET', url, headers, params=params)
    
    if success:
        return data.get('results', [])
    else:
        print(f"❌ Error fetching contacts: {data}")
        return []

def find_contact_by_email(token: str, email: str) -> Optional[str]:
    """Find a contact in sandbox by email address"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/objects/contacts/search'
    
    payload = {
        'filterGroups': [{
            'filters': [{
                'propertyName': 'email',
                'operator': 'EQ',
                'value': email
            }]
        }],
        'properties': ['email', 'firstname', 'lastname'],
        'limit': 1
    }
    
    success, data = make_hubspot_request('POST', url, headers, json_data=payload)
    
    if success:
        results = data.get('results', [])
        return results[0]['id'] if results else None
    else:
        return None

def create_contact_in_sandbox(token: str, contact_data: Dict[str, Any], filter_system: HubSpotFieldFilter) -> tuple[bool, str]:
    """Create a new contact in sandbox"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/objects/contacts'
    
    # Filter and clean properties (is_update=False for new contact creation)
    properties = filter_system.filter_contact_properties(contact_data.get('properties', {}), is_update=False)
    
    payload = {'properties': properties}
    
    success, data = make_hubspot_request('POST', url, headers, json_data=payload)
    
    if success:
        return True, data.get('id', 'unknown')
    else:
        error_msg = data.get('error', str(data)) if isinstance(data, dict) else str(data)
        return False, error_msg

def update_contact_in_sandbox(token: str, contact_id: str, contact_data: Dict[str, Any], filter_system: HubSpotFieldFilter) -> tuple[bool, int]:
    """Update an existing contact in sandbox with filtered properties only"""
    headers = get_api_headers(token)
    url = f'https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}'
    
    # Filter properties using comprehensive filtering system (is_update=True for existing contact)
    properties = filter_system.filter_contact_properties(contact_data.get('properties', {}), is_update=True)
    
    if not properties:
        return True, 0  # No properties to update
    
    payload = {'properties': properties}
    
    success, data = make_hubspot_request('PATCH', url, headers, json_data=payload)
    
    if success:
        return True, len(properties)
    else:
        error_msg = data.get('error', str(data)) if isinstance(data, dict) else str(data)
        return False, f"Update failed: {error_msg}"

def get_contact_display_name(contact: Dict[str, Any]) -> str:
    """Get a display name for a contact"""
    props = contact.get('properties', {})
    firstname = (props.get('firstname') or '').strip()
    lastname = (props.get('lastname') or '').strip()
    email = (props.get('email') or '').strip()
    
    if firstname or lastname:
        return f"{firstname} {lastname}".strip()
    elif email:
        return email
    else:
        return "Unknown Contact"

def migrate_contacts(prod_token: str, sandbox_token: str, limit: int = 50) -> Dict[str, int]:
    """
    Main contact migration function
    
    Returns:
        Dictionary with migration statistics
    """
    print("🔄 Starting contact migration...")
    print("=" * 60)
    
    # Initialize comprehensive field filtering system
    filter_system = HubSpotFieldFilter()
    
    # Get writable properties
    print("📋 Analyzing contact properties with comprehensive filtering...")
    writable_props = get_writable_properties(prod_token, filter_system)
    
    if not writable_props:
        print("❌ Failed to get writable properties")
        return {'migrated': 0, 'updated': 0, 'failed': 0, 'total': 0}
    
    print(f"✅ Found {len(writable_props)} safe writable properties")
    print(f"🛡️  Filtering system excludes {354 + 36 + 23} readonly/system fields")
    
    # Get contacts from production
    print(f"📥 Fetching {limit} contacts from production...")
    prod_contacts = get_contacts_from_production(prod_token, writable_props, limit)
    
    if not prod_contacts:
        print("❌ Failed to get production contacts")
        return {'migrated': 0, 'updated': 0, 'failed': 0, 'total': 0}
    
    print(f"✅ Retrieved {len(prod_contacts)} contacts")
    
    # Process each contact
    print(f"🔄 Processing contacts...")
    print()
    
    stats = {'migrated': 0, 'updated': 0, 'failed': 0, 'total': len(prod_contacts)}
    
    for i, contact in enumerate(prod_contacts, 1):
        email = contact.get('properties', {}).get('email')
        display_name = get_contact_display_name(contact)
        
        print_progress_bar(i-1, len(prod_contacts), "Migrating contacts")
        
        if email:
            # Contact with email - check for duplicates
            print(f"  📧 {display_name} ({email})")
            
            # Check if contact already exists in sandbox
            existing_contact_id = find_contact_by_email(sandbox_token, email)
            
            if existing_contact_id:
                # Update existing contact
                success, result = update_contact_in_sandbox(sandbox_token, existing_contact_id, contact, filter_system)
                if success:
                    stats['updated'] += 1
                    print(f"    ✅ Updated with {result} properties")
                else:
                    stats['failed'] += 1
                    print(f"    ❌ Update failed: {str(result)[:60]}...")
            else:
                # Create new contact
                success, result = create_contact_in_sandbox(sandbox_token, contact, filter_system)
                if success:
                    stats['migrated'] += 1
                    print(f"    ✅ Created new contact (ID: {result})")
                    
                    # Verify and fix properties after creation
                    time.sleep(0.3)  # Brief delay before verification
                    _verify_contact_properties(sandbox_token, result, contact, filter_system)
                else:
                    stats['failed'] += 1
                    print(f"    ❌ Creation failed: {str(result)[:60]}...")
        else:
            # Contact without email - create directly (no duplicate checking possible)
            print(f"  👤 {display_name} (no email)")
            
            # Create new contact without duplicate checking
            success, result = create_contact_in_sandbox(sandbox_token, contact, filter_system)
            if success:
                stats['migrated'] += 1
                print(f"    ✅ Created new contact (ID: {result})")
                
                # Verify and fix properties after creation
                time.sleep(0.3)  # Brief delay before verification
                _verify_contact_properties(sandbox_token, result, contact, filter_system)
            else:
                stats['failed'] += 1
                print(f"    ❌ Creation failed: {str(result)[:60]}...")
        
        # Rate limiting
        time.sleep(0.2)
    
    print_progress_bar(len(prod_contacts), len(prod_contacts), "Migrating contacts")
    
    return stats

def main():
    """Main execution function"""
    print("🚀 HubSpot Contact Migration (2025)")
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
    
    # Default to 50 contacts, but allow override
    contact_limit = 50
    
    print(f"📊 Migration target: {contact_limit} contacts")
    print(f"🔐 Using 2025 API with Bearer token authentication")
    print()
    
    # Run migration
    results = migrate_contacts(prod_token, sandbox_token, contact_limit)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 MIGRATION SUMMARY")
    print("=" * 60)
    print(f"✨ New contacts created: {results['migrated']}")
    print(f"🔄 Existing contacts updated: {results['updated']}")
    print(f"❌ Failed migrations: {results['failed']}")
    print(f"📝 Total processed: {results['total']}")
    print("=" * 60)
    
    if results['failed'] == 0:
        print("🎉 Contact migration completed successfully!")
        print("💡 Your sandbox now has up-to-date contact data from production")
    else:
        print("⚠️  Some contacts failed to migrate - check errors above")
    
    total_success = results['migrated'] + results['updated']
    success_rate = (total_success / results['total']) * 100 if results['total'] > 0 else 0
    print(f"📈 Success rate: {success_rate:.1f}% ({total_success}/{results['total']})")

if __name__ == "__main__":
    main()