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
from migrations.deal_property_migrator import migrate_deal_properties
from migrations.deal_pipeline_migrator import migrate_deal_pipelines
from migrations.deal_migrator import migrate_deals
from migrations.deal_association_migrator import migrate_deal_associations
from migrations.ticket_property_migrator import migrate_ticket_properties
from migrations.ticket_pipeline_migrator import migrate_ticket_pipelines
from migrations.ticket_migrator import migrate_tickets
from migrations.custom_object_migrator import migrate_custom_objects
from core.selective_sync import SelectiveSyncManager
from core.rollback_manager import RollbackManager
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
    parser.add_argument('--deals-only', action='store_true',
                       help='Migrate only deals (skip contacts and companies)')
    parser.add_argument('--skip-deals', action='store_true',
                       help='Skip deal migration steps')
    parser.add_argument('--tickets-only', action='store_true',
                       help='Migrate only tickets (skip contacts, companies, and deals)')
    parser.add_argument('--skip-tickets', action='store_true',
                       help='Skip ticket migration steps')
    parser.add_argument('--custom-objects-only', action='store_true',
                       help='Migrate only custom objects (skip all standard objects)')
    parser.add_argument('--skip-custom-objects', action='store_true',
                       help='Skip custom object migration steps')
    
    # Selective Sync Options
    parser.add_argument('--selective-contacts', action='store_true',
                       help='Sync specific contacts and their related objects')
    parser.add_argument('--selective-deals', action='store_true',
                       help='Sync specific deals and their related objects')
    parser.add_argument('--selective-tickets', action='store_true',
                       help='Sync specific tickets and their related objects')
    parser.add_argument('--selective-custom-objects', action='store_true',
                       help='Sync specific custom objects and their related objects')
    
    # ID-based selective sync for all object types
    parser.add_argument('--contact-ids', type=str,
                       help='Comma-separated list of contact IDs for selective sync')
    parser.add_argument('--deal-ids', type=str,
                       help='Comma-separated list of deal IDs for selective sync')
    parser.add_argument('--ticket-ids', type=str,
                       help='Comma-separated list of ticket IDs for selective sync')
    parser.add_argument('--custom-object-ids', type=str,
                       help='Comma-separated list of custom object IDs for selective sync')
    parser.add_argument('--custom-object-type', type=str,
                       help='Custom object type name for selective sync (e.g. "projects", "assets")')
    
    # Date-based filtering (works with all object types)
    parser.add_argument('--days-since-created', type=int,
                       help='Sync objects created within last N days (works with all object types)')
    parser.add_argument('--days-since-modified', type=int,
                       help='Sync objects modified within last N days (works with all object types)')
    
    # Contact-specific filtering options
    parser.add_argument('--email-domains', type=str,
                       help='Comma-separated list of email domains for contact filtering')
    parser.add_argument('--lifecycle-stages', type=str,
                       help='Comma-separated list of lifecycle stages for contact filtering')
    
    # Company-specific filtering options
    parser.add_argument('--company-domains', type=str,
                       help='Comma-separated list of company domains for filtering')
    parser.add_argument('--industries', type=str,
                       help='Comma-separated list of industries for company filtering')
    
    # Deal-specific filtering options
    parser.add_argument('--deal-stages', type=str,
                       help='Comma-separated list of deal stages for filtering')
    parser.add_argument('--deal-pipelines', type=str,
                       help='Comma-separated list of deal pipeline IDs for filtering')
    parser.add_argument('--min-deal-amount', type=float,
                       help='Minimum deal amount for filtering')
    parser.add_argument('--max-deal-amount', type=float,
                       help='Maximum deal amount for filtering')
    
    # Ticket-specific filtering options  
    parser.add_argument('--ticket-priorities', type=str,
                       help='Comma-separated list of ticket priorities for filtering')
    parser.add_argument('--ticket-statuses', type=str,
                       help='Comma-separated list of ticket statuses for filtering')
    parser.add_argument('--ticket-categories', type=str,
                       help='Comma-separated list of ticket categories for filtering')
    
    # General property-based filtering
    parser.add_argument('--property-filters', type=str,
                       help='JSON string of property filters e.g. \'{"property":"value","property2":"value2"}\'')
    
    # Owner-based filtering (works across all object types)
    parser.add_argument('--owner-ids', type=str,
                       help='Comma-separated list of owner IDs for filtering (works with all object types)')
    
    # Rollback Options
    parser.add_argument('--rollback-last', action='store_true',
                       help='Rollback the last migration')
    parser.add_argument('--rollback-last-n', type=int,
                       help='Rollback the last N migrations')
    parser.add_argument('--reset-records-only', action='store_true',
                       help='Delete all migrated records but keep properties/pipelines')
    parser.add_argument('--reset-properties-only', action='store_true',
                       help='Delete all custom properties but keep records')
    parser.add_argument('--full-reset', action='store_true',
                       help='Complete reset - remove all migration changes')
    parser.add_argument('--show-rollback-options', action='store_true',
                       help='Show available rollback options')
    
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

def handle_rollback_operations(config, args, logger):
    """Handle rollback and reset operations"""
    hubspot_config = config.get_hubspot_config()
    rollback_manager = RollbackManager(hubspot_config['sandbox_token'])
    
    if args.show_rollback_options:
        print("📋 AVAILABLE ROLLBACK OPTIONS")
        print("=" * 60)
        reports = rollback_manager.get_migration_reports()
        
        if not reports:
            print("No migration reports found.")
            return True
        
        for i, report in enumerate(reports, 1):
            print(f"{i}. {report['report_type']} - {report.get('migration_date', 'unknown')[:19]}")
            if report.get('summary'):
                summary = report['summary']
                for key, value in summary.items():
                    if isinstance(value, int) and value > 0:
                        print(f"   {key}: {value}")
        return True
    
    if args.rollback_last:
        print("🔄 ROLLING BACK LAST MIGRATION")
        print("=" * 60)
        result = rollback_manager.rollback_last_migration()
        report_file = rollback_manager.save_rollback_report(result)
        print(f"📄 Rollback report saved: {report_file}")
        return True
    
    if args.rollback_last_n:
        print(f"🔄 ROLLING BACK LAST {args.rollback_last_n} MIGRATIONS")
        print("=" * 60)
        result = rollback_manager.rollback_last_n_migrations(args.rollback_last_n)
        report_file = rollback_manager.save_rollback_report(result)
        print(f"📄 Rollback report saved: {report_file}")
        return True
    
    if args.reset_records_only:
        print("🧹 RECORDS-ONLY RESET")
        print("=" * 60)
        print("⚠️  This will delete all migrated records but keep properties and pipelines")
        result = rollback_manager.records_only_reset()
        report_file = rollback_manager.save_rollback_report(result)
        print(f"📄 Reset report saved: {report_file}")
        return True
    
    if args.reset_properties_only:
        print("🔧 PROPERTIES-ONLY RESET")
        print("=" * 60)
        print("⚠️  This will delete all custom properties created during migration")
        result = rollback_manager.properties_only_reset()
        report_file = rollback_manager.save_rollback_report(result)
        print(f"📄 Reset report saved: {report_file}")
        return True
    
    if args.full_reset:
        print("💥 FULL RESET")
        print("=" * 60)
        print("⚠️  This will remove ALL changes made by the migration tool")
        
        confirm = input("Type 'CONFIRM' to proceed with full reset: ")
        if confirm != 'CONFIRM':
            print("❌ Full reset cancelled")
            return True
        
        result = rollback_manager.full_reset()
        report_file = rollback_manager.save_rollback_report(result)
        print(f"📄 Reset report saved: {report_file}")
        return True
    
    return False

def handle_selective_sync(config, args, logger):
    """Handle selective sync operations for all object types"""
    hubspot_config = config.get_hubspot_config()
    migration_config = config.get_migration_config()
    sync_manager = SelectiveSyncManager(
        hubspot_config['production_token'],
        hubspot_config['sandbox_token']
    )
    
    # Build comprehensive criteria based on arguments
    criteria = {}
    
    # ID-based filtering for all object types
    if args.contact_ids:
        criteria['contact_ids'] = [id.strip() for id in args.contact_ids.split(',')]
    if args.deal_ids:
        criteria['deal_ids'] = [id.strip() for id in args.deal_ids.split(',')]
    if args.ticket_ids:
        criteria['ticket_ids'] = [id.strip() for id in args.ticket_ids.split(',')]
    if args.custom_object_ids:
        criteria['custom_object_ids'] = [id.strip() for id in args.custom_object_ids.split(',')]
    if args.custom_object_type:
        criteria['custom_object_type'] = args.custom_object_type.strip()
    
    # Date-based filtering (works with all object types)
    if args.days_since_created:
        criteria['days_since_created'] = args.days_since_created
    if args.days_since_modified:
        criteria['days_since_modified'] = args.days_since_modified
    
    # Contact-specific filtering
    if args.email_domains:
        criteria['email_domains'] = [domain.strip() for domain in args.email_domains.split(',')]
    if args.lifecycle_stages:
        criteria['lifecycle_stages'] = [stage.strip() for stage in args.lifecycle_stages.split(',')]
    
    # Company-specific filtering  
    if args.company_domains:
        criteria['company_domains'] = [domain.strip() for domain in args.company_domains.split(',')]
    if args.industries:
        criteria['industries'] = [industry.strip() for industry in args.industries.split(',')]
    
    # Deal-specific filtering
    if args.deal_stages:
        criteria['deal_stages'] = [stage.strip() for stage in args.deal_stages.split(',')]
    if args.deal_pipelines:
        criteria['deal_pipelines'] = [pipeline.strip() for pipeline in args.deal_pipelines.split(',')]
    if args.min_deal_amount:
        criteria['min_deal_amount'] = args.min_deal_amount
    if args.max_deal_amount:
        criteria['max_deal_amount'] = args.max_deal_amount
    
    # Ticket-specific filtering
    if args.ticket_priorities:
        criteria['ticket_priorities'] = [priority.strip() for priority in args.ticket_priorities.split(',')]
    if args.ticket_statuses:
        criteria['ticket_statuses'] = [status.strip() for status in args.ticket_statuses.split(',')]
    if args.ticket_categories:
        criteria['ticket_categories'] = [category.strip() for category in args.ticket_categories.split(',')]
    
    # General filtering options
    if args.owner_ids:
        criteria['owner_ids'] = [id.strip() for id in args.owner_ids.split(',')]
    if args.property_filters:
        import json
        try:
            criteria['property_filters'] = json.loads(args.property_filters)
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON format for --property-filters")
            return False
    
    # Set a reasonable limit if not specified and no specific criteria provided
    has_specific_criteria = any([
        args.contact_ids, args.deal_ids, args.ticket_ids, args.custom_object_ids,
        args.email_domains, args.company_domains, args.deal_stages, args.ticket_priorities
    ])
    if not has_specific_criteria:
        criteria['limit'] = args.limit if args.limit else migration_config['contact_limit']
    
    # Handle different selective sync types
    if args.selective_contacts:
        print("🎯 SELECTIVE SYNC: CONTACTS → ALL RELATED OBJECTS")
        print("=" * 60)
        results = sync_manager.selective_sync_contacts_with_related(criteria)
        report_file = sync_manager.save_selective_sync_report(results)
        print(f"📄 Selective sync report saved: {report_file}")
        return True
    
    if args.selective_deals:
        print("🎯 SELECTIVE SYNC: DEALS → ALL RELATED OBJECTS")
        print("=" * 60)
        results = sync_manager.selective_sync_deals_with_related(criteria)
        report_file = sync_manager.save_selective_sync_report(results)
        print(f"📄 Selective sync report saved: {report_file}")
        return True
    
    if args.selective_tickets:
        print("🎯 SELECTIVE SYNC: TICKETS → ALL RELATED OBJECTS")
        print("=" * 60)
        results = sync_manager.selective_sync_tickets_with_related(criteria)
        report_file = sync_manager.save_selective_sync_report(results)
        print(f"📄 Selective sync report saved: {report_file}")
        return True
    
    if args.selective_custom_objects:
        object_type = criteria.get('custom_object_type', 'custom_objects')
        print(f"🎯 SELECTIVE SYNC: {object_type.upper()} → ALL RELATED OBJECTS")
        print("=" * 60)
        results = sync_manager.selective_sync_custom_objects_with_related(criteria)
        report_file = sync_manager.save_selective_sync_report(results)
        print(f"📄 Selective sync report saved: {report_file}")
        return True
    
    return False

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
        if not args.skip_properties and not args.tickets_only and not args.custom_objects_only:
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
        if not args.deals_only and not args.tickets_only and not args.custom_objects_only:
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
        if not args.contacts_only and not args.deals_only and not args.tickets_only and not args.custom_objects_only:
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
        
        # Step 4: Deal Migration
        if not args.skip_deals and not args.contacts_only and not args.tickets_only and not args.custom_objects_only:
            print("💼 STEP 4: DEAL MIGRATION")
            print("=" * 60)
            if args.dry_run:
                print("🌙 Dry run: Would migrate deal properties, pipelines, and deals")
            else:
                # Step 4a: Deal Properties
                print("🔧 4a. Deal Properties Migration")
                deal_prop_results = migrate_deal_properties()
                migration_results['deal_properties'] = deal_prop_results
                print()
                
                # Step 4b: Deal Pipelines
                print("📊 4b. Deal Pipeline Migration")
                pipeline_results = migrate_deal_pipelines()
                migration_results['deal_pipelines'] = pipeline_results
                print()
                
                # Step 4c: Deal Objects
                print("💼 4c. Deal Object Migration")
                deal_results = migrate_deals(migration_config['contact_limit'])
                migration_results['deals'] = deal_results
                print()
                
                # Step 4d: Deal Associations
                print("🔗 4d. Deal Association Migration")
                deal_assoc_results = migrate_deal_associations()
                migration_results['deal_associations'] = deal_assoc_results
            print()
        
        # Step 5: Ticket Migration (or Step 1 if tickets-only)
        if ((not args.skip_tickets and not args.contacts_only and not args.deals_only and not args.custom_objects_only) or args.tickets_only):
            print("🎫 STEP 5: TICKET MIGRATION")
            print("=" * 60)
            if args.dry_run:
                print("🌙 Dry run: Would migrate ticket properties, pipelines, and tickets")
            else:
                # Step 5a: Ticket Properties
                print("🔧 5a. Ticket Properties Migration")
                ticket_prop_results = migrate_ticket_properties()
                migration_results['ticket_properties'] = ticket_prop_results
                print()
                
                # Step 5b: Ticket Pipelines
                print("📊 5b. Ticket Pipeline Migration")
                ticket_pipeline_results = migrate_ticket_pipelines()
                migration_results['ticket_pipelines'] = ticket_pipeline_results
                print()
                
                # Step 5c: Ticket Objects
                print("🎫 5c. Ticket Object Migration")
                ticket_results = migrate_tickets(migration_config['contact_limit'])
                migration_results['tickets'] = ticket_results
                print()
            print()
        
        # Step 6: Custom Object Migration (Advanced)
        if (not args.skip_custom_objects and not args.contacts_only and not args.deals_only and not args.tickets_only) or args.custom_objects_only:
            print("🔧 STEP 6: CUSTOM OBJECT MIGRATION")
            print("=" * 60)
            if args.dry_run:
                print("🌙 Dry run: Would analyze and migrate any custom objects")
            else:
                custom_obj_results = migrate_custom_objects(migration_config['contact_limit'])
                migration_results['custom_objects'] = custom_obj_results
            print()
        
        # Step 7: Verification
        if not args.dry_run:
            print("✅ STEP 7: DATA VERIFICATION")
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
        
        # Handle rollback operations first
        if (args.show_rollback_options or args.rollback_last or args.rollback_last_n or 
            args.reset_records_only or args.reset_properties_only or args.full_reset):
            success = handle_rollback_operations(config, args, logger)
            sys.exit(0 if success else 1)
        
        # Handle selective sync operations
        if args.selective_contacts or args.selective_deals or args.selective_tickets or args.selective_custom_objects:
            success = handle_selective_sync(config, args, logger)
            sys.exit(0 if success else 1)
        
        # Run normal migration
        success = run_migration(config, args, logger)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        print("📋 Please check your configuration and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()