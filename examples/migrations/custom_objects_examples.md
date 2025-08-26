# Custom Objects Migration Examples

This document provides comprehensive examples of how to use the HubSpot Migration Tool's custom object migration capabilities.

## Overview

The Custom Objects Migration system can migrate ANY custom object type from your HubSpot portal. It works by:

1. **Discovery**: Automatically detects all custom object types in both source and destination portals
2. **Schema Migration**: Creates missing object schemas and properties in the destination
3. **Data Migration**: Migrates object records with full property fidelity
4. **Error Handling**: Gracefully handles objects without data or invalid configurations

## Basic Usage

### Migrate All Custom Objects
```bash
# Migrate all custom objects found in the source portal
python migrate.py --custom-objects-only

# Preview what custom objects would be migrated (no changes)
python migrate.py --custom-objects-only --dry-run

# Migrate with verbose logging to see detailed progress
python migrate.py --custom-objects-only --verbose
```

### Skip Custom Objects in Full Migration
```bash
# Run full migration but exclude custom objects
python migrate.py --skip-custom-objects

# Migrate only standard objects (contacts, companies, deals, tickets)
python migrate.py --contacts-only --deals-only --tickets-only
```

## Analysis Before Migration

### Analyze Custom Objects Structure
```bash
# Get comprehensive analysis of all custom objects
python src/utils/custom_object_analyzer.py

# This generates detailed reports showing:
# - All custom object types in both environments
# - Property comparisons and compatibility
# - Sample data and structure analysis
# - Migration recommendations
```

Example output from analyzer:
```
🔍 Custom Object Discovery & Analysis Tool
================================================================================

📋 CUSTOM OBJECTS FOUND:
✅ Source Portal: 7 custom object types
✅ Destination Portal: 2 custom object types

🆕 NEW CUSTOM OBJECT TYPES TO MIGRATE:
1. purchased_products (15 properties, 0 objects)
2. surveys (8 properties, 0 objects)  
3. visit_reports__ (12 properties, 0 objects)
4. equipments (10 properties, 0 objects)
5. internal_requests (9 properties, 0 objects - SCHEMA ERROR)

⚠️  POTENTIAL ISSUES:
- internal_requests: No valid primaryDisplayProperty set
```

## Real-World Examples

### Example 1: Project Management Objects
If your portal has custom objects for project management:

```bash
# Migrate projects, tasks, and milestones
python migrate.py --custom-objects-only --verbose

# Common custom objects for project management:
# - projects (with properties: project_name, start_date, budget, status)
# - tasks (with properties: task_name, assignee, due_date, completion_status)
# - milestones (with properties: milestone_name, target_date, completion_date)
```

### Example 2: E-commerce and Inventory
For e-commerce businesses with custom inventory objects:

```bash
# First analyze the structure
python src/utils/custom_object_analyzer.py

# Then migrate products, orders, and inventory
python migrate.py --custom-objects-only

# Common e-commerce custom objects:
# - products (with properties: sku, price, category, stock_level)
# - orders (with properties: order_number, total_amount, order_status)
# - inventory_items (with properties: item_code, location, quantity)
```

### Example 3: Service Industry Objects
For service businesses with custom objects:

```bash
# Migrate service requests, equipment, and scheduling
python migrate.py --custom-objects-only --limit 50

# Common service industry objects:
# - service_requests (with properties: request_type, priority, technician)
# - equipment (with properties: serial_number, model, maintenance_date)
# - schedules (with properties: appointment_date, duration, location)
```

## Advanced Usage Scenarios

### Scenario 1: Large Scale Migration with Monitoring
```bash
# Step 1: Analyze first to understand scope
python src/utils/custom_object_analyzer.py > reports/custom_objects_analysis.txt

# Step 2: Test with small batch
python migrate.py --custom-objects-only --limit 10 --verbose

# Step 3: Full migration with comprehensive logging
python migrate.py --custom-objects-only --verbose 2>&1 | tee logs/custom_objects_migration.log

# Step 4: Verify results
grep -E "(SUCCESS|ERROR|FAILED)" logs/custom_objects_migration.log
```

### Scenario 2: Selective Custom Object Migration
```bash
# If you want to migrate only specific custom object types,
# you can use the direct migrator (advanced users):

# First see what's available
python src/utils/custom_object_analyzer.py

# Then migrate specific types using the migrator directly
# (Note: This requires understanding the object type names)
python -c "
from src.migrations.custom_object_migrator import CustomObjectMigrator
migrator = CustomObjectMigrator()
migrator.migrate_custom_object_type('projects')
migrator.migrate_custom_object_type('tasks')
"
```

### Scenario 3: Error Recovery and Troubleshooting
```bash
# If some objects fail to migrate, use verbose mode to diagnose
python migrate.py --custom-objects-only --verbose

# Check the detailed error reports
cat reports/custom_object_migration_*.json | jq '.errors[]'

# For objects with schema issues, you may need to:
# 1. Check the object configuration in HubSpot
# 2. Ensure required properties are set correctly
# 3. Verify primaryDisplayProperty is configured
```

## Understanding Migration Reports

After running custom object migration, detailed JSON reports are generated:

### Report Structure
```json
{
  "timestamp": "2025-08-26T15:27:14.610369",
  "summary": {
    "total_object_types": 7,
    "object_results": [
      {
        "object_type": "purchased_products", 
        "objects_created": 0,
        "objects_failed": 0,
        "success_rate": 100.0
      }
    ],
    "overall_success_rate": 100,
    "total_objects_created": 0,
    "total_objects_failed": 0
  },
  "errors": [
    "Failed to create schema internal_requests: primaryDisplayProperty not set"
  ]
}
```

### Reading the Reports
- **objects_created**: Number of object records successfully migrated
- **success_rate**: Percentage of successful migrations for this object type
- **errors**: Detailed error messages for troubleshooting

## Common Custom Object Types

### Business Operations
- **projects**: Project management and tracking
- **contracts**: Contract lifecycle management
- **assets**: Asset and equipment management
- **invoices**: Financial document tracking

### Sales & Marketing
- **campaigns**: Marketing campaign tracking
- **leads**: Lead qualification and scoring
- **opportunities**: Sales opportunity management
- **quotes**: Quote and proposal management

### Service & Support
- **service_requests**: Service ticket management
- **equipment**: Equipment and device tracking
- **maintenance_records**: Maintenance scheduling
- **warranties**: Warranty and service agreement tracking

### Industry-Specific
- **patients**: Healthcare patient management
- **properties**: Real estate property management
- **students**: Educational institution management
- **vehicles**: Fleet and transportation management

## Error Handling and Troubleshooting

### Common Issues and Solutions

#### 1. Schema Creation Errors
```
Error: "primaryDisplayProperty not set"
```
**Solution**: In HubSpot, go to Settings > Objects > [Your Object] and set a primary display property.

#### 2. Property Migration Failures
```
Error: "Property validation failed"
```
**Solution**: Check that custom properties in source don't conflict with system properties in destination.

#### 3. No Objects to Migrate
```
Info: "0 objects found for object_type"
```
**Solution**: This is normal if the custom object exists but has no data. The schema will still be migrated.

### Debugging Steps
1. **Run Analysis First**: Always use `custom_object_analyzer.py` to understand what you're migrating
2. **Test Small Batches**: Use `--limit 10` for initial testing
3. **Use Verbose Logging**: Add `--verbose` to see detailed progress
4. **Check Reports**: Review JSON reports in `reports/` directory
5. **Verify in HubSpot**: Check the destination portal to confirm objects were created correctly

## Best Practices

### Before Migration
1. **Backup Important Data**: Always backup critical custom object data
2. **Test in Sandbox**: Use a test destination portal first  
3. **Review Object Dependencies**: Understand relationships between custom objects
4. **Check Permissions**: Ensure your API tokens have custom object permissions

### During Migration
1. **Monitor Progress**: Watch for error messages during migration
2. **Don't Interrupt**: Let long-running migrations complete
3. **Check Rate Limits**: Large custom object migrations may hit API limits
4. **Verify Incrementally**: Check objects are being created correctly

### After Migration
1. **Validate Data**: Verify all custom objects and properties migrated correctly
2. **Test Functionality**: Ensure custom objects work as expected in destination
3. **Update Associations**: Check that relationships between objects are preserved
4. **Document Changes**: Keep track of what was migrated for future reference

## Performance Considerations

### Large Custom Object Datasets
- **Batch Processing**: Large objects are processed in batches automatically
- **Memory Usage**: Very large custom objects may require multiple runs
- **API Limits**: HubSpot rate limits apply to custom objects
- **Time Estimates**: Complex custom objects take longer to migrate

### Optimization Tips
```bash
# For very large custom object migrations:
# 1. Increase batch processing delays
python migrate.py --custom-objects-only --verbose
# (Rate limiting is automatic)

# 2. Process in smaller chunks if needed
python migrate.py --custom-objects-only --limit 1000

# 3. Monitor system resources during migration
top -p $(pgrep -f migrate.py)
```

## Integration with Full Migration

Custom objects integrate seamlessly with full portal migration:

```bash
# Full migration including custom objects (default behavior)
python migrate.py

# This runs:
# Step 1: Company properties
# Step 2: Contact migration  
# Step 3: Deal migration
# Step 4: Ticket migration
# Step 5: Association migration
# Step 6: Custom object migration  ← Your custom objects

# Skip custom objects if not needed
python migrate.py --skip-custom-objects

# Include custom objects with selective sync
python migrate.py --selective-contacts --days-since-created 30
# (This will still migrate all related custom objects)
```

## Support and Resources

### Getting Help
1. **Check Error Logs**: Review detailed logs in `logs/` directory
2. **Analyze Reports**: Check JSON reports in `reports/` directory  
3. **Use Verbose Mode**: Add `--verbose` to any command for detailed output
4. **Test First**: Always test with `--dry-run` and small limits first

### Additional Documentation
- **Main README**: `/README.md` - Complete setup and basic usage
- **Usage Guide**: `/docs/guides/USAGE.md` - Comprehensive command reference
- **Setup Guide**: `/docs/guides/SETUP.md` - Detailed configuration instructions
- **Troubleshooting**: Check GitHub issues for known problems and solutions

---

**The Custom Object Migration system is the most advanced feature of this tool, providing complete HubSpot migration coverage for any portal configuration!** 🚀