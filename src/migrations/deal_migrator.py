#!/usr/bin/env python
"""
Deal Migration Script
Migrates deal objects with properties, maintaining pipeline mapping and ownership
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
from core.field_filters import DealFieldFilter
import time
import json
from datetime import datetime
import math

class DealMigrator:
    def __init__(self, prod_token, sandbox_token):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.field_filter = DealFieldFilter()
        self.pipeline_mapping = {}
        self.stage_mapping = {}
        self.created_deals = []
        self.updated_deals = []
        self.failed_deals = []
        
    def load_pipeline_mapping(self):
        """Load pipeline mapping from previous pipeline migration"""
        try:
            # Find the most recent pipeline migration report
            report_files = [f for f in os.listdir('reports') if f.startswith('deal_pipeline_migration_')]
            if not report_files:
                print("❌ No pipeline migration report found. Please run deal pipeline migration first.")
                return False
                
            latest_report = sorted(report_files)[-1]
            report_path = f"reports/{latest_report}"
            
            with open(report_path, 'r') as f:
                report = json.load(f)
                
            self.pipeline_mapping = report.get('pipeline_mapping', {})
            print(f"✅ Loaded pipeline mapping from {latest_report}")
            print(f"📊 Pipeline mappings: {len(self.pipeline_mapping)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading pipeline mapping: {str(e)}")
            return False
    
    def get_deals_batch(self, token, after=None, limit=100, properties=None):
        """Get a batch of deals from HubSpot"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/objects/deals'
        
        params = {
            'limit': limit,
            'associations': 'contacts,companies'
        }
        
        if after:
            params['after'] = after
            
        if properties:
            params['properties'] = ','.join(properties)
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        
        if success:
            return data.get('results', []), data.get('paging', {}).get('next', {}).get('after')
        else:
            print(f"❌ Error fetching deals: {data}")
            return [], None
    
    def get_all_deals(self, token, limit=None):
        """Get all deals from a portal with pagination"""
        all_deals = []
        after = None
        batch_size = 100
        processed = 0
        
        # Get filtered properties for deals
        filtered_props = self.field_filter.get_filtered_properties(token)
        
        print(f"📊 Using {len(filtered_props)} filtered properties for migration")
        
        while True:
            deals, next_after = self.get_deals_batch(
                token, 
                after=after, 
                limit=batch_size,
                properties=filtered_props
            )
            
            if not deals:
                break
                
            all_deals.extend(deals)
            processed += len(deals)
            
            print(f"  📥 Fetched {len(deals)} deals (Total: {processed})")
            
            if limit and processed >= limit:
                all_deals = all_deals[:limit]
                break
                
            after = next_after
            if not after:
                break
                
            # Rate limiting
            time.sleep(0.1)
        
        return all_deals
    
    def clean_deal_properties(self, deal_props, sandbox_properties):
        """Clean deal properties for creation in sandbox"""
        cleaned = {}
        sandbox_prop_names = {prop['name'] for prop in sandbox_properties}
        
        for prop_name, value in deal_props.items():
            # Skip if property doesn't exist in sandbox
            if prop_name not in sandbox_prop_names:
                continue
                
            # Skip empty values
            if value is None or value == '':
                continue
                
            # Handle pipeline mapping
            if prop_name == 'pipeline' and value in self.pipeline_mapping:
                cleaned[prop_name] = self.pipeline_mapping[value]
                continue
                
            # Handle stage mapping (stages should be updated after pipeline migration)
            if prop_name == 'dealstage':
                # For now, we'll let HubSpot assign default stage
                # Stage mapping would require more complex logic
                continue
                
            cleaned[prop_name] = value
        
        return cleaned
    
    def create_deal(self, deal_data, sandbox_properties):
        """Create a deal in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/deals'
        
        # Clean properties
        clean_props = self.clean_deal_properties(
            deal_data.get('properties', {}), 
            sandbox_properties
        )
        
        # Prepare deal creation payload
        payload = {
            'properties': clean_props
        }
        
        success, result = make_hubspot_request('POST', url, headers, json_data=payload)
        return success, result
    
    def find_existing_deal(self, deal_name, sandbox_deals):
        """Find existing deal by name in sandbox"""
        for sandbox_deal in sandbox_deals:
            sandbox_name = sandbox_deal.get('properties', {}).get('dealname', '')
            if sandbox_name and sandbox_name == deal_name:
                return sandbox_deal
        return None
    
    def migrate_deals(self, batch_size=50, limit=None):
        """Main deal migration function"""
        print("💼 Deal Object Migration")
        print("=" * 50)
        
        # Load pipeline mapping
        if not self.load_pipeline_mapping():
            return False
        
        # Get sandbox properties for validation
        print("📥 Fetching sandbox deal properties...")
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/properties/deals'
        success, data = make_hubspot_request('GET', url, headers)
        
        if not success:
            print(f"❌ Failed to get sandbox properties: {data}")
            return False
            
        sandbox_properties = data.get('results', [])
        print(f"✅ Found {len(sandbox_properties)} properties in sandbox")
        
        # Get deals from production
        print("📥 Fetching deals from production...")
        prod_deals = self.get_all_deals(self.prod_token, limit=limit)
        
        if not prod_deals:
            print("❌ No deals found in production")
            return False
            
        print(f"✅ Found {len(prod_deals)} deals in production")
        
        # Get existing deals from sandbox (for comparison)
        print("📥 Fetching existing deals from sandbox...")
        sandbox_deals = self.get_all_deals(self.sandbox_token)
        print(f"✅ Found {len(sandbox_deals)} existing deals in sandbox")
        
        # Process deals in batches
        total_batches = math.ceil(len(prod_deals) / batch_size)
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(prod_deals))
            batch_deals = prod_deals[start_idx:end_idx]
            
            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_deals)} deals)")
            
            for i, deal in enumerate(batch_deals, 1):
                deal_props = deal.get('properties', {})
                deal_name = deal_props.get('dealname', 'Unnamed Deal')
                deal_amount = deal_props.get('amount', 'N/A')
                deal_stage = deal_props.get('dealstage', 'Unknown')
                
                print(f"  [{start_idx + i}/{len(prod_deals)}] {deal_name} (${deal_amount})")
                
                # Check if deal already exists
                existing_deal = self.find_existing_deal(deal_name, sandbox_deals)
                
                if existing_deal:
                    print(f"    🔄 Deal exists, skipping: {deal_name}")
                    self.updated_deals.append({
                        'name': deal_name,
                        'prod_id': deal.get('id'),
                        'sandbox_id': existing_deal.get('id'),
                        'status': 'skipped_exists'
                    })
                    continue
                
                # Create new deal
                success, result = self.create_deal(deal, sandbox_properties)
                
                if success:
                    new_deal_id = result.get('id')
                    print(f"    ✅ Created successfully (ID: {new_deal_id})")
                    
                    self.created_deals.append({
                        'name': deal_name,
                        'prod_id': deal.get('id'),
                        'sandbox_id': new_deal_id,
                        'amount': deal_amount,
                        'stage': deal_stage
                    })
                else:
                    error_msg = result.get('error', str(result)) if isinstance(result, dict) else str(result)
                    print(f"    ❌ Failed: {str(error_msg)[:60]}...")
                    
                    self.failed_deals.append({
                        'name': deal_name,
                        'prod_id': deal.get('id'),
                        'error': str(error_msg)[:100]
                    })
                
                # Rate limiting
                time.sleep(0.2)
                
                # Progress update
                if (start_idx + i) % 20 == 0:
                    print(f"  📊 Progress: {start_idx + i}/{len(prod_deals)} deals processed")
            
            print(f"✅ Batch {batch_num + 1} completed")
            time.sleep(0.5)  # Batch pause
        
        return True
    
    def generate_migration_report(self):
        """Generate comprehensive migration report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'timestamp': timestamp,
            'migration_date': datetime.now().isoformat(),
            'summary': {
                'deals_created': len(self.created_deals),
                'deals_updated': len(self.updated_deals),
                'deals_failed': len(self.failed_deals),
                'total_processed': len(self.created_deals) + len(self.updated_deals) + len(self.failed_deals),
                'success_rate': len(self.created_deals) / (len(self.created_deals) + len(self.failed_deals)) * 100 if (len(self.created_deals) + len(self.failed_deals)) > 0 else 0
            },
            'pipeline_mapping_used': self.pipeline_mapping,
            'created_deals': self.created_deals,
            'updated_deals': self.updated_deals,
            'failed_deals': self.failed_deals
        }
        
        # Save report
        os.makedirs('reports', exist_ok=True)
        report_file = f'reports/deal_migration_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file, report

def migrate_deals():
    """Main function to execute deal migration"""
    print("💼 Deal Migration System")
    print("=" * 50)
    
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    if not prod_token or not sandbox_token:
        print("❌ Error: API tokens not found in .env file")
        return False
    
    # Initialize migrator
    migrator = DealMigrator(prod_token, sandbox_token)
    
    # Run migration
    success = migrator.migrate_deals(batch_size=10, limit=50)  # Test with larger batch to find new deals
    
    if success:
        # Generate report
        report_file, report = migrator.generate_migration_report()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 DEAL MIGRATION SUMMARY")
        print("=" * 50)
        print(f"✅ Deals created: {report['summary']['deals_created']}")
        print(f"🔄 Deals updated/skipped: {report['summary']['deals_updated']}")
        print(f"❌ Deals failed: {report['summary']['deals_failed']}")
        print(f"📊 Success rate: {report['summary']['success_rate']:.1f}%")
        print(f"📝 Total processed: {report['summary']['total_processed']}")
        print(f"📄 Detailed report: {report_file}")
        print("=" * 50)
        
        if report['summary']['deals_failed'] == 0:
            print("🎉 All deals migrated successfully!")
            return True
        else:
            print("⚠️  Some deals failed - check report for details")
            return False
    else:
        print("❌ Deal migration failed")
        return False

if __name__ == "__main__":
    success = migrate_deals()
    exit(0 if success else 1)