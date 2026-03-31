# Terraform AWS Serverless Labs 4–5

## 📌 Overview

This project implements a serverless task tracker application on AWS and extends it with AI-based prioritization using Amazon Comprehend.

The solution uses:

- API Gateway (HTTP API)
- AWS Lambda (Python 3.12)
- DynamoDB (task storage)
- Amazon S3 (audit logs)
- CloudWatch Logs / Monitor
- Amazon Comprehend (sentiment analysis)

Infrastructure is provisioned using Terraform with a modular structure.

---

## ⚙️ Architecture

User → API Gateway → Lambda → DynamoDB  
                             ↘ S3 (audit logs)  
                             ↘ Amazon Comprehend (sentiment analysis)

---

## 🚀 Features

### Lab 4
- `POST /tasks` → create task
- `GET /tasks?status=open` → get tasks by status
- `PUT /tasks/{id}` → update task status
- Audit logging to S3

### Lab 5
- `POST /tasks/{id}/prioritize` → analyze task description using Amazon Comprehend
- Automatic priority update based on sentiment
- Store AI analysis result in DynamoDB (`ai_sentiment`, `ai_sentiment_score`)

---

## 📁 Project Structure

```text
modules/
  dynamodb/
    main.tf
  lambda/
    main.tf
  api_gateway/
    main.tf
  s3/
    main.tf

envs/
  dev/
    main.tf
    backend.tf

src/
  app.py
```

---

## 🔧 Deployment

```bash
terraform init
terraform plan
terraform apply
```

---

## 🧪 Testing

### Lab 4

```bash
POST /tasks
GET /tasks?status=open
PUT /tasks/{id}
```

### Lab 5

```bash
POST /tasks/{id}/prioritize
```

---

## Example flow

1. Create a task with a text description
2. Call `/tasks/{id}/prioritize`
3. Check updated priority and AI sentiment in DynamoDB / API response

## 🧹 Cleanup

```bash
terraform destroy -auto-approve
```

---

## 📝 Notes

- Resource naming format: `kaparov-oleksii-04`
- Terraform state is stored in an S3 backend
- Audit logs are stored in a separate S3 bucket
- Amazon Comprehend is used through `boto3.detect_sentiment()`
- Lambda execution role follows the least privilege principle