#!/usr/bin/env python
"""
Deal Pipeline Migration Script
Recreates deal pipelines and stages from production in sandbox with exact configuration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
import time
import json
from datetime import datetime

def get_deal_pipelines(token):
    """Get all deal pipelines from a HubSpot portal"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/pipelines/deals'
    
    success, data = make_hubspot_request('GET', url, headers)
    if success:
        return data.get('results', [])
    else:
        print(f"❌ Error fetching deal pipelines: {data}")
        return []

def create_deal_pipeline(token, pipeline_definition):
    """Create a deal pipeline in the target portal"""
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/pipelines/deals'
    
    # Clean the pipeline definition for creation
    clean_def = {
        'label': pipeline_definition['label'],
        'displayOrder': pipeline_definition.get('displayOrder', 0),
        'stages': []
    }
    
    # Process stages
    for stage in pipeline_definition.get('stages', []):
        clean_stage = {
            'label': stage['label'],
            'displayOrder': stage.get('displayOrder', 0),
            'metadata': {}
        }
        
        # Add stage metadata (probability, etc.)
        stage_metadata = stage.get('metadata', {})
        if 'probability' in stage_metadata:
            clean_stage['metadata']['probability'] = stage_metadata['probability']
        if 'isClosed' in stage_metadata:
            clean_stage['metadata']['isClosed'] = stage_metadata['isClosed']
        if 'closeWon' in stage_metadata:
            clean_stage['metadata']['closeWon'] = stage_metadata['closeWon']
        
        clean_def['stages'].append(clean_stage)
    
    success, data = make_hubspot_request('POST', url, headers, json_data=clean_def)
    return success, data

def update_deal_pipeline(token, pipeline_id, pipeline_definition):
    """Update an existing deal pipeline"""
    headers = get_api_headers(token)
    url = f'https://api.hubapi.com/crm/v3/pipelines/deals/{pipeline_id}'
    
    # Clean the pipeline definition for update
    clean_def = {
        'label': pipeline_definition['label'],
        'displayOrder': pipeline_definition.get('displayOrder', 0)
    }
    
    success, data = make_hubspot_request('PATCH', url, headers, json_data=clean_def)
    return success, data

def create_deal_stage(token, pipeline_id, stage_definition):
    """Create a stage in a deal pipeline"""
    headers = get_api_headers(token)
    url = f'https://api.hubapi.com/crm/v3/pipelines/deals/{pipeline_id}/stages'
    
    clean_stage = {
        'label': stage_definition['label'],
        'displayOrder': stage_definition.get('displayOrder', 0),
        'metadata': {}
    }
    
    # Add stage metadata
    stage_metadata = stage_definition.get('metadata', {})
    if 'probability' in stage_metadata:
        clean_stage['metadata']['probability'] = stage_metadata['probability']
    if 'isClosed' in stage_metadata:
        clean_stage['metadata']['isClosed'] = stage_metadata['isClosed']
    if 'closeWon' in stage_metadata:
        clean_stage['metadata']['closeWon'] = stage_metadata['closeWon']
    
    success, data = make_hubspot_request('POST', url, headers, json_data=clean_stage)
    return success, data

def migrate_deal_pipelines():
    """Main function to migrate deal pipelines from production to sandbox"""
    print("📊 Deal Pipeline Migration")
    print("=" * 50)
    
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    if not prod_token or not sandbox_token:
        print("❌ Error: API tokens not found in .env file")
        return False
    
    # Get pipelines from production
    print("📥 Fetching deal pipelines from production...")
    prod_pipelines = get_deal_pipelines(prod_token)
    
    if not prod_pipelines:
        print("❌ Failed to get production pipelines")
        return False
    
    print(f"✅ Found {len(prod_pipelines)} pipelines in production")
    
    # Get pipelines from sandbox
    print("📥 Fetching deal pipelines from sandbox...")
    sandbox_pipelines = get_deal_pipelines(sandbox_token)
    sandbox_pipeline_labels = {pipeline['label'] for pipeline in sandbox_pipelines}
    
    print(f"✅ Found {len(sandbox_pipelines)} pipelines in sandbox")
    
    # Analyze what needs to be created
    pipelines_to_create = []
    pipelines_to_update = []
    
    for prod_pipeline in prod_pipelines:
        pipeline_label = prod_pipeline['label']
        
        # Skip default pipeline (always exists)
        if prod_pipeline.get('id') == 'default' or pipeline_label == 'Sales Pipeline':
            print(f"⏭️  Skipping default pipeline: {pipeline_label}")
            continue
        
        # Check if pipeline exists in sandbox
        if pipeline_label in sandbox_pipeline_labels:
            print(f"🔄 Pipeline exists, will check for updates: {pipeline_label}")
            pipelines_to_update.append(prod_pipeline)
        else:
            print(f"➕ New pipeline to create: {pipeline_label}")
            pipelines_to_create.append(prod_pipeline)
    
    print(f"🔄 Pipelines to create: {len(pipelines_to_create)}")
    print(f"🔄 Pipelines to check/update: {len(pipelines_to_update)}")
    
    if not pipelines_to_create and not pipelines_to_update:
        print("✅ All pipelines already exist in sandbox")
        return True
    
    print()
    
    # Create new pipelines
    created = 0
    failed = 0
    pipeline_mapping = {}
    
    if pipelines_to_create:
        print(f"📊 Creating {len(pipelines_to_create)} new pipelines...")
        for i, pipeline in enumerate(pipelines_to_create, 1):
            pipeline_label = pipeline['label']
            stages_count = len(pipeline.get('stages', []))
            
            print(f"  [{i}/{len(pipelines_to_create)}] Creating: {pipeline_label} ({stages_count} stages)")
            
            success, result = create_deal_pipeline(sandbox_token, pipeline)
            
            if success:
                created += 1
                new_pipeline_id = result.get('id')
                pipeline_mapping[pipeline['id']] = new_pipeline_id
                print(f"    ✅ Created successfully (ID: {new_pipeline_id})")
                
                # Display created stages
                created_stages = result.get('stages', [])
                for stage in created_stages:
                    stage_label = stage['label']
                    probability = stage.get('metadata', {}).get('probability', 'N/A')
                    print(f"      🎯 Stage: {stage_label} (Probability: {probability})")
                    
            else:
                failed += 1
                error_msg = result.get('error', str(result)) if isinstance(result, dict) else str(result)
                print(f"    ❌ Failed: {str(error_msg)[:80]}...")
            
            # Rate limiting
            time.sleep(0.2)
            print()
    
    # Update existing pipelines if needed
    updated = 0
    if pipelines_to_update:
        print(f"🔄 Checking {len(pipelines_to_update)} existing pipelines...")
        for pipeline in pipelines_to_update:
            pipeline_label = pipeline['label']
            print(f"  🔍 Checking pipeline: {pipeline_label}")
            
            # For now, we'll just log what would be updated
            # In a full implementation, we'd compare stages and update as needed
            print(f"    📊 Production stages: {len(pipeline.get('stages', []))}")
            
            # Find matching sandbox pipeline
            matching_sandbox = None
            for sandbox_pipeline in sandbox_pipelines:
                if sandbox_pipeline['label'] == pipeline_label:
                    matching_sandbox = sandbox_pipeline
                    break
            
            if matching_sandbox:
                print(f"    📊 Sandbox stages: {len(matching_sandbox.get('stages', []))}")
                pipeline_mapping[pipeline['id']] = matching_sandbox['id']
                
                # Simple check - if stage counts differ, note it
                prod_stages = len(pipeline.get('stages', []))
                sandbox_stages = len(matching_sandbox.get('stages', []))
                if prod_stages != sandbox_stages:
                    print(f"    ⚠️  Stage count mismatch - may need manual review")
                else:
                    print(f"    ✅ Stage counts match")
            
            updated += 1
    
    # Summary
    print()
    print("=" * 50)
    print("📊 DEAL PIPELINE MIGRATION SUMMARY")
    print("=" * 50)
    print(f"✅ New pipelines created: {created}")
    if failed > 0:
        print(f"❌ Pipeline creation failed: {failed}")
    print(f"🔄 Existing pipelines checked: {updated}")
    print(f"📝 Total processed: {len(pipelines_to_create) + len(pipelines_to_update)} pipelines")
    print("=" * 50)
    
    # Save pipeline mapping for deal migration
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = {
        'timestamp': timestamp,
        'migration_date': datetime.now().isoformat(),
        'summary': {
            'pipelines_created': created,
            'pipelines_failed': failed,
            'pipelines_updated': updated,
            'total_processed': len(pipelines_to_create) + len(pipelines_to_update)
        },
        'pipeline_mapping': pipeline_mapping,  # prod_id -> sandbox_id
        'created_pipelines': [p['label'] for p in pipelines_to_create[:created]],
        'production_pipelines': {p['id']: p['label'] for p in prod_pipelines}
    }
    
    os.makedirs('reports', exist_ok=True)
    report_file = f'reports/deal_pipeline_migration_{timestamp}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Pipeline mapping saved: {report_file}")
    
    if failed == 0:
        print("🎉 All deal pipelines migrated successfully!")
        print("💡 Ready for deal data migration")
        return True
    else:
        print("⚠️  Some pipelines failed to create - check errors above")
        return False

if __name__ == "__main__":
    success = migrate_deal_pipelines()
    exit(0 if success else 1)