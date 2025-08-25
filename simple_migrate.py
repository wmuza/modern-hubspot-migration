#!/usr/bin/env python
"""
Simple Migration Script - Temporary working version
This script provides a working migration until we fully update all components
"""

import sys
import os

# Simplified version that works with existing files
from src.core.config import load_config
from src.utils.utils import print_banner, get_api_headers, make_hubspot_request

def simple_migration():
    """Run a simplified migration to demonstrate the structure"""
    try:
        print_banner()
        
        # Load configuration
        config = load_config()
        hubspot_config = config.get_hubspot_config()
        migration_config = config.get_migration_config()
        
        print("✅ Configuration loaded successfully")
        print(f"📊 Contact limit: {migration_config['contact_limit']}")
        print(f"🔐 Production token: {hubspot_config['production_token'][:15]}...")
        print(f"🧪 Sandbox token: {hubspot_config['sandbox_token'][:15]}...")
        print()
        
        # Test API connectivity
        print("🔌 Testing API connectivity...")
        
        # Test production API
        prod_headers = get_api_headers(hubspot_config['production_token'])
        success, data = make_hubspot_request(
            'GET',
            'https://api.hubapi.com/crm/v3/objects/contacts?limit=1',
            prod_headers
        )
        
        if success:
            print("✅ Production API connection successful")
        else:
            print(f"❌ Production API failed: {data}")
            return False
        
        # Test sandbox API
        sandbox_headers = get_api_headers(hubspot_config['sandbox_token'])
        success, data = make_hubspot_request(
            'GET',
            'https://api.hubapi.com/crm/v3/objects/contacts?limit=1',
            sandbox_headers
        )
        
        if success:
            print("✅ Sandbox API connection successful")
        else:
            print(f"❌ Sandbox API failed: {data}")
            return False
        
        print()
        print("🎉 Setup verification completed successfully!")
        print("📋 Your repository structure is working correctly")
        print("🚀 Ready for full migration implementation")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = simple_migration()
    sys.exit(0 if success else 1)