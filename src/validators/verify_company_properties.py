#!/usr/bin/env python
"""
Company Property Verification Script
Compares company properties between production and sandbox to ensure data integrity
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
from core.field_filters import HubSpotFieldFilter
import json

def get_company_details(token, company_id, properties_list):
    """Get detailed company information"""
    headers = get_api_headers(token)
    url = f'https://api.hubapi.com/crm/v3/objects/companies/{company_id}'
    
    params = {
        'properties': ','.join(properties_list)
    }
    
    success, data = make_hubspot_request('GET', url, headers, params=params)
    return data if success else None

def get_company_properties_list(token):
    """Get list of writable company properties"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/companies'
    
    success, data = make_hubspot_request('GET', url, headers)
    if not success:
        return []
    
    filter_system = HubSpotFieldFilter()
    properties = data.get('results', [])
    
    # Get writable properties (adapt the contact filter for companies)
    safe_props = []
    for prop in properties:
        prop_name = prop.get('name', '').lower()
        
        # Skip HubSpot system fields for companies
        if prop.get('hubspotDefined', False) and prop_name not in {'name', 'domain', 'website', 'phone', 'address', 'city', 'state', 'zip', 'country', 'industry', 'description'}:
            continue
        if prop.get('readOnlyValue', False):
            continue
        if prop.get('calculated', False):
            continue
            
        safe_props.append(prop['name'])
    
    return safe_props

def verify_company_data():
    """Verify company data between production and sandbox"""
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    print("🔍 Company Property Verification")
    print("=" * 50)
    
    # Load the company mapping from the last migration
    try:
        with open('migration_report_20250825_141020.json', 'r') as f:
            report = json.load(f)
            company_mapping = report.get('company_mapping', {})
    except FileNotFoundError:
        print("❌ No migration report found. Please run the association migrator first.")
        return
    
    if not company_mapping:
        print("❌ No company mappings found in migration report.")
        return
    
    print(f"📊 Found {len(company_mapping)} companies to verify")
    print()
    
    # Get company properties list
    print("📋 Getting company properties list...")
    company_props = get_company_properties_list(prod_token)
    print(f"✅ Found {len(company_props)} writable company properties")
    print()
    
    # Verify each company
    discrepancies = []
    
    for prod_id, sandbox_id in company_mapping.items():
        print(f"🔄 Verifying company {prod_id} -> {sandbox_id}")
        
        # Get production company data
        prod_company = get_company_details(prod_token, prod_id, company_props)
        if not prod_company:
            print(f"  ❌ Could not fetch production company {prod_id}")
            continue
            
        # Get sandbox company data
        sandbox_company = get_company_details(sandbox_token, sandbox_id, company_props)
        if not sandbox_company:
            print(f"  ❌ Could not fetch sandbox company {sandbox_id}")
            continue
        
        prod_props = prod_company.get('properties', {})
        sandbox_props = sandbox_company.get('properties', {})
        
        company_name = prod_props.get('name', 'Unknown Company')
        print(f"  📋 {company_name}")
        
        # Compare properties
        mismatches = []
        missing_props = []
        
        for prop_name in company_props:
            prod_value = prod_props.get(prop_name)
            sandbox_value = sandbox_props.get(prop_name)
            
            # Clean values for comparison
            prod_clean = str(prod_value).strip() if prod_value else ''
            sandbox_clean = str(sandbox_value).strip() if sandbox_value else ''
            
            if prod_clean and not sandbox_clean:
                missing_props.append(f"{prop_name}: '{prod_value}' missing in sandbox")
            elif prod_clean != sandbox_clean:
                mismatches.append(f"{prop_name}: prod='{prod_value}' vs sandbox='{sandbox_value}'")
        
        if mismatches or missing_props:
            discrepancies.append({
                'company': company_name,
                'prod_id': prod_id,
                'sandbox_id': sandbox_id,
                'mismatches': mismatches,
                'missing': missing_props
            })
            print(f"  ⚠️  {len(mismatches)} mismatches, {len(missing_props)} missing properties")
        else:
            print(f"  ✅ All properties match")
        
        print()
    
    # Summary
    print("=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    if not discrepancies:
        print("🎉 All company properties are perfectly synchronized!")
        print("✅ Production and sandbox company data match exactly")
    else:
        print(f"⚠️  Found discrepancies in {len(discrepancies)} companies:")
        print()
        
        for disc in discrepancies:
            print(f"🏢 {disc['company']} ({disc['prod_id']} -> {disc['sandbox_id']})")
            for mismatch in disc['mismatches']:
                print(f"  🔸 {mismatch}")
            for missing in disc['missing']:
                print(f"  🔸 {missing}")
            print()

if __name__ == "__main__":
    verify_company_data()