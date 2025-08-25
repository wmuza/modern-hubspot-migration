# Usage Guide

## Quick Start

The simplest way to migrate data is using the main migration script:

```bash
python migrate.py
```

This will run the complete migration process with default settings.

## Command Line Options

### Basic Usage
```bash
# Full migration with default settings
python migrate.py

# Migrate specific number of contacts
python migrate.py --limit 100

# Use custom configuration file
python migrate.py --config examples/configs/production-to-staging.ini

# Verbose logging for debugging
python migrate.py --verbose

# Preview what would be migrated (no changes made)
python migrate.py --dry-run
```

### Advanced Options
```bash
# Skip property migration (if already done)
python migrate.py --skip-properties

# Migrate only contacts (no associations)
python migrate.py --contacts-only

# Combine options
python migrate.py --verbose --limit 50 --dry-run
```

## Step-by-Step Migration

### 1. Initial Setup and Testing
```bash
# Test your configuration
python migrate.py --dry-run --limit 5 --verbose

# Small test migration
python migrate.py --limit 10
```

### 2. Property Migration
The first step creates custom properties in the destination portal:

```bash
# Run property migration only
python src/migrations/company_property_migrator.py
```

### 3. Contact Migration
Migrate contacts with all their custom properties:

```bash
# Run contact migration only
python src/migrations/contact_migration.py
```

### 4. Association Migration
Migrate company associations and relationships:

```bash
# Run association migration only
python src/migrations/enterprise_association_migrator.py
```

### 5. Verification
Verify data integrity after migration:

```bash
python src/validators/verify_company_properties.py
```

## Configuration Options

### Basic Configuration
Edit `config/config.ini`:

```ini
[hubspot]
production_token = pat-na1-your-production-token
sandbox_token = pat-na1-your-destination-token

[migration]
contact_limit = 50        # Number of contacts (0 = all)
batch_size = 10          # Processing batch size
rate_limit_delay = 0.3   # Delay between requests
max_retries = 3          # Retry attempts
```

### Logging Configuration
```ini
[logging]
log_level = INFO         # DEBUG, INFO, WARNING, ERROR
log_to_file = true       # Save logs to file
log_directory = logs     # Log file location
debug_reports = false    # Include debug info in reports
```

### Output Configuration
```ini
[output]
reports_directory = reports     # Report file location
generate_csv_exports = true     # Create CSV exports
save_property_mappings = true   # Save property mappings
```

## Migration Scenarios

### Scenario 1: Production to Sandbox
```bash
# Use default configuration for sandbox testing
python migrate.py --limit 100
```

### Scenario 2: Staging Environment
```bash
# Use staging configuration
python migrate.py --config examples/configs/production-to-staging.ini
```

### Scenario 3: Large Scale Migration
```bash
# Full migration with no limits
python migrate.py --config examples/configs/production-to-staging.ini --limit 0
```

### Scenario 4: Development Testing
```bash
# Small test batch with debug logging
python migrate.py --config examples/configs/small-batch-test.ini --verbose
```

## Understanding Output

### Console Output
- 🔧 **Configuration**: Shows migration settings
- 🏢 **Property Migration**: Creates custom properties
- 👥 **Contact Migration**: Migrates contact records
- 🔗 **Association Migration**: Creates relationships
- ✅ **Verification**: Validates data integrity
- 📊 **Summary**: Final results and statistics

### Log Files
Located in `logs/` directory:
- **migration_TIMESTAMP.log**: Detailed operation log
- **hubspot_migration_TIMESTAMP.log**: API interaction log

### Report Files
Located in `reports/` directory:
- **migration_report_TIMESTAMP.json**: Structured migration results
- **property_mappings.json**: Property name mappings
- **error_analysis.json**: Detailed error information

## Monitoring Progress

### Real-time Monitoring
The tool shows progress bars and status updates:
```
🔄 Processing contacts...
Migrating associations |████████████████████| 47/50 (94.0%)
```

### Log Monitoring
Monitor detailed logs in real-time:
```bash
# Follow the latest log file
tail -f logs/migration_$(date +%Y%m%d)*.log
```

## Error Handling

### Common Errors and Solutions

1. **Rate Limiting**
   - Increase `rate_limit_delay` in configuration
   - Reduce `batch_size`

2. **Permission Errors**
   - Verify Private App scopes
   - Check token permissions

3. **Property Errors**
   - Run property migration first
   - Check property compatibility

4. **Association Errors**
   - Verify company records exist
   - Check association API permissions

### Recovery from Failures
The tool is designed to be re-runnable:
- **Existing records**: Will be updated, not duplicated
- **Failed operations**: Can be retried safely
- **Partial migrations**: Resume from where it left off

## Best Practices

### Pre-Migration
1. **Test with small batches** first
2. **Verify token permissions** in both portals
3. **Review property compatibility** between portals
4. **Backup important data** before migration

### During Migration
1. **Monitor logs** for errors
2. **Check progress reports** regularly
3. **Don't interrupt** long-running migrations
4. **Have contingency plans** for failures

### Post-Migration
1. **Verify data integrity** using validation tools
2. **Review reports** for any issues
3. **Test portal functionality** with migrated data
4. **Document any customizations** made

## Troubleshooting

### Debug Mode
Enable verbose logging for detailed troubleshooting:
```bash
python migrate.py --verbose --dry-run
```

### Configuration Validation
Test your configuration:
```bash
python simple_migrate.py
```

### API Connectivity
Verify API access:
```bash
python src/utils/debug_contacts.py
```

### Property Analysis
Analyze property compatibility:
```bash
python src/validators/verify_company_properties.py
```

## Support

For additional support:
1. Check the [Setup Guide](SETUP.md)
2. Review error logs in `logs/` directory
3. Examine reports in `reports/` directory
4. Create GitHub issues with detailed error information