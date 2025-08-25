# Setup Guide

## Prerequisites

1. **Python 3.8+** installed on your system
2. **HubSpot Private App Access Tokens** for both source and destination portals
3. **Appropriate permissions** in both HubSpot portals:
   - `crm.objects.contacts.read` and `crm.objects.contacts.write`
   - `crm.objects.companies.read` and `crm.objects.companies.write`
   - `crm.schemas.contacts.read` and `crm.schemas.companies.read`
   - `crm.associations.read` and `crm.associations.write`

## Installation Steps

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/modern-hubspot-migration.git
cd modern-hubspot-migration
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Tokens

#### Option A: Using Configuration File (Recommended)
```bash
# Copy example configuration
cp config/config.example.ini config/config.ini

# Edit the configuration file
nano config/config.ini  # or use your preferred editor
```

Edit the `[hubspot]` section with your tokens:
```ini
[hubspot]
production_token = pat-na1-your-production-token-here
sandbox_token = pat-na1-your-sandbox-token-here
```

#### Option B: Using Environment File (Legacy)
```bash
# Create .env file
echo "HUBSPOT_PROD_API_KEY=pat-na1-your-production-token" >> .env
echo "HUBSPOT_SANDBOX_API_KEY=pat-na1-your-sandbox-token" >> .env
```

## HubSpot Private App Setup

### Creating Private Apps in HubSpot

1. **Go to Settings** in your HubSpot account
2. **Navigate to Integrations > Private Apps**
3. **Click "Create a private app"**
4. **Configure the app:**
   - Name: "Migration Tool - [Portal Name]"
   - Description: "Data migration between HubSpot portals"
5. **Set Scopes** (Required permissions):
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.companies.read`
   - `crm.objects.companies.write`
   - `crm.schemas.contacts.read`
   - `crm.schemas.companies.read`
   - `crm.associations.read`
   - `crm.associations.write`
6. **Create the app** and copy the access token

### Security Best Practices

- **Never commit tokens to version control**
- **Use different tokens for production and sandbox**
- **Regularly rotate your tokens**
- **Restrict token permissions to minimum required**

## Verification

Test your setup:
```bash
# Dry run to verify configuration
python migrate.py --dry-run --limit 5

# Test with verbose logging
python migrate.py --dry-run --verbose --limit 5
```

## Troubleshooting

### Common Issues

1. **"No configuration file found"**
   - Ensure `config/config.ini` exists
   - Copy from `config/config.example.ini`

2. **"Please configure your API tokens"**
   - Check token format (should start with `pat-na1-`)
   - Verify tokens are not placeholder values

3. **"Permission denied" errors**
   - Verify Private App has required scopes
   - Check that tokens are for the correct portals

4. **Rate limiting errors**
   - Increase `rate_limit_delay` in config
   - Reduce `batch_size` in config

### Getting Help

1. Check the logs in `logs/` directory
2. Review the reports in `reports/` directory
3. Enable verbose logging with `--verbose` flag
4. Create an issue on GitHub with detailed error information