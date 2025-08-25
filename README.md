# Modern HubSpot Migration Tools (2025)

This folder contains updated HubSpot migration scripts that work with the latest HubSpot APIs as of 2025.

## Features

- ✅ **2025 API Compatible**: Uses Private App Access Tokens (Bearer authentication)
- ✅ **Property Sync**: Automatically syncs custom properties from production to sandbox
- ✅ **Safe Updates**: Only updates writable properties to avoid API errors
- ✅ **Smart Filtering**: Excludes read-only and calculated fields automatically
- ✅ **Error Handling**: Robust error handling with detailed feedback

## Files

- `contact_migration.py` - Main contact migration script
- `property_sync.py` - Property synchronization utility
- `utils.py` - Common utilities and helper functions
- `.env` - API key configuration (not committed to git)

## Setup

1. Configure your API keys in `.env`
2. Run property sync: `python property_sync.py`  
3. Run contact migration: `python contact_migration.py`

## API Requirements

- HubSpot Private App Access Tokens (format: `pat-na1-...`)
- Requires permissions: `crm.objects.contacts.read`, `crm.objects.contacts.write`, `crm.schemas.contacts.read`