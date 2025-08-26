#!/usr/bin/env python3
"""
Ticket Property Migrator - Creates and syncs ticket properties between HubSpot accounts
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
from src.utils.utils import get_api_headers, make_hubspot_request, ensure_directory


class TicketPropertyMigrator:
    """Migrate ticket properties between HubSpot accounts"""
    
    def __init__(self, prod_token: str, sandbox_token: str):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.report_dir = 'reports'
        ensure_directory(self.report_dir)
        
        # Track migrations
        self.created_properties = []
        self.created_groups = []
        self.errors = []
    
    def get_ticket_properties(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all ticket properties from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def get_property_groups(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all ticket property groups from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets/groups'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def create_property_group(self, group_data: Dict[str, Any]) -> bool:
        """Create a property group in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets/groups'
        
        payload = {
            'name': group_data['name'],
            'label': group_data['label'],
            'displayOrder': group_data.get('displayOrder', -1)
        }
        
        print(f"  🔧 Creating group: {group_data['label']}")
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            self.created_groups.append(group_data['name'])
            return True
        else:
            if 'already exists' in str(data).lower():
                print(f"    ℹ️  Group already exists: {group_data['label']}")
                return True
            else:
                self.errors.append(f"Failed to create group {group_data['name']}: {data}")
                print(f"    ❌ Failed: {data}")
                return False
    
    def create_ticket_property(self, property_data: Dict[str, Any]) -> bool:
        """Create a custom property in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets'
        
        # Prepare property payload
        payload = {
            'name': property_data['name'],
            'label': property_data['label'],
            'type': property_data.get('type', 'string'),
            'fieldType': property_data.get('fieldType', 'text'),
            'groupName': property_data.get('groupName', 'ticketinformation'),
            'description': property_data.get('description', ''),
            'options': property_data.get('options', []),
            'displayOrder': property_data.get('displayOrder', -1)
        }
        
        # Add additional fields if present
        if 'formField' in property_data:
            payload['formField'] = property_data['formField']
        if 'hasUniqueValue' in property_data:
            payload['hasUniqueValue'] = property_data['hasUniqueValue']
        
        print(f"  🔧 Creating property: {property_data['label']} ({property_data['name']})")
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            self.created_properties.append(property_data['name'])
            return True
        else:
            if 'already exists' in str(data).lower():
                print(f"    ℹ️  Property already exists")
                return True
            else:
                self.errors.append(f"Failed to create property {property_data['name']}: {data}")
                print(f"    ❌ Failed: {data}")
                return False
    
    def migrate_ticket_properties(self) -> Dict[str, Any]:
        """Main migration function for ticket properties"""
        print("💼 Ticket Property Migration")
        print("=" * 50)
        
        # Get properties from both environments
        print("📥 Fetching ticket properties from production...")
        prod_properties = self.get_ticket_properties(self.prod_token)
        prod_custom = [p for p in prod_properties if not p['name'].startswith('hs_')]
        print(f"✅ Found {len(prod_properties)} properties in production")
        
        print("📥 Fetching ticket properties from sandbox...")
        sandbox_properties = self.get_ticket_properties(self.sandbox_token)
        sandbox_prop_names = {p['name'] for p in sandbox_properties}
        print(f"✅ Found {len(sandbox_properties)} properties in sandbox")
        
        # Get property groups
        print("📥 Fetching ticket property groups from production...")
        prod_groups = self.get_property_groups(self.prod_token)
        prod_custom_groups = [g for g in prod_groups 
                             if not g.get('name', '').startswith('hs_')]
        
        sandbox_groups = self.get_property_groups(self.sandbox_token)
        sandbox_group_names = {g['name'] for g in sandbox_groups}
        
        # Create missing groups first
        groups_to_create = [g for g in prod_custom_groups 
                           if g['name'] not in sandbox_group_names]
        
        print(f"🔄 Need to create {len(groups_to_create)} property groups")
        
        if groups_to_create:
            print("\n📦 Creating property groups...")
            for group in groups_to_create:
                self.create_property_group(group)
                time.sleep(0.3)  # Rate limiting
        
        # Create missing custom properties
        properties_to_create = [p for p in prod_custom 
                               if p['name'] not in sandbox_prop_names]
        
        print(f"🔄 Need to create {len(properties_to_create)} custom properties")
        
        if properties_to_create:
            print("\n📦 Creating custom properties...")
            for prop in properties_to_create:
                self.create_ticket_property(prop)
                time.sleep(0.3)  # Rate limiting
        
        # Generate report
        report = self._generate_report(
            prod_properties, 
            sandbox_properties, 
            properties_to_create, 
            groups_to_create
        )
        
        # Summary
        if properties_to_create or groups_to_create:
            print("\n" + "=" * 50)
            print("📊 MIGRATION SUMMARY")
            print("=" * 50)
            print(f"✅ Property groups created: {len(self.created_groups)}")
            print(f"✅ Properties created: {len(self.created_properties)}")
            if self.errors:
                print(f"❌ Errors encountered: {len(self.errors)}")
            print("=" * 50)
        else:
            print("\n✅ All custom properties and groups already exist in sandbox")
        
        return report
    
    def _generate_report(self, prod_props: List[Dict], sand_props: List[Dict], 
                        created_props: List[Dict], created_groups: List[Dict]) -> Dict[str, Any]:
        """Generate migration report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'production_properties': len(prod_props),
                'production_custom': len([p for p in prod_props if not p['name'].startswith('hs_')]),
                'sandbox_properties': len(sand_props),
                'properties_created': len(self.created_properties),
                'groups_created': len(self.created_groups),
                'errors': len(self.errors)
            },
            'created': {
                'properties': self.created_properties,
                'groups': self.created_groups
            },
            'errors': self.errors,
            'details': {
                'properties_created': created_props,
                'groups_created': created_groups
            }
        }
        
        report_file = os.path.join(self.report_dir, f'ticket_property_migration_{timestamp}.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Report saved: {report_file}")
        return report


def migrate_ticket_properties():
    """Main function to migrate ticket properties"""
    print("💼 Ticket Property Migration")
    print("=" * 50)
    
    # Load configuration
    config = SecureConfig()
    hubspot_config = config.get_hubspot_config()
    
    # Initialize migrator
    migrator = TicketPropertyMigrator(
        prod_token=hubspot_config['production_token'],
        sandbox_token=hubspot_config['sandbox_token']
    )
    
    # Run migration
    report = migrator.migrate_ticket_properties()
    
    return report['summary'].get('errors', 0) == 0


if __name__ == "__main__":
    success = migrate_ticket_properties()
    if success:
        print("🎉 All ticket properties migrated successfully!")
    else:
        print("⚠️ Some errors occurred during migration. Check the report for details.")
    exit(0 if success else 1)