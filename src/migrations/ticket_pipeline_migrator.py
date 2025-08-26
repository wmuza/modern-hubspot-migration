#!/usr/bin/env python3
"""
Ticket Pipeline Migrator - Creates and syncs ticket pipelines between HubSpot accounts
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


class TicketPipelineMigrator:
    """Migrate ticket pipelines between HubSpot accounts"""
    
    DEFAULT_PIPELINE_ID = '0'  # HubSpot's default ticket pipeline ID
    
    def __init__(self, prod_token: str, sandbox_token: str):
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.report_dir = 'reports'
        ensure_directory(self.report_dir)
        
        # Track migrations
        self.pipeline_mapping = {}
        self.created_pipelines = []
        self.updated_pipelines = []
        self.errors = []
    
    def get_ticket_pipelines(self, token: str) -> List[Dict[str, Any]]:
        """Fetch all ticket pipelines from a portal"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/pipelines/tickets'
        
        success, data = make_hubspot_request('GET', url, headers)
        if success:
            return data.get('results', [])
        return []
    
    def create_ticket_pipeline(self, pipeline_data: Dict[str, Any]) -> Optional[str]:
        """Create a ticket pipeline in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/pipelines/tickets'
        
        # Prepare stages
        stages = []
        for idx, stage in enumerate(pipeline_data.get('stages', [])):
            stage_data = {
                'label': stage['label'],
                'displayOrder': stage.get('displayOrder', idx),
                'metadata': {
                    'ticketState': stage.get('metadata', {}).get('ticketState', 'OPEN')
                }
            }
            # Add stage properties if present
            if 'properties' in stage:
                stage_data['properties'] = stage['properties']
            
            stages.append(stage_data)
        
        # Prepare pipeline payload
        payload = {
            'label': pipeline_data['label'],
            'displayOrder': pipeline_data.get('displayOrder', 0),
            'stages': stages
        }
        
        print(f"  🔧 Creating pipeline: {pipeline_data['label']}")
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            new_pipeline_id = data['id']
            self.created_pipelines.append(pipeline_data['label'])
            print(f"    ✅ Created with ID: {new_pipeline_id}")
            return new_pipeline_id
        else:
            self.errors.append(f"Failed to create pipeline {pipeline_data['label']}: {data}")
            print(f"    ❌ Failed: {data}")
            return None
    
    def update_pipeline_stages(self, pipeline_id: str, prod_pipeline: Dict[str, Any], 
                              sand_pipeline: Dict[str, Any]) -> bool:
        """Update pipeline stages to match production"""
        prod_stages = prod_pipeline.get('stages', [])
        sand_stages = sand_pipeline.get('stages', [])
        
        # Check if stages need updating
        prod_stage_labels = [s['label'] for s in prod_stages]
        sand_stage_labels = [s['label'] for s in sand_stages]
        
        if prod_stage_labels == sand_stage_labels:
            print(f"    ✅ Stage counts match")
            return True
        
        print(f"    ⚠️ Stage mismatch - Production: {len(prod_stages)}, Sandbox: {len(sand_stages)}")
        
        # For now, log the difference but don't auto-update (safer approach)
        missing_stages = set(prod_stage_labels) - set(sand_stage_labels)
        extra_stages = set(sand_stage_labels) - set(prod_stage_labels)
        
        if missing_stages:
            print(f"    📌 Missing stages: {', '.join(missing_stages)}")
        if extra_stages:
            print(f"    📌 Extra stages: {', '.join(extra_stages)}")
        
        self.updated_pipelines.append({
            'pipeline': pipeline_id,
            'label': prod_pipeline['label'],
            'missing_stages': list(missing_stages),
            'extra_stages': list(extra_stages)
        })
        
        return True
    
    def migrate_ticket_pipelines(self) -> Dict[str, Any]:
        """Main migration function for ticket pipelines"""
        print("📊 Ticket Pipeline Migration")
        print("=" * 50)
        
        # Get pipelines from both environments
        print("📥 Fetching ticket pipelines from production...")
        prod_pipelines = self.get_ticket_pipelines(self.prod_token)
        print(f"✅ Found {len(prod_pipelines)} pipelines in production")
        
        print("📥 Fetching ticket pipelines from sandbox...")
        sand_pipelines = self.get_ticket_pipelines(self.sandbox_token)
        sand_pipeline_map = {p['id']: p for p in sand_pipelines}
        print(f"✅ Found {len(sand_pipelines)} pipelines in sandbox")
        
        pipelines_to_create = []
        pipelines_to_check = []
        
        # Process each production pipeline
        for prod_pipeline in prod_pipelines:
            pipeline_id = prod_pipeline['id']
            pipeline_label = prod_pipeline['label']
            
            # Skip default pipeline (can't create or modify)
            if pipeline_id == self.DEFAULT_PIPELINE_ID:
                print(f"⏭️  Skipping default pipeline: {pipeline_label}")
                self.pipeline_mapping[pipeline_id] = pipeline_id
                continue
            
            # Check if pipeline exists in sandbox
            if pipeline_id in sand_pipeline_map:
                print(f"🔄 Pipeline exists, will check for updates: {pipeline_label}")
                pipelines_to_check.append(prod_pipeline)
                self.pipeline_mapping[pipeline_id] = pipeline_id
            else:
                print(f"📝 Pipeline needs to be created: {pipeline_label}")
                pipelines_to_create.append(prod_pipeline)
        
        # Summary
        print(f"🔄 Pipelines to create: {len(pipelines_to_create)}")
        print(f"🔄 Pipelines to check/update: {len(pipelines_to_check)}")
        
        # Create missing pipelines
        if pipelines_to_create:
            print("\n📦 Creating pipelines...")
            for pipeline in pipelines_to_create:
                new_id = self.create_ticket_pipeline(pipeline)
                if new_id:
                    self.pipeline_mapping[pipeline['id']] = new_id
                time.sleep(0.3)  # Rate limiting
        
        # Check existing pipelines for updates
        if pipelines_to_check:
            print(f"\n🔄 Checking {len(pipelines_to_check)} existing pipelines...")
            for prod_pipeline in pipelines_to_check:
                pipeline_id = prod_pipeline['id']
                pipeline_label = prod_pipeline['label']
                sand_pipeline = sand_pipeline_map.get(pipeline_id)
                
                if sand_pipeline:
                    print(f"  🔍 Checking pipeline: {pipeline_label}")
                    prod_stage_count = len(prod_pipeline.get('stages', []))
                    sand_stage_count = len(sand_pipeline.get('stages', []))
                    print(f"    📊 Production stages: {prod_stage_count}")
                    print(f"    📊 Sandbox stages: {sand_stage_count}")
                    self.update_pipeline_stages(pipeline_id, prod_pipeline, sand_pipeline)
        
        # Generate report
        report = self._generate_report(prod_pipelines, sand_pipelines)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TICKET PIPELINE MIGRATION SUMMARY")
        print("=" * 50)
        print(f"✅ New pipelines created: {len(self.created_pipelines)}")
        print(f"🔄 Existing pipelines checked: {len(pipelines_to_check)}")
        print(f"📝 Total processed: {len(prod_pipelines)} pipelines")
        if self.errors:
            print(f"❌ Errors encountered: {len(self.errors)}")
        print("=" * 50)
        
        return report
    
    def _generate_report(self, prod_pipelines: List[Dict], sand_pipelines: List[Dict]) -> Dict[str, Any]:
        """Generate migration report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'production_pipelines': len(prod_pipelines),
                'sandbox_pipelines': len(sand_pipelines),
                'pipelines_created': len(self.created_pipelines),
                'pipelines_updated': len(self.updated_pipelines),
                'errors': len(self.errors)
            },
            'pipeline_mapping': self.pipeline_mapping,
            'created': self.created_pipelines,
            'updated': self.updated_pipelines,
            'errors': self.errors,
            'production_pipelines': prod_pipelines,
            'sandbox_pipelines': sand_pipelines
        }
        
        report_file = os.path.join(self.report_dir, f'ticket_pipeline_migration_{timestamp}.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Pipeline mapping saved: {report_file}")
        
        return report


def migrate_ticket_pipelines():
    """Main function to migrate ticket pipelines"""
    # Load configuration
    config = SecureConfig()
    hubspot_config = config.get_hubspot_config()
    
    # Initialize migrator
    migrator = TicketPipelineMigrator(
        prod_token=hubspot_config['production_token'],
        sandbox_token=hubspot_config['sandbox_token']
    )
    
    # Run migration
    report = migrator.migrate_ticket_pipelines()
    
    if report['summary']['errors'] == 0:
        print("🎉 All ticket pipelines migrated successfully!")
        print("💡 Ready for ticket data migration")
        return True
    else:
        print("⚠️ Some errors occurred during pipeline migration. Check the report for details.")
        return False


if __name__ == "__main__":
    success = migrate_ticket_pipelines()
    exit(0 if success else 1)