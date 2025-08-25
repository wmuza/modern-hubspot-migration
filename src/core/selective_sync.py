#!/usr/bin/env python
"""
Selective Sync Manager
Enables targeted migration of specific contacts/deals with their related data only
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
from migrations.contact_migration import migrate_contacts
from migrations.deal_migrator import DealMigrator
from migrations.deal_association_migrator import DealAssociationMigrator
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set

class SelectiveSyncManager:
    def __init__(self, prod_token: str, sandbox_token: str):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.sync_metadata = {
            'sync_date': datetime.now().isoformat(),
            'sync_type': '',
            'primary_objects': [],
            'related_objects': {
                'contacts': [],
                'companies': [],
                'deals': []
            },
            'associations_created': [],
            'properties_synced': []
        }
    
    def get_contacts_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict]:
        """Get contacts based on various criteria ordered by creation date DESC (newest first)"""
        headers = get_api_headers(self.prod_token)
        
        # Priority 1: Specific contact IDs
        if 'contact_ids' in criteria and criteria['contact_ids']:
            print(f"📋 Fetching {len(criteria['contact_ids'])} specific contacts by ID...")
            return self._fetch_contacts_by_ids(criteria['contact_ids'])
        
        # Priority 2: Email domain filtering
        elif 'email_domains' in criteria and criteria['email_domains']:
            print(f"📧 Fetching contacts by email domains: {criteria['email_domains']}")
            return self._fetch_contacts_by_email_domains(criteria['email_domains'], criteria.get('limit'))
        
        # Priority 3: Date filtering  
        elif 'days_since_created' in criteria:
            from datetime import datetime, timedelta
            
            # Calculate the date threshold
            days_back = criteria['days_since_created']
            threshold_date = datetime.now() - timedelta(days=days_back)
            threshold_timestamp = int(threshold_date.timestamp() * 1000)  # HubSpot uses milliseconds
            
            # Use search API for date filtering (only get basic info first)
            url = 'https://api.hubapi.com/crm/v3/objects/contacts/search'
            
            payload = {
                'filterGroups': [{
                    'filters': [{
                        'propertyName': 'createdate',
                        'operator': 'GTE',
                        'value': threshold_timestamp
                    }]
                }],
                'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}],
                'properties': ['email', 'firstname', 'lastname', 'createdate', 'hs_object_id'],
                'limit': criteria.get('limit', 50)
            }
            
            success, data = make_hubspot_request('POST', url, headers, json_data=payload)
            
            if success:
                basic_contacts = data.get('results', [])
                print(f"📊 Date filter: Found {len(basic_contacts)} contacts created in last {criteria.get('days_since_created', 'all')} days")
                
                # Now fetch full contact data with all properties
                if basic_contacts:
                    print(f"📋 Fetching full contact properties...")
                    full_contacts = self._fetch_full_contact_properties(basic_contacts)
                    return full_contacts
                else:
                    return basic_contacts
            else:
                print(f"❌ Error fetching contacts by date: {data}")
                return []
        
        # Priority 4: General query with limit
        else:
            # Use simple GET API with pagination, ordered by creation date descending
            url = 'https://api.hubapi.com/crm/v3/objects/contacts'
            params = {
                'properties': 'email,firstname,lastname,createdate,hs_object_id',
                'limit': criteria.get('limit', 50),
                'sorts': 'createdate:desc'  # Order by creation date descending (newest first)
            }
            
            success, data = make_hubspot_request('GET', url, headers, params=params)
            
            if success:
                basic_contacts = data.get('results', [])
                print(f"📊 General query: Found {len(basic_contacts)} contacts (limit: {criteria.get('limit', 50)})")
                
                # Now fetch full contact data with all properties
                if basic_contacts:
                    print(f"📋 Fetching full contact properties...")
                    full_contacts = self._fetch_full_contact_properties(basic_contacts)
                    return full_contacts
                else:
                    return basic_contacts
            else:
                print(f"❌ Error fetching contacts: {data}")
                return []
    
    def _fetch_contacts_by_ids(self, contact_ids: List[str]) -> List[Dict]:
        """Fetch specific contacts by their IDs"""
        contacts = []
        headers = get_api_headers(self.prod_token)
        
        for contact_id in contact_ids:
            contact_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}'
            params = {
                'properties': 'email,firstname,lastname,createdate,hs_object_id'
            }
            
            success, contact_data = make_hubspot_request('GET', contact_url, headers, params=params)
            
            if success:
                contacts.append(contact_data)
                print(f"  ✅ Fetched contact {contact_id}")
            else:
                print(f"  ❌ Failed to fetch contact {contact_id}: {contact_data}")
            
            time.sleep(0.1)  # Rate limiting
        
        # Now fetch full properties for all found contacts
        if contacts:
            print(f"📋 Fetching full contact properties for {len(contacts)} contacts...")
            full_contacts = self._fetch_full_contact_properties(contacts)
            return full_contacts
        
        return contacts
    
    def _fetch_contacts_by_email_domains(self, email_domains: List[str], limit: int = None) -> List[Dict]:
        """Fetch contacts by email domains using search API with pagination to get ALL results"""
        headers = get_api_headers(self.prod_token)
        url = 'https://api.hubapi.com/crm/v3/objects/contacts/search'
        
        # Build OR filters for each email domain
        filters = []
        for domain in email_domains:
            filters.append({
                'propertyName': 'email',
                'operator': 'CONTAINS_TOKEN',
                'value': f'@{domain.strip().lstrip("@")}'
            })
        
        all_contacts = []
        after = None
        page = 1
        max_per_page = 100  # HubSpot max limit per request (but Search API might default to 50)
        
        # If limit is specified, use it; otherwise get all results
        total_limit = limit if limit else float('inf')
        
        while len(all_contacts) < total_limit:
            # Calculate how many to fetch in this request
            current_limit = min(max_per_page, total_limit - len(all_contacts)) if limit else max_per_page
            
            # HubSpot search API payload
            payload = {
                'filterGroups': [{
                    'filters': filters
                }],
                'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}],
                'properties': ['email', 'firstname', 'lastname', 'createdate', 'hs_object_id'],
                'limit': int(current_limit)
            }
            
            # Add pagination token if we have one
            if after:
                payload['after'] = after
            
            success, data = make_hubspot_request('POST', url, headers, json_data=payload)
            
            if success:
                page_results = data.get('results', [])
                all_contacts.extend(page_results)
                
                print(f"📊 Page {page}: Found {len(page_results)} contacts (Total so far: {len(all_contacts)})")
                
                # Check if there are more results
                paging = data.get('paging', {})
                next_page = paging.get('next', {})
                after = next_page.get('after') if next_page else None
                
                # Break if no more results or we've hit our limit
                if not after or len(page_results) == 0:
                    break
                
                page += 1
                time.sleep(0.2)  # Rate limiting between pages
                
            else:
                print(f"❌ Error fetching contacts by email domains (page {page}): {data}")
                break
        
        # Trim to exact limit if specified
        if limit and len(all_contacts) > limit:
            all_contacts = all_contacts[:limit]
        
        print(f"📊 Email domain filter: Found {len(all_contacts)} total contacts with domains {email_domains}")
        
        # Now fetch full contact data with all properties
        if all_contacts:
            print(f"📋 Fetching full contact properties...")
            full_contacts = self._fetch_full_contact_properties(all_contacts)
            return full_contacts
        else:
            return all_contacts
    
    def get_deals_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict]:
        """Get deals based on various criteria ordered by creation date DESC (newest first)"""
        headers = get_api_headers(self.prod_token)
        
        # Priority 1: Specific deal IDs
        if 'deal_ids' in criteria and criteria['deal_ids']:
            print(f"📋 Fetching {len(criteria['deal_ids'])} specific deals by ID...")
            return self._fetch_deals_by_ids(criteria['deal_ids'])
        
        # Priority 2: Date filtering
        elif 'days_since_created' in criteria:
            from datetime import datetime, timedelta
            
            # Calculate the date threshold
            days_back = criteria['days_since_created']
            threshold_date = datetime.now() - timedelta(days=days_back)
            threshold_timestamp = int(threshold_date.timestamp() * 1000)  # HubSpot uses milliseconds
            
            # Use search API for date filtering
            url = 'https://api.hubapi.com/crm/v3/objects/deals/search'
            
            payload = {
                'filterGroups': [{
                    'filters': [{
                        'propertyName': 'createdate',
                        'operator': 'GTE',
                        'value': threshold_timestamp
                    }]
                }],
                'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}],
                'properties': ['dealname', 'amount', 'pipeline', 'dealstage', 'createdate', 'hs_object_id'],
                'limit': criteria.get('limit', 50)
            }
            
            success, data = make_hubspot_request('POST', url, headers, json_data=payload)
            
            if success:
                deals = data.get('results', [])
                print(f"📊 Date filter: Found {len(deals)} deals created in last {criteria.get('days_since_created', 'all')} days")
                return deals
            else:
                print(f"❌ Error fetching deals by date: {data}")
                return []
        
        # Priority 3: General query with limit
        else:
            # Use simple GET API with pagination, ordered by creation date descending
            url = 'https://api.hubapi.com/crm/v3/objects/deals'
            params = {
                'properties': 'dealname,amount,pipeline,dealstage,createdate,hs_object_id',
                'associations': 'contacts,companies',
                'limit': criteria.get('limit', 50),
                'sorts': 'createdate:desc'  # Order by creation date descending (newest first)
            }
            
            success, data = make_hubspot_request('GET', url, headers, params=params)
            
            if success:
                deals = data.get('results', [])
                print(f"📊 General query: Found {len(deals)} deals (limit: {criteria.get('limit', 50)})")
                return deals
            else:
                print(f"❌ Error fetching deals: {data}")
                return []
    
    def _fetch_deals_by_ids(self, deal_ids: List[str]) -> List[Dict]:
        """Fetch specific deals by their IDs"""
        deals = []
        headers = get_api_headers(self.prod_token)
        
        for deal_id in deal_ids:
            deal_url = f'https://api.hubapi.com/crm/v3/objects/deals/{deal_id}'
            params = {
                'properties': 'dealname,amount,pipeline,dealstage,createdate,hs_object_id',
                'associations': 'contacts,companies'
            }
            
            success, deal_data = make_hubspot_request('GET', deal_url, headers, params=params)
            
            if success:
                deals.append(deal_data)
                print(f"  ✅ Fetched deal {deal_id}")
            else:
                print(f"  ❌ Failed to fetch deal {deal_id}: {deal_data}")
            
            time.sleep(0.1)  # Rate limiting
        
        print(f"📊 ID filter: Successfully fetched {len(deals)}/{len(deal_ids)} deals")
        return deals
    
    def get_related_deals_for_contacts(self, contact_ids: List[str]) -> List[Dict]:
        """Get all deals associated with specific contacts"""
        related_deals = []
        
        for contact_id in contact_ids:
            headers = get_api_headers(self.prod_token)
            url = f'https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}/associations/deals'
            
            success, data = make_hubspot_request('GET', url, headers)
            
            if success:
                deal_ids = [result['id'] for result in data.get('results', [])]
                
                # Get deal details
                for deal_id in deal_ids:
                    deal_url = f'https://api.hubapi.com/crm/v3/objects/deals/{deal_id}'
                    deal_params = {
                        'properties': 'dealname,amount,pipeline,dealstage,createdate',
                        'associations': 'contacts,companies'
                    }
                    
                    deal_success, deal_data = make_hubspot_request('GET', deal_url, headers, params=deal_params)
                    
                    if deal_success:
                        related_deals.append(deal_data)
                    
                    time.sleep(0.1)  # Rate limiting
            
            time.sleep(0.1)  # Rate limiting
        
        return related_deals
    
    def get_related_contacts_for_deals(self, deal_ids: List[str]) -> List[Dict]:
        """Get all contacts associated with specific deals"""
        related_contacts = []
        
        for deal_id in deal_ids:
            headers = get_api_headers(self.prod_token)
            url = f'https://api.hubapi.com/crm/v3/objects/deals/{deal_id}/associations/contacts'
            
            success, data = make_hubspot_request('GET', url, headers)
            
            if success:
                contact_ids = [result['id'] for result in data.get('results', [])]
                
                # Get contact details
                for contact_id in contact_ids:
                    contact_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}'
                    contact_params = {
                        'properties': 'email,firstname,lastname,createdate,lifecyclestage'
                    }
                    
                    contact_success, contact_data = make_hubspot_request('GET', contact_url, headers, params=contact_params)
                    
                    if contact_success:
                        related_contacts.append(contact_data)
                    
                    time.sleep(0.1)  # Rate limiting
            
            time.sleep(0.1)  # Rate limiting
        
        return related_contacts
    
    def get_related_companies_for_contacts(self, contact_ids: List[str]) -> List[Dict]:
        """Get all companies associated with specific contacts"""
        related_companies = []
        
        for contact_id in contact_ids:
            headers = get_api_headers(self.prod_token)
            url = f'https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}/associations/companies'
            
            success, data = make_hubspot_request('GET', url, headers)
            
            if success:
                company_ids = [result['id'] for result in data.get('results', [])]
                
                # Get company details
                for company_id in company_ids:
                    company_url = f'https://api.hubapi.com/crm/v3/objects/companies/{company_id}'
                    company_params = {
                        'properties': 'name,domain,createdate,city,state'
                    }
                    
                    company_success, company_data = make_hubspot_request('GET', company_url, headers, params=company_params)
                    
                    if company_success:
                        related_companies.append(company_data)
                    
                    time.sleep(0.1)  # Rate limiting
            
            time.sleep(0.1)  # Rate limiting
        
        return related_companies
    
    def _fetch_full_contact_properties(self, basic_contacts: List[Dict]) -> List[Dict]:
        """Fetch full contact data with all properties"""
        from core.field_filters import HubSpotFieldFilter
        
        # Get all writable properties for comprehensive data fetching
        filter_system = HubSpotFieldFilter()
        headers = get_api_headers(self.prod_token)
        
        # Get writable properties list
        url = 'https://api.hubapi.com/crm/v3/properties/contacts'
        success, data = make_hubspot_request('GET', url, headers)
        
        if not success:
            print(f"  ⚠️  Could not fetch property list, using basic contacts")
            return basic_contacts
            
        properties = data.get('results', [])
        safe_props = filter_system.get_safe_properties_list(properties)
        
        print(f"  📊 Fetching {len(safe_props)} properties for {len(basic_contacts)} contacts")
        
        # Fetch full contact data for each contact
        full_contacts = []
        for contact in basic_contacts:
            contact_id = contact['id']
            contact_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}'
            
            params = {
                'properties': ','.join(safe_props)
            }
            
            success, full_contact_data = make_hubspot_request('GET', contact_url, headers, params=params)
            
            if success:
                full_contacts.append(full_contact_data)
            else:
                print(f"  ⚠️  Could not fetch full data for contact {contact_id}, using basic data")
                full_contacts.append(contact)
                
            time.sleep(0.1)  # Rate limiting
        
        print(f"  ✅ Fetched full property data for {len(full_contacts)} contacts")
        return full_contacts
    
    def _verify_and_fix_contact_properties(self, sandbox_contact_id: str, original_contact: Dict[str, Any]) -> bool:
        """Verify all properties were transferred correctly and fix missing ones"""
        print(f"    🔍 Verifying properties for contact {sandbox_contact_id}...")
        
        from core.field_filters import HubSpotFieldFilter
        
        # Get the contact from sandbox
        headers = get_api_headers(self.sandbox_token)
        sandbox_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{sandbox_contact_id}'
        
        # Get all properties for comparison
        filter_system = HubSpotFieldFilter()
        
        # Get writable properties list
        props_url = 'https://api.hubapi.com/crm/v3/properties/contacts'
        props_success, props_data = make_hubspot_request('GET', props_url, headers)
        
        if not props_success:
            print(f"    ❌ Could not fetch properties list for verification")
            return False
            
        properties = props_data.get('results', [])
        safe_props = filter_system.get_safe_properties_list(properties)
        
        params = {
            'properties': ','.join(safe_props)
        }
        
        success, sandbox_data = make_hubspot_request('GET', sandbox_url, headers, params=params)
        
        if not success:
            print(f"    ❌ Could not fetch sandbox contact data for verification")
            return False
        
        # Compare properties
        original_props = original_contact.get('properties', {})
        sandbox_props = sandbox_data.get('properties', {})
        
        missing_props = {}
        different_props = {}
        
        # Check important properties specifically
        key_properties = ['phone', 'mobilephone', 'company', 'jobtitle', 'website', 'city', 'state', 'country']
        
        for prop_name, prop_value in original_props.items():
            if prop_name in safe_props and prop_value:  # Only check non-empty values
                sandbox_value = sandbox_props.get(prop_name)
                
                if not sandbox_value:
                    missing_props[prop_name] = prop_value
                elif str(sandbox_value).strip() != str(prop_value).strip():
                    different_props[prop_name] = {
                        'original': prop_value,
                        'sandbox': sandbox_value
                    }
        
        # Report findings
        if missing_props or different_props:
            print(f"    ⚠️  Property verification issues found:")
            
            if missing_props:
                print(f"      📋 Missing properties: {len(missing_props)}")
                for prop, value in list(missing_props.items())[:5]:  # Show first 5
                    print(f"        • {prop}: {str(value)[:50]}")
                if len(missing_props) > 5:
                    print(f"        ... and {len(missing_props)-5} more")
            
            if different_props:
                print(f"      🔄 Different values: {len(different_props)}")
                for prop, values in list(different_props.items())[:3]:  # Show first 3
                    print(f"        • {prop}: '{values['original']}' vs '{values['sandbox']}'")
            
            # Fix missing properties
            if missing_props:
                print(f"    🔧 Fixing {len(missing_props)} missing properties...")
                
                # Filter the missing properties through the field filter
                filtered_missing = filter_system.filter_contact_properties(missing_props, is_update=True)
                
                if filtered_missing:
                    update_payload = {'properties': filtered_missing}
                    update_success, update_result = make_hubspot_request('PATCH', sandbox_url, headers, json_data=update_payload)
                    
                    if update_success:
                        print(f"    ✅ Successfully updated {len(filtered_missing)} properties")
                        return True
                    else:
                        print(f"    ❌ Failed to update properties: {update_result}")
                        return False
                else:
                    print(f"    ℹ️  No properties needed updating after filtering")
                    return True
            else:
                print(f"    ℹ️  Only value differences found, no missing properties to fix")
                return True
        else:
            print(f"    ✅ All properties verified successfully")
            return True

    def selective_sync_contacts_with_deals(self, contact_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Sync specific contacts and their associated deals"""
        print("🎯 SELECTIVE SYNC: CONTACTS → DEALS")
        print("=" * 50)
        
        self.sync_metadata['sync_type'] = 'contacts_with_deals'
        
        # Step 1: Get target contacts
        print("📥 Fetching target contacts...")
        target_contacts = self.get_contacts_by_criteria(contact_criteria)
        contact_ids = [contact['id'] for contact in target_contacts]
        
        print(f"✅ Found {len(target_contacts)} target contacts")
        self.sync_metadata['primary_objects'] = contact_ids
        
        # Step 2: Get related deals
        print("📊 Fetching related deals...")
        related_deals = self.get_related_deals_for_contacts(contact_ids)
        deal_ids = [deal['id'] for deal in related_deals]
        
        print(f"✅ Found {len(related_deals)} related deals")
        self.sync_metadata['related_objects']['deals'] = deal_ids
        
        # Step 3: Get related companies
        print("🏢 Fetching related companies...")
        related_companies = self.get_related_companies_for_contacts(contact_ids)
        company_ids = [company['id'] for company in related_companies]
        
        print(f"✅ Found {len(related_companies)} related companies")
        self.sync_metadata['related_objects']['companies'] = company_ids
        
        # Step 4: Migrate companies first (so they exist for associations)
        print("\n🏢 Migrating related companies...")
        companies_migrated = 0
        if related_companies:
            companies_migrated = self._migrate_specific_companies(related_companies)
        
        # Step 5: Migrate contacts
        print("\n👥 Migrating target contacts...")
        contacts_migrated = 0
        if target_contacts:
            contacts_migrated = self._migrate_specific_contacts(target_contacts)
        
        # Step 6: Migrate related deals  
        print("💼 Migrating related deals...")
        deals_migrated = 0
        deal_id_mapping = {}
        if related_deals:
            deals_migrated, deal_id_mapping = self._migrate_specific_deals(related_deals)
        
        # Step 7: Create associations
        print("🔗 Creating associations...")
        associations_created = 0
        
        # Add delay to allow HubSpot to index the newly created contacts
        if contacts_migrated > 0 or deals_migrated > 0:
            print("  ⏳ Waiting for HubSpot to index new records...")
            time.sleep(3)  # 3 second delay for indexing
        
        if contact_ids and (deal_ids or company_ids):
            associations_created = self._create_selective_associations(contact_ids, deal_ids, company_ids, deal_id_mapping)
        
        results = {
            'contacts_synced': contacts_migrated,
            'deals_synced': deals_migrated,
            'companies_synced': companies_migrated,
            'associations_created': associations_created,
            'sync_metadata': self.sync_metadata
        }
        
        return results
    
    def selective_sync_deals_with_contacts(self, deal_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Sync specific deals and their associated contacts"""
        print("🎯 SELECTIVE SYNC: DEALS → CONTACTS")
        print("=" * 50)
        
        self.sync_metadata['sync_type'] = 'deals_with_contacts'
        
        # Step 1: Get target deals
        print("📥 Fetching target deals...")
        target_deals = self.get_deals_by_criteria(deal_criteria)
        deal_ids = [deal['id'] for deal in target_deals]
        
        print(f"✅ Found {len(target_deals)} target deals")
        self.sync_metadata['primary_objects'] = deal_ids
        
        # Step 2: Get related contacts
        print("👥 Fetching related contacts...")
        related_contacts = self.get_related_contacts_for_deals(deal_ids)
        contact_ids = [contact['id'] for contact in related_contacts]
        
        print(f"✅ Found {len(related_contacts)} related contacts")
        self.sync_metadata['related_objects']['contacts'] = contact_ids
        
        # Step 3: Get related companies (from contacts)
        print("🏢 Fetching related companies...")
        related_companies = self.get_related_companies_for_contacts(contact_ids)
        company_ids = [company['id'] for company in related_companies]
        
        print(f"✅ Found {len(related_companies)} related companies")
        self.sync_metadata['related_objects']['companies'] = company_ids
        
        results = {
            'deals_synced': len(target_deals),
            'contacts_synced': len(related_contacts),
            'companies_synced': len(related_companies),
            'sync_metadata': self.sync_metadata
        }
        
        return results
    
    def save_selective_sync_report(self, results: Dict[str, Any]) -> str:
        """Save selective sync report with metadata for rollback"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'timestamp': timestamp,
            'sync_date': datetime.now().isoformat(),
            'sync_type': results['sync_metadata']['sync_type'],
            'summary': {
                'contacts_synced': results.get('contacts_synced', 0),
                'deals_synced': results.get('deals_synced', 0), 
                'companies_synced': results.get('companies_synced', 0)
            },
            'sync_metadata': results['sync_metadata'],
            'rollback_info': {
                'primary_objects': results['sync_metadata']['primary_objects'],
                'related_objects': results['sync_metadata']['related_objects'],
                'can_rollback': True
            }
        }
        
        # Save report
        os.makedirs('reports', exist_ok=True)
        report_file = f'reports/selective_sync_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file
    
    def _migrate_specific_contacts(self, contacts: List[Dict]) -> int:
        """Migrate specific contacts to sandbox"""
        print(f"  📞 Migrating {len(contacts)} contacts...")
        
        # Import contact migration functions
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
        from contact_migration import (
            get_writable_properties, find_contact_by_email, 
            create_contact_in_sandbox, update_contact_in_sandbox,
            get_contact_display_name, print_progress_bar
        )
        from core.field_filters import HubSpotFieldFilter
        
        migrated_count = 0
        
        try:
            # Initialize field filtering
            filter_system = HubSpotFieldFilter()
            
            # Get writable properties
            writable_props = get_writable_properties(self.sandbox_token, filter_system)
            print(f"    📊 Using {len(writable_props)} safe properties")
            
            # Migrate each specific contact
            for i, contact in enumerate(contacts, 1):
                email = contact.get('properties', {}).get('email')
                display_name = get_contact_display_name(contact)
                
                print_progress_bar(i-1, len(contacts), "Migrating contacts")
                
                if email:
                    # Contact with email - check for duplicates
                    print(f"    📧 {display_name} ({email})")
                    
                    # Check if contact exists in sandbox
                    existing_id = find_contact_by_email(self.sandbox_token, email)
                    
                    if existing_id:
                        # Update existing contact
                        success, _ = update_contact_in_sandbox(self.sandbox_token, existing_id, contact, filter_system)
                        if success:
                            print(f"      🔄 Updated existing contact (ID: {existing_id})")
                            migrated_count += 1
                            
                            # Verify and fix properties
                            time.sleep(0.5)  # Brief delay before verification
                            self._verify_and_fix_contact_properties(existing_id, contact)
                    else:
                        # Create new contact
                        success, new_id = create_contact_in_sandbox(self.sandbox_token, contact, filter_system)
                        if success:
                            print(f"      ✅ Created new contact (ID: {new_id})")
                            migrated_count += 1
                            
                            # Verify and fix properties
                            time.sleep(0.5)  # Brief delay before verification
                            self._verify_and_fix_contact_properties(new_id, contact)
                        else:
                            print(f"      ❌ Failed to create contact: {new_id}")
                else:
                    # Contact without email - create directly (no duplicate checking possible)
                    print(f"    👤 {display_name} (no email)")
                    
                    # Create new contact without duplicate checking
                    success, new_id = create_contact_in_sandbox(self.sandbox_token, contact, filter_system)
                    if success:
                        print(f"      ✅ Created new contact (ID: {new_id})")
                        migrated_count += 1
                        
                        # Verify and fix properties
                        time.sleep(0.5)  # Brief delay before verification
                        self._verify_and_fix_contact_properties(new_id, contact)
                    else:
                        print(f"      ❌ Failed to create contact: {new_id}")
            
            print_progress_bar(len(contacts), len(contacts), "Migrating contacts")
            print(f"  ✅ Successfully migrated {migrated_count}/{len(contacts)} contacts")
            
        except Exception as e:
            print(f"  ❌ Contact migration failed: {str(e)}")
            
        return migrated_count
    
    def _migrate_specific_companies(self, companies: List[Dict]) -> int:
        """Migrate specific companies to sandbox"""
        print(f"  🏢 Migrating {len(companies)} companies...")
        
        migrated_count = 0
        headers = get_api_headers(self.sandbox_token)
        
        try:
            for i, company in enumerate(companies, 1):
                company_props = company.get('properties', {})
                domain = (company_props.get('domain') or '').strip()
                name = (company_props.get('name') or '').strip()
                
                print(f"    🏢 {name or 'Unnamed Company'} ({domain or 'no domain'})")
                
                # Check if company already exists in sandbox
                existing_company_id = None
                if domain:
                    existing_company_id = self._find_company_by_domain(domain)
                elif name:
                    existing_company_id = self._find_company_by_name(name)
                
                if existing_company_id:
                    print(f"      🔄 Company already exists (ID: {existing_company_id})")
                    migrated_count += 1
                else:
                    # Create new company
                    success, new_company_id = self._create_company_in_sandbox(company)
                    if success:
                        print(f"      ✅ Created new company (ID: {new_company_id})")
                        migrated_count += 1
                    else:
                        print(f"      ❌ Failed to create company: {new_company_id}")
                
                time.sleep(0.2)  # Rate limiting
            
            print(f"  ✅ Successfully migrated {migrated_count}/{len(companies)} companies")
            
        except Exception as e:
            print(f"  ❌ Company migration failed: {str(e)}")
            
        return migrated_count
    
    def _find_company_by_domain(self, domain: str) -> Optional[str]:
        """Find a company in sandbox by domain"""
        headers = get_api_headers(self.sandbox_token)
        search_url = 'https://api.hubapi.com/crm/v3/objects/companies/search'
        
        search_payload = {
            'filterGroups': [{
                'filters': [{
                    'propertyName': 'domain',
                    'operator': 'EQ',
                    'value': domain
                }]
            }],
            'properties': ['domain', 'name'],
            'limit': 1
        }
        
        success, search_data = make_hubspot_request('POST', search_url, headers, json_data=search_payload)
        
        if success:
            results = search_data.get('results', [])
            return results[0]['id'] if results else None
        
        return None
    
    def _find_company_by_name(self, name: str) -> Optional[str]:
        """Find a company in sandbox by name"""
        headers = get_api_headers(self.sandbox_token)
        search_url = 'https://api.hubapi.com/crm/v3/objects/companies/search'
        
        search_payload = {
            'filterGroups': [{
                'filters': [{
                    'propertyName': 'name',
                    'operator': 'EQ',
                    'value': name
                }]
            }],
            'properties': ['domain', 'name'],
            'limit': 1
        }
        
        success, search_data = make_hubspot_request('POST', search_url, headers, json_data=search_payload)
        
        if success:
            results = search_data.get('results', [])
            return results[0]['id'] if results else None
        
        return None
    
    def _create_company_in_sandbox(self, company: Dict[str, Any]) -> tuple[bool, str]:
        """Create a new company in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/companies'
        
        # Filter properties to only include safe ones
        company_props = company.get('properties', {})
        
        # Common company properties that are usually safe
        safe_company_props = {}
        safe_fields = ['name', 'domain', 'city', 'state', 'country', 'industry', 'phone', 'website']
        
        for field in safe_fields:
            if field in company_props and company_props[field]:
                safe_company_props[field] = company_props[field]
        
        if not safe_company_props:
            return False, "No safe properties to migrate"
        
        payload = {'properties': safe_company_props}
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            return True, data.get('id', 'unknown')
        else:
            error_msg = data.get('error', str(data)) if isinstance(data, dict) else str(data)
            return False, error_msg
    
    def _migrate_specific_deals(self, deals: List[Dict]) -> tuple[int, Dict[str, str]]:
        """Migrate specific deals to sandbox and return mapping of old to new IDs"""
        print(f"  💼 Migrating {len(deals)} deals...")
        
        migrated_count = 0
        deal_id_mapping = {}  # production_deal_id -> sandbox_deal_id
        headers = get_api_headers(self.sandbox_token)
        
        try:
            for i, deal in enumerate(deals, 1):
                deal_props = deal.get('properties', {})
                deal_name = (deal_props.get('dealname') or '').strip()
                amount = deal_props.get('amount', '')
                stage = deal_props.get('dealstage', '')
                production_deal_id = deal['id']
                
                print(f"    💼 [{i}/{len(deals)}] {deal_name} (${amount})")
                
                # Check if deal already exists in sandbox
                existing_deal_id = self._find_deal_by_name_and_amount(deal_name, amount)
                
                if existing_deal_id:
                    print(f"      🔄 Deal already exists (ID: {existing_deal_id})")
                    deal_id_mapping[production_deal_id] = existing_deal_id
                    migrated_count += 1
                else:
                    # Create new deal
                    success, new_deal_id = self._create_deal_in_sandbox(deal)
                    if success:
                        print(f"      ✅ Created new deal (ID: {new_deal_id})")
                        deal_id_mapping[production_deal_id] = new_deal_id
                        migrated_count += 1
                    else:
                        print(f"      ❌ Failed to create deal: {new_deal_id}")
                
                time.sleep(0.2)  # Rate limiting
            
            print(f"  ✅ Successfully migrated {migrated_count}/{len(deals)} deals")
            print(f"  📋 Deal ID mapping: {len(deal_id_mapping)} deals mapped")
            
        except Exception as e:
            print(f"  ❌ Deal migration failed: {str(e)}")
            
        return migrated_count, deal_id_mapping
    
    def _find_deal_by_name_and_amount(self, deal_name: str, amount: str) -> Optional[str]:
        """Find a deal in sandbox by name and amount"""
        if not deal_name:
            return None
            
        headers = get_api_headers(self.sandbox_token)
        search_url = 'https://api.hubapi.com/crm/v3/objects/deals/search'
        
        # Primary filter: exact deal name match
        filters = [{
            'propertyName': 'dealname',
            'operator': 'EQ',
            'value': deal_name
        }]
        
        # Secondary filter: amount if available
        if amount:
            filters.append({
                'propertyName': 'amount',
                'operator': 'EQ',
                'value': amount
            })
        
        search_payload = {
            'filterGroups': [{'filters': filters}],
            'properties': ['dealname', 'amount', 'dealstage'],
            'limit': 1
        }
        
        success, search_data = make_hubspot_request('POST', search_url, headers, json_data=search_payload)
        
        if success:
            results = search_data.get('results', [])
            return results[0]['id'] if results else None
        
        return None
    
    def _create_deal_in_sandbox(self, deal: Dict[str, Any]) -> tuple[bool, str]:
        """Create a new deal in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/deals'
        
        # Filter properties to only include safe ones
        deal_props = deal.get('properties', {})
        
        # Common deal properties that are usually safe
        safe_deal_props = {}
        safe_fields = ['dealname', 'amount', 'dealstage', 'pipeline', 'closedate', 'createdate']
        
        for field in safe_fields:
            if field in deal_props and deal_props[field]:
                safe_deal_props[field] = deal_props[field]
        
        if not safe_deal_props:
            return False, "No safe properties to migrate"
        
        # Ensure we have a pipeline - use default if not specified
        if 'pipeline' not in safe_deal_props:
            safe_deal_props['pipeline'] = 'default'  # HubSpot will use the default pipeline
        
        payload = {'properties': safe_deal_props}
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            return True, data.get('id', 'unknown')
        else:
            error_msg = data.get('error', str(data)) if isinstance(data, dict) else str(data)
            return False, error_msg
    
    def _create_selective_associations(self, contact_ids: List[str], deal_ids: List[str], company_ids: List[str], deal_id_mapping: Dict[str, str] = None) -> int:
        """Create associations between migrated objects using proper association API"""
        print(f"  🔗 Creating associations between migrated objects...")
        
        associations_created = 0
        headers = get_api_headers(self.sandbox_token)
        
        # Get the mapping of old IDs to new sandbox IDs
        old_to_new_contacts = self._get_contact_id_mapping(contact_ids)
        
        # Use the provided deal mapping instead of searching again
        old_to_new_deals = deal_id_mapping if deal_id_mapping else {}
        
        old_to_new_companies = self._get_company_id_mapping(company_ids) if company_ids else {}
        
        print(f"    📋 ID Mappings: {len(old_to_new_contacts)} contacts, {len(old_to_new_deals)} deals, {len(old_to_new_companies)} companies")
        
        # Create contact-to-company associations
        if old_to_new_contacts and old_to_new_companies:
            print(f"    🏢 Creating contact-to-company associations...")
            
            # Get original associations from production
            for prod_contact_id in contact_ids:
                if prod_contact_id in old_to_new_contacts:
                    sandbox_contact_id = old_to_new_contacts[prod_contact_id]
                    
                    # Find companies associated with this contact in production
                    prod_headers = get_api_headers(self.prod_token)
                    assoc_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{prod_contact_id}/associations/companies'
                    
                    success, assoc_data = make_hubspot_request('GET', assoc_url, prod_headers)
                    
                    if success:
                        prod_company_ids = [result['id'] for result in assoc_data.get('results', [])]
                        
                        # Create associations in sandbox
                        for prod_company_id in prod_company_ids:
                            if prod_company_id in old_to_new_companies:
                                sandbox_company_id = old_to_new_companies[prod_company_id]
                                
                                if self._create_association(sandbox_contact_id, sandbox_company_id, 'contacts', 'companies'):
                                    associations_created += 1
                    
                    time.sleep(0.1)  # Rate limiting
        
        # Create contact-to-deal associations  
        if old_to_new_contacts and old_to_new_deals:
            print(f"    💼 Creating contact-to-deal associations...")
            
            # Get original associations from production
            for prod_contact_id in contact_ids:
                if prod_contact_id in old_to_new_contacts:
                    sandbox_contact_id = old_to_new_contacts[prod_contact_id]
                    
                    # Find deals associated with this contact in production
                    prod_headers = get_api_headers(self.prod_token)
                    assoc_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{prod_contact_id}/associations/deals'
                    
                    success, assoc_data = make_hubspot_request('GET', assoc_url, prod_headers)
                    
                    if success:
                        prod_deal_ids = [result['id'] for result in assoc_data.get('results', [])]
                        
                        # Create associations in sandbox
                        for prod_deal_id in prod_deal_ids:
                            if prod_deal_id in old_to_new_deals:
                                sandbox_deal_id = old_to_new_deals[prod_deal_id]
                                
                                if self._create_association(sandbox_contact_id, sandbox_deal_id, 'contacts', 'deals'):
                                    associations_created += 1
                    
                    time.sleep(0.1)  # Rate limiting
        
        print(f"  ✅ Created {associations_created} associations successfully")
        return associations_created
    
    def _get_contact_id_mapping(self, prod_contact_ids: List[str]) -> Dict[str, str]:
        """Get mapping from production contact IDs to sandbox contact IDs"""
        mapping = {}
        
        # Import contact search function
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
        from contact_migration import find_contact_by_email
        
        prod_headers = get_api_headers(self.prod_token)
        
        for prod_id in prod_contact_ids:
            # Get email from production contact
            prod_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{prod_id}'
            success, prod_data = make_hubspot_request('GET', prod_url, prod_headers, params={'properties': 'email'})
            
            if success:
                email = prod_data.get('properties', {}).get('email')
                if email:
                    sandbox_id = find_contact_by_email(self.sandbox_token, email)
                    if sandbox_id:
                        mapping[prod_id] = sandbox_id
            
            time.sleep(0.1)  # Rate limiting
        
        return mapping
    
    def _get_deal_id_mapping(self, prod_deal_ids: List[str]) -> Dict[str, str]:
        """Get mapping from production deal IDs to sandbox deal IDs"""
        mapping = {}
        
        prod_headers = get_api_headers(self.prod_token)
        sandbox_headers = get_api_headers(self.sandbox_token)
        
        for prod_id in prod_deal_ids:
            # Get deal details from production
            prod_url = f'https://api.hubapi.com/crm/v3/objects/deals/{prod_id}'
            success, prod_data = make_hubspot_request('GET', prod_url, prod_headers, params={'properties': 'dealname,amount,createdate'})
            
            if success:
                deal_name = prod_data.get('properties', {}).get('dealname', '').strip()
                amount = prod_data.get('properties', {}).get('amount')
                
                if deal_name:
                    # Search for deal in sandbox by name and amount
                    search_url = 'https://api.hubapi.com/crm/v3/objects/deals/search'
                    
                    # Primary filter: exact deal name match
                    filters = [{
                        'propertyName': 'dealname',
                        'operator': 'EQ',
                        'value': deal_name
                    }]
                    
                    # Secondary filter: amount if available
                    if amount:
                        filters.append({
                            'propertyName': 'amount',
                            'operator': 'EQ',
                            'value': amount
                        })
                    
                    search_payload = {
                        'filterGroups': [{'filters': filters}],
                        'properties': ['dealname', 'amount', 'createdate'],
                        'limit': 1
                    }
                    
                    search_success, search_data = make_hubspot_request('POST', search_url, sandbox_headers, json_data=search_payload)
                    
                    if search_success:
                        results = search_data.get('results', [])
                        if results:
                            sandbox_deal = results[0]
                            sandbox_id = sandbox_deal['id']
                            mapping[prod_id] = sandbox_id
                            print(f"      🔗 Mapped deal '{deal_name}' ({prod_id} → {sandbox_id})")
                        else:
                            # Try fuzzy matching by name only if exact match failed
                            name_only_filters = [{
                                'propertyName': 'dealname',
                                'operator': 'CONTAINS_TOKEN',
                                'value': deal_name
                            }]
                            
                            fuzzy_payload = {
                                'filterGroups': [{'filters': name_only_filters}],
                                'properties': ['dealname', 'amount', 'createdate'],
                                'limit': 5  # Get top 5 potential matches
                            }
                            
                            fuzzy_success, fuzzy_data = make_hubspot_request('POST', search_url, sandbox_headers, json_data=fuzzy_payload)
                            
                            if fuzzy_success:
                                fuzzy_results = fuzzy_data.get('results', [])
                                # Take the first fuzzy match if available
                                if fuzzy_results:
                                    best_match = fuzzy_results[0]
                                    sandbox_id = best_match['id']
                                    mapping[prod_id] = sandbox_id
                                    print(f"      🔗 Fuzzy mapped deal '{deal_name}' ({prod_id} → {sandbox_id})")
                                else:
                                    print(f"      ❌ No match found for deal '{deal_name}' ({prod_id})")
                            else:
                                print(f"      ❌ Fuzzy search failed for deal '{deal_name}' ({prod_id})")
                    else:
                        print(f"      ❌ Search failed for deal '{deal_name}' ({prod_id}): {search_data}")
                else:
                    print(f"      ⚠️  Deal {prod_id} has no name, skipping mapping")
            else:
                print(f"      ❌ Failed to fetch production deal {prod_id}: {prod_data}")
            
            time.sleep(0.1)  # Rate limiting
        
        print(f"    📋 Deal mapping: {len(mapping)}/{len(prod_deal_ids)} deals mapped")
        return mapping
    
    def _get_company_id_mapping(self, prod_company_ids: List[str]) -> Dict[str, str]:
        """Get mapping from production company IDs to sandbox company IDs"""
        mapping = {}
        
        prod_headers = get_api_headers(self.prod_token)
        sandbox_headers = get_api_headers(self.sandbox_token)
        
        for prod_id in prod_company_ids:
            # Get company domain from production
            prod_url = f'https://api.hubapi.com/crm/v3/objects/companies/{prod_id}'
            success, prod_data = make_hubspot_request('GET', prod_url, prod_headers, params={'properties': 'domain,name'})
            
            if success:
                domain = prod_data.get('properties', {}).get('domain')
                name = prod_data.get('properties', {}).get('name')
                
                if domain or name:
                    # Search for company in sandbox by domain or name
                    search_url = 'https://api.hubapi.com/crm/v3/objects/companies/search'
                    
                    filters = []
                    if domain:
                        filters.append({'propertyName': 'domain', 'operator': 'EQ', 'value': domain})
                    elif name:
                        filters.append({'propertyName': 'name', 'operator': 'EQ', 'value': name})
                    
                    if filters:
                        search_payload = {
                            'filterGroups': [{'filters': filters}],
                            'properties': ['domain', 'name'],
                            'limit': 1
                        }
                        
                        search_success, search_data = make_hubspot_request('POST', search_url, sandbox_headers, json_data=search_payload)
                        
                        if search_success:
                            results = search_data.get('results', [])
                            if results:
                                mapping[prod_id] = results[0]['id']
            
            time.sleep(0.1)  # Rate limiting
        
        return mapping
    
    def _create_association(self, from_object_id: str, to_object_id: str, from_type: str, to_type: str) -> bool:
        """Create an association between two objects using HubSpot batch associations API"""
        headers = get_api_headers(self.sandbox_token)
        
        # Try using the batch associations API which is more reliable
        # This API allows creating multiple associations at once but we'll use it for single ones too
        batch_url = f'https://api.hubapi.com/crm/v3/associations/{from_type}/{to_type}/batch/create'
        
        # The batch API requires specific payload format
        payload = {
            "inputs": [
                {
                    "from": {
                        "id": from_object_id
                    },
                    "to": {
                        "id": to_object_id
                    },
                    "type": "contact_to_deal" if from_type == "contacts" and to_type == "deals" else 
                            "deal_to_contact" if from_type == "deals" and to_type == "contacts" else
                            "contact_to_company" if from_type == "contacts" and to_type == "companies" else
                            "company_to_contact" if from_type == "companies" and to_type == "contacts" else
                            "company_to_deal" if from_type == "companies" and to_type == "deals" else
                            "deal_to_company"
                }
            ]
        }
        
        print(f"      🔗 Creating {from_type} {from_object_id} → {to_type} {to_object_id}")
        
        success, result = make_hubspot_request('POST', batch_url, headers, json_data=payload)
        
        if success:
            # Check if the association was created
            if isinstance(result, dict):
                status = result.get('status', 'COMPLETE')
                results_list = result.get('results', [])
                if results_list and len(results_list) > 0:
                    print(f"      ✅ Association created successfully")
                    return True
                elif status == 'COMPLETE':
                    print(f"      ✅ Association created")
                    return True
            print(f"      ✅ Association request completed")
            return True
        else:
            # Check for specific error codes
            if isinstance(result, dict):
                status_code = result.get('status_code', 0)
                error_msg = result.get('error', {})
                
                if status_code == 409:
                    print(f"      ℹ️  Association already exists")
                    return True  # Already exists, that's fine
                elif status_code == 404:
                    print(f"      ❌ One of the objects not found: {from_object_id} or {to_object_id}")
                    return False
                elif status_code == 400:
                    # Parse the error message
                    if 'message' in error_msg:
                        error_detail = error_msg.get('message', '')
                        if 'already exists' in error_detail.lower():
                            print(f"      ℹ️  Association already exists")
                            return True
                        else:
                            print(f"      ❌ Bad request: {error_detail}")
                    print(f"      🔍 URL: {batch_url}")
                    print(f"      🔍 Payload: {payload}")
                else:
                    print(f"      ❌ Failed to create {from_type}-{to_type} association: {result}")
                    print(f"      🔍 URL: {batch_url}")
                    print(f"      🔍 Payload: {payload}")
            else:
                print(f"      ❌ Failed to create association: {result}")
                
            return False

def main():
    """Demo function for selective sync"""
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    if not prod_token or not sandbox_token:
        print("❌ Error: API tokens not found in .env file")
        return
    
    manager = SelectiveSyncManager(prod_token, sandbox_token)
    
    # Example: Sync contacts created in last 7 days with their deals
    contact_criteria = {
        'days_since_created': 7,
        'limit': 10
    }
    
    results = manager.selective_sync_contacts_with_deals(contact_criteria)
    report_file = manager.save_selective_sync_report(results)
    
    print(f"\n📄 Selective sync report saved: {report_file}")

if __name__ == "__main__":
    main()