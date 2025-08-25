#!/usr/bin/env python
"""
HubSpot Modern Migration Tool - Main Execution Script
Professional, enterprise-grade migration tool for HubSpot portals

Usage:
    python migrate.py [OPTIONS]

Options:
    --config CONFIG_FILE    Use custom configuration file
    --limit NUMBER          Migrate specific number of contacts
    --verbose              Enable verbose logging
    --dry-run              Show what would be migrated without making changes
    --help                 Show this help message

Examples:
    python migrate.py                           # Full migration with default settings
    python migrate.py --limit 100              # Migrate 100 contacts
    python migrate.py --config custom.ini      # Use custom config
    python migrate.py --verbose                # Detailed logging
    python migrate.py --dry-run                # Preview mode
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.config import load_config
from core.field_filters import HubSpotFieldFilter
from utils.utils import setup_logging, print_banner, print_summary
from migrations.contact_migration import migrate_contacts
from migrations.company_property_migrator import migrate_company_properties
from migrations.enterprise_association_migrator import EnterpriseAssociationMigrator
from validators.verify_company_properties import verify_company_data

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='HubSpot Modern Migration Tool - Enterprise-grade portal migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--config', type=str, 
                       help='Path to configuration file (default: config/config.ini)')
    parser.add_argument('--limit', type=int, 
                       help='Number of contacts to migrate (overrides config)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without making changes')
    parser.add_argument('--skip-properties', action='store_true',
                       help='Skip property migration step')
    parser.add_argument('--contacts-only', action='store_true',
                       help='Migrate only contacts (skip associations)')
    
    return parser.parse_args()

def setup_environment(config, args):
    """Setup logging and create necessary directories"""
    # Ensure directories exist
    config.ensure_directories()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else config.get_logging_config()['log_level']
    log_config = config.get_logging_config()
    
    setup_logging(
        level=log_level,
        log_to_file=log_config['log_to_file'],
        log_directory=log_config['log_directory']
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("HUBSPOT MODERN MIGRATION TOOL - SESSION STARTED")
    logger.info("=" * 80)
    logger.info(f"Configuration file: {config.config_file}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Dry run mode: {args.dry_run}")
    
    return logger

def run_migration(config, args, logger):
    """Execute the complete migration process"""
    hubspot_config = config.get_hubspot_config()
    migration_config = config.get_migration_config()
    
    # Override contact limit if specified
    if args.limit:
        migration_config['contact_limit'] = args.limit
        logger.info(f"Contact limit overridden to: {args.limit}")
    
    print_banner()
    
    print("🔧 MIGRATION CONFIGURATION")
    print("=" * 60)
    print(f"📊 Contact limit: {migration_config['contact_limit']}")
    print(f"📦 Batch size: {migration_config['batch_size']}")
    print(f"⏱️  Rate limit: {migration_config['rate_limit_delay']}s")
    print(f"🔄 Max retries: {migration_config['max_retries']}")
    print(f"🌙 Dry run mode: {'Yes' if args.dry_run else 'No'}")
    print()
    
    # Validation
    if not config.is_secure():
        print("❌ SECURITY ERROR: Please configure your API tokens properly")
        print("📝 Edit config/config.ini with your actual HubSpot Private App tokens")
        return False
    
    if args.dry_run:
        print("🌙 DRY RUN MODE: No actual changes will be made")
        print()
    
    migration_results = {}
    
    try:
        # Step 1: Company Property Migration
        if not args.skip_properties:
            print("🏢 STEP 1: COMPANY PROPERTY MIGRATION")
            print("=" * 60)
            if args.dry_run:
                print("🌙 Dry run: Would analyze and create missing company properties")
            else:
                property_results = migrate_company_properties(
                    hubspot_config['production_token'],
                    hubspot_config['sandbox_token']
                )
                migration_results['properties'] = property_results
            print()
        
        # Step 2: Contact Migration
        print("👥 STEP 2: CONTACT MIGRATION")
        print("=" * 60)
        if args.dry_run:
            print(f"🌙 Dry run: Would migrate {migration_config['contact_limit']} contacts with properties")
        else:
            contact_results = migrate_contacts(
                hubspot_config['production_token'],
                hubspot_config['sandbox_token'],
                migration_config['contact_limit']
            )
            migration_results['contacts'] = contact_results
        print()
        
        # Step 3: Association Migration
        if not args.contacts_only:
            print("🔗 STEP 3: ASSOCIATION MIGRATION")
            print("=" * 60)
            if args.dry_run:
                print("🌙 Dry run: Would migrate contact-company associations")
            else:
                migrator = EnterpriseAssociationMigrator(
                    prod_token=hubspot_config['production_token'],
                    sandbox_token=hubspot_config['sandbox_token'],
                    config=migration_config
                )
                
                association_results = migrator.migrate_associations(
                    migration_config['contact_limit']
                )
                migration_results['associations'] = association_results
            print()
        
        # Step 4: Verification
        if not args.dry_run:
            print("✅ STEP 4: DATA VERIFICATION")
            print("=" * 60)
            verify_company_data()
            print()
        
        # Final Summary
        print_summary(migration_results, args.dry_run)
        
        return True
        
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user")
        print("\n⚠️  Migration interrupted by user")
        return False
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        print(f"\n❌ Migration failed: {str(e)}")
        print("📋 Check the logs for detailed error information")
        return False

def main():
    """Main execution function"""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Load configuration
        config = load_config(args.config)
        
        # Setup environment
        logger = setup_environment(config, args)
        
        # Run migration
        success = run_migration(config, args, logger)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        print("📋 Please check your configuration and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()