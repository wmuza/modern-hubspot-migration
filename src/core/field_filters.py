"""
Comprehensive HubSpot Field Filtering System
Handles all readonly, calculated, and production-specific fields
"""

from typing import Any, Dict, List, Set

class HubSpotFieldFilter:
    """
    Comprehensive filtering system for HubSpot contact properties
    """
    
    def __init__(self):
        # System prefixes that should never be updated
        self.SYSTEM_PREFIXES = {
            'hs_additional_', 'hs_all_', 'hs_analytics_', 'hs_associated_',
            'hs_avatar_', 'hs_buying_', 'hs_calculated_', 'hs_clicked_',
            'hs_contact_', 'hs_content_', 'hs_conversations_', 'hs_count_',
            'hs_country_', 'hs_created_', 'hs_createdate_', 'hs_cross_',
            'hs_currently_', 'hs_customer_', 'hs_data_', 'hs_document_',
            'hs_email_', 'hs_emailconfirmationstatus_', 'hs_employment_',
            'hs_enriched_', 'hs_facebook_', 'hs_facebookid_', 'hs_feedback_',
            'hs_first_', 'hs_full_', 'hs_google_', 'hs_googleplusid_',
            'hs_gps_', 'hs_has_', 'hs_inferred_', 'hs_intent_', 'hs_ip_',
            'hs_is_', 'hs_job_', 'hs_journey_', 'hs_language_', 'hs_last_',
            'hs_lastmodifieddate_', 'hs_latest_', 'hs_latitude_', 'hs_lead_',
            'hs_legal_', 'hs_linkedin_', 'hs_linkedinid_', 'hs_live_',
            'hs_longitude_', 'hs_marketable_', 'hs_membership_', 'hs_merged_',
            'hs_messaging_', 'hs_mobile_', 'hs_notes_', 'hs_object_',
            'hs_owning_', 'hs_persona_', 'hs_pinned_', 'hs_pipeline_',
            'hs_predictivecontactscore_', 'hs_predictivecontactscorebucket_',
            'hs_predictivescoringtier_', 'hs_prospecting_', 'hs_quarantined_',
            'hs_read_', 'hs_recent_', 'hs_registered_', 'hs_registration_',
            'hs_returning_', 'hs_role_', 'hs_sa_', 'hs_sales_',
            'hs_searchable_', 'hs_seniority_', 'hs_sequences_', 'hs_shared_',
            'hs_social_', 'hs_source_', 'hs_state_', 'hs_sub_',
            'hs_testpurge_', 'hs_testrollback_', 'hs_time_', 'hs_timezone_',
            'hs_twitterid_', 'hs_unique_', 'hs_updated_', 'hs_user_',
            'hs_v2_', 'hs_was_', 'hs_whatsapp_'
        }
        
        # Exact field names that are readonly or system-generated
        self.READONLY_EXACT_FIELDS = {
            'createdate', 'lastmodifieddate', 'hs_object_id',
            'first_deal_created_date', 'recent_conversion_date',
            'first_conversion_date', 'recent_conversion_event_name',
            'first_conversion_event_name', 'num_conversion_events',
            'num_unique_conversion_events', 'days_to_close'
        }
        
        # Production-specific identifiers that don't exist in sandbox
        self.PRODUCTION_IDENTIFIERS = {
            'associatedcompanyid', 'hubspot_owner_id', 'hubspot_team_id',
            'hubspot_owner_assigneddate', 'hs_all_owner_ids', 'hs_all_team_ids',
            'hs_created_by_user_id', 'hs_updated_by_user_id',
            'hs_object_source_user_id', 'hs_contact_creation_legal_basis_source_instance_id',
            'hs_facebook_click_id', 'hs_google_click_id', 'hs_first_closed_order_id',
            'hs_first_engagement_object_id', 'hs_marketable_reason_id',
            'hs_object_source_id', 'hs_source_object_id', 'hs_source_portal_id',
            'hs_pinned_engagement_id', 'unific_last_draft_order_id',
            'unific_shopping_cart_customer_id', 'unific_sync_id'
        }
        
        # Fields that contain IP-based or analytics data
        self.ANALYTICS_FIELDS = {
            'ip_city', 'ip_country', 'ip_country_code', 'ip_state', 'ip_state_code',
            'ip_zipcode', 'ip_latlon'
        }
        
        # Additional prefixes for non-hs fields that are readonly
        self.OTHER_READONLY_PREFIXES = {
            'num_', 'first_', 'recent_', 'last_', 'total_'
        }
    
    def is_writable_property(self, prop: Dict[str, Any]) -> bool:
        """
        Comprehensive check if a property can be written to
        
        Args:
            prop: Property definition from HubSpot API
            
        Returns:
            True if property can be safely written to
        """
        prop_name = prop.get('name', '').lower()
        
        # Always allow core contact fields (even if marked as hubspotDefined)
        core_fields = {
            'email', 'firstname', 'lastname', 'phone', 'mobilephone', 
            'company', 'jobtitle', 'website', 'address', 'city', 
            'state', 'zip', 'country', 'lifecyclestage'
        }
        
        if prop_name in core_fields:
            return True
        
        # Skip if explicitly marked as hubspot defined, read-only, or calculated
        if prop.get('hubspotDefined', False):
            return False
            
        if prop.get('readOnlyValue', False):
            return False
            
        if prop.get('calculated', False):
            return False
        
        # Skip exact readonly field names
        if prop_name in self.READONLY_EXACT_FIELDS:
            return False
        
        # Skip production identifiers
        if prop_name in self.PRODUCTION_IDENTIFIERS:
            return False
        
        # Skip analytics fields
        if prop_name in self.ANALYTICS_FIELDS:
            return False
        
        # Skip system prefixes
        if any(prop_name.startswith(prefix) for prefix in self.SYSTEM_PREFIXES):
            return False
        
        # Skip other readonly prefixes
        if any(prop_name.startswith(prefix) for prefix in self.OTHER_READONLY_PREFIXES):
            return False
        
        # Skip any field ending with _id (likely identifiers)
        if prop_name.endswith('_id') and not prop_name in {'email', 'phone', 'mobile'}:
            return False
        
        return True
    
    def filter_contact_properties(self, contact_properties: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """
        Filter contact properties to only include writable ones
        
        Args:
            contact_properties: Dictionary of property name -> value
            is_update: True if this is for updating existing contact, False for creating new
            
        Returns:
            Filtered dictionary with only writable properties
        """
        filtered = {}
        
        for prop_name, prop_value in contact_properties.items():
            if self.is_property_name_writable(prop_name):
                # Clean the value
                cleaned_value = self.clean_property_value(prop_value)
                if cleaned_value is not None:
                    filtered[prop_name] = cleaned_value
        
        # Only remove email for updates (not for creates)
        if is_update and 'email' in filtered:
            del filtered['email']
        
        return filtered
    
    def is_property_name_writable(self, prop_name: str) -> bool:
        """
        Check if a property name is writable (simpler version without full property object)
        
        Args:
            prop_name: Property name
            
        Returns:
            True if property name suggests it's writable
        """
        prop_name_lower = prop_name.lower()
        
        # Skip exact readonly field names
        if prop_name_lower in self.READONLY_EXACT_FIELDS:
            return False
        
        # Skip production identifiers
        if prop_name_lower in self.PRODUCTION_IDENTIFIERS:
            return False
        
        # Skip analytics fields
        if prop_name_lower in self.ANALYTICS_FIELDS:
            return False
        
        # Skip system prefixes
        if any(prop_name_lower.startswith(prefix) for prefix in self.SYSTEM_PREFIXES):
            return False
        
        # Skip other readonly prefixes
        if any(prop_name_lower.startswith(prefix) for prefix in self.OTHER_READONLY_PREFIXES):
            return False
        
        # Skip any field ending with _id (likely identifiers)
        if prop_name_lower.endswith('_id') and prop_name_lower not in {'email', 'phone', 'mobile'}:
            return False
        
        return True
    
    def clean_property_value(self, value: Any) -> str | None:
        """
        Clean and validate a property value for API submission
        
        Args:
            value: Raw property value
            
        Returns:
            Cleaned string value or None if invalid
        """
        if value is None:
            return None
            
        # Convert to string and strip whitespace
        str_value = str(value).strip()
        
        # Return None for empty strings
        if not str_value or str_value.lower() in ['none', 'null', '']:
            return None
            
        return str_value
    
    def get_safe_properties_list(self, all_properties: List[Dict[str, Any]]) -> List[str]:
        """
        Get a list of property names that are safe to write to
        
        Args:
            all_properties: List of property definitions from HubSpot API
            
        Returns:
            List of property names that can be safely written to
        """
        safe_properties = []
        
        for prop in all_properties:
            if self.is_writable_property(prop):
                safe_properties.append(prop['name'])
        
        # Always include email for fetching (we'll filter it out during updates)
        if 'email' not in safe_properties:
            safe_properties.append('email')
        
        return safe_properties


class DealFieldFilter:
    """
    Deal-specific field filtering system for HubSpot deal properties
    """
    
    def __init__(self):
        # System prefixes that should never be updated in deals
        self.SYSTEM_PREFIXES = {
            'hs_additional_', 'hs_all_', 'hs_analytics_', 'hs_associated_',
            'hs_buying_', 'hs_calculated_', 'hs_clicked_', 'hs_closed_',
            'hs_createdate_', 'hs_cross_', 'hs_currently_', 'hs_customer_',
            'hs_data_', 'hs_deal_', 'hs_document_', 'hs_email_',
            'hs_first_', 'hs_forecast_', 'hs_full_', 'hs_has_',
            'hs_inferred_', 'hs_is_', 'hs_last_', 'hs_lastmodifieddate_',
            'hs_latest_', 'hs_lead_', 'hs_likelihood_', 'hs_merged_',
            'hs_next_', 'hs_notes_', 'hs_object_', 'hs_owning_',
            'hs_predictive_', 'hs_projected_', 'hs_read_', 'hs_recent_',
            'hs_sales_', 'hs_searchable_', 'hs_shared_', 'hs_source_',
            'hs_time_', 'hs_timezone_', 'hs_unique_', 'hs_updated_',
            'hs_user_', 'hs_was_'
        }
        
        # Exact field names that are readonly or system-generated for deals
        self.READONLY_EXACT_FIELDS = {
            'createdate', 'lastmodifieddate', 'hs_object_id', 'hs_deal_id',
            'num_contacted_notes', 'num_notes', 'dealid', 'deal_id',
            'days_to_close', 'closed_won_count', 'closed_lost_count',
            'first_deal_created_date', 'recent_deal_close_date'
        }
        
        # Production-specific identifiers that don't exist in sandbox
        self.PRODUCTION_IDENTIFIERS = {
            'hubspot_owner_id', 'hubspot_team_id', 'associatedcompanyids',
            'associatedvids', 'hs_all_owner_ids', 'hs_all_team_ids',
            'hs_created_by_user_id', 'hs_updated_by_user_id',
            'hs_object_source_user_id', 'hs_object_source_id',
            'hs_source_object_id', 'hs_source_portal_id',
            'hs_pinned_engagement_id', 'hs_first_engagement_object_id'
        }
        
        # Analytics and calculated fields
        self.ANALYTICS_FIELDS = {
            'hs_analytics_source', 'hs_analytics_source_data_1',
            'hs_analytics_source_data_2', 'ip_city', 'ip_country'
        }
        
        # Deal-specific readonly prefixes
        self.DEAL_READONLY_PREFIXES = {
            'num_', 'first_', 'recent_', 'last_', 'total_', 'count_',
            'days_', 'closed_', 'hs_closed_', 'hs_days_'
        }
    
    def is_writable_deal_property(self, prop: Dict[str, Any]) -> bool:
        """
        Check if a deal property can be written to
        
        Args:
            prop: Property definition from HubSpot API
            
        Returns:
            True if property can be safely written to
        """
        prop_name = prop.get('name', '').lower()
        
        # Always allow core deal fields
        core_fields = {
            'dealname', 'amount', 'closedate', 'dealtype', 
            'dealstage', 'pipeline', 'description'
        }
        
        if prop_name in core_fields:
            # Pipeline and dealstage need special handling
            if prop_name in ['pipeline', 'dealstage']:
                return True
            return True
        
        # Skip if explicitly marked as hubspot defined, read-only, or calculated
        if prop.get('hubspotDefined', False):
            return False
            
        if prop.get('readOnlyValue', False):
            return False
            
        if prop.get('calculated', False):
            return False
        
        # Skip exact readonly field names
        if prop_name in self.READONLY_EXACT_FIELDS:
            return False
        
        # Skip production identifiers
        if prop_name in self.PRODUCTION_IDENTIFIERS:
            return False
        
        # Skip analytics fields
        if prop_name in self.ANALYTICS_FIELDS:
            return False
        
        # Skip system prefixes
        if any(prop_name.startswith(prefix) for prefix in self.SYSTEM_PREFIXES):
            return False
        
        # Skip deal-specific readonly prefixes
        if any(prop_name.startswith(prefix) for prefix in self.DEAL_READONLY_PREFIXES):
            return False
        
        # Skip any field ending with _id (likely identifiers)
        if prop_name.endswith('_id') and prop_name not in core_fields:
            return False
        
        return True
    
    def get_filtered_properties(self, token, include_core_only=False) -> List[str]:
        """
        Get filtered deal properties from HubSpot API
        
        Args:
            token: HubSpot API token
            include_core_only: If True, only return core deal fields
            
        Returns:
            List of property names safe for migration
        """
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from utils.utils import get_api_headers, make_hubspot_request
        
        if include_core_only:
            return ['dealname', 'amount', 'closedate', 'dealtype', 'description']
        
        # Get all properties
        headers = get_api_headers(token)
        url = 'https://api.hubapi.com/crm/v3/properties/deals'
        
        success, data = make_hubspot_request('GET', url, headers)
        
        if not success:
            print(f"❌ Error fetching deal properties: {data}")
            return ['dealname', 'amount', 'closedate']  # Fallback to basic fields
        
        all_properties = data.get('results', [])
        filtered_properties = []
        
        for prop in all_properties:
            if self.is_writable_deal_property(prop):
                filtered_properties.append(prop['name'])
        
        # Always include basic deal identification
        essential_fields = ['dealname', 'amount', 'closedate']
        for field in essential_fields:
            if field not in filtered_properties:
                filtered_properties.append(field)
        
        return filtered_properties
    
    def clean_deal_properties(self, deal_props: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean deal properties for migration
        
        Args:
            deal_props: Dictionary of property name -> value
            
        Returns:
            Cleaned dictionary with only safe properties
        """
        cleaned = {}
        
        for prop_name, prop_value in deal_props.items():
            if self.is_property_name_writable(prop_name):
                cleaned_value = self.clean_property_value(prop_value)
                if cleaned_value is not None:
                    cleaned[prop_name] = cleaned_value
        
        return cleaned
    
    def is_property_name_writable(self, prop_name: str) -> bool:
        """
        Check if a property name is writable (without full property object)
        
        Args:
            prop_name: Property name
            
        Returns:
            True if property name suggests it's writable
        """
        prop_name_lower = prop_name.lower()
        
        # Core deal fields are always writable
        core_fields = {
            'dealname', 'amount', 'closedate', 'dealtype', 
            'pipeline', 'description'
        }
        
        if prop_name_lower in core_fields:
            return True
        
        # Skip exact readonly field names
        if prop_name_lower in self.READONLY_EXACT_FIELDS:
            return False
        
        # Skip production identifiers
        if prop_name_lower in self.PRODUCTION_IDENTIFIERS:
            return False
        
        # Skip analytics fields
        if prop_name_lower in self.ANALYTICS_FIELDS:
            return False
        
        # Skip system prefixes
        if any(prop_name_lower.startswith(prefix) for prefix in self.SYSTEM_PREFIXES):
            return False
        
        # Skip deal-specific readonly prefixes
        if any(prop_name_lower.startswith(prefix) for prefix in self.DEAL_READONLY_PREFIXES):
            return False
        
        # Skip any field ending with _id
        if prop_name_lower.endswith('_id'):
            return False
        
        return True
    
    def clean_property_value(self, value: Any) -> str | None:
        """
        Clean and validate a property value for API submission
        
        Args:
            value: Raw property value
            
        Returns:
            Cleaned string value or None if invalid
        """
        if value is None:
            return None
            
        # Convert to string and strip whitespace
        str_value = str(value).strip()
        
        # Return None for empty strings
        if not str_value or str_value.lower() in ['none', 'null', '']:
            return None
            
        return str_value