#!/usr/bin/env python3
"""
Custom Object Analyzer - Discover and analyze custom objects in HubSpot
For HubSpot Modern Migration Tool
"""
import sys
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.config import SecureConfig
from src.utils.utils import get_api_headers, make_hubspot_request, ensure_directory


class CustomObjectAnalyzer:
    """Analyze custom objects in HubSpot environments"""
    
    def __init__(self, prod_token: str, sandbox_token: Optional[str] = None):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.report_dir = 'reports/custom_object_analysis'
        ensure_directory(self.report_dir)
    
    def get_custom_object_schemas(self, token: str) -> List[Dict[str, Any]]:
        """Get all custom object schemas from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/schemas'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            # Filter out standard objects, keep only custom ones
            all_schemas = data.get('results', [])
            custom_schemas = []
            
            # Standard HubSpot objects to exclude
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
    
    def get_object_properties(self, token: str, object_type: str) -> List[Dict[str, Any]]:
        """Get properties for a specific custom object"""
        headers = get_api_headers(token)
        url = f'https://api.hubapi.com/crm/v3/properties/{object_type}'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def get_sample_objects(self, token: str, object_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample objects of a custom type"""
        headers = get_api_headers(token)
        url = f'https://api.hubapi.com/crm/v3/objects/{object_type}'
        
        params = {
            'limit': limit,
            'sorts': 'createdate:desc'
        }
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        if success:
            return data.get('results', [])
        return []
    
    def get_object_associations(self, token: str, object_type: str) -> List[Dict[str, Any]]:
        """Get association types for a custom object"""
        headers = get_api_headers(token)
        url = f'https://api.hubapi.com/crm/v4/associations/{object_type}/labels'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def analyze_custom_objects(self) -> Dict[str, Any]:
        """Perform complete custom object analysis"""
        print("🔍 CUSTOM OBJECT ANALYSIS")
        print("=" * 60)
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'production': {},
            'sandbox': {},
            'comparison': {}
        }
        
        # Analyze production
        print("\n📥 Analyzing Production Custom Objects...")
        prod_schemas = self.get_custom_object_schemas(self.prod_token)
        
        print(f"✅ Found {len(prod_schemas)} custom object types in production")
        
        if not prod_schemas:
            print("ℹ️ No custom objects found in production environment")
            analysis['production'] = {
                'schemas': [],
                'total_objects': 0,
                'details': {}
            }
        else:
            prod_details = {}
            
            for schema in prod_schemas:
                object_type = schema['name']
                print(f"\n📊 Analyzing custom object: {schema.get('labels', {}).get('singular', object_type)}")
                
                # Get properties
                properties = self.get_object_properties(self.prod_token, object_type)
                custom_props = [p for p in properties if not p['name'].startswith('hs_')]
                
                # Get sample data
                samples = self.get_sample_objects(self.prod_token, object_type)
                
                # Get associations
                associations = self.get_object_associations(self.prod_token, object_type)
                
                prod_details[object_type] = {
                    'schema': schema,
                    'properties': {
                        'total': len(properties),
                        'custom': len(custom_props),
                        'details': properties
                    },
                    'samples': {
                        'count': len(samples),
                        'data': samples
                    },
                    'associations': {
                        'types': len(associations),
                        'details': associations
                    }
                }
                
                print(f"   Properties: {len(properties)} (custom: {len(custom_props)})")
                print(f"   Sample records: {len(samples)}")
                print(f"   Association types: {len(associations)}")
            
            analysis['production'] = {
                'schemas': prod_schemas,
                'total_objects': len(prod_schemas),
                'details': prod_details
            }
        
        # Analyze sandbox if token provided
        if self.sandbox_token:
            print("\n📥 Analyzing Sandbox Custom Objects...")
            sand_schemas = self.get_custom_object_schemas(self.sandbox_token)
            
            print(f"✅ Found {len(sand_schemas)} custom object types in sandbox")
            
            if not sand_schemas:
                analysis['sandbox'] = {
                    'schemas': [],
                    'total_objects': 0,
                    'details': {}
                }
            else:
                sand_details = {}
                
                for schema in sand_schemas:
                    object_type = schema['name']
                    
                    # Get properties
                    properties = self.get_object_properties(self.sandbox_token, object_type)
                    custom_props = [p for p in properties if not p['name'].startswith('hs_')]
                    
                    # Get sample data
                    samples = self.get_sample_objects(self.sandbox_token, object_type)
                    
                    # Get associations
                    associations = self.get_object_associations(self.sandbox_token, object_type)
                    
                    sand_details[object_type] = {
                        'schema': schema,
                        'properties': {
                            'total': len(properties),
                            'custom': len(custom_props),
                            'details': properties
                        },
                        'samples': {
                            'count': len(samples),
                            'data': samples
                        },
                        'associations': {
                            'types': len(associations),
                            'details': associations
                        }
                    }
                
                analysis['sandbox'] = {
                    'schemas': sand_schemas,
                    'total_objects': len(sand_schemas),
                    'details': sand_details
                }
            
            # Compare environments
            self._compare_environments(analysis)
        
        # Generate report
        self._generate_report(analysis)
        
        return analysis
    
    def _compare_environments(self, analysis: Dict[str, Any]):
        """Compare production and sandbox custom objects"""
        print("\n🔍 ENVIRONMENT COMPARISON")
        print("=" * 60)
        
        prod_objects = {schema['name'] for schema in analysis['production']['schemas']}
        sand_objects = {schema['name'] for schema in analysis['sandbox']['schemas']}
        
        missing_in_sandbox = prod_objects - sand_objects
        extra_in_sandbox = sand_objects - prod_objects
        common_objects = prod_objects & sand_objects
        
        analysis['comparison'] = {
            'objects_to_create': list(missing_in_sandbox),
            'extra_in_sandbox': list(extra_in_sandbox),
            'common_objects': list(common_objects),
            'migration_needed': len(missing_in_sandbox) > 0
        }
        
        print(f"📊 Custom objects to migrate: {len(missing_in_sandbox)}")
        if missing_in_sandbox:
            for obj in missing_in_sandbox:
                schema = next(s for s in analysis['production']['schemas'] if s['name'] == obj)
                label = schema.get('labels', {}).get('singular', obj)
                print(f"   - {label} ({obj})")
        
        print(f"📊 Common objects: {len(common_objects)}")
        if common_objects:
            print(f"   Objects: {', '.join(common_objects)}")
    
    def _generate_report(self, analysis: Dict[str, Any]):
        """Generate detailed analysis report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.report_dir, f'custom_object_analysis_{timestamp}.json')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n📄 Analysis report saved: {report_file}")
        
        # Generate summary report
        summary_file = os.path.join(self.report_dir, f'custom_object_summary_{timestamp}.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("CUSTOM OBJECT MIGRATION ANALYSIS SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("PRODUCTION ENVIRONMENT\n")
            f.write(f"Custom Object Types: {analysis['production']['total_objects']}\n")
            
            if analysis['production']['total_objects'] > 0:
                f.write("Objects Found:\n")
                for schema in analysis['production']['schemas']:
                    label = schema.get('labels', {}).get('singular', schema['name'])
                    f.write(f"  - {label} ({schema['name']})\n")
            
            f.write(f"\nSANDBOX ENVIRONMENT\n")
            f.write(f"Custom Object Types: {analysis['sandbox']['total_objects']}\n")
            
            if self.sandbox_token and 'comparison' in analysis:
                f.write(f"\nMIGRATION REQUIREMENTS\n")
                f.write(f"Objects to create: {len(analysis['comparison']['objects_to_create'])}\n")
                if analysis['comparison']['objects_to_create']:
                    for obj in analysis['comparison']['objects_to_create']:
                        f.write(f"  - {obj}\n")
        
        print(f"📄 Summary report saved: {summary_file}")


def main():
    """Main function to run custom object analysis"""
    print("🔍 HubSpot Custom Object Analysis Tool")
    print("=" * 60)
    
    # Load configuration
    config = SecureConfig()
    hubspot_config = config.get_hubspot_config()
    
    # Initialize analyzer
    analyzer = CustomObjectAnalyzer(
        prod_token=hubspot_config['production_token'],
        sandbox_token=hubspot_config['sandbox_token']
    )
    
    # Run analysis
    analysis = analyzer.analyze_custom_objects()
    
    print("\n✅ Custom object analysis complete!")
    print("📋 Check the reports folder for detailed analysis")
    
    # Quick summary
    prod_count = analysis['production']['total_objects']
    sand_count = analysis['sandbox']['total_objects'] if analyzer.sandbox_token else 0
    
    if prod_count == 0:
        print("\n💡 No custom objects found in production - standard migration covers your needs!")
    else:
        print(f"\n📊 Found {prod_count} custom object type(s) in production")
        if analyzer.sandbox_token:
            missing = len(analysis['comparison']['objects_to_create'])
            if missing == 0:
                print("✅ All custom objects already exist in sandbox")
            else:
                print(f"🔄 {missing} custom object type(s) need migration")


if __name__ == "__main__":
    main()