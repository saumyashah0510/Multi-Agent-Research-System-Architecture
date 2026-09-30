# AWS DevOps & Infrastructure as Code (Terraform) Guide

This guide documents the complete automated AWS Cloud infrastructure deployment for the **Multi-Agent Research & Literature Review Assistant** using **Terraform (IaC)**, **AWS EC2**, **AWS Elastic IP**, and **AWS S3**.

---

## 🏛️ Infrastructure Overview

```text
               ┌───────────────────────────────┐
               │    AWS Elastic IP (Static)    │
               └───────────────┬───────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS EC2 Server Instance (t3.micro in ap-south-1)            │
│   ├── Docker & Docker Compose Plugin                        │
│   ├── FastAPI Backend Container (Port 8000)                 │
│   └── Next.js / React Frontend Container (Port 3000)        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                Database Queries│ & S3 PDF Storage
                               ▼
                ┌─────────────────────────────┐
                │ Managed Neon PostgreSQL     │
                │ AWS S3 PDF Bucket           │
                └─────────────────────────────┘
```

---

## 🌐 Live AWS Cloud Application Endpoints

When the EC2 server instance is running, the application is accessible via your permanent AWS Elastic IP (`13.207.232.123`):

- **Frontend User Interface**: 👉 `http://13.207.232.123:3000`
- **FastAPI Backend Health Check**: 👉 `http://13.207.232.123:8000/api/v1/health`
- **FastAPI Interactive API Documentation**: 👉 `http://13.207.232.123:8000/docs`

---

## 🛠️ Key Terraform Resources Configured

1. **Remote State Backend (`terraform/providers.tf`)**:
   - Stores `terraform.tfstate` remotely in AWS S3 (`multi-agent-research-tfstate-233171357958`) in `ap-south-1`.
   - Uses native S3 lockfiles (`use_lockfile = true`) for concurrent state locking.

2. **AWS S3 PDF & Report Bucket (`terraform/main.tf`)**:
   - Globally unique bucket name: `multi-agent-research-pdf-bucket-233171357958`.
   - Includes CORS configuration allowing web asset downloads.

3. **AWS Security Group (`aws_security_group.ec2_sg`)**:
   - Ingress Rules: SSH (`22`), HTTP (`80`), HTTPS (`443`), Backend API (`8000`), Frontend UI (`3000`).

4. **AWS EC2 Instance (`aws_instance.web_server`)**:
   - `t3.micro` instance running Ubuntu 24.04 LTS (100% AWS Free Tier eligible).
   - Automated startup script (`user_data`) installing Docker & Docker Compose automatically.

5. **AWS Elastic IP (`aws_eip.web_eip`)**:
   - Permanent, static public IPv4 address associated with the EC2 instance.

---

## 💻 Step-by-Step Command Reference

### 1. Initialize Terraform & Remote State
```bash
cd terraform
terraform init -reconfigure
```

### 2. View Execution Plan
```bash
terraform plan
```

### 3. Apply Infrastructure (Spin Up AWS Cloud)
```bash
terraform apply -auto-approve
```

### 4. Destroy Infrastructure (Pause AWS Costs)
```bash
terraform destroy -auto-approve
```

---

## 🔒 Security & Best Practices
- **No Private Keys in Git**: SSH keys (`ec2_key.pem`) and `.tfstate` files are automatically ignored via `.gitignore`.
- **AWS Free Tier Optimized**: Uses `t3.micro` server and attached Elastic IP.
