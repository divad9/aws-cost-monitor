import json
import boto3
from datetime import datetime, timedelta

def lambda_handler(event, context):
    """
    Fetches yesterday's AWS costs and prints them.
    This is Version 1 - just getting costs.
    """
    
    # Initialize Cost Explorer client
    ce = boto3.client('ce', region_name='us-east-1')
    
    # Get yesterday's date
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    day_before = yesterday - timedelta(days=1)
    
    # Format dates for Cost Explorer API
    start_date = day_before.strftime('%Y-%m-%d')
    end_date = yesterday.strftime('%Y-%m-%d')
    
    try:
        # Call Cost Explorer API
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        # Extract cost data
        results = response['ResultsByTime'][0]
        total_cost = results['Total']['UnblendedCost']['Amount']
        
        # Get top services by cost
        services = []
        for group in results['Groups']:
            service_name = group['Keys'][0]
            cost = float(group['Metrics']['UnblendedCost']['Amount'])
            if cost > 0.01:  # Only show services costing more than 1 cent
                services.append({
                    'service': service_name,
                    'cost': cost
                })
        
        # Sort by cost
        services.sort(key=lambda x: x['cost'], reverse=True)
        
        # Print results
        print(f"📊 AWS Cost Report for {yesterday}")
        print(f"Total Cost: ${float(total_cost):.2f}")
        print("\nTop Services:")
        for i, svc in enumerate(services[:5], 1):
            print(f"  {i}. {svc['service']}: ${svc['cost']:.2f}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'date': str(yesterday),
                'total_cost': float(total_cost),
                'top_services': services[:5]
            })
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }