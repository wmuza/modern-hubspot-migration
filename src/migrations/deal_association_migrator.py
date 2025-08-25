#!/usr/bin/env python
"""
Deal Association Migration Script
Migrates deal-contact and deal-company associations from production to sandbox
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
import time
import json
from datetime import datetime
import math

class DealAssociationMigrator:
    def __init__(self, prod_token, sandbox_token):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.deal_mapping = {}  # prod_id -> sandbox_id
        self.contact_mapping = {}  # prod_id -> sandbox_id  
        self.company_mapping = {}  # prod_id -> sandbox_id
        self.created_contact_associations = []
        self.created_company_associations = []
        self.failed_associations = []
    
    def load_mappings(self):
        """Load deal, contact, and company mappings from previous migrations"""
        mappings_loaded = 0
        
        # Load deal mapping
        try:
            deal_reports = [f for f in os.listdir('reports') if f.startswith('deal_migration_')]
            if deal_reports:
                latest_deal_report = sorted(deal_reports)[-1]
                with open(f"reports/{latest_deal_report}", 'r') as f:
                    deal_report = json.load(f)
                
                # Build deal mapping from both created and updated deals
                for deal in deal_report.get('created_deals', []):
                    self.deal_mapping[deal['prod_id']] = deal['sandbox_id']
                
                for deal in deal_report.get('updated_deals', []):
                    self.deal_mapping[deal['prod_id']] = deal['sandbox_id']
                
                mappings_loaded += 1
                print(f"✅ Loaded {len(self.deal_mapping)} deal mappings from {latest_deal_report}")
        except Exception as e:
            print(f"❌ Error loading deal mappings: {str(e)}")
        
        # Load contact mapping
        try:
            contact_reports = [f for f in os.listdir('reports') if f.startswith('migration_report_')]
            if contact_reports:
                latest_contact_report = sorted(contact_reports)[-1]
                with open(f"reports/{latest_contact_report}", 'r') as f:
                    contact_report = json.load(f)
                
                # Build contact mapping
                for contact in contact_report.get('created_contacts', []):
                    if 'prod_id' in contact and 'sandbox_id' in contact:
                        self.contact_mapping[contact['prod_id']] = contact['sandbox_id']
                
                for contact in contact_report.get('updated_contacts', []):
                    if 'prod_id' in contact and 'sandbox_id' in contact:
                        self.contact_mapping[contact['prod_id']] = contact['sandbox_id']
                
                mappings_loaded += 1
                print(f"✅ Loaded {len(self.contact_mapping)} contact mappings from {latest_contact_report}")
        except Exception as e:
            print(f"❌ Error loading contact mappings: {str(e)}")
        
        # Load company mapping
        try:
            company_reports = [f for f in os.listdir('reports') if f.startswith('enterprise_association_migration_')]
            if company_reports:
                latest_company_report = sorted(company_reports)[-1]
                with open(f"reports/{latest_company_report}", 'r') as f:
                    company_report = json.load(f)
                
                # Build company mapping
                for company in company_report.get('created_companies', []):
                    if 'prod_id' in company and 'sandbox_id' in company:
                        self.company_mapping[company['prod_id']] = company['sandbox_id']
                
                for company in company_report.get('updated_companies', []):
                    if 'prod_id' in company and 'sandbox_id' in company:
                        self.company_mapping[company['prod_id']] = company['sandbox_id']
                
                mappings_loaded += 1
                print(f"✅ Loaded {len(self.company_mapping)} company mappings from {latest_company_report}")
        except Exception as e:
            print(f"❌ Error loading company mappings: {str(e)}")
        
        if mappings_loaded == 0:
            print("❌ No mapping files found. Please run object migrations first.")
            return False
        
        print(f"📊 Total mappings loaded: {len(self.deal_mapping)} deals, {len(self.contact_mapping)} contacts, {len(self.company_mapping)} companies")
        return True
    
    def get_deal_associations(self, deal_id, token):
        """Get all associations for a specific deal"""
        headers = get_api_headers(token)
        
        # Get contacts associated with deal
        contacts_url = f'https://api.hubapi.com/crm/v3/objects/deals/{deal_id}/associations/contacts'
        contacts_success, contacts_data = make_hubspot_request('GET', contacts_url, headers)
        
        contacts = []
        if contacts_success:
            contacts = [result['id'] for result in contacts_data.get('results', [])]
        
        # Get companies associated with deal
        companies_url = f'https://api.hubapi.com/crm/v3/objects/deals/{deal_id}/associations/companies'
        companies_success, companies_data = make_hubspot_request('GET', companies_url, headers)
        
        companies = []
        if companies_success:
            companies = [result['id'] for result in companies_data.get('results', [])]
        
        return contacts, companies
    
    def create_deal_contact_associations(self, sandbox_deal_id, sandbox_contact_ids):
        """Create associations between a deal and contacts in sandbox"""
        if not sandbox_contact_ids:
            return True, "No contacts to associate"
        
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/associations/deals/contacts/batch/create'
        
        # Build association inputs
        inputs = []
        for contact_id in sandbox_contact_ids:
            inputs.append({
                "from": {"id": sandbox_deal_id},
                "to": {"id": contact_id},
                "type": "deal_to_contact"
            })
        
        payload = {"inputs": inputs}
        
        success, result = make_hubspot_request('POST', url, headers, json_data=payload)
        return success, result
    
    def create_deal_company_associations(self, sandbox_deal_id, sandbox_company_ids):
        """Create associations between a deal and companies in sandbox"""
        if not sandbox_company_ids:
            return True, "No companies to associate"
        
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/associations/deals/companies/batch/create'
        
        # Build association inputs  
        inputs = []
        for company_id in sandbox_company_ids:
            inputs.append({
                "from": {"id": sandbox_deal_id},
                "to": {"id": company_id},
                "type": "deal_to_company"
            })
        
        payload = {"inputs": inputs}
        
        success, result = make_hubspot_request('POST', url, headers, json_data=payload)
        return success, result
    
    def migrate_deal_associations(self, limit=None):
        """Main function to migrate all deal associations"""
        print("🔗 Deal Association Migration")
        print("=" * 50)
        
        # Load mappings
        if not self.load_mappings():
            return False
        
        # Get deals to process (limit to deals we have mappings for)
        deals_to_process = list(self.deal_mapping.keys())
        
        if limit:
            deals_to_process = deals_to_process[:limit]
        
        print(f"🔄 Processing associations for {len(deals_to_process)} deals...")
        print()
        
        processed = 0
        contact_associations_created = 0
        company_associations_created = 0
        
        for i, prod_deal_id in enumerate(deals_to_process, 1):
            sandbox_deal_id = self.deal_mapping[prod_deal_id]
            
            # Get associations from production
            prod_contacts, prod_companies = self.get_deal_associations(prod_deal_id, self.prod_token)
            
            print(f"  [{i}/{len(deals_to_process)}] Deal ID: {prod_deal_id} → {sandbox_deal_id}")
            print(f"    📞 Production contacts: {len(prod_contacts)}")
            print(f"    🏢 Production companies: {len(prod_companies)}")
            
            # Map production IDs to sandbox IDs
            sandbox_contacts = []
            for contact_id in prod_contacts:
                if contact_id in self.contact_mapping:
                    sandbox_contacts.append(self.contact_mapping[contact_id])
                else:
                    print(f"    ⚠️  Contact {contact_id} not found in mappings")
            
            sandbox_companies = []
            for company_id in prod_companies:
                if company_id in self.company_mapping:
                    sandbox_companies.append(self.company_mapping[company_id])
                else:
                    print(f"    ⚠️  Company {company_id} not found in mappings")
            
            print(f"    ✅ Mapped contacts: {len(sandbox_contacts)}")
            print(f"    ✅ Mapped companies: {len(sandbox_companies)}")
            
            # Create contact associations
            if sandbox_contacts:
                contact_success, contact_result = self.create_deal_contact_associations(
                    sandbox_deal_id, sandbox_contacts
                )
                
                if contact_success:
                    contact_associations_created += len(sandbox_contacts)
                    print(f"    🔗 Created {len(sandbox_contacts)} contact associations")
                    
                    self.created_contact_associations.append({
                        'deal_id': sandbox_deal_id,
                        'contact_ids': sandbox_contacts,
                        'count': len(sandbox_contacts)
                    })
                else:
                    error_msg = str(contact_result)[:100] if contact_result else "Unknown error"
                    print(f"    ❌ Failed to create contact associations: {error_msg}")
                    
                    self.failed_associations.append({
                        'deal_id': sandbox_deal_id,
                        'type': 'contact',
                        'error': error_msg
                    })
            
            # Create company associations
            if sandbox_companies:
                company_success, company_result = self.create_deal_company_associations(
                    sandbox_deal_id, sandbox_companies
                )
                
                if company_success:
                    company_associations_created += len(sandbox_companies)
                    print(f"    🔗 Created {len(sandbox_companies)} company associations")
                    
                    self.created_company_associations.append({
                        'deal_id': sandbox_deal_id,
                        'company_ids': sandbox_companies,
                        'count': len(sandbox_companies)
                    })
                else:
                    error_msg = str(company_result)[:100] if company_result else "Unknown error"
                    print(f"    ❌ Failed to create company associations: {error_msg}")
                    
                    self.failed_associations.append({
                        'deal_id': sandbox_deal_id,
                        'type': 'company',
                        'error': error_msg
                    })
            
            processed += 1
            
            # Rate limiting
            time.sleep(0.3)
            
            # Progress update
            if processed % 10 == 0:
                print(f"  📊 Progress: {processed}/{len(deals_to_process)} deals processed")
                print()
        
        # Summary
        print()
        print("=" * 50)
        print("📊 DEAL ASSOCIATION MIGRATION SUMMARY")
        print("=" * 50)
        print(f"✅ Deals processed: {processed}")
        print(f"🔗 Contact associations created: {contact_associations_created}")
        print(f"🔗 Company associations created: {company_associations_created}")
        print(f"❌ Failed associations: {len(self.failed_associations)}")
        print("=" * 50)
        
        return True
    
    def generate_association_report(self):
        """Generate comprehensive association migration report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'timestamp': timestamp,
            'migration_date': datetime.now().isoformat(),
            'summary': {
                'contact_associations_created': len(self.created_contact_associations),
                'company_associations_created': len(self.created_company_associations),
                'failed_associations': len(self.failed_associations),
                'total_contact_links': sum(assoc['count'] for assoc in self.created_contact_associations),
                'total_company_links': sum(assoc['count'] for assoc in self.created_company_associations)
            },
            'mappings_used': {
                'deals': len(self.deal_mapping),
                'contacts': len(self.contact_mapping),
                'companies': len(self.company_mapping)
            },
            'created_contact_associations': self.created_contact_associations,
            'created_company_associations': self.created_company_associations,
            'failed_associations': self.failed_associations
        }
        
        # Save report
        os.makedirs('reports', exist_ok=True)
        report_file = f'reports/deal_association_migration_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file, report

def migrate_deal_associations():
    """Main function to execute deal association migration"""
    print("🔗 Deal Association Migration System")
    print("=" * 50)
    
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    if not prod_token or not sandbox_token:
        print("❌ Error: API tokens not found in .env file")
        return False
    
    # Initialize migrator
    migrator = DealAssociationMigrator(prod_token, sandbox_token)
    
    # Run migration
    success = migrator.migrate_deal_associations(limit=50)  # Test with limited deals
    
    if success:
        # Generate report
        report_file, report = migrator.generate_association_report()
        
        # Final summary
        total_links = report['summary']['total_contact_links'] + report['summary']['total_company_links']
        
        print(f"📄 Association report saved: {report_file}")
        print(f"🎯 Total associations created: {total_links}")
        
        if report['summary']['failed_associations'] == 0:
            print("🎉 All deal associations migrated successfully!")
            return True
        else:
            print("⚠️  Some associations failed - check report for details")
            return False
    else:
        print("❌ Deal association migration failed")
        return False

if __name__ == "__main__":
    success = migrate_deal_associations()
    exit(0 if success else 1)