"""
Secure Configuration Management
Handles loading and validation of configuration files with security measures
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import sys

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.utils import validate_hubspot_token

class SecureConfig:
    """Secure configuration loader with validation and safety checks"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self.config = configparser.ConfigParser()
        self._load_config()
        self._validate_config()
    
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations"""
        possible_paths = [
            'config/config.ini',
            'config.ini',
            '.env'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError(
            "No configuration file found. Please create config/config.ini from config/config.example.ini"
        )
    
    def _load_config(self):
        """Load configuration file with error handling"""
        try:
            self.config.read(self.config_file)
            
            # Also check for .env file for backward compatibility
            env_file = '.env'
            if os.path.exists(env_file):
                self._load_env_file(env_file)
                
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration from {self.config_file}: {e}")
    
    def _load_env_file(self, env_file: str):
        """Load environment variables from .env file"""
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Convert .env format to config format
                    if key == 'HUBSPOT_PROD_API_KEY':
                        if not self.config.has_section('hubspot'):
                            self.config.add_section('hubspot')
                        self.config.set('hubspot', 'production_token', value)
                    elif key == 'HUBSPOT_SANDBOX_API_KEY':
                        if not self.config.has_section('hubspot'):
                            self.config.add_section('hubspot')
                        self.config.set('hubspot', 'sandbox_token', value)
    
    def _validate_config(self):
        """Validate configuration and check for security issues"""
        # Check required sections
        required_sections = ['hubspot']
        for section in required_sections:
            if not self.config.has_section(section):
                raise ValueError(f"Missing required configuration section: [{section}]")
        
        # Check required HubSpot tokens with enhanced validation
        required_tokens = ['production_token', 'sandbox_token']
        for token_name in required_tokens:
            token_value = self.config.get('hubspot', token_name, fallback='')
            
            if not token_value:
                raise ValueError(
                    f"Missing {token_name} in {self.config_file}. "
                    f"Get your tokens from HubSpot Private App settings."
                )
            
            # Use the new validation function
            is_valid, validation_message = validate_hubspot_token(token_value)
            if not is_valid:
                raise ValueError(f"Invalid {token_name}: {validation_message}")
            
            logging.info(f"{token_name} validation: {validation_message}")
        
        # Validate migration settings
        migration_limit = self.config.getint('migration', 'contact_limit', fallback=0)
        if migration_limit > 10000:
            logging.warning(f"Very high contact limit ({migration_limit}). Consider using smaller batches.")
        
        # Validate rate limiting settings
        rate_limit = self.config.getfloat('migration', 'rate_limit_delay', fallback=0.3)
        if rate_limit < 0.1:
            logging.warning(f"Very low rate limit delay ({rate_limit}s) may cause API rate limiting issues.")
    
    def get_hubspot_config(self) -> Dict[str, str]:
        """Get HubSpot API configuration"""
        return {
            'production_token': self.config.get('hubspot', 'production_token'),
            'sandbox_token': self.config.get('hubspot', 'sandbox_token')
        }
    
    def get_migration_config(self) -> Dict[str, Any]:
        """Get migration settings"""
        return {
            'contact_limit': self.config.getint('migration', 'contact_limit', fallback=0),
            'batch_size': self.config.getint('migration', 'batch_size', fallback=10),
            'rate_limit_delay': self.config.getfloat('migration', 'rate_limit_delay', fallback=0.3),
            'max_retries': self.config.getint('migration', 'max_retries', fallback=3),
            'skip_contacts_without_email': self.config.getboolean('migration', 'skip_contacts_without_email', fallback=True)
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'log_level': self.config.get('logging', 'log_level', fallback='INFO'),
            'log_to_file': self.config.getboolean('logging', 'log_to_file', fallback=True),
            'log_directory': self.config.get('logging', 'log_directory', fallback='logs'),
            'debug_reports': self.config.getboolean('logging', 'debug_reports', fallback=False)
        }
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output and reporting configuration"""
        return {
            'reports_directory': self.config.get('output', 'reports_directory', fallback='reports'),
            'generate_csv_exports': self.config.getboolean('output', 'generate_csv_exports', fallback=True),
            'save_property_mappings': self.config.getboolean('output', 'save_property_mappings', fallback=True)
        }
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        logging_config = self.get_logging_config()
        output_config = self.get_output_config()
        
        directories = [
            logging_config['log_directory'],
            output_config['reports_directory']
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def is_secure(self) -> bool:
        """Check if configuration is secure for production use"""
        hubspot_config = self.get_hubspot_config()
        
        # Check for placeholder tokens
        for token_name, token_value in hubspot_config.items():
            if not token_value or token_value.startswith('your-'):
                return False
        
        return True

def load_config(config_file: Optional[str] = None) -> SecureConfig:
    """Load and validate configuration"""
    return SecureConfig(config_file)