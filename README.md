#  AWS Cost Monitor

> A serverless cost monitoring and alerting system that tracks AWS spending, stores historical data, and sends email alerts when costs exceed thresholds.

[![AWS](https://img.shields.io/badge/AWS-Serverless-FF9900?style=flat&logo=amazon-aws)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase%203%20Complete-success)](https://github.com/yourusername/aws-cost-monitor)

##  Problem Statement

Cloud costs can spiral quickly, and surprise AWS bills are a common nightmare. While CloudWatch provides basic billing alarms, they lack:
- Service-level cost breakdowns
- Historical data storage
- Custom alerting logic
- Detailed notification content

**This project solves that.**

##  Features

-  **Daily Cost Tracking** - Automatically fetches AWS costs via Cost Explorer API
-  **Email Alerts** - Sends notifications when spending exceeds configurable thresholds
-  **Historical Storage** - Stores cost data in DynamoDB for trend analysis
-  **Service Breakdown** - Shows exactly which AWS services are costing money
-  **Test Mode** - Includes mock data generation for safe development
-  **Secure** - Implements least-privilege IAM policies
-  **Cost Efficient** - Operates at < $1/month

##  Architecture

```
Manual Trigger → Lambda (Python) → Cost Explorer API
                    ↓                      ↓
                DynamoDB              Service Costs
                    ↓
                SNS → Email Alert
```

**Components:**
- **AWS Lambda** - Python 3.12 function for cost processing
- **DynamoDB** - NoSQL database for historical cost storage
- **SNS** - Simple Notification Service for email delivery
- **Cost Explorer API** - Retrieves AWS billing data
- **IAM** - Least-privilege security policies
- **CloudWatch Logs** - Monitoring and debugging

##  Results

**Before:** 
-  Received $47 surprise bill from forgotten resources
-  No visibility into service-level costs
-  Manual cost checking required

**After:**
-  Real-time cost monitoring
-  Automated daily email reports
-  Historical cost trends stored
-  Prevented multiple surprise billing incidents
-  Operates at < $1/month

##  Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Basic familiarity with AWS services

### Setup (15 minutes)

#### 1. Create DynamoDB Table

```bash
aws dynamodb create-table \
    --table-name AWSCostHistory \
    --attribute-definitions AttributeName=date,AttributeType=S \
    --key-schema AttributeName=date,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
```

#### 2. Create SNS Topic

```bash
# Create topic
aws sns create-topic --name CostAlertTopic

# Subscribe your email
aws sns subscribe \
    --topic-arn arn:aws:sns:REGION:ACCOUNT_ID:CostAlertTopic \
    --protocol email \
    --notification-endpoint your-email@example.com

# Confirm subscription via email
```

#### 3. Create Lambda Function

**Create IAM role first:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "sns:Publish",
        "dynamodb:PutItem",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**Deploy Lambda:**

```bash
# Package the Lambda function
cd lambda
zip function.zip cost_checker.py

# Create Lambda function
aws lambda create-function \
    --function-name CostCheckerFunction \
    --runtime python3.12 \
    --role arn:aws:iam::ACCOUNT_ID:role/your-lambda-role \
    --handler cost_checker.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 60 \
    --environment Variables={SNS_TOPIC_ARN=arn:aws:sns:REGION:ACCOUNT_ID:CostAlertTopic}
```

#### 4. Test It

```bash
# Test with real data
aws lambda invoke \
    --function-name CostCheckerFunction \
    --payload '{}' \
    response.json

# Test with mock data
aws lambda invoke \
    --function-name CostCheckerFunction \
    --payload '{"use_test_data": true}' \
    response.json
```

Check your email! 📧

##  Project Structure

```
aws-cost-monitor/
├── lambda/
│   └── cost_checker.py          # Main Lambda function
├── docs/
│   ├── SETUP.md                 # Detailed setup guide
│   └── ARCHITECTURE.md          # Architecture deep dive
├── diagrams/
│   └── architecture.png         # Visual architecture diagram
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

##  Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SNS_TOPIC_ARN` | ARN of SNS topic for alerts | Yes |

### Cost Threshold

Edit `COST_THRESHOLD` in `lambda/cost_checker.py`:

```python
COST_THRESHOLD = 5.0  # Alert if daily cost exceeds $5
```

### Test Mode

Invoke Lambda with test data:

```json
{
  "use_test_data": true
}
```

##  Email Alert Example

**Subject:** AWS Daily Cost Report: $3.47

**Body:**
```
AWS Cost Report - 2024-12-25
========================================

Total Cost: $3.47

Top Services:
1. Amazon Simple Storage Service: $1.23
2. AWS Lambda: $0.89
3. Amazon DynamoDB: $0.67
4. Amazon SNS: $0.34
5. Amazon CloudFront: $0.34

 Cost data stored in DynamoDB
Note: Costs may take 24-48 hours to appear in Cost Explorer.
```

##  What I Learned

Building this project taught me:
- Serverless architecture patterns
- AWS Cost Explorer API intricacies
- DynamoDB data modeling with Decimal types
- IAM least-privilege policy design
- SNS notification formatting
- Lambda error handling best practices
- CloudWatch Logs debugging techniques

##  Current Limitations

- Manual trigger required (Phase 4 will add EventBridge automation)
- Email-only notifications (could add Slack, SMS)
- Basic threshold alerting (could add anomaly detection)
- No web dashboard (coming in Phase 4B)

##  Roadmap

### Phase 4 Options (Vote in Issues!)

- [ ] **Option A:** EventBridge automation for daily triggers
- [ ] **Option B:** Interactive web dashboard with charts
- [ ] **Option C:** Terraform Infrastructure as Code

### Future Enhancements

- [ ] Multi-account support
- [ ] Cost forecasting
- [ ] Budget tracking
- [ ] Slack integration
- [ ] Cost optimization recommendations
- [ ] Tagging-based cost analysis
- [ ] Weekly/monthly summary reports

##  Cost Breakdown

**Monthly Operating Costs:**

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 30 invocations/month | $0.00 (free tier) |
| DynamoDB | ~30 writes/month | $0.00 (free tier) |
| SNS | 30 emails/month | $0.00 (free tier) |
| Cost Explorer API | 30 calls/month | $0.30 |
| **Total** | | **< $1/month** |

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Acknowledgments

- Built as part of my AWS Solutions Architect learning journey
- Inspired by real-world cloud cost management challenges
- Thanks to the AWS community for documentation and support

##  Contact

**Babayo David Buba**
- Email: davidbabayo94@gmail.com
- LinkedIn: [Connect with me](www.linkedin.com/in/david-babayo)
- Location: Abuja, Nigeria

---

**Built with ❤️ and ☕ in Abuja, Nigeria**