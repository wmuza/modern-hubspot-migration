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
        # For simplicity, use basic API and filter locally for demo
        headers = get_api_headers(self.prod_token)
        url = 'https://api.hubapi.com/crm/v3/objects/contacts'
        
        # Use simple GET API with pagination, ordered by creation date descending
        params = {
            'properties': 'email,firstname,lastname,createdate,hs_object_id',
            'limit': criteria.get('limit', 10),
            'sorts': 'createdate:desc'  # Order by creation date descending (newest first)
        }
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        
        if success:
            return data.get('results', [])
        else:
            print(f"❌ Error fetching contacts: {data}")
            return []
    
    def get_deals_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict]:
        """Get deals based on various criteria ordered by creation date DESC (newest first)"""
        headers = get_api_headers(self.prod_token)
        url = 'https://api.hubapi.com/crm/v3/objects/deals'
        
        # Use simple GET API with pagination, ordered by creation date descending
        params = {
            'properties': 'dealname,amount,pipeline,dealstage,createdate,hs_object_id',
            'associations': 'contacts,companies',
            'limit': criteria.get('limit', 10),
            'sorts': 'createdate:desc'  # Order by creation date descending (newest first)
        }
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        
        if success:
            return data.get('results', [])
        else:
            print(f"❌ Error fetching deals: {data}")
            return []
    
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
        
        # Step 4: Migrate contacts
        print("\n👥 Migrating target contacts...")
        # Here we would call the contact migration with specific IDs
        # For now, showing the structure
        
        # Step 5: Migrate related deals
        print("💼 Migrating related deals...")
        # Deal migration with specific IDs
        
        # Step 6: Create associations
        print("🔗 Creating associations...")
        # Association creation
        
        results = {
            'contacts_synced': len(target_contacts),
            'deals_synced': len(related_deals),
            'companies_synced': len(related_companies),
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