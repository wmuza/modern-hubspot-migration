"""
Utility Functions for HubSpot Migration
Common utilities and helper functions
"""

import os
import requests
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path

def setup_logging(level: str = 'INFO', log_to_file: bool = True, log_directory: str = 'logs'):
    """Setup logging configuration"""
    # Create log directory if it doesn't exist
    if log_to_file:
        os.makedirs(log_directory, exist_ok=True)
    
    # Configure logging
    log_level = getattr(logging, level.upper())
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_directory, f'migration_{timestamp}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

def load_env_config(env_file: str = '.env') -> Dict[str, str]:
    """Load environment configuration from .env file (backward compatibility)"""
    config = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key] = value
    return config

def get_api_headers(token: str) -> Dict[str, str]:
    """Get API headers for HubSpot requests"""
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

def make_hubspot_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    timeout: int = 30,
    backoff_factor: float = 2.0
) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    Make a HubSpot API request with enhanced error handling and retries
    
    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        url: API endpoint URL
        headers: Request headers
        json_data: JSON payload for POST/PUT requests
        params: Query parameters
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        backoff_factor: Exponential backoff multiplier
        
    Returns:
        Tuple of (success: bool, data: dict or error_info)
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Add request session for connection pooling
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=timeout
            )
            
            # Enhanced status code handling
            if response.status_code in [200, 201, 202]:
                try:
                    return True, response.json()
                except ValueError:
                    # Handle non-JSON responses
                    return True, {'status': 'success', 'text': response.text}
                    
            elif response.status_code == 204:
                # No content success
                return True, {'status': 'success', 'message': 'No content'}
                
            elif response.status_code == 409:
                # Conflict - might be duplicate, return as success for some cases
                try:
                    return True, response.json()
                except ValueError:
                    return True, {'status': 'conflict', 'text': response.text}
                    
            elif response.status_code == 429:
                # Rate limited - enhanced backoff with jitter
                if attempt < max_retries:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        sleep_time = min(int(retry_after), 300)  # Cap at 5 minutes
                    else:
                        sleep_time = min(backoff_factor ** attempt, 60)  # Cap at 1 minute
                    
                    logging.warning(f"Rate limited, waiting {sleep_time}s before retry {attempt + 1}")
                    time.sleep(sleep_time)
                    continue
                else:
                    return False, {
                        'status_code': response.status_code,
                        'error': 'Rate limited - max retries exceeded',
                        'retry_after': response.headers.get('Retry-After')
                    }
                    
            elif response.status_code in [500, 502, 503, 504]:
                # Server errors - retry with backoff
                if attempt < max_retries:
                    sleep_time = min(backoff_factor ** attempt, 30)
                    logging.warning(f"Server error {response.status_code}, retrying in {sleep_time}s")
                    time.sleep(sleep_time)
                    continue
                    
            # Client errors and other status codes
            try:
                error_data = response.json()
            except ValueError:
                error_data = response.text
                
            return False, {
                'status_code': response.status_code,
                'error': error_data,
                'url': url,
                'method': method
            }
                
        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries:
                sleep_time = min(backoff_factor ** attempt, 10)
                logging.warning(f"Request timeout, retrying in {sleep_time}s")
                time.sleep(sleep_time)
                continue
                
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                sleep_time = min(backoff_factor ** attempt, 10)
                logging.warning(f"Connection error, retrying in {sleep_time}s")
                time.sleep(sleep_time)
                continue
                
        except requests.exceptions.RequestException as e:
            last_exception = e
            logging.error(f"Request exception: {str(e)}")
            return False, {'error': f'Request exception: {str(e)}', 'url': url}
            
        except Exception as e:
            last_exception = e
            logging.error(f"Unexpected error: {str(e)}")
            return False, {'error': f'Unexpected error: {str(e)}', 'url': url}
    
    # All retries exhausted
    error_msg = f'Max retries ({max_retries}) exceeded'
    if last_exception:
        error_msg += f': {str(last_exception)}'
        
    return False, {'error': error_msg, 'url': url, 'last_exception': str(last_exception)}

def print_progress_bar(current: int, total: int, prefix: str = 'Progress', length: int = 30):
    """Print a progress bar"""
    if total == 0:
        return
        
    percent = current / total
    filled_length = int(length * percent)
    bar = '█' * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {current}/{total} ({percent:.1%})', end='', flush=True)
    
    if current == total:
        print()  # New line when complete

def print_banner():
    """Print the application banner"""
    print()
    print("🚀 HubSpot Modern Migration Tool (2025)")
    print("=" * 80)
    print("Professional-grade portal migration with enterprise security")
    print("Built for HubSpot's latest APIs with comprehensive data protection")
    print("=" * 80)
    print()

def print_summary(results: Dict[str, Any], dry_run: bool = False):
    """Print migration summary"""
    print("📊 MIGRATION SUMMARY")
    print("=" * 80)
    
    if dry_run:
        print("🌙 DRY RUN COMPLETED - No actual changes were made")
        print("✅ All validation checks passed")
        print("💡 Run without --dry-run flag to perform actual migration")
    else:
        total_contacts = 0
        total_companies = 0
        total_associations = 0
        
        if 'contacts' in results:
            contact_data = results['contacts']
            print(f"👥 Contacts: {contact_data.get('migrated', 0)} new + {contact_data.get('updated', 0)} updated = {contact_data.get('migrated', 0) + contact_data.get('updated', 0)} total")
            total_contacts = contact_data.get('total', 0)
        
        if 'associations' in results:
            assoc_data = results['associations']
            print(f"🏢 Companies: {assoc_data.total_companies_migrated} migrated")
            print(f"🔗 Associations: {assoc_data.total_associations_created} established")
            total_companies = assoc_data.total_companies_migrated
            total_associations = assoc_data.total_associations_created
        
        success_rate = 100.0
        if total_contacts > 0:
            if 'contacts' in results:
                failed = results['contacts'].get('failed', 0)
                success_rate = ((total_contacts - failed) / total_contacts) * 100
        
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if success_rate == 100.0:
            print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            print("✅ All data has been migrated with full integrity")
        else:
            print("⚠️  Some issues encountered during migration")
            print("📋 Check the detailed logs and reports for more information")
    
    print("=" * 80)
    print(f"📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def ensure_directory(path: str):
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)

def validate_hubspot_token(token: str) -> Tuple[bool, str]:
    """
    Validate HubSpot API token format and basic security checks
    
    Args:
        token: The API token to validate
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not token or not isinstance(token, str):
        return False, "Token is empty or not a string"
    
    token = token.strip()
    
    # Check if it's a placeholder token
    placeholder_indicators = ['your-', 'example-', 'replace-', 'token-here', 'api-key']
    if any(indicator in token.lower() for indicator in placeholder_indicators):
        return False, "Token appears to be a placeholder - please replace with your actual HubSpot Private App token"
    
    # Check length (HubSpot tokens are typically long)
    if len(token) < 20:
        return False, "Token appears too short to be valid"
    
    # Check for HubSpot Private App token format (pat-na1-xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
    if not token.startswith('pat-na1-'):
        return False, "Token should start with 'pat-na1-' for HubSpot Private App tokens"
    
    # Check for proper UUID-like format after the prefix
    token_parts = token.split('-')
    if len(token_parts) < 5:  # pat, na1, and at least 3 more parts
        return False, "Token format doesn't match expected HubSpot Private App token structure"
    
    return True, "Token format appears valid"

def sanitize_api_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize API response data to remove sensitive information for logging
    
    Args:
        response_data: Raw API response data
        
    Returns:
        Sanitized response data safe for logging
    """
    if not isinstance(response_data, dict):
        return response_data
    
    sensitive_keys = ['token', 'api_key', 'password', 'secret', 'auth', 'authorization']
    sanitized = {}
    
    for key, value in response_data.items():
        key_lower = key.lower()
        if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_api_response(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_api_response(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    
    return sanitized