# Changelog

All notable changes to the HubSpot Modern Migration Tool will be documented in this file.

## [2.1.0] - 2025-08-26

### Added
- 🎫 **Complete Ticket Migration System**: Full support for migrating HubSpot tickets
  - Ticket property migration with custom field support
  - Ticket pipeline migration with stage mapping
  - Ticket object migration with data integrity preservation
  - New command: `--tickets-only` for standalone ticket migration
  - New command: `--skip-tickets` to exclude tickets from migration
- 📊 **Ticket Analysis Tool**: Comprehensive ticket schema analysis (`ticket_analyzer.py`)
- 🏗️ **Modular Architecture**: Separate migrators for properties, pipelines, and objects
- 📄 **Enhanced Reporting**: Detailed ticket migration reports with success metrics

### Technical Improvements
- Added `TicketPropertyMigrator`, `TicketPipelineMigrator`, and `TicketMigrator` classes
- Integrated ticket migration into main workflow as Step 5
- Enhanced field filtering for ticket-specific properties
- Improved pipeline mapping between environments

### Impact
- **Complete CRM Coverage**: Now supports all core HubSpot objects (Contacts, Companies, Deals, Tickets)
- **Production Ready**: Tested ticket migration with 100% success rate
- **Phase 1.4 Complete**: All primary CRM objects fully supported

## [2.0.2] - 2025-08-26

### Changed
- 🚀 **Default Behavior**: Changed default `contact_limit` from 50 to 0 (unlimited) to migrate all records by default
- 🔧 **Token Validation**: Fixed HubSpot Private App token validation to properly support `pat-na1-` format tokens
- 📚 **Documentation**: Updated README.md, USAGE.md, and QUICK_START.md to reflect new defaults

### Fixed
- ❌ **Configuration Override**: Fixed hardcoded 50-record limit that ignored config file settings
- 🔐 **Token Format**: Corrected token validation logic to accept proper HubSpot Private App token structure

### Impact
- Users can now migrate all their data by default without specifying limits
- Proper token validation prevents false authentication errors
- Consistent behavior between config file settings and actual migration limits

## [2.0.1] - 2025-08-25

### Fixed
- 🎯 **Critical Ordering Issue**: All migrations now fetch newest records first (sorted by createdate DESC)
- 🔢 **Limit Enforcement Bug**: Deal migration now properly respects user-specified limits (e.g., --limit 20)
- 🔧 **Parameter Passing**: Fixed deal migration function to accept limit parameter from main script
- 📊 **Selective Sync Ordering**: Contact and deal selective sync now return most recent records first
- 🧹 **Environment Cleanup**: Logs and reports folders are properly cleaned for fresh starts

### Technical Improvements
- Added `sorts: 'createdate:desc'` to all HubSpot API calls in:
  - Deal migration (`deal_migrator.py`)
  - Contact migration (`contact_migration.py`) 
  - Selective sync for both contacts and deals (`selective_sync.py`)
- Modified `migrate_deals()` function signature to accept limit parameter
- Updated main migration script to pass contact_limit to deal migration
- Enhanced API parameter consistency across all migration modules

### Impact
- Users now get the most recently created records when using limits
- Deal migrations properly respect --limit parameter instead of using hardcoded values
- Selective sync operations target the newest records for better accuracy
- Migration behavior is now predictable and matches user expectations

## [2.0.0] - 2025-08-25

### Added
- 💼 **Complete Deal Migration** with properties, pipelines, and associations
- 🎯 **Selective Sync System** for targeted migrations of specific contacts/deals
- 🔄 **Complete Rollback System** with granular undo capabilities
- 🗑️ **Advanced Reset Options** (records-only, properties-only, full reset)
- 📊 **Enhanced Field Filtering** (116 safe properties out of 359 total)
- 🏗️ **Deal Pipeline Recreation** with exact structure preservation
- 🔗 **Deal Association Migration** for contact-deal-company relationships
- 📈 **Enterprise Batch Processing** with intelligent rate limiting

### Migration Capabilities Extended
- Deal object migration with full property fidelity
- Deal pipeline and stage recreation
- Deal-contact-company association mapping
- Selective migration based on creation date or IDs
- Email domain-based contact filtering
- Complete rollback of any migration type

### Advanced Features
- Command-line interface with 15+ options
- Real-time progress tracking and reporting
- Comprehensive JSON audit trails
- Production-grade error handling and recovery
- Professional CLI with status indicators

## [1.0.0] - 2025-08-25

### Added
- ✨ **Complete Contact Migration** with all custom properties
- 🏢 **Company Property Migration** with automatic creation
- 🔗 **Association Management** between contacts and companies
- 🔒 **Enterprise Security** with comprehensive field filtering
- 📊 **Professional Reporting** with detailed logs and JSON reports
- 🎯 **One-click Migration** with single command execution
- 🌙 **Dry Run Mode** for testing without changes
- 📁 **Organized Structure** with proper folder hierarchy
- 🔧 **Configurable Settings** via INI files
- 📚 **Comprehensive Documentation** with setup and usage guides
- 🛡️ **Security Measures** preventing sensitive data commits
- 🎛️ **Portal-agnostic Design** working with any HubSpot portal

### Technical Features
- **2025 API Compatible** using Bearer token authentication
- **Rate Limiting** and retry logic for production safety
- **Property Filtering** excluding readonly and system fields
- **Batch Processing** for optimal performance
- **Error Recovery** with resumable migrations
- **Data Validation** ensuring migration integrity
- **Logging Framework** with multiple verbosity levels
- **Git Integration** with proper .gitignore

### Migration Capabilities
- Contact properties migration and synchronization
- Company properties creation and updates
- Contact-company association recreation
- Custom property field mapping
- Data integrity verification
- Comprehensive error reporting

### Documentation
- Complete README with installation and usage
- Detailed setup guide with HubSpot configuration
- Usage examples for different scenarios
- Troubleshooting guide for common issues
- Example configurations for various use cases

### Security
- Automatic exclusion of sensitive data from version control
- Secure configuration management
- Token validation and format checking
- Portal-specific data isolation
- No hardcoded portal identifiers

## Developer Notes

### Architecture
- Modular design with separated concerns
- Core logic in `src/core/`
- Migration modules in `src/migrations/`
- Utilities in `src/utils/`
- Validators in `src/validators/`

### Configuration
- INI-based configuration with sections
- Environment file backward compatibility
- Example configurations for different scenarios
- Secure token management

### Future Enhancements
- Deal associations migration
- Ticket associations migration
- Custom object support
- Workflow migration
- Email template migration