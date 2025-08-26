#!/usr/bin/env python3
"""
Custom Object Migrator - Universal migration system for HubSpot custom objects
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
from src.utils.utils import get_api_headers, make_hubspot_request, ensure_directory


class CustomObjectMigrator:
    """Universal migrator for any HubSpot custom object type"""
    
    def __init__(self, prod_token: str, sandbox_token: str):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.report_dir = 'reports'
        ensure_directory(self.report_dir)
        
        # Initialize field filter
        self.field_filter = HubSpotFieldFilter()
        
        # Track migrations
        self.object_mappings = {}  # Maps object_type -> {prod_id: sandbox_id}
        self.created_objects = {}  # Maps object_type -> [created_ids]
        self.updated_objects = {}  # Maps object_type -> [updated_ids]
        self.failed_objects = {}   # Maps object_type -> [failed_records]
        self.errors = []
    
    def get_custom_object_schemas(self, token: str) -> List[Dict[str, Any]]:
        """Get all custom object schemas from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/schemas'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            # Filter out standard objects
            all_schemas = data.get('results', [])
            custom_schemas = []
            
            standard_objects = {
                'contacts', 'companies', 'deals', 'tickets', 'products', 
                'line_items', 'quotes', 'calls', 'emails', 'meetings', 
                'tasks', 'notes', 'communications'
            }
            
            for schema in all_schemas:
                object_type = schema.get('name', '').lower()
                if object_type not in standard_objects:
                    custom_schemas.append(schema)
            
            return custom_schemas
        return []
    
    def create_custom_object_schema(self, schema_data: Dict[str, Any]) -> bool:
        """Create a custom object schema in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/schemas'
        
        # Prepare schema payload
        payload = {
            'name': schema_data['name'],
            'labels': schema_data.get('labels', {}),
            'primaryDisplayProperty': schema_data.get('primaryDisplayProperty', 'name'),
            'requiredProperties': schema_data.get('requiredProperties', []),
            'searchableProperties': schema_data.get('searchableProperties', []),
            'secondaryDisplayProperties': schema_data.get('secondaryDisplayProperties', [])
        }
        
        # Add description if present
        if 'description' in schema_data:
            payload['description'] = schema_data['description']
        
        object_label = schema_data.get('labels', {}).get('singular', schema_data['name'])
        print(f"  🔧 Creating custom object schema: {object_label}")
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            print(f"    ✅ Created successfully")
            return True
        else:
            if 'already exists' in str(data).lower():
                print(f"    ℹ️  Schema already exists")
                return True
            else:
                self.errors.append(f"Failed to create schema {schema_data['name']}: {data}")
                print(f"    ❌ Failed: {data}")
                return False
    
    def get_object_properties(self, token: str, object_type: str) -> List[Dict[str, Any]]:
        """Get properties for a custom object"""
        headers = get_api_headers(token)
        url = f'https://api.hubapi.com/crm/v3/properties/{object_type}'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def create_object_property(self, object_type: str, property_data: Dict[str, Any]) -> bool:
        """Create a custom property for an object"""
        headers = get_api_headers(self.sandbox_token)
        url = f'https://api.hubapi.com/crm/v3/properties/{object_type}'
        
        # Prepare property payload
        payload = {
            'name': property_data['name'],
            'label': property_data['label'],
            'type': property_data.get('type', 'string'),
            'fieldType': property_data.get('fieldType', 'text'),
            'groupName': property_data.get('groupName', 'information'),
            'description': property_data.get('description', ''),
            'options': property_data.get('options', []),
            'displayOrder': property_data.get('displayOrder', -1)
        }
        
        # Add additional fields if present
        for field in ['formField', 'hasUniqueValue', 'hidden', 'calculated']:
            if field in property_data:
                payload[field] = property_data[field]
        
        print(f"    🔧 Creating property: {property_data['label']} ({property_data['name']})")
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            return True
        else:
            if 'already exists' in str(data).lower():
                print(f"      ℹ️  Property already exists")
                return True
            else:
                self.errors.append(f"Failed to create property {property_data['name']} for {object_type}: {data}")
                print(f"      ❌ Failed: {data}")
                return False
    
    def get_custom_objects(self, token: str, object_type: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get custom objects of a specific type"""
        headers = get_api_headers(token)
        url = f'https://api.hubapi.com/crm/v3/objects/{object_type}'
        
        all_objects = []
        after = None
        batch_size = 100
        processed = 0
        
        # Get properties for the object
        properties = self.get_object_properties(token, object_type)
        if properties:
            safe_props = self.field_filter.get_safe_properties_list(properties)
            print(f"    📊 Using {len(safe_props)} properties for {object_type}")
        else:
            safe_props = ['name']  # Fallback to basic property
        
        while True:
            params = {
                'limit': batch_size,
                'sorts': 'createdate:desc'
            }
            
            if after:
                params['after'] = after
            
            if safe_props:
                params['properties'] = ','.join(safe_props[:50])  # API URL limit
            
            success, data = make_hubspot_request('GET', url, headers, params=params)
            
            if not success:
                print(f"    ⚠️ Failed to fetch {object_type}: {data}")
                break
            
            objects = data.get('results', [])
            if not objects:
                break
            
            all_objects.extend(objects)
            processed += len(objects)
            
            print(f"      📥 Fetched {len(objects)} {object_type} objects (Total: {processed})")
            
            if limit and processed >= limit:
                all_objects = all_objects[:limit]
                break
            
            after = data.get('paging', {}).get('next', {}).get('after')
            if not after:
                break
            
            time.sleep(0.1)  # Rate limiting
        
        return all_objects
    
    def clean_object_properties(self, object_props: Dict[str, Any], sandbox_properties: List[Dict]) -> Dict[str, Any]:
        """Clean object properties for creation in sandbox"""
        cleaned = {}
        sandbox_prop_names = {prop['name'] for prop in sandbox_properties}
        
        for prop_name, value in object_props.items():
            # Skip if property doesn't exist in sandbox
            if prop_name not in sandbox_prop_names:
                continue
            
            # Skip empty values
            if value is None or value == '':
                continue
            
            # Skip read-only properties
            if prop_name in ['hs_object_id', 'hs_createdate', 'hs_lastmodifieddate']:
                continue
            
            # Skip owner IDs for now (need special handling)
            if prop_name == 'hubspot_owner_id':
                continue
            
            cleaned[prop_name] = value
        
        return cleaned
    
    def create_custom_object(self, object_type: str, object_data: Dict[str, Any], 
                           sandbox_properties: List[Dict]) -> Tuple[bool, Dict]:
        """Create a custom object in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = f'https://api.hubapi.com/crm/v3/objects/{object_type}'
        
        # Clean properties
        cleaned_props = self.clean_object_properties(
            object_data.get('properties', {}),
            sandbox_properties
        )
        
        # Ensure we have at least a name or primary property
        if not cleaned_props:
            cleaned_props = {'name': f'Migrated {object_type}'}
        
        payload = {
            'properties': cleaned_props
        }
        
        success, result = make_hubspot_request('POST', url, headers, json_data=payload)
        return success, result
    
    def migrate_custom_object_type(self, object_type: str, schema: Dict[str, Any], 
                                 limit: Optional[int] = None) -> Dict[str, Any]:
        """Migrate all objects of a specific custom type"""
        object_label = schema.get('labels', {}).get('singular', object_type)
        print(f"\n🔄 Migrating custom object: {object_label} ({object_type})")
        print("=" * 60)
        
        # Initialize tracking for this object type
        if object_type not in self.object_mappings:
            self.object_mappings[object_type] = {}
            self.created_objects[object_type] = []
            self.updated_objects[object_type] = []
            self.failed_objects[object_type] = []
        
        # Step 1: Migrate properties
        print("  📋 1. Migrating properties...")
        prod_properties = self.get_object_properties(self.prod_token, object_type)
        sandbox_properties = self.get_object_properties(self.sandbox_token, object_type)
        
        if not prod_properties:
            print("    ⚠️ No properties found in production")
        else:
            print(f"    ✅ Found {len(prod_properties)} properties in production")
            
            # Create missing custom properties
            sandbox_prop_names = {p['name'] for p in sandbox_properties}
            custom_props_to_create = [p for p in prod_properties 
                                    if not p['name'].startswith('hs_') 
                                    and p['name'] not in sandbox_prop_names]
            
            if custom_props_to_create:
                print(f"    🔧 Creating {len(custom_props_to_create)} custom properties...")
                for prop in custom_props_to_create:
                    self.create_object_property(object_type, prop)
                    time.sleep(0.2)  # Rate limiting
                
                # Refresh sandbox properties
                sandbox_properties = self.get_object_properties(self.sandbox_token, object_type)
        
        # Step 2: Migrate objects
        print("  📦 2. Migrating objects...")
        prod_objects = self.get_custom_objects(self.prod_token, object_type, limit)
        
        if not prod_objects:
            print(f"    ℹ️ No {object_type} objects found in production")
            return {
                'object_type': object_type,
                'objects_created': 0,
                'objects_failed': 0,
                'success_rate': 100.0
            }
        
        print(f"    ✅ Found {len(prod_objects)} objects in production")
        
        # Get existing objects from sandbox
        sandbox_objects = self.get_custom_objects(self.sandbox_token, object_type)
        print(f"    ✅ Found {len(sandbox_objects)} existing objects in sandbox")
        
        # Process objects
        batch_size = 10
        total_objects = len(prod_objects)
        
        for i in range(0, total_objects, batch_size):
            batch = prod_objects[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_objects + batch_size - 1) // batch_size
            
            print(f"\n    📦 Processing batch {batch_num}/{total_batches} ({len(batch)} objects)")
            
            for idx, prod_object in enumerate(batch):
                prod_id = prod_object['id']
                properties = prod_object.get('properties', {})
                name = properties.get('name', f'Object {prod_id}')
                
                print(f"      [{i + idx + 1}/{total_objects}] {name[:50]}...")
                
                # Create object
                success, result = self.create_custom_object(object_type, prod_object, sandbox_properties)
                
                if success:
                    new_id = result['id']
                    self.object_mappings[object_type][prod_id] = new_id
                    self.created_objects[object_type].append(prod_id)
                    print(f"        ✅ Created successfully (ID: {new_id})")
                else:
                    self.failed_objects[object_type].append({
                        'id': prod_id,
                        'name': name,
                        'error': str(result)
                    })
                    print(f"        ❌ Failed: {result}")
                
                time.sleep(0.3)  # Rate limiting
        
        # Generate summary for this object type
        created_count = len(self.created_objects[object_type])
        failed_count = len(self.failed_objects[object_type])
        success_rate = (created_count / (created_count + failed_count) * 100) if (created_count + failed_count) > 0 else 0
        
        print(f"\n  📊 {object_label} Migration Summary:")
        print(f"    ✅ Objects created: {created_count}")
        print(f"    ❌ Objects failed: {failed_count}")
        print(f"    📈 Success rate: {success_rate:.1f}%")
        
        return {
            'object_type': object_type,
            'objects_created': created_count,
            'objects_failed': failed_count,
            'success_rate': success_rate
        }
    
    def migrate_all_custom_objects(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Migrate all custom objects from production to sandbox"""
        print("🔄 CUSTOM OBJECT MIGRATION")
        print("=" * 60)
        
        # Get custom object schemas from production
        print("📥 Analyzing custom objects in production...")
        prod_schemas = self.get_custom_object_schemas(self.prod_token)
        
        if not prod_schemas:
            print("✅ No custom objects found in production - migration complete!")
            return {
                'total_object_types': 0,
                'object_results': [],
                'overall_success_rate': 100.0,
                'errors': []
            }
        
        print(f"✅ Found {len(prod_schemas)} custom object types")
        
        # Get sandbox schemas for comparison
        sandbox_schemas = self.get_custom_object_schemas(self.sandbox_token)
        sandbox_schema_names = {s['name'] for s in sandbox_schemas}
        
        # Create missing schemas
        schemas_to_create = [s for s in prod_schemas if s['name'] not in sandbox_schema_names]
        
        if schemas_to_create:
            print(f"\n🔧 Creating {len(schemas_to_create)} custom object schemas...")
            for schema in schemas_to_create:
                self.create_custom_object_schema(schema)
                time.sleep(0.5)  # Rate limiting
        
        # Migrate each object type
        migration_results = []
        
        for schema in prod_schemas:
            object_type = schema['name']
            result = self.migrate_custom_object_type(object_type, schema, limit)
            migration_results.append(result)
        
        # Generate overall report
        total_created = sum(r['objects_created'] for r in migration_results)
        total_failed = sum(r['objects_failed'] for r in migration_results)
        overall_success_rate = (total_created / (total_created + total_failed) * 100) if (total_created + total_failed) > 0 else 100
        
        report = {
            'total_object_types': len(prod_schemas),
            'object_results': migration_results,
            'overall_success_rate': overall_success_rate,
            'total_objects_created': total_created,
            'total_objects_failed': total_failed,
            'errors': self.errors
        }
        
        # Save detailed report
        self._generate_report(report)
        
        # Final summary
        print(f"\n" + "=" * 60)
        print("📊 CUSTOM OBJECT MIGRATION SUMMARY")
        print("=" * 60)
        print(f"✅ Object types processed: {len(prod_schemas)}")
        print(f"✅ Total objects created: {total_created}")
        print(f"❌ Total objects failed: {total_failed}")
        print(f"📈 Overall success rate: {overall_success_rate:.1f}%")
        if self.errors:
            print(f"⚠️ Errors encountered: {len(self.errors)}")
        print("=" * 60)
        
        return report
    
    def _generate_report(self, migration_report: Dict[str, Any]):
        """Generate detailed migration report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.report_dir, f'custom_object_migration_{timestamp}.json')
        
        detailed_report = {
            'timestamp': datetime.now().isoformat(),
            'summary': migration_report,
            'object_mappings': self.object_mappings,
            'created_objects': self.created_objects,
            'failed_objects': self.failed_objects,
            'errors': self.errors
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_report, f, indent=2, default=str)
        
        print(f"📄 Detailed report saved: {report_file}")


def migrate_custom_objects(limit: Optional[int] = None):
    """Main function to execute custom object migration"""
    print("🔄 Custom Object Migration System")
    print("=" * 60)
    
    config = SecureConfig()
    hubspot_config = config.get_hubspot_config()
    
    migrator = CustomObjectMigrator(
        prod_token=hubspot_config['production_token'],
        sandbox_token=hubspot_config['sandbox_token']
    )
    
    # Run migration
    report = migrator.migrate_all_custom_objects(limit)
    
    success_rate = report['overall_success_rate']
    if success_rate >= 95:
        print("🎉 Custom object migration completed successfully!")
        return True
    else:
        print(f"⚠️ Migration completed with {success_rate:.1f}% success rate")
        return False


if __name__ == "__main__":
    success = migrate_custom_objects()
    exit(0 if success else 1)