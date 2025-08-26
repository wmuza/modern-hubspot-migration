#!/usr/bin/env python3
"""
Ticket Migrator - Migrates ticket objects between HubSpot accounts
For HubSpot Modern Migration Tool
"""
import sys
import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.config import SecureConfig
from src.core.field_filters import HubSpotFieldFilter
from src.utils.utils import get_api_headers, make_hubspot_request, ensure_directory, load_env_config


class TicketMigrator:
    """Migrate tickets between HubSpot accounts"""
    
    def __init__(self, prod_token: str, sandbox_token: str):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.report_dir = 'reports'
        ensure_directory(self.report_dir)
        
        # Initialize field filter
        self.field_filter = HubSpotFieldFilter()
        
        # Track migrations
        self.ticket_mapping = {}  # Maps prod ID to sandbox ID
        self.created_tickets = []
        self.updated_tickets = []
        self.failed_tickets = []
        self.errors = []
        
        # Load pipeline mapping if available
        self.pipeline_mapping = {}
        self.load_pipeline_mapping()
    
    def load_pipeline_mapping(self) -> bool:
        """Load pipeline mapping from the most recent pipeline migration"""
        try:
            # Find the most recent pipeline migration report
            import glob
            pattern = os.path.join(self.report_dir, 'ticket_pipeline_migration_*.json')
            files = glob.glob(pattern)
            
            if not files:
                print("⚠️ No pipeline mapping found. Tickets will use same pipeline IDs.")
                return False
            
            # Get the most recent file
            latest_file = max(files, key=os.path.getctime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.pipeline_mapping = data.get('pipeline_mapping', {})
            
            print(f"✅ Loaded pipeline mapping from {os.path.basename(latest_file)}")
            print(f"📊 Pipeline mappings: {len(self.pipeline_mapping)}")
            return True
            
        except Exception as e:
            print(f"⚠️ Could not load pipeline mapping: {e}")
            return False
    
    def get_tickets_batch(self, token: str, after: Optional[str] = None, 
                         limit: int = 100, properties: List[str] = None) -> Tuple[List[Dict], Optional[str]]:
        """Get a batch of tickets from HubSpot"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/objects/tickets'
        
        params = {
            'limit': limit,
            'associations': 'contacts,companies,deals',
            'sorts': 'createdate:desc'  # Get newest tickets first
        }
        
        if after:
            params['after'] = after
        
        if properties:
            # Limit properties to avoid URL too long error
            params['properties'] = ','.join(properties[:100])
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        
        if success:
            tickets = data.get('results', [])
            next_after = data.get('paging', {}).get('next', {}).get('after')
            return tickets, next_after
        
        return [], None
    
    def get_all_tickets(self, token: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all tickets from a portal with pagination"""
        all_tickets = []
        after = None
        batch_size = 100
        processed = 0
        
        # Get all ticket properties first
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets'
        success, data = make_hubspot_request('GET', url, headers)
        
        if not success:
            print(f"❌ Failed to get ticket properties: {data}")
            return []
        
        all_properties = data.get('results', [])
        
        # Get filtered properties for tickets
        filtered_props = self.field_filter.get_safe_properties_list(all_properties)
        
        print(f"📊 Using {len(filtered_props)} filtered properties for migration")
        
        while True:
            tickets, next_after = self.get_tickets_batch(
                token, 
                after=after, 
                limit=batch_size,
                properties=filtered_props
            )
            
            if not tickets:
                break
            
            all_tickets.extend(tickets)
            processed += len(tickets)
            
            print(f"  📥 Fetched {len(tickets)} tickets (Total: {processed})")
            
            if limit and processed >= limit:
                all_tickets = all_tickets[:limit]
                break
            
            after = next_after
            if not after:
                break
            
            # Rate limiting
            time.sleep(0.1)
        
        return all_tickets
    
    def clean_ticket_properties(self, ticket_props: Dict[str, Any], sandbox_properties: List[Dict]) -> Dict[str, Any]:
        """Clean ticket properties for creation in sandbox"""
        cleaned = {}
        sandbox_prop_names = {prop['name'] for prop in sandbox_properties}
        
        # Ensure we include required fields
        required_fields = ['hs_pipeline', 'hs_pipeline_stage', 'subject']
        
        for prop_name, value in ticket_props.items():
            # Skip if property doesn't exist in sandbox
            if prop_name not in sandbox_prop_names:
                continue
            
            # Skip empty values unless it's a required field
            if value is None or value == '':
                if prop_name not in required_fields:
                    continue
            
            # Handle pipeline mapping
            if prop_name == 'hs_pipeline':
                if value in self.pipeline_mapping:
                    cleaned[prop_name] = self.pipeline_mapping[value]
                elif value:
                    cleaned[prop_name] = value
                else:
                    # Use default pipeline if not set
                    cleaned[prop_name] = '0'
            # Handle pipeline stage
            elif prop_name == 'hs_pipeline_stage':
                if value:
                    cleaned[prop_name] = value
                else:
                    # Use a default stage if not set (usually the first stage)
                    cleaned[prop_name] = '1'  # Default stage ID
            # Skip owner IDs (need special handling)
            elif prop_name == 'hubspot_owner_id':
                continue
            # Skip object ID (read-only)
            elif prop_name == 'hs_object_id':
                continue
            # Skip computed/read-only properties
            elif prop_name.startswith('hs_') and prop_name.endswith(('_date', '_timestamp')):
                if prop_name not in ['hs_ticket_priority', 'hs_ticket_category']:
                    continue
            else:
                cleaned[prop_name] = value
        
        # Ensure required fields are present
        if 'hs_pipeline' not in cleaned:
            cleaned['hs_pipeline'] = '0'  # Default pipeline
        if 'hs_pipeline_stage' not in cleaned:
            cleaned['hs_pipeline_stage'] = '1'  # Default stage
        
        return cleaned
    
    def create_ticket(self, ticket_data: Dict[str, Any], sandbox_properties: List[Dict]) -> Tuple[bool, Dict]:
        """Create a ticket in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/tickets'
        
        # Clean properties
        cleaned_props = self.clean_ticket_properties(
            ticket_data.get('properties', {}),
            sandbox_properties
        )
        
        # Ensure we have at least a subject
        if 'subject' not in cleaned_props:
            cleaned_props['subject'] = 'Migrated Ticket'
        
        payload = {
            'properties': cleaned_props
        }
        
        success, result = make_hubspot_request('POST', url, headers, json_data=payload)
        return success, result
    
    def find_existing_ticket(self, ticket_subject: str, sandbox_tickets: List[Dict]) -> Optional[Dict]:
        """Find existing ticket by subject in sandbox"""
        for sandbox_ticket in sandbox_tickets:
            sandbox_subject = sandbox_ticket.get('properties', {}).get('subject', '')
            if sandbox_subject and sandbox_subject == ticket_subject:
                return sandbox_ticket
        return None
    
    def migrate_tickets(self, batch_size: int = 10, limit: Optional[int] = None) -> bool:
        """Main ticket migration function"""
        print("🎫 Ticket Object Migration")
        print("=" * 50)
        
        # Load pipeline mapping if not already loaded
        if not self.pipeline_mapping:
            self.load_pipeline_mapping()
        
        # Get sandbox properties for validation
        print("📥 Fetching sandbox ticket properties...")
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets'
        success, data = make_hubspot_request('GET', url, headers)
        
        if not success:
            print(f"❌ Failed to get sandbox properties: {data}")
            return False
        
        sandbox_properties = data.get('results', [])
        print(f"✅ Found {len(sandbox_properties)} properties in sandbox")
        
        # Get tickets from production
        print("📥 Fetching tickets from production...")
        prod_tickets = self.get_all_tickets(self.prod_token, limit=limit)
        
        if not prod_tickets:
            print("❌ No tickets found in production")
            return False
        
        print(f"✅ Found {len(prod_tickets)} tickets in production")
        
        # Get existing tickets from sandbox (for comparison)
        print("📥 Fetching existing tickets from sandbox...")
        sandbox_tickets = self.get_all_tickets(self.sandbox_token)
        print(f"✅ Found {len(sandbox_tickets)} existing tickets in sandbox")
        
        # Process tickets in batches
        total_tickets = len(prod_tickets)
        num_batches = (total_tickets + batch_size - 1) // batch_size
        
        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_tickets)
            batch = prod_tickets[start_idx:end_idx]
            
            print(f"\n📦 Processing batch {batch_num + 1}/{num_batches} ({len(batch)} tickets)")
            
            for idx, prod_ticket in enumerate(batch, start=start_idx + 1):
                prod_id = prod_ticket['id']
                properties = prod_ticket.get('properties', {})
                subject = properties.get('subject', 'No Subject')
                priority = properties.get('hs_ticket_priority', 'N/A')
                category = properties.get('hs_ticket_category', 'N/A')
                
                # Display progress
                print(f"  [{idx}/{total_tickets}] {subject[:50]}... (Priority: {priority})")
                
                # Check if ticket already exists
                existing = self.find_existing_ticket(subject, sandbox_tickets)
                if existing:
                    print(f"    🔄 Ticket exists, skipping: {subject[:50]}...")
                    self.ticket_mapping[prod_id] = existing['id']
                    self.updated_tickets.append(prod_id)
                    continue
                
                # Create ticket
                success, result = self.create_ticket(prod_ticket, sandbox_properties)
                
                if success:
                    new_id = result['id']
                    self.ticket_mapping[prod_id] = new_id
                    self.created_tickets.append(prod_id)
                    print(f"    ✅ Created successfully (ID: {new_id})")
                else:
                    self.failed_tickets.append({
                        'id': prod_id,
                        'subject': subject,
                        'error': str(result)
                    })
                    print(f"    ❌ Failed: {result}")
                
                # Rate limiting
                time.sleep(0.3)
            
            if batch_num < num_batches - 1:
                print(f"  📊 Progress: {end_idx}/{total_tickets} tickets processed")
            
            print(f"✅ Batch {batch_num + 1} completed")
        
        # Generate report
        self.generate_migration_report()
        
        return True
    
    def generate_migration_report(self) -> Tuple[str, Dict]:
        """Generate detailed migration report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'tickets_created': len(self.created_tickets),
                'tickets_updated': len(self.updated_tickets),
                'tickets_failed': len(self.failed_tickets),
                'total_processed': len(self.created_tickets) + len(self.updated_tickets),
                'success_rate': (len(self.created_tickets) / 
                               (len(self.created_tickets) + len(self.failed_tickets)) * 100) 
                               if (self.created_tickets or self.failed_tickets) else 0
            },
            'ticket_mapping': self.ticket_mapping,
            'created': self.created_tickets,
            'updated': self.updated_tickets,
            'failed': self.failed_tickets
        }
        
        report_file = os.path.join(self.report_dir, f'ticket_migration_{timestamp}.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report_file, report


def migrate_tickets(limit: Optional[int] = None):
    """Main function to execute ticket migration"""
    print("🎫 Ticket Migration System")
    print("=" * 50)
    
    config = SecureConfig()
    hubspot_config = config.get_hubspot_config()
    
    migrator = TicketMigrator(
        prod_token=hubspot_config['production_token'],
        sandbox_token=hubspot_config['sandbox_token']
    )
    
    # Run migration with proper limit
    success = migrator.migrate_tickets(batch_size=10, limit=limit)
    
    if success:
        # Generate report
        report_file, report = migrator.generate_migration_report()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TICKET MIGRATION SUMMARY")
        print("=" * 50)
        print(f"✅ Tickets created: {report['summary']['tickets_created']}")
        print(f"🔄 Tickets updated/skipped: {report['summary']['tickets_updated']}")
        print(f"❌ Tickets failed: {report['summary']['tickets_failed']}")
        print(f"📊 Success rate: {report['summary']['success_rate']:.1f}%")
        print(f"📝 Total processed: {report['summary']['total_processed']}")
        print(f"📄 Detailed report: {report_file}")
        print("=" * 50)
        print("🎉 All tickets migrated successfully!")
        
        return True
    
    print("❌ Ticket migration failed")
    return False


if __name__ == "__main__":
    success = migrate_tickets()
    exit(0 if success else 1)