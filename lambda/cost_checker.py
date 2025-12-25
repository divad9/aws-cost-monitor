import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

def lambda_handler(event, context):
    """
    Fetches AWS costs, stores in DynamoDB, and sends alerts.
    Supports test mode with mock data.
    """
    
    # Check if test mode is requested
    USE_TEST_DATA = event.get('use_test_data', False)
    
    if USE_TEST_DATA:
        print(" TEST MODE ACTIVATED")
        return test_mode_handler(event, context)
    
    # Normal mode - fetch real costs
    return real_cost_handler(event, context)


def save_to_dynamodb(date, total_cost, services, is_test=False):
    """
    Save cost data to DynamoDB
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('AWSCostHistory')
        
        # Convert floats to Decimal for DynamoDB
        item = {
            'date': str(date),
            'total_cost': Decimal(str(round(total_cost, 2))),
            'top_services': [
                {
                    'service': svc['service'],
                    'cost': Decimal(str(round(svc['cost'], 2)))
                }
                for svc in services[:10]  # Store top 10 services
            ],
            'timestamp': datetime.now().isoformat(),
            'is_test_data': is_test
        }
        
        table.put_item(Item=item)
        print(f" Saved to DynamoDB: {date}, ${total_cost:.2f}")
        return True
        
    except Exception as e:
        print(f" Failed to save to DynamoDB: {str(e)}")
        return False


def real_cost_handler(event, context):
    """
    Fetches real AWS costs from Cost Explorer
    """
    
    # Configuration
    COST_THRESHOLD = 5.0
    SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
    
    # Initialize clients
    ce = boto3.client('ce', region_name='us-east-1')
    sns = boto3.client('sns', region_name='us-east-1')
    
    # Get date range - last 7 days to ensure we get data
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    print(f"Fetching costs from {start_date} to {end_date}")
    
    try:
        # Fetch costs
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        print(f" Cost Explorer Response received")
        
        # Check if we have results
        if 'ResultsByTime' not in response or len(response['ResultsByTime']) == 0:
            print(" No cost data available yet")
            
            if SNS_TOPIC_ARN:
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject="AWS Cost Monitor - No Data Yet",
                    Message="No cost data available yet. This is normal for new accounts.\n\nCosts typically appear 24-48 hours after resource usage."
                )
            
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No cost data available yet'})
            }
        
        # Get the most recent day's data
        results = response['ResultsByTime'][-1]
        report_date = results['TimePeriod']['Start']
        
        print(f"Processing data for: {report_date}")
        
        # Extract total cost
        total_cost = 0.0
        if 'Total' in results and 'UnblendedCost' in results['Total']:
            total_cost = float(results['Total']['UnblendedCost']['Amount'])
        
        # Get service breakdown
        services = []
        if 'Groups' in results:
            for group in results['Groups']:
                service_name = group['Keys'][0]
                if 'Metrics' in group and 'UnblendedCost' in group['Metrics']:
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    if cost > 0.01:
                        services.append({
                            'service': service_name,
                            'cost': cost
                        })
        
        services.sort(key=lambda x: x['cost'], reverse=True)
        top_5 = services[:5]
        
        # Save to DynamoDB
        save_to_dynamodb(report_date, total_cost, services, is_test=False)
        
        # Prepare message
        message = f"""
AWS Cost Report - {report_date}
{'='*40}

Total Cost: ${total_cost:.2f}

"""
        
        if top_5:
            message += "Top Services:\n"
            for i, svc in enumerate(top_5, 1):
                message += f"{i}. {svc['service']}: ${svc['cost']:.2f}\n"
        else:
            message += "No individual service costs recorded.\n"
        
        message += f"\n💾 Cost data stored in DynamoDB"
        message += f"\nNote: Costs may take 24-48 hours to appear in Cost Explorer."
        
        # Determine if alert needed
        alert_triggered = total_cost > COST_THRESHOLD
        
        if alert_triggered:
            subject = f" AWS Cost Alert: ${total_cost:.2f}"
            message = f" ALERT: Daily cost exceeded ${COST_THRESHOLD}\n\n" + message
        else:
            subject = f"AWS Daily Cost Report: ${total_cost:.2f}"
        
        # Send SNS notification
        if SNS_TOPIC_ARN:
            try:
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject=subject,
                    Message=message
                )
                print(f" Notification sent to SNS")
            except Exception as sns_error:
                print(f" Failed to send SNS: {str(sns_error)}")
        
        print(message)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'date': report_date,
                'total_cost': total_cost,
                'top_services': top_5,
                'alert_sent': alert_triggered,
                'saved_to_db': True
            })
        }
        
    except Exception as e:
        error_msg = f" Error: {str(e)}"
        print(error_msg)
        
        if SNS_TOPIC_ARN:
            try:
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject=" AWS Cost Monitor Error",
                    Message=f"Error occurred:\n\n{str(e)}"
                )
            except:
                pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def test_mode_handler(event, context):
    """
    Returns fake cost data for testing and development
    """
    import random
    
    print("="*50)
    print(" GENERATING TEST DATA")
    print("="*50)
    
    SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
    sns = boto3.client('sns', region_name='us-east-1')
    
    # Generate realistic fake costs
    fake_services = [
        {'service': 'Amazon Elastic Compute Cloud - Compute', 'cost': random.uniform(1.0, 3.0)},
        {'service': 'Amazon Simple Storage Service', 'cost': random.uniform(0.3, 1.2)},
        {'service': 'AWS Lambda', 'cost': random.uniform(0.05, 0.4)},
        {'service': 'Amazon Relational Database Service', 'cost': random.uniform(0.5, 2.0)},
        {'service': 'Amazon CloudFront', 'cost': random.uniform(0.1, 0.6)},
        {'service': 'Amazon DynamoDB', 'cost': random.uniform(0.05, 0.3)},
        {'service': 'Amazon SNS', 'cost': random.uniform(0.01, 0.1)}
    ]
    
    # Calculate total
    total_cost = sum(svc['cost'] for svc in fake_services)
    
    # Sort by cost
    fake_services.sort(key=lambda x: x['cost'], reverse=True)
    
    # Get today's date
    today = datetime.now().date()
    
    # Save to DynamoDB
    save_to_dynamodb(today, total_cost, fake_services, is_test=True)
    
    # Build message
    message = f"""
 TEST MODE - AWS Cost Report - {today}
{'='*40}

 THIS IS SIMULATED DATA FOR TESTING

Total Cost: ${total_cost:.2f}

Top Services:
"""
    
    for i, svc in enumerate(fake_services[:5], 1):
        message += f"{i}. {svc['service']}: ${svc['cost']:.2f}\n"
    
    message += f"""
{'='*40}
 Test data stored in DynamoDB

This is test data generated for development.
Real cost data will appear here once available.
"""
    
    # Determine subject
    COST_THRESHOLD = 5.0
    if total_cost > COST_THRESHOLD:
        subject = f" TEST ALERT - Cost: ${total_cost:.2f}"
    else:
        subject = f" TEST - AWS Cost: ${total_cost:.2f}"
    
    # Send notification
    if SNS_TOPIC_ARN:
        try:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=subject,
                Message=message
            )
            print(" Test notification sent to SNS")
        except Exception as e:
            print(f" Failed to send test notification: {str(e)}")
    
    print(message)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'test_mode': True,
            'date': str(today),
            'total_cost': total_cost,
            'top_services': fake_services[:5],
            'saved_to_db': True,
            'message': 'Test data generated and stored'
        })
    }