#!/usr/bin/env python
"""
Deal Structure Analyzer
Analyzes deals, properties, and pipelines in HubSpot to understand migration requirements
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils import load_env_config, get_api_headers, make_hubspot_request
import json
from datetime import datetime

def analyze_deal_properties(token):
    """Analyze all deal properties"""
    print("📋 Analyzing Deal Properties...")
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/properties/deals'
    
    success, data = make_hubspot_request('GET', url, headers)
    
    if not success:
        print(f"❌ Error fetching deal properties: {data}")
        return {}
    
    properties = data.get('results', [])
    
    # Categorize properties
    standard_props = []
    custom_props = []
    readonly_props = []
    calculated_props = []
    
    for prop in properties:
        prop_name = prop.get('name', '')
        
        if prop.get('calculated', False):
            calculated_props.append(prop_name)
        elif prop.get('readOnlyValue', False):
            readonly_props.append(prop_name)
        elif prop.get('hubspotDefined', False):
            standard_props.append(prop_name)
        else:
            custom_props.append(prop_name)
    
    print(f"✅ Found {len(properties)} total deal properties:")
    print(f"   📊 Standard properties: {len(standard_props)}")
    print(f"   🔧 Custom properties: {len(custom_props)}")
    print(f"   🔒 Read-only properties: {len(readonly_props)}")
    print(f"   🧮 Calculated properties: {len(calculated_props)}")
    
    if custom_props:
        print(f"\n🔧 Custom Properties ({len(custom_props)}):")
        for prop in custom_props[:10]:  # Show first 10
            print(f"   • {prop}")
        if len(custom_props) > 10:
            print(f"   ... and {len(custom_props) - 10} more")
    
    return {
        'total': len(properties),
        'standard': standard_props,
        'custom': custom_props,
        'readonly': readonly_props,
        'calculated': calculated_props,
        'all_properties': properties
    }

def analyze_deal_pipelines(token):
    """Analyze deal pipelines and stages"""
    print("\n📊 Analyzing Deal Pipelines...")
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/pipelines/deals'
    
    success, data = make_hubspot_request('GET', url, headers)
    
    if not success:
        print(f"❌ Error fetching deal pipelines: {data}")
        return {}
    
    pipelines = data.get('results', [])
    
    print(f"✅ Found {len(pipelines)} deal pipelines:")
    
    pipeline_analysis = {}
    
    for pipeline in pipelines:
        pipeline_id = pipeline.get('id')
        pipeline_label = pipeline.get('label', 'Unnamed Pipeline')
        stages = pipeline.get('stages', [])
        
        print(f"\n📈 Pipeline: {pipeline_label} (ID: {pipeline_id})")
        print(f"   🎯 Stages: {len(stages)}")
        
        stage_info = []
        for stage in stages:
            stage_label = stage.get('label', 'Unnamed Stage')
            stage_probability = stage.get('metadata', {}).get('probability', 'N/A')
            print(f"      • {stage_label} (Probability: {stage_probability})")
            stage_info.append({
                'id': stage.get('id'),
                'label': stage_label,
                'probability': stage_probability,
                'metadata': stage.get('metadata', {})
            })
        
        pipeline_analysis[pipeline_id] = {
            'label': pipeline_label,
            'stages': stage_info,
            'full_data': pipeline
        }
    
    return pipeline_analysis

def analyze_sample_deals(token, limit=10):
    """Analyze a sample of deals to understand structure"""
    print(f"\n💼 Analyzing Sample Deals (limit: {limit})...")
    headers = get_api_headers(token)
    url = 'https://api.hubapi.com/crm/v3/objects/deals'
    
    # Get basic deal properties for analysis
    basic_props = ['dealname', 'amount', 'closedate', 'dealstage', 'pipeline', 'hubspot_owner_id', 'createdate']
    
    params = {
        'limit': limit,
        'properties': ','.join(basic_props),
        'associations': 'contacts,companies'
    }
    
    success, data = make_hubspot_request('GET', url, headers, params=params)
    
    if not success:
        print(f"❌ Error fetching sample deals: {data}")
        return {}
    
    deals = data.get('results', [])
    
    print(f"✅ Analyzed {len(deals)} sample deals:")
    
    # Analyze deal structure
    has_contacts = 0
    has_companies = 0
    has_amount = 0
    pipelines_used = set()
    stages_used = set()
    
    for deal in deals:
        props = deal.get('properties', {})
        associations = deal.get('associations', {})
        
        # Check associations
        if associations.get('contacts', {}).get('results'):
            has_contacts += 1
        if associations.get('companies', {}).get('results'):
            has_companies += 1
        
        # Check amount
        if props.get('amount'):
            has_amount += 1
        
        # Track pipelines and stages
        if props.get('pipeline'):
            pipelines_used.add(props.get('pipeline'))
        if props.get('dealstage'):
            stages_used.add(props.get('dealstage'))
    
    print(f"   👥 Deals with contact associations: {has_contacts}/{len(deals)} ({has_contacts/len(deals)*100:.1f}%)")
    print(f"   🏢 Deals with company associations: {has_companies}/{len(deals)} ({has_companies/len(deals)*100:.1f}%)")
    print(f"   💰 Deals with amount values: {has_amount}/{len(deals)} ({has_amount/len(deals)*100:.1f}%)")
    print(f"   📊 Unique pipelines used: {len(pipelines_used)}")
    print(f"   🎯 Unique stages used: {len(stages_used)}")
    
    # Show sample deal
    if deals:
        print(f"\n💼 Sample Deal Structure:")
        sample_deal = deals[0]
        print(f"   Deal Name: {sample_deal.get('properties', {}).get('dealname', 'N/A')}")
        print(f"   Amount: {sample_deal.get('properties', {}).get('amount', 'N/A')}")
        print(f"   Stage: {sample_deal.get('properties', {}).get('dealstage', 'N/A')}")
        print(f"   Pipeline: {sample_deal.get('properties', {}).get('pipeline', 'N/A')}")
        
        # Show associations
        associations = sample_deal.get('associations', {})
        if associations:
            contacts = associations.get('contacts', {}).get('results', [])
            companies = associations.get('companies', {}).get('results', [])
            print(f"   Associated Contacts: {len(contacts)}")
            print(f"   Associated Companies: {len(companies)}")
    
    return {
        'total_deals': len(deals),
        'contact_associations': has_contacts,
        'company_associations': has_companies,
        'has_amounts': has_amount,
        'pipelines_used': list(pipelines_used),
        'stages_used': list(stages_used),
        'sample_deals': deals
    }

def save_analysis_report(properties_analysis, pipelines_analysis, deals_analysis):
    """Save comprehensive analysis report"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    report = {
        'timestamp': timestamp,
        'analysis_date': datetime.now().isoformat(),
        'summary': {
            'total_properties': properties_analysis.get('total', 0),
            'custom_properties': len(properties_analysis.get('custom', [])),
            'total_pipelines': len(pipelines_analysis),
            'sample_deals_analyzed': deals_analysis.get('total_deals', 0)
        },
        'properties': properties_analysis,
        'pipelines': pipelines_analysis,
        'deals': deals_analysis
    }
    
    # Ensure reports directory exists
    os.makedirs('reports', exist_ok=True)
    
    report_file = f'reports/deal_analysis_{timestamp}.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Analysis report saved: {report_file}")
    return report_file

def main():
    """Main analysis function"""
    print("🔍 HubSpot Deal Analysis Tool")
    print("=" * 50)
    
    # Load configuration
    config = load_env_config()
    prod_token = config.get('HUBSPOT_PROD_API_KEY')
    
    if not prod_token:
        print("❌ Error: HUBSPOT_PROD_API_KEY not found in .env file")
        return
    
    print(f"🔐 Using production token: {prod_token[:15]}...")
    print()
    
    # Run analyses
    properties_analysis = analyze_deal_properties(prod_token)
    pipelines_analysis = analyze_deal_pipelines(prod_token)
    deals_analysis = analyze_sample_deals(prod_token, limit=20)
    
    # Save report
    report_file = save_analysis_report(properties_analysis, pipelines_analysis, deals_analysis)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"✅ Deal properties analyzed: {properties_analysis.get('total', 0)}")
    print(f"✅ Custom properties found: {len(properties_analysis.get('custom', []))}")
    print(f"✅ Pipelines analyzed: {len(pipelines_analysis)}")
    print(f"✅ Sample deals analyzed: {deals_analysis.get('total_deals', 0)}")
    print(f"📄 Full report saved: {report_file}")
    print()
    print("🚀 Ready to build deal migration system!")

if __name__ == "__main__":
    main()