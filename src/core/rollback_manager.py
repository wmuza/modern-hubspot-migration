#!/usr/bin/env python
"""
Rollback Manager
Enables undoing migration changes with granular control options
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.utils import load_env_config, get_api_headers, make_hubspot_request
import json
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class RollbackManager:
    def __init__(self, sandbox_token: str):
        self.sandbox_token = sandbox_token
        self.rollback_actions = []
        self.errors = []
        
    def get_migration_reports(self, days_back: int = 30) -> List[Dict]:
        """Get all migration reports from the specified time period"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        report_files = []
        patterns = [
            'reports/migration_report_*.json',
            'reports/deal_migration_*.json', 
            'reports/deal_pipeline_migration_*.json',
            'reports/deal_property_migration_*.json',
            'reports/deal_association_migration_*.json',
            'reports/enterprise_association_migration_*.json',
            'reports/selective_sync_*.json'
        ]
        
        for pattern in patterns:
            for file_path in glob.glob(pattern):
                try:
                    with open(file_path, 'r') as f:
                        report = json.load(f)
                    
                    report_date = datetime.fromisoformat(report.get('migration_date', '1970-01-01'))
                    
                    if report_date >= cutoff_date:
                        report['file_path'] = file_path
                        report['report_type'] = self._identify_report_type(file_path)
                        report_files.append(report)
                        
                except Exception as e:
                    print(f"⚠️  Error reading {file_path}: {str(e)}")
        
        # Sort by date, newest first
        report_files.sort(key=lambda x: x.get('migration_date', ''), reverse=True)
        return report_files
    
    def _identify_report_type(self, file_path: str) -> str:
        """Identify the type of migration report"""
        if 'contact' in file_path or 'migration_report_' in file_path:
            return 'contacts'
        elif 'deal_migration_' in file_path:
            return 'deals'
        elif 'deal_pipeline_' in file_path:
            return 'pipelines'
        elif 'deal_property_' in file_path:
            return 'deal_properties'
        elif 'deal_association_' in file_path:
            return 'deal_associations'
        elif 'enterprise_association_' in file_path:
            return 'contact_associations'
        elif 'selective_sync_' in file_path:
            return 'selective_sync'
        else:
            return 'unknown'
    
    def delete_objects(self, object_type: str, object_ids: List[str]) -> Dict[str, Any]:
        """Delete objects from sandbox"""
        deleted = 0
        failed = 0
        
        print(f"🗑️  Deleting {len(object_ids)} {object_type}...")
        
        for obj_id in object_ids:
            headers = get_api_headers(self.sandbox_token)
            url = f'https://api.hubapi.com/crm/v3/objects/{object_type}/{obj_id}'
            
            success, result = make_hubspot_request('DELETE', url, headers)
            
            if success:
                deleted += 1
                self.rollback_actions.append({
                    'action': 'delete',
                    'object_type': object_type,
                    'object_id': obj_id,
                    'status': 'success'
                })
            else:
                failed += 1
                error_msg = str(result)[:100] if result else "Unknown error"
                self.errors.append(f"{object_type} {obj_id}: {error_msg}")
                
                self.rollback_actions.append({
                    'action': 'delete',
                    'object_type': object_type,
                    'object_id': obj_id,
                    'status': 'failed',
                    'error': error_msg
                })
            
            # Rate limiting
            time.sleep(0.2)
            
            if (deleted + failed) % 10 == 0:
                print(f"  📊 Progress: {deleted + failed}/{len(object_ids)} processed")
        
        return {
            'deleted': deleted,
            'failed': failed,
            'total': len(object_ids)
        }
    
    def delete_properties(self, object_type: str, property_names: List[str]) -> Dict[str, Any]:
        """Delete custom properties from sandbox"""
        deleted = 0
        failed = 0
        
        print(f"🔧 Deleting {len(property_names)} {object_type} properties...")
        
        for prop_name in property_names:
            headers = get_api_headers(self.sandbox_token)
            url = f'https://api.hubapi.com/crm/v3/properties/{object_type}/{prop_name}'
            
            success, result = make_hubspot_request('DELETE', url, headers)
            
            if success:
                deleted += 1
                self.rollback_actions.append({
                    'action': 'delete_property',
                    'object_type': object_type,
                    'property_name': prop_name,
                    'status': 'success'
                })
            else:
                failed += 1
                error_msg = str(result)[:100] if result else "Unknown error"
                
                # Property might not exist or be system-defined
                if "does not exist" in str(result) or "hubspotDefined" in str(result):
                    print(f"  ⚠️  Property {prop_name} cannot be deleted (system-defined or doesn't exist)")
                else:
                    self.errors.append(f"Property {prop_name}: {error_msg}")
                
                self.rollback_actions.append({
                    'action': 'delete_property',
                    'object_type': object_type,
                    'property_name': prop_name,
                    'status': 'failed',
                    'error': error_msg
                })
            
            # Rate limiting
            time.sleep(0.1)
        
        return {
            'deleted': deleted,
            'failed': failed,
            'total': len(property_names)
        }
    
    def delete_pipelines(self, pipeline_ids: List[str]) -> Dict[str, Any]:
        """Delete deal pipelines from sandbox"""
        deleted = 0
        failed = 0
        
        print(f"📊 Deleting {len(pipeline_ids)} pipelines...")
        
        for pipeline_id in pipeline_ids:
            headers = get_api_headers(self.sandbox_token)
            url = f'https://api.hubapi.com/crm/v3/pipelines/deals/{pipeline_id}'
            
            success, result = make_hubspot_request('DELETE', url, headers)
            
            if success:
                deleted += 1
                self.rollback_actions.append({
                    'action': 'delete_pipeline',
                    'pipeline_id': pipeline_id,
                    'status': 'success'
                })
            else:
                failed += 1
                error_msg = str(result)[:100] if result else "Unknown error"
                
                # Default pipeline cannot be deleted
                if "default" in str(result).lower() or "cannot be deleted" in str(result):
                    print(f"  ⚠️  Pipeline {pipeline_id} cannot be deleted (system default)")
                else:
                    self.errors.append(f"Pipeline {pipeline_id}: {error_msg}")
                
                self.rollback_actions.append({
                    'action': 'delete_pipeline',
                    'pipeline_id': pipeline_id,
                    'status': 'failed',
                    'error': error_msg
                })
            
            # Rate limiting
            time.sleep(0.2)
        
        return {
            'deleted': deleted,
            'failed': failed,
            'total': len(pipeline_ids)
        }
    
    def rollback_last_migration(self) -> Dict[str, Any]:
        """Rollback the most recent migration"""
        reports = self.get_migration_reports(days_back=7)
        
        if not reports:
            return {'error': 'No migration reports found in the last 7 days'}
        
        latest_report = reports[0]
        return self.rollback_specific_migration(latest_report)
    
    def rollback_last_n_migrations(self, n: int) -> Dict[str, Any]:
        """Rollback the last N migrations"""
        reports = self.get_migration_reports(days_back=30)
        
        if len(reports) < n:
            return {'error': f'Only {len(reports)} migration reports found, cannot rollback {n} migrations'}
        
        rollback_results = []
        
        for report in reports[:n]:
            result = self.rollback_specific_migration(report)
            rollback_results.append(result)
        
        return {
            'rollback_results': rollback_results,
            'total_migrations_rolled_back': n
        }
    
    def rollback_specific_migration(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback a specific migration based on its report"""
        print(f"🔄 Rolling back {report.get('report_type', 'unknown')} migration from {report.get('migration_date', 'unknown date')}")
        
        rollback_summary = {
            'report_type': report.get('report_type'),
            'migration_date': report.get('migration_date'),
            'actions_taken': {}
        }
        
        # Rollback based on report type
        report_type = report.get('report_type', '')
        
        if report_type == 'contacts':
            rollback_summary['actions_taken'] = self._rollback_contacts(report)
            
        elif report_type == 'deals':
            rollback_summary['actions_taken'] = self._rollback_deals(report)
            
        elif report_type == 'pipelines':
            rollback_summary['actions_taken'] = self._rollback_pipelines(report)
            
        elif report_type == 'deal_properties':
            rollback_summary['actions_taken'] = self._rollback_deal_properties(report)
            
        elif report_type == 'deal_associations':
            rollback_summary['actions_taken'] = self._rollback_deal_associations(report)
            
        elif report_type == 'contact_associations':
            rollback_summary['actions_taken'] = self._rollback_contact_associations(report)
            
        elif report_type == 'selective_sync':
            rollback_summary['actions_taken'] = self._rollback_selective_sync(report)
        
        return rollback_summary
    
    def _rollback_contacts(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback contact migration"""
        actions = {}
        
        # Delete created contacts
        created_contacts = report.get('created_contacts', [])
        if created_contacts:
            contact_ids = [contact.get('sandbox_id') for contact in created_contacts if contact.get('sandbox_id')]
            if contact_ids:
                actions['contacts_deleted'] = self.delete_objects('contacts', contact_ids)
        
        return actions
    
    def _rollback_deals(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback deal migration"""
        actions = {}
        
        # Delete created deals
        created_deals = report.get('created_deals', [])
        if created_deals:
            deal_ids = [deal.get('sandbox_id') for deal in created_deals if deal.get('sandbox_id')]
            if deal_ids:
                actions['deals_deleted'] = self.delete_objects('deals', deal_ids)
        
        return actions
    
    def _rollback_pipelines(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback pipeline migration"""
        actions = {}
        
        # Delete created pipelines
        pipeline_mapping = report.get('pipeline_mapping', {})
        if pipeline_mapping:
            # Get sandbox pipeline IDs (values in the mapping)
            sandbox_pipeline_ids = list(pipeline_mapping.values())
            if sandbox_pipeline_ids:
                actions['pipelines_deleted'] = self.delete_pipelines(sandbox_pipeline_ids)
        
        return actions
    
    def _rollback_deal_properties(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback deal property migration"""
        actions = {}
        
        # Delete created properties
        created_properties = report.get('created_properties', [])
        if created_properties:
            actions['deal_properties_deleted'] = self.delete_properties('deals', created_properties)
        
        return actions
    
    def _rollback_deal_associations(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback deal association migration"""
        # Note: HubSpot doesn't have a direct way to delete associations
        # This would require more complex logic to identify and remove specific associations
        return {'note': 'Association rollback requires manual intervention - associations cannot be bulk deleted'}
    
    def _rollback_contact_associations(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback contact association migration"""
        actions = {}
        
        # Delete created companies if they were created during association migration
        created_companies = report.get('created_companies', [])
        if created_companies:
            company_ids = [company.get('sandbox_id') for company in created_companies if company.get('sandbox_id')]
            if company_ids:
                actions['companies_deleted'] = self.delete_objects('companies', company_ids)
        
        return actions
    
    def _rollback_selective_sync(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback selective sync operation"""
        # This would be similar to other rollbacks but based on the selective sync metadata
        return {'note': 'Selective sync rollback not yet implemented'}
    
    def records_only_reset(self, days_back: int = 30) -> Dict[str, Any]:
        """Delete all migrated records but keep property/pipeline changes"""
        print("🧹 RECORDS-ONLY RESET")
        print("=" * 50)
        print("⚠️  This will delete all migrated records but keep properties and pipelines")
        
        reports = self.get_migration_reports(days_back)
        
        reset_summary = {
            'contacts_deleted': 0,
            'deals_deleted': 0,
            'companies_deleted': 0
        }
        
        for report in reports:
            report_type = report.get('report_type', '')
            
            if report_type == 'contacts':
                created_contacts = report.get('created_contacts', [])
                if created_contacts:
                    contact_ids = [c.get('sandbox_id') for c in created_contacts if c.get('sandbox_id')]
                    if contact_ids:
                        result = self.delete_objects('contacts', contact_ids)
                        reset_summary['contacts_deleted'] += result['deleted']
            
            elif report_type == 'deals':
                created_deals = report.get('created_deals', [])
                if created_deals:
                    deal_ids = [d.get('sandbox_id') for d in created_deals if d.get('sandbox_id')]
                    if deal_ids:
                        result = self.delete_objects('deals', deal_ids)
                        reset_summary['deals_deleted'] += result['deleted']
            
            elif report_type == 'contact_associations':
                created_companies = report.get('created_companies', [])
                if created_companies:
                    company_ids = [c.get('sandbox_id') for c in created_companies if c.get('sandbox_id')]
                    if company_ids:
                        result = self.delete_objects('companies', company_ids)
                        reset_summary['companies_deleted'] += result['deleted']
        
        return reset_summary
    
    def properties_only_reset(self, days_back: int = 30) -> Dict[str, Any]:
        """Delete all custom properties but keep records and pipelines"""
        print("🔧 PROPERTIES-ONLY RESET")
        print("=" * 50)
        print("⚠️  This will delete all custom properties created during migration")
        
        reports = self.get_migration_reports(days_back)
        
        reset_summary = {
            'deal_properties_deleted': 0,
            'company_properties_deleted': 0
        }
        
        for report in reports:
            report_type = report.get('report_type', '')
            
            if report_type == 'deal_properties':
                created_properties = report.get('created_properties', [])
                if created_properties:
                    result = self.delete_properties('deals', created_properties)
                    reset_summary['deal_properties_deleted'] += result['deleted']
        
        return reset_summary
    
    def full_reset(self, days_back: int = 30) -> Dict[str, Any]:
        """Complete reset - remove all migration changes"""
        print("💥 FULL RESET")
        print("=" * 50)
        print("⚠️  This will remove ALL changes made by the migration tool")
        
        # First delete records
        records_result = self.records_only_reset(days_back)
        
        # Then delete properties
        properties_result = self.properties_only_reset(days_back)
        
        # Then delete pipelines
        reports = self.get_migration_reports(days_back)
        pipelines_deleted = 0
        
        for report in reports:
            if report.get('report_type') == 'pipelines':
                pipeline_mapping = report.get('pipeline_mapping', {})
                if pipeline_mapping:
                    sandbox_pipeline_ids = list(pipeline_mapping.values())
                    result = self.delete_pipelines(sandbox_pipeline_ids)
                    pipelines_deleted += result['deleted']
        
        return {
            **records_result,
            **properties_result,
            'pipelines_deleted': pipelines_deleted
        }
    
    def save_rollback_report(self, rollback_results: Dict[str, Any]) -> str:
        """Save rollback operation report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'timestamp': timestamp,
            'rollback_date': datetime.now().isoformat(),
            'rollback_results': rollback_results,
            'rollback_actions': self.rollback_actions,
            'errors': self.errors
        }
        
        os.makedirs('reports', exist_ok=True)
        report_file = f'reports/rollback_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file

def main():
    """Demo rollback functionality"""
    config = load_env_config()
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    if not sandbox_token:
        print("❌ Error: Sandbox API token not found in .env file")
        return
    
    manager = RollbackManager(sandbox_token)
    
    # Show available migrations
    reports = manager.get_migration_reports()
    
    print("📋 Available Migration Reports:")
    print("=" * 50)
    
    for i, report in enumerate(reports, 1):
        print(f"{i}. {report['report_type']} - {report.get('migration_date', 'unknown')[:10]}")
        if report.get('summary'):
            summary = report['summary']
            for key, value in summary.items():
                if isinstance(value, int) and value > 0:
                    print(f"   {key}: {value}")
    
    if not reports:
        print("No migration reports found.")

if __name__ == "__main__":
    main()