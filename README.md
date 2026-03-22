# Terraform AWS Serverless Lab 4

## 📌 Overview

This project implements a serverless task tracker application using AWS services:

- API Gateway (HTTP API)
- AWS Lambda (Python 3.12)
- DynamoDB (task storage)
- Amazon S3 (audit logs)
- CloudWatch Logs (monitoring)

Infrastructure is provisioned using Terraform with modular architecture.

---

## ⚙️ Architecture

User → API Gateway → Lambda → DynamoDB  
                             ↘ S3 (audit logs)

---

## 🚀 Features

- POST /tasks → create task
- GET /tasks?status=open → get tasks
- PUT /tasks/{id} → update status
- Audit logging to S3

---

## 📁 Project Structure
modules/
dynamodb/
lambda/
api_gateway/
s3/

envs/dev/
main.tf
backend.tf

src/
app.py

---

## 🔧 Deployment

```bash
terraform init
terraform plan
terraform apply
```
---

## 🧪 Testing

```bash
POST /tasks
GET /tasks?status=open
PUT /tasks/{id}
```
## 🧹 Cleanup
```bash
terraform destroy -auto-approve
```