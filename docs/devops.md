# DevOps & Cloud Infrastructure

This document serves as the complete operational guide for DevOps and Cloud Engineers managing containerization, CI/CD pipelines, Terraform infrastructure, and cloud deployments for the Multi-Agent Research Assistant.

## 📌 Table of Contents
1. [Purpose & Scope](#1-purpose--scope)
2. [Infrastructure Architecture](#2-infrastructure-architecture)
3. [Terraform Infrastructure-as-Code (IaC)](#3-terraform-infrastructure-as-code-iac)
4. [Containerized Services Table](#4-containerized-services-table)
5. [Dockerfile Specifications](#5-dockerfile-specifications)
6. [Docker Management Commands](#6-docker-management-commands)
7. [Manual Non-Docker Startup Order](#7-manual-non-docker-startup-order)
8. [Environment Variables & Secrets](#8-environment-variables--secrets)
9. [CI/CD Pipelines (GitHub Actions)](#9-cicd-pipelines-github-actions)
10. [Environments & Configuration](#10-environments--configuration)
11. [Deployment & Rollback Procedures](#11-deployment--rollback-procedures)
12. [Monitoring, Logging & Health Checks](#12-monitoring-logging--health-checks)
13. [Database Backup & Migration Commands](#13-database-backup--migration-commands)
14. [Common Troubleshooting Issues](#14-common-troubleshooting-issues)
15. [Pre-Deployment Checklist](#15-pre-deployment-checklist)
16. [Open Questions & Code Mismatches](#16-open-questions--code-mismatches)

---

## 1. Purpose & Scope

This guide defines the cloud infrastructure, Docker containerization, Terraform AWS provisioning, GitHub Actions CI/CD automation, and database administration procedures required to run the production system.

---

## 2. Infrastructure Architecture

```mermaid
flowchart TD
    classDef client fill:#2563eb,color:#fff,stroke:#1d4ed8,stroke-width:2px;
    classDef container fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef db fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;
    classDef external fill:#d97706,color:#fff,stroke:#b45309,stroke-width:2px;
    classDef iac fill:#7c3aed,color:#fff,stroke:#6d28d9,stroke-width:2px;

    TF[Terraform IaC Provisioner]:::iac -->|Provisions EC2, EIP, S3 & SG| EC2_Server
    Client[Browser User]:::client -->|Port 3000| Frontend[React / Nginx Container]:::container
    Client -->|Port 8000 REST & WS| Backend[FastAPI Backend Container]:::container
    Frontend -->|API Requests| Backend

    subgraph EC2_Server ["AWS EC2 Host Server"]
        direction TB
        Backend --> LangGraph[LangGraph 9-Agent Pipeline]:::container
    end

    LangGraph -->|RAG Cosine Search| NeonDB[(PostgreSQL + pgvector)]:::db
    LangGraph -->|Pub/Sub & Caching| Redis[(Redis Server)]:::db
    LangGraph -->|PDF File Storage| S3[(AWS S3 Bucket)]:::db
    LangGraph -->|LLM Inference| Gemini[Google Gemini AI Studio API]:::external
    LangGraph -->|Academic Search| AcademicAPIs[ArXiv / PubMed / OpenAlex / Crossref]:::external
```

---

## 3. Terraform Infrastructure-as-Code (IaC)

Infrastructure provisioning is automated using HCL code located in [terraform/](../terraform/).

### Provisioned AWS Resources

| Resource Identifier | Terraform Resource Type | Configuration Details | Purpose |
| :--- | :--- | :--- | :--- |
| `pdf_storage` | `aws_s3_bucket` | `force_destroy = true`, CORS enabled | S3 storage bucket for research paper PDFs & reports |
| `ec2_sg` | `aws_security_group` | Ingress ports: `22` (SSH), `80` (HTTP), `443` (HTTPS), `3000` (React), `8000` (FastAPI) | AWS EC2 firewall security group |
| `ec2_key` / `generated_key` | `tls_private_key` / `aws_key_pair` | RSA 4096-bit key pair (`ec2_key.pem`) | Automated SSH authentication key creation |
| `web_server` | `aws_instance` | `t3.micro`, Canonical Ubuntu 24.04 LTS AMI (`ap-south-1`) | EC2 virtual server running Docker runtime |
| `web_eip` | `aws_eip` | Attached to `web_server` | Static permanent Elastic IPv4 address (`13.207.232.123`) |

Defined in [terraform/main.tf](../terraform/main.tf).

### Terraform CLI Commands

```bash
# Navigate to terraform directory
cd terraform

# Initialize AWS provider and modules
terraform init

# Validate HCL syntax and preview plan
terraform plan

# Apply infrastructure changes
terraform apply -auto-approve

# View outputs (Elastic IP, S3 bucket name, SSH key path)
terraform output
```

---

## 4. Containerized Services Table

| Service | Docker Image | Host Port | Internal Port | Dependencies | Volumes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **frontend** | `multi-agent-frontend:latest` | `3000` | `3000` | `backend` | None |
| **backend** | `multi-agent-backend:latest` | `8000` | `8000` | PostgreSQL, Redis | None |
| **postgres** | `pgvector/pgvector:pg16` | `5432` | `5432` | None | `postgres_data:/var/lib/postgresql/data` |
| **redis** | `redis:alpine` | `6379` | `6379` | None | `redis_data:/data` |

Defined in [docker-compose.yml](../docker-compose.yml#L1-L27).

---

## 5. Dockerfile Specifications

### a) Backend Dockerfile ([backend/Dockerfile](../backend/Dockerfile))

| Stage / Step | Instruction | Purpose |
| :--- | :--- | :--- |
| **Base Image** | `FROM python:3.11-slim` | Minimal Python runtime environment |
| **Env Flags** | `ENV PYTHONUNBUFFERED=1` | Direct terminal logging without buffering |
| **Dependencies** | `RUN pip install --no-cache-dir -r requirements.txt` | Installs FastAPI, SQLAlchemy, LangGraph, Scikit-Learn |
| **Application Code**| `COPY app/ app/` | Copies backend application source code |
| **Entrypoint** | `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` | ASGI Uvicorn server launcher |

### b) Frontend Dockerfile ([frontend/Dockerfile](../frontend/Dockerfile))

| Stage / Step | Instruction | Purpose |
| :--- | :--- | :--- |
| **Build Stage** | `FROM node:20-alpine AS builder` | Compiles React TSX assets into static JS/CSS |
| **Compile Command**| `RUN npm run build` | Executes Vite production build outputting to `/app/dist` |
| **Runtime Stage** | `FROM nginx:alpine` | Production Nginx web server |
| **Nginx Routing** | `try_files $uri $uri/ /index.html;` | Handles Client-Side React Router single page routing |
| **Entrypoint** | `CMD ["nginx", "-g", "daemon off;"]` | Runs foreground Nginx process |

---

## 6. Docker Management Commands

```bash
# Build and launch container stack in detached mode
docker compose up --build -d

# Stop and remove running container stack
docker compose down

# Follow live container log streams
docker compose logs -f

# Follow specific service logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild a specific service without cache
docker compose build --no-cache backend

# Execute an interactive shell inside backend container
docker compose exec backend bash
```

---

## 7. Manual Non-Docker Startup Order

| Step # | Target Service | Startup Command | Verification |
| :---: | :--- | :--- | :--- |
| **1** | **Redis Server** | `redis-server` | `redis-cli ping` $\rightarrow$ `PONG` |
| **2** | **PostgreSQL + pgvector**| Cloud Neon DB or `pg_ctl start` | `psql -c "SELECT * FROM pg_extension WHERE extname='vector';"` |
| **3** | **FastAPI Backend** | `cd backend && uvicorn app.main:app --reload` | `curl http://localhost:8000/api/v1/health` |
| **4** | **React Frontend** | `cd frontend && npm run dev` | Open `http://localhost:3000` in browser |

---

## 8. Environment Variables & Secrets

| Variable Name | Service | Secret? | Storage Location |
| :--- | :--- | :---: | :--- |
| `DATABASE_URL` | Backend | **Yes** | Root `.env` / GitHub Secret `DATABASE_URL` |
| `REDIS_URL` | Backend | **Yes** | Root `.env` / GitHub Secret `REDIS_URL` |
| `GEMINI_API_KEY` | Backend | **Yes** | Root `.env` / GitHub Secret `GEMINI_API_KEY` |
| `VITE_API_URL` | Frontend | No | `frontend/.env` / Environment Variable |
| `AWS_ACCESS_KEY_ID` | Terraform / CI | **Yes** | GitHub Secrets |
| `AWS_SECRET_ACCESS_KEY` | Terraform / CI | **Yes** | GitHub Secrets |
| `EC2_HOST` | Deployment CI | **Yes** | GitHub Secret (`13.207.232.123`) |
| `EC2_SSH_KEY` | Deployment CI | **Yes** | GitHub Secret (RSA Private Key) |

---

## 9. CI/CD Pipelines (GitHub Actions)

### a) CI Pipeline Workflow (`.github/workflows/ci.yml`)

```mermaid
flowchart LR
    Push[Git Push / PR to main] --> Checkout[Checkout Code]
    Checkout --> Setup[Setup Python 3.11]
    Setup --> DB_Container[Launch pgvector/pgvector:pg16 Container]
    DB_Container --> Ruff[1. Ruff Code Quality Check]
    Ruff --> Black[2. Black Formatting Verification]
    Black --> Bandit[3. Bandit Security Vulnerability Scan]
    Bandit --> Pytest[4. Pytest Test Suite Execution]
```

| Step # | CI Job Step | Action Command | Purpose |
| :---: | :--- | :--- | :--- |
| **1** | **Ruff Linting** | `ruff check backend/app` | Enforces code quality and catches syntax issues |
| **2** | **Black Formatting** | `black --check backend/app` | Verifies consistent code formatting |
| **3** | **Bandit Security** | `bandit -r backend/app -ll` | Performs static security vulnerability scanning |
| **4** | **Pytest Test Suite** | `pytest backend/tests -v` | Executes 100% of backend unit & integration tests |

### b) CD Deployment Workflow (`.github/workflows/deploy.yml`)

1. **Trigger**: Push to `main` branch.
2. **AWS Authentication**: Authenticates with AWS credentials via `aws-actions/configure-aws-credentials@v4`.
3. **Instance Check**: Verifies EC2 state using AWS CLI (`aws ec2 describe-instances`); automatically starts instance if stopped.
4. **SSH Deployment**: Connects via `appleboy/ssh-action`, pulls latest `main`, updates `.env`, and executes `docker compose up --build -d`.

---

## 10. Environments & Configuration

| Environment | Host URL / Endpoint | Infrastructure Details |
| :--- | :--- | :--- |
| **Development** | `http://localhost:3000` | Local machine, Uvicorn auto-reload, local `.env` |
| **Staging / CI** | GitHub Actions Runner | Ephemeral PostgreSQL container (`pgvector/pgvector:pg16`) |
| **Production** | `http://13.207.232.123:3000` | AWS EC2 (`t3.micro`), Neon Cloud DB, Redis, AWS S3 Bucket |

---

## 11. Deployment & Rollback Procedures

### Automated Production Deployment

```bash
# Push commits to main branch to trigger deployment workflow
git checkout main
git pull origin main
git merge feature/your-feature-name
git push origin main
```

### Manual Emergency Rollback via SSH

```bash
# Connect to production EC2 instance
ssh -i terraform/ec2_key.pem ubuntu@13.207.232.123

# Navigate to application directory and checkout stable commit hash
cd /home/ubuntu/app
git checkout <previous_stable_commit_hash>

# Rebuild and restart containers
docker compose up --build -d
```

---

## 12. Monitoring, Logging & Health Checks

- **Application Health Check**: `GET http://13.207.232.123:8000/api/v1/health` returns status of database and Redis connections.
- **Backend Logs**: `docker compose logs -f backend`
- **Frontend Nginx Logs**: `docker compose logs -f frontend`
- **AWS CloudWatch & EC2 Status**: CPU and Network utilization monitored via AWS EC2 Dashboard.

---

## 13. Database Backup & Migration Commands

```bash
# PostgreSQL Cloud DB Dump
pg_dump "postgresql://postgres:pass@host:5432/multi_agent_db" -F c -b -v -f backup.dump

# Restore PostgreSQL Database Dump
pg_restore -h <host> -U <user> -d <dbname> -v backup.dump

# Verify pgvector extension initialization
psql "postgresql://postgres:pass@host:5432/multi_agent_db" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 14. Common Troubleshooting Issues

| Problem | Cause | Fix |
| :--- | :--- | :--- |
| `Port 8000 / 3000 in use error` | Existing process occupying server ports | Kill process using `fuser -k 8000/tcp` or `Stop-Process` |
| `SSH connection refused` | EC2 Security group missing port 22 or server stopped | Verify security group rules in [terraform/main.tf](../terraform/main.tf#L31-L36) |
| `pgvector extension missing` | Standard Postgres image used instead of `pgvector` | Update docker image to `pgvector/pgvector:pg16` |

---

## 15. Pre-Deployment Checklist

- [ ] All CI status checks passed on GitHub (`ruff`, `black`, `bandit`, `pytest`).
- [ ] Terraform infrastructure applied and verified in `ap-south-1`.
- [ ] Production `.env` secrets (`DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`) set on EC2 host.
- [ ] Verified open ports 8000, 3000, 22 in AWS Security Group.

---

## 16. Open Questions & Code Mismatches

| Topic | Codebase Value | Implementation Plan Value | Action Required |
| :--- | :--- | :--- | :--- |
| **Frontend Production Port** | Nginx listens on `:3000` in [frontend/Dockerfile](../frontend/Dockerfile#L17) | HTTP `:80` / HTTPS `:443` | Configure Nginx reverse proxy or AWS Application Load Balancer for port 80/443 |
| **EC2 Server Instance Type** | `t3.micro` in [terraform/main.tf](../terraform/main.tf#L107) | Standard Cloud Instance | Monitor RAM usage during heavy local sentence-transformers model embeddings |
