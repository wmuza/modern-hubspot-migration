#!/usr/bin/env python3
"""
Ticket Analysis Tool - Analyze ticket properties, pipelines, and data structure
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


class TicketAnalyzer:
    """Analyze tickets in HubSpot production environment"""
    
    def __init__(self, prod_token: str, sandbox_token: Optional[str] = None):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.report_dir = 'reports/ticket_analysis'
        ensure_directory(self.report_dir)
    
    def get_ticket_properties(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all ticket properties from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def get_ticket_pipelines(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all ticket pipelines from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/pipelines/tickets'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def get_ticket_property_groups(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all ticket property groups from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/properties/tickets/groups'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def get_sample_tickets(self, token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch sample tickets to analyze data structure"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/objects/tickets'
        
        # Get all properties for analysis
        properties = self.get_ticket_properties(token)
        prop_names = [p['name'] for p in properties]
        
        params = {
            'limit': limit,
            'properties': ','.join(prop_names[:50]),  # API has limit on URL length
            'associations': 'contacts,companies,deals',
            'sorts': 'createdate:desc'
        }
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        if success:
            return data.get('results', [])
        return []
    
    def analyze_ticket_schema(self) -> Dict[str, Any]:
        """Perform complete ticket schema analysis"""
        print("🎫 TICKET SCHEMA ANALYSIS")
        print("=" * 60)
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'production': {},
            'sandbox': {},
            'comparison': {}
        }
        
        # Analyze production
        print("\n📥 Analyzing Production Tickets...")
        prod_properties = self.get_ticket_properties(self.prod_token)
        prod_pipelines = self.get_ticket_pipelines(self.prod_token)
        prod_groups = self.get_ticket_property_groups(self.prod_token)
        prod_samples = self.get_sample_tickets(self.prod_token)
        
        analysis['production'] = {
            'properties': {
                'total': len(prod_properties),
                'custom': len([p for p in prod_properties if not p['name'].startswith('hs_')]),
                'system': len([p for p in prod_properties if p['name'].startswith('hs_')]),
                'details': prod_properties
            },
            'pipelines': {
                'total': len(prod_pipelines),
                'details': prod_pipelines,
                'stages': self._extract_stages(prod_pipelines)
            },
            'property_groups': {
                'total': len(prod_groups),
                'custom': len([g for g in prod_groups if not g.get('name', '').startswith('hs_')]),
                'details': prod_groups
            },
            'sample_tickets': {
                'count': len(prod_samples),
                'data': prod_samples
            }
        }
        
        print(f"✅ Found {len(prod_properties)} properties")
        print(f"   - Custom: {analysis['production']['properties']['custom']}")
        print(f"   - System: {analysis['production']['properties']['system']}")
        print(f"✅ Found {len(prod_pipelines)} pipelines")
        print(f"✅ Found {len(prod_groups)} property groups")
        print(f"✅ Found {len(prod_samples)} sample tickets")
        
        # Analyze sandbox if token provided
        if self.sandbox_token:
            print("\n📥 Analyzing Sandbox Tickets...")
            sand_properties = self.get_ticket_properties(self.sandbox_token)
            sand_pipelines = self.get_ticket_pipelines(self.sandbox_token)
            sand_groups = self.get_ticket_property_groups(self.sandbox_token)
            sand_samples = self.get_sample_tickets(self.sandbox_token)
            
            analysis['sandbox'] = {
                'properties': {
                    'total': len(sand_properties),
                    'custom': len([p for p in sand_properties if not p['name'].startswith('hs_')]),
                    'system': len([p for p in sand_properties if p['name'].startswith('hs_')]),
                    'details': sand_properties
                },
                'pipelines': {
                    'total': len(sand_pipelines),
                    'details': sand_pipelines,
                    'stages': self._extract_stages(sand_pipelines)
                },
                'property_groups': {
                    'total': len(sand_groups),
                    'custom': len([g for g in sand_groups if not g.get('name', '').startswith('hs_')]),
                    'details': sand_groups
                },
                'sample_tickets': {
                    'count': len(sand_samples),
                    'data': sand_samples
                }
            }
            
            print(f"✅ Found {len(sand_properties)} properties")
            print(f"   - Custom: {analysis['sandbox']['properties']['custom']}")
            print(f"   - System: {analysis['sandbox']['properties']['system']}")
            print(f"✅ Found {len(sand_pipelines)} pipelines")
            print(f"✅ Found {len(sand_groups)} property groups")
            print(f"✅ Found {len(sand_samples)} sample tickets")
            
            # Compare environments
            self._compare_environments(analysis)
        
        # Generate report
        self._generate_report(analysis)
        
        return analysis
    
    def _extract_stages(self, pipelines: List[Dict]) -> Dict[str, List[str]]:
        """Extract stages from pipelines"""
        stages = {}
        for pipeline in pipelines:
            pipeline_id = pipeline.get('id', 'unknown')
            pipeline_label = pipeline.get('label', 'Unknown')
            pipeline_stages = pipeline.get('stages', [])
            stages[f"{pipeline_label} ({pipeline_id})"] = [
                f"{stage.get('label', 'Unknown')} ({stage.get('id', '')})"
                for stage in pipeline_stages
            ]
        return stages
    
    def _compare_environments(self, analysis: Dict[str, Any]):
        """Compare production and sandbox environments"""
        print("\n🔍 ENVIRONMENT COMPARISON")
        print("=" * 60)
        
        prod_props = {p['name'] for p in analysis['production']['properties']['details']}
        sand_props = {p['name'] for p in analysis['sandbox']['properties']['details']}
        
        missing_in_sandbox = prod_props - sand_props
        extra_in_sandbox = sand_props - prod_props
        
        prod_pipelines = {p['id'] for p in analysis['production']['pipelines']['details']}
        sand_pipelines = {p['id'] for p in analysis['sandbox']['pipelines']['details']}
        
        missing_pipelines = prod_pipelines - sand_pipelines
        
        analysis['comparison'] = {
            'properties': {
                'missing_in_sandbox': list(missing_in_sandbox),
                'extra_in_sandbox': list(extra_in_sandbox),
                'common': list(prod_props & sand_props)
            },
            'pipelines': {
                'missing_in_sandbox': list(missing_pipelines),
                'production_count': len(prod_pipelines),
                'sandbox_count': len(sand_pipelines)
            }
        }
        
        print(f"📊 Properties to migrate: {len(missing_in_sandbox)}")
        if missing_in_sandbox:
            print(f"   Missing: {', '.join(list(missing_in_sandbox)[:5])}...")
        
        print(f"📊 Pipelines to create: {len(missing_pipelines)}")
    
    def _generate_report(self, analysis: Dict[str, Any]):
        """Generate detailed analysis report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.report_dir, f'ticket_analysis_{timestamp}.json')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n📄 Analysis report saved: {report_file}")
        
        # Generate summary report
        summary_file = os.path.join(self.report_dir, f'ticket_summary_{timestamp}.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("TICKET MIGRATION ANALYSIS SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("PRODUCTION ENVIRONMENT\n")
            f.write(f"Total Properties: {analysis['production']['properties']['total']}\n")
            f.write(f"  - Custom: {analysis['production']['properties']['custom']}\n")
            f.write(f"  - System: {analysis['production']['properties']['system']}\n")
            f.write(f"Total Pipelines: {analysis['production']['pipelines']['total']}\n")
            f.write(f"Property Groups: {analysis['production']['property_groups']['total']}\n")
            f.write(f"Sample Tickets: {analysis['production']['sample_tickets']['count']}\n\n")
            
            if self.sandbox_token:
                f.write("SANDBOX ENVIRONMENT\n")
                f.write(f"Total Properties: {analysis['sandbox']['properties']['total']}\n")
                f.write(f"  - Custom: {analysis['sandbox']['properties']['custom']}\n")
                f.write(f"  - System: {analysis['sandbox']['properties']['system']}\n")
                f.write(f"Total Pipelines: {analysis['sandbox']['pipelines']['total']}\n")
                f.write(f"Property Groups: {analysis['sandbox']['property_groups']['total']}\n")
                f.write(f"Sample Tickets: {analysis['sandbox']['sample_tickets']['count']}\n\n")
                
                f.write("MIGRATION REQUIREMENTS\n")
                f.write(f"Properties to create: {len(analysis['comparison']['properties']['missing_in_sandbox'])}\n")
                f.write(f"Pipelines to create: {len(analysis['comparison']['pipelines']['missing_in_sandbox'])}\n")
        
        print(f"📄 Summary report saved: {summary_file}")


def main():
    """Main function to run ticket analysis"""
    print("🎫 HubSpot Ticket Analysis Tool")
    print("=" * 60)
    
    # Load configuration
    config = SecureConfig()
    hubspot_config = config.get_hubspot_config()
    
    # Initialize analyzer
    analyzer = TicketAnalyzer(
        prod_token=hubspot_config['production_token'],
        sandbox_token=hubspot_config['sandbox_token']
    )
    
    # Run analysis
    analysis = analyzer.analyze_ticket_schema()
    
    print("\n✅ Ticket analysis complete!")
    print("📋 Check the reports folder for detailed analysis")


if __name__ == "__main__":
    main()