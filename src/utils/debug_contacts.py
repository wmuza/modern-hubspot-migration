#!/usr/bin/env python
"""
Debug script to see what contacts we're fetching
"""

from utils import load_env_config, get_api_headers, make_hubspot_request
from field_filters import HubSpotFieldFilter

def debug_contacts():
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    
    filter_system = HubSpotFieldFilter()
    
    # Get all properties first
    headers = get_api_headers(prod_token)
    url = 'https://api.hubapi.com/crm/v3/properties/contacts'
    success, data = make_hubspot_request('GET', url, headers)
    
    if success:
        all_props = data.get('results', [])
        safe_props = filter_system.get_safe_properties_list(all_props)
        print(f"Safe properties ({len(safe_props)}):")
        for prop in safe_props[:20]:  # First 20
            print(f"  - {prop}")
        print(f"  ... and {len(safe_props) - 20} more")
    
    # Now fetch contacts with just basic properties
    basic_props = ['email', 'firstname', 'lastname', 'phone', 'company']
    
    headers = get_api_headers(prod_token)
    url = 'https://api.hubapi.com/crm/v3/objects/contacts'
    params = {
        'limit': 5,
        'properties': ','.join(basic_props)
    }
    
    success, data = make_hubspot_request('GET', url, headers, params=params)
    
    if success:
        contacts = data.get('results', [])
        print(f"\nFound {len(contacts)} contacts:")
        for i, contact in enumerate(contacts):
            props = contact.get('properties', {})
            email = props.get('email', 'NO EMAIL')
            firstname = props.get('firstname', '')
            lastname = props.get('lastname', '')
            name = f"{firstname} {lastname}".strip() or 'No name'
            print(f"  {i+1}. {name} - {email}")

if __name__ == "__main__":
    debug_contacts()