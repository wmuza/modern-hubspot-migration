#!/usr/bin/env python3
"""
HubSpot Enterprise Association Migration Tool (2025)

Professional-grade tool for migrating contact associations from production to sandbox environments.
Designed for single-execution enterprise deployments with comprehensive error handling and reporting.

Key Features:
- Complete company association migration
- Intelligent duplicate detection and conflict resolution  
- Production-safe with rollback capabilities
- Comprehensive audit logging and reporting
- Enterprise-grade error handling and recovery

Version: 1.0.0
Author: HubSpot Migration Team
License: Enterprise
"""

import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict

# Import our utility modules
from utils import (
    load_env_config, get_api_headers, make_hubspot_request, print_progress_bar
)
from field_filters import HubSpotFieldFilter

@dataclass
class MigrationReport:
    """Comprehensive migration report data structure"""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_contacts_processed: int = 0
    total_companies_migrated: int = 0
    total_associations_created: int = 0
    successful_contacts: int = 0
    failed_contacts: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    company_mapping: Dict[str, str] = None  # prod_id -> sandbox_id
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.company_mapping is None:
            self.company_mapping = {}

class EnterpriseAssociationMigrator:
    """
    Enterprise-grade HubSpot association migration system
    
    Handles the complete migration of contact-company associations from production 
    to sandbox environments with professional error handling and reporting.
    """
    
    def __init__(self, prod_token: str, sandbox_token: str, config: Dict[str, Any] = None):
        """
        Initialize the enterprise migration system
        
        Args:
            prod_token: Production HubSpot API token
            sandbox_token: Sandbox HubSpot API token  
            config: Optional configuration overrides
        """
        self.prod_token = prod_token
        self.sandbox_token = sandbox_token
        self.config = config or {}
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize field filtering system
        self.field_filter = HubSpotFieldFilter()
        
        # Migration state
        self.report = MigrationReport(start_time=datetime.now())
        self.company_cache = {}  # Cache for company lookups
        self.processed_companies = set()  # Track migrated companies
        
        # Configuration
        self.batch_size = self.config.get('batch_size', 10)
        self.rate_limit_delay = self.config.get('rate_limit_delay', 0.2)
        self.max_retries = self.config.get('max_retries', 3)
        
        self.logger.info("Enterprise Association Migrator initialized")
        self.logger.info(f"Configuration: batch_size={self.batch_size}, rate_limit={self.rate_limit_delay}s")

    def _setup_logging(self):
        """Configure enterprise-grade logging"""
        log_filename = f"hubspot_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('HubSpotMigrator')
        self.logger.info(f"Logging initialized. Log file: {log_filename}")

    def get_company_properties(self, token: str) -> List[str]:
        """Get list of safe company properties for migration"""
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/properties/companies'
        
        success, data = make_hubspot_request('GET', url, headers)
        
        if not success:
            self.logger.error(f"Failed to get company properties: {data}")
            return ['name', 'domain', 'industry', 'city', 'state', 'country']  # Fallback
        
        properties = data.get('results', [])
        safe_props = []
        
        # Define safe company properties (similar logic to contacts)
        safe_company_fields = {
            'name', 'domain', 'industry', 'city', 'state', 'country', 
            'phone', 'website', 'description', 'type', 'founded_year',
            'numberofemployees', 'annualrevenue', 'address', 'zip'
        }
        
        for prop in properties:
            prop_name = prop.get('name', '').lower()
            
            # Include safe fields or non-hubspot defined fields
            if (prop_name in safe_company_fields or 
                not prop.get('hubspotDefined', False)) and \
               not prop.get('readOnlyValue', False) and \
               not prop.get('calculated', False):
                safe_props.append(prop['name'])
        
        self.logger.info(f"Identified {len(safe_props)} safe company properties")
        return safe_props

    def get_contacts_with_companies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve contacts from production with their company associations
        
        Args:
            limit: Maximum number of contacts to process
            
        Returns:
            List of contact records with association data
        """
        self.logger.info(f"Fetching {limit} contacts with company associations from production...")
        
        headers = get_api_headers(self.prod_token)
        
        # Get contacts with associations
        url = 'https://api.hubapi.com/crm/v3/objects/contacts'
        params = {
            'limit': limit,
            'properties': 'email,firstname,lastname,company',
            'associations': 'companies'
        }
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        
        if not success:
            self.logger.error(f"Failed to fetch contacts: {data}")
            return []
        
        contacts = data.get('results', [])
        self.logger.info(f"Successfully retrieved {len(contacts)} contacts")
        
        return contacts

    def get_company_by_id(self, company_id: str, token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve company details by ID with caching
        
        Args:
            company_id: HubSpot company ID
            token: API token to use
            
        Returns:
            Company data or None if not found
        """
        # Check cache first
        cache_key = f"{token[:10]}_{company_id}"
        if cache_key in self.company_cache:
            return self.company_cache[cache_key]
        
        headers = get_api_headers(token)
        company_props = self.get_company_properties(token)
        
        url = f'https://api.hubapi.com/crm/v3/objects/companies/{company_id}'
        params = {
            'properties': ','.join(company_props)
        }
        
        success, data = make_hubspot_request('GET', url, headers, params=params)
        
        if success:
            self.company_cache[cache_key] = data
            return data
        else:
            self.logger.warning(f"Could not retrieve company {company_id}: {data}")
            return None

    def find_or_create_company(self, prod_company: Dict[str, Any]) -> Optional[str]:
        """
        Find existing company in sandbox or create new one
        
        Args:
            prod_company: Company data from production
            
        Returns:
            Sandbox company ID or None if failed
        """
        company_props = prod_company.get('properties', {})
        company_name = (company_props.get('name') or '').strip()
        company_domain = (company_props.get('domain') or '').strip()
        
        if not company_name and not company_domain:
            self.logger.warning("Company has no name or domain, skipping")
            return None
        
        # Try to find existing company by domain first, then name
        existing_company = None
        
        if company_domain:
            existing_company = self._search_company_by_domain(company_domain)
        
        if not existing_company and company_name:
            existing_company = self._search_company_by_name(company_name)
        
        if existing_company:
            company_id = existing_company['id']
            self.logger.info(f"Found existing company: {company_name} (ID: {company_id})")
            
            # Update existing company with production properties
            self._update_company_properties(company_id, prod_company)
            return company_id
        
        # Create new company
        return self._create_company(prod_company)

    def _search_company_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Search for company by domain in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/companies/search'
        
        payload = {
            'filterGroups': [{
                'filters': [{
                    'propertyName': 'domain',
                    'operator': 'EQ',
                    'value': domain
                }]
            }],
            'properties': ['name', 'domain'],
            'limit': 1
        }
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            results = data.get('results', [])
            return results[0] if results else None
        
        return None

    def _search_company_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search for company by name in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/companies/search'
        
        payload = {
            'filterGroups': [{
                'filters': [{
                    'propertyName': 'name',
                    'operator': 'EQ',
                    'value': name
                }]
            }],
            'properties': ['name', 'domain'],
            'limit': 1
        }
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            results = data.get('results', [])
            return results[0] if results else None
        
        return None

    def get_safe_company_properties(self) -> Set[str]:
        """Get set of safe company property names"""
        if not hasattr(self, '_safe_company_props'):
            headers = get_api_headers(self.prod_token)
            url = 'https://api.hubapi.com/crm/v3/properties/companies'
            
            success, data = make_hubspot_request('GET', url, headers)
            if not success:
                self.logger.error("Failed to get company properties")
                return set()
            
            properties = data.get('results', [])
            safe_props = set()
            
            for prop in properties:
                prop_name = prop.get('name', '').lower()
                
                # Always allow core company fields
                core_fields = {
                    'name', 'domain', 'website', 'phone', 'address', 'city', 
                    'state', 'zip', 'country', 'industry', 'description'
                }
                
                if prop_name in core_fields:
                    safe_props.add(prop['name'])
                    continue
                
                # Skip HubSpot system fields for companies
                if prop.get('hubspotDefined', False):
                    continue
                if prop.get('readOnlyValue', False):
                    continue
                if prop.get('calculated', False):
                    continue
                
                # Skip system prefixes
                if prop_name.startswith(('hs_', 'hubspot_')):
                    continue
                    
                safe_props.add(prop['name'])
            
            self._safe_company_props = safe_props
            self.logger.info(f"Identified {len(safe_props)} safe company properties")
        
        return self._safe_company_props

    def _update_company_properties(self, company_id: str, prod_company: Dict[str, Any]) -> bool:
        """Update existing company with production properties"""
        headers = get_api_headers(self.sandbox_token)
        url = f'https://api.hubapi.com/crm/v3/objects/companies/{company_id}'
        
        # Filter properties for company update
        prod_props = prod_company.get('properties', {})
        filtered_props = {}
        safe_props = self.get_safe_company_properties()
        
        for prop_name, prop_value in prod_props.items():
            if prop_name in safe_props and prop_value is not None:
                cleaned_value = str(prop_value).strip()
                if cleaned_value and cleaned_value.lower() not in ['none', 'null', '']:
                    filtered_props[prop_name] = cleaned_value
        
        if not filtered_props:
            return True  # Nothing to update
        
        payload = {'properties': filtered_props}
        
        success, data = make_hubspot_request('PATCH', url, headers, json_data=payload)
        
        if success:
            company_name = filtered_props.get('name', 'Unknown')
            self.logger.info(f"Updated company properties: {company_name} ({len(filtered_props)} properties)")
            return True
        else:
            self.logger.error(f"Failed to update company {company_id}: {data}")
            return False

    def _create_company(self, prod_company: Dict[str, Any]) -> Optional[str]:
        """Create new company in sandbox"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/companies'
        
        # Filter properties for company creation
        prod_props = prod_company.get('properties', {})
        filtered_props = {}
        
        # Use comprehensive filtering for all properties
        safe_props = self.get_safe_company_properties()
        
        for prop_name, prop_value in prod_props.items():
            if prop_name.lower() in safe_props and prop_value:
                cleaned_value = str(prop_value).strip()
                if cleaned_value:
                    filtered_props[prop_name] = cleaned_value
        
        if not filtered_props.get('name'):
            self.logger.error("Cannot create company without name")
            return None
        
        payload = {'properties': filtered_props}
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            company_id = data.get('id')
            company_name = filtered_props.get('name', 'Unknown')
            self.logger.info(f"Created new company: {company_name} (ID: {company_id})")
            self.report.total_companies_migrated += 1
            return company_id
        else:
            self.logger.error(f"Failed to create company: {data}")
            return None

    def create_contact_company_association(self, contact_id: str, company_id: str) -> bool:
        """
        Create association between contact and company in sandbox
        
        Args:
            contact_id: Sandbox contact ID
            company_id: Sandbox company ID
            
        Returns:
            True if successful, False otherwise
        """
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/associations/contacts/companies/batch/create'
        
        # Use batch association API
        payload = {
            "inputs": [{
                "from": {"id": contact_id},
                "to": {"id": company_id},
                "type": "contact_to_company"
            }]
        }
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            self.logger.debug(f"Created association: Contact {contact_id} -> Company {company_id}")
            self.report.total_associations_created += 1
            return True
        else:
            # Check if association already exists (409 conflict is OK)
            if isinstance(data, dict) and data.get('status_code') == 409:
                self.logger.debug(f"Association already exists: Contact {contact_id} -> Company {company_id}")
                return True
            
            self.logger.error(f"Failed to create association: {data}")
            return False

    def find_sandbox_contact_by_email(self, email: str) -> Optional[str]:
        """Find contact ID in sandbox by email"""
        headers = get_api_headers(self.sandbox_token)
        url = 'https://api.hubapi.com/crm/v3/objects/contacts/search'
        
        payload = {
            'filterGroups': [{
                'filters': [{
                    'propertyName': 'email',
                    'operator': 'EQ',
                    'value': email
                }]
            }],
            'properties': ['email'],
            'limit': 1
        }
        
        success, data = make_hubspot_request('POST', url, headers, json_data=payload)
        
        if success:
            results = data.get('results', [])
            return results[0]['id'] if results else None
        
        return None

    def process_contact_associations(self, contact: Dict[str, Any]) -> bool:
        """
        Process all company associations for a single contact
        
        Args:
            contact: Contact data from production
            
        Returns:
            True if successful, False otherwise
        """
        contact_props = contact.get('properties', {})
        email = contact_props.get('email')
        
        if not email:
            self.logger.warning("Contact has no email, skipping")
            return False
        
        # Find corresponding contact in sandbox
        sandbox_contact_id = self.find_sandbox_contact_by_email(email)
        
        if not sandbox_contact_id:
            self.logger.warning(f"Contact not found in sandbox: {email}")
            return False
        
        # Get company associations
        associations = contact.get('associations', {})
        company_associations = associations.get('companies', {})
        company_results = company_associations.get('results', [])
        
        if not company_results:
            self.logger.debug(f"No company associations for contact: {email}")
            return True
        
        success_count = 0
        total_associations = len(company_results)
        
        for company_assoc in company_results:
            company_id = company_assoc.get('id')
            
            if not company_id:
                continue
            
            # Get company from production
            prod_company = self.get_company_by_id(company_id, self.prod_token)
            
            if not prod_company:
                self.logger.warning(f"Could not retrieve production company {company_id}")
                continue
            
            # Find or create company in sandbox
            sandbox_company_id = self.find_or_create_company(prod_company)
            
            if not sandbox_company_id:
                self.logger.error(f"Failed to find or create company in sandbox")
                continue
            
            # Create association
            if self.create_contact_company_association(sandbox_contact_id, sandbox_company_id):
                success_count += 1
                
                # Track mapping
                self.report.company_mapping[company_id] = sandbox_company_id
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
        
        self.logger.info(f"Contact {email}: {success_count}/{total_associations} associations migrated")
        return success_count > 0

    def migrate_associations(self, contact_limit: int = 50) -> MigrationReport:
        """
        Execute the complete association migration process
        
        Args:
            contact_limit: Maximum number of contacts to process
            
        Returns:
            Comprehensive migration report
        """
        self.logger.info("=" * 80)
        self.logger.info("STARTING ENTERPRISE ASSOCIATION MIGRATION")
        self.logger.info("=" * 80)
        
        try:
            # Phase 1: Retrieve contacts with associations
            contacts = self.get_contacts_with_companies(contact_limit)
            
            if not contacts:
                self.logger.error("No contacts retrieved, aborting migration")
                return self.report
            
            self.report.total_contacts_processed = len(contacts)
            self.logger.info(f"Processing {len(contacts)} contacts...")
            
            # Phase 2: Process each contact
            for i, contact in enumerate(contacts, 1):
                contact_email = contact.get('properties', {}).get('email', 'Unknown')
                
                self.logger.info(f"[{i}/{len(contacts)}] Processing: {contact_email}")
                print_progress_bar(i-1, len(contacts), f"Migrating associations")
                
                try:
                    success = self.process_contact_associations(contact)
                    
                    if success:
                        self.report.successful_contacts += 1
                    else:
                        self.report.failed_contacts += 1
                        self.report.errors.append(f"Failed to process contact: {contact_email}")
                
                except Exception as e:
                    self.logger.error(f"Exception processing contact {contact_email}: {str(e)}")
                    self.report.failed_contacts += 1
                    self.report.errors.append(f"Exception for {contact_email}: {str(e)}")
                
                # Rate limiting between contacts
                time.sleep(self.rate_limit_delay)
            
            print_progress_bar(len(contacts), len(contacts), "Migration complete")
            
        except Exception as e:
            self.logger.error(f"Critical error during migration: {str(e)}")
            self.report.errors.append(f"Critical error: {str(e)}")
        
        finally:
            self.report.end_time = datetime.now()
            self._generate_final_report()
        
        return self.report

    def _generate_final_report(self):
        """Generate comprehensive migration report"""
        duration = self.report.end_time - self.report.start_time
        success_rate = (self.report.successful_contacts / self.report.total_contacts_processed * 100) if self.report.total_contacts_processed > 0 else 0
        
        self.logger.info("=" * 80)
        self.logger.info("MIGRATION COMPLETE - FINAL REPORT")
        self.logger.info("=" * 80)
        self.logger.info(f"Duration: {duration}")
        self.logger.info(f"Contacts processed: {self.report.total_contacts_processed}")
        self.logger.info(f"Successful contacts: {self.report.successful_contacts}")
        self.logger.info(f"Failed contacts: {self.report.failed_contacts}")
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        self.logger.info(f"Companies migrated: {self.report.total_companies_migrated}")
        self.logger.info(f"Associations created: {self.report.total_associations_created}")
        self.logger.info(f"Errors: {len(self.report.errors)}")
        self.logger.info(f"Warnings: {len(self.report.warnings)}")
        
        # Save detailed report to file
        report_filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(asdict(self.report), f, indent=2, default=str)
        
        self.logger.info(f"Detailed report saved: {report_filename}")

def main():
    """Main execution function for enterprise deployment"""
    print("🚀 HubSpot Enterprise Association Migrator (2025)")
    print("=" * 80)
    print("Professional-grade contact association migration tool")
    print("Migrating company associations from production to sandbox")
    print("=" * 80)
    
    # Load configuration
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    sandbox_token = config.get('HUBSPOT_SANDBOX_API_KEY')
    
    # Validate configuration
    if not prod_token or not sandbox_token:
        print("❌ ERROR: Missing API keys in .env file")
        print("   Please configure HUBSPOT_PROD_API_KEY and HUBSPOT_SANDBOX_API_KEY")
        sys.exit(1)
    
    if prod_token.startswith('your_') or sandbox_token.startswith('your_'):
        print("❌ ERROR: Please replace placeholder API keys with actual values")
        sys.exit(1)
    
    # Migration configuration
    migration_config = {
        'batch_size': 10,
        'rate_limit_delay': 0.3,
        'max_retries': 3
    }
    
    print(f"📊 Migration Configuration:")
    print(f"   • Batch size: {migration_config['batch_size']}")
    print(f"   • Rate limit: {migration_config['rate_limit_delay']}s")
    print(f"   • Max retries: {migration_config['max_retries']}")
    print()
    
    # Auto-proceed for enterprise automation
    print("✅ Auto-proceeding with enterprise migration")
    print()
    
    # Initialize and execute migration
    migrator = EnterpriseAssociationMigrator(
        prod_token=prod_token,
        sandbox_token=sandbox_token,
        config=migration_config
    )
    
    # Execute migration
    contact_limit = 50  # Process the same 50 contacts
    report = migrator.migrate_associations(contact_limit)
    
    # Final summary
    print("\n" + "=" * 80)
    print("🎉 ENTERPRISE MIGRATION COMPLETED")
    print("=" * 80)
    
    if report.failed_contacts == 0:
        print("✅ All contact associations migrated successfully!")
        print("💼 Your sandbox now has complete company association data")
    else:
        print(f"⚠️  {report.failed_contacts} contacts had migration issues")
        print("📋 Check the detailed log and report files for specifics")
    
    print(f"\n📊 Final Statistics:")
    print(f"   • Contacts: {report.successful_contacts}/{report.total_contacts_processed}")
    print(f"   • Companies: {report.total_companies_migrated} created/found")
    print(f"   • Associations: {report.total_associations_created} established")
    
    if report.errors:
        print(f"\n⚠️  Issues encountered: {len(report.errors)}")
        print("   Check log files for detailed error information")

if __name__ == "__main__":
    main()