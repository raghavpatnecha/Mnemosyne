# Cloud Deployment Guide

Comprehensive guide for deploying Mnemosyne to popular cloud platforms.

---

## Table of Contents

1. [AWS EC2 + S3](#aws-ec2--s3)
2. [DigitalOcean Droplet + Spaces](#digitalocean-droplet--spaces)
3. [Railway.app (PaaS)](#railwayapp-paas)
4. [Render.com (PaaS)](#rendercom-paas)
5. [Google Cloud Platform](#google-cloud-platform)
6. [Azure](#azure)

---

## AWS EC2 + S3

### Prerequisites
- AWS account
- AWS CLI installed
- SSH key pair

### 1. Launch EC2 Instance

```bash
# Launch Ubuntu 22.04 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.xlarge \
  --key-name your-key-pair \
  --security-groups mnemosyne-sg \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100}}]'
```

**Recommended Instance Type:**
- **Development**: t3.large (2 vCPU, 8GB RAM) - $0.0832/hour
- **Production**: t3.xlarge (4 vCPU, 16GB RAM) - $0.1664/hour
- **High Load**: c6i.2xlarge (8 vCPU, 16GB RAM) - $0.34/hour

### 2. Configure Security Group

```bash
# Create security group
aws ec2 create-security-group \
  --group-name mnemosyne-sg \
  --description "Mnemosyne API server"

# Allow HTTP
aws ec2 authorize-security-group-ingress \
  --group-name mnemosyne-sg \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Allow HTTPS
aws ec2 authorize-security-group-ingress \
  --group-name mnemosyne-sg \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Allow SSH (restrict to your IP)
aws ec2 authorize-security-group-ingress \
  --group-name mnemosyne-sg \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32
```

### 3. Create S3 Bucket

```bash
# Create S3 bucket for document storage
aws s3api create-bucket \
  --bucket mnemosyne-documents-YOUR_UNIQUE_ID \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
  --bucket mnemosyne-documents-YOUR_UNIQUE_ID \
  --versioning-configuration Status=Enabled

# Set lifecycle policy to transition old files to Glacier
aws s3api put-bucket-lifecycle-configuration \
  --bucket mnemosyne-documents-YOUR_UNIQUE_ID \
  --lifecycle-configuration file://s3-lifecycle.json
```

**s3-lifecycle.json:**
```json
{
  "Rules": [
    {
      "Id": "TransitionToGlacier",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

### 4. Create IAM User for S3 Access

```bash
# Create IAM user
aws iam create-user --user-name mnemosyne-s3

# Attach S3 policy
aws iam put-user-policy \
  --user-name mnemosyne-s3 \
  --policy-name MnemosyneS3Access \
  --policy-document file://s3-policy.json

# Create access keys
aws iam create-access-key --user-name mnemosyne-s3
```

**s3-policy.json:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::mnemosyne-documents-YOUR_UNIQUE_ID",
        "arn:aws:s3:::mnemosyne-documents-YOUR_UNIQUE_ID/*"
      ]
    }
  ]
}
```

### 5. SSH into EC2 and Deploy

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone https://github.com/yourusername/mnemosyne.git
cd mnemosyne

# Configure environment
cp .env.example .env.production
nano .env.production
```

**Update .env.production with:**
```bash
# S3 Storage
STORAGE_BACKEND=s3
S3_BUCKET_NAME=mnemosyne-documents-YOUR_UNIQUE_ID
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=your_secret_key
S3_REGION=us-east-1

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your_secret_key_here
POSTGRES_PASSWORD=your_postgres_password
REDIS_PASSWORD=your_redis_password

# OpenAI
OPENAI_API_KEY=sk-...

# Domain
DOMAIN=api.yourdomain.com
```

```bash
# Deploy
./deploy.sh
```

### 6. Configure SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone \
  -d api.yourdomain.com \
  --agree-tos \
  --email admin@yourdomain.com

# Update nginx config
sudo nano nginx/nginx.conf
# Update SSL certificate paths

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### Cost Estimate (AWS)

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| EC2 (t3.xlarge) | 4 vCPU, 16GB RAM | ~$120 |
| EBS Storage | 100GB SSD | ~$10 |
| S3 Storage | 1TB documents | ~$23 |
| Data Transfer | 1TB outbound | ~$90 |
| **Total** | | **~$243/month** |

---

## DigitalOcean Droplet + Spaces

### 1. Create Droplet

```bash
# Using doctl CLI
doctl compute droplet create mnemosyne-prod \
  --region nyc3 \
  --image ubuntu-22-04-x64 \
  --size s-4vcpu-8gb \
  --ssh-keys YOUR_SSH_KEY_ID \
  --enable-monitoring \
  --enable-ipv6
```

**Recommended Droplet Sizes:**
- **Development**: s-2vcpu-4gb ($24/month)
- **Production**: s-4vcpu-8gb ($48/month)
- **High Load**: c-8 ($96/month)

### 2. Create Spaces Bucket

```bash
# Create Spaces bucket (S3-compatible)
doctl compute spaces create mnemosyne-documents \
  --region nyc3

# Generate Spaces access keys
doctl compute spaces keys create mnemosyne-app
```

### 3. Configure DNS

```bash
# Add A record
doctl compute domain records create yourdomain.com \
  --record-type A \
  --record-name api \
  --record-data YOUR_DROPLET_IP
```

### 4. Deploy

```bash
# SSH into droplet
ssh root@your-droplet-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone and configure
git clone https://github.com/yourusername/mnemosyne.git
cd mnemosyne
cp .env.example .env.production
nano .env.production
```

**Update .env.production:**
```bash
# DigitalOcean Spaces (S3-compatible)
STORAGE_BACKEND=s3
S3_BUCKET_NAME=mnemosyne-documents
S3_ACCESS_KEY_ID=your_spaces_key
S3_SECRET_ACCESS_KEY=your_spaces_secret
S3_REGION=nyc3
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com

# Other settings...
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 32)
OPENAI_API_KEY=sk-...
```

```bash
# Deploy
./deploy.sh
```

### Cost Estimate (DigitalOcean)

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| Droplet | 4 vCPU, 8GB RAM | $48 |
| Spaces | 1TB storage | $20 |
| Bandwidth | 1TB transfer | Included |
| **Total** | | **~$68/month** |

---

## Railway.app (PaaS)

Railway is the easiest deployment option - zero DevOps required!

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### 2. Create New Project

```bash
cd mnemosyne
railway init
railway link
```

### 3. Add Services

```bash
# Add PostgreSQL
railway add postgres

# Add Redis
railway add redis

# The app will be auto-detected from Dockerfile.prod
```

### 4. Configure Environment Variables

```bash
# Set environment variables
railway variables set STORAGE_BACKEND=s3
railway variables set S3_BUCKET_NAME=your-bucket
railway variables set S3_ACCESS_KEY_ID=your-key
railway variables set S3_SECRET_ACCESS_KEY=your-secret
railway variables set S3_REGION=us-east-1
railway variables set OPENAI_API_KEY=sk-...

# Generate secrets
railway variables set SECRET_KEY=$(openssl rand -hex 32)
```

### 5. Deploy

```bash
# Deploy to Railway
railway up
```

Railway will:
- Build Docker image
- Deploy API, workers, and beat scheduler
- Provide HTTPS domain automatically
- Handle SSL certificates
- Auto-scale based on load

### Cost Estimate (Railway)

| Tier | Resources | Monthly Cost |
|------|-----------|--------------|
| Hobby | 512MB RAM per service | $5 |
| Starter | 8GB RAM total | $20 |
| **Pro** | **32GB RAM, priority support** | **$50** |

---

## Render.com (PaaS)

### 1. Create render.yaml

```yaml
services:
  - type: web
    name: mnemosyne-api
    env: docker
    dockerfilePath: ./Dockerfile.prod
    envVars:
      - key: STORAGE_BACKEND
        value: s3
      - key: S3_BUCKET_NAME
        value: mnemosyne-documents
      - key: S3_ACCESS_KEY_ID
        sync: false
      - key: S3_SECRET_ACCESS_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: mnemosyne-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: mnemosyne-redis
          type: redis
          property: connectionString

  - type: worker
    name: mnemosyne-celery
    env: docker
    dockerfilePath: ./Dockerfile.prod
    dockerCommand: celery -A backend.worker worker --loglevel=info

databases:
  - name: mnemosyne-db
    databaseName: mnemosyne
    user: mnemosyne

  - name: mnemosyne-redis
    type: redis
```

### 2. Deploy

1. Connect GitHub repository to Render
2. Select render.yaml
3. Configure environment variables in dashboard
4. Click "Deploy"

### Cost Estimate (Render)

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| Web Service | 2GB RAM | $25 |
| Worker | 2GB RAM | $25 |
| PostgreSQL | Starter | $7 |
| Redis | 256MB | $10 |
| **Total** | | **~$67/month** |

---

## Google Cloud Platform

### 1. Create GCP Project

```bash
gcloud projects create mnemosyne-prod
gcloud config set project mnemosyne-prod
```

### 2. Create GCS Bucket

```bash
gsutil mb -c standard -l us-east1 gs://mnemosyne-documents-YOUR_ID
gsutil versioning set on gs://mnemosyne-documents-YOUR_ID
```

### 3. Create Compute Engine Instance

```bash
gcloud compute instances create mnemosyne-vm \
  --machine-type=e2-standard-4 \
  --zone=us-east1-b \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --tags=http-server,https-server
```

### 4. Configure and Deploy

```bash
# SSH into instance
gcloud compute ssh mnemosyne-vm

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Deploy Mnemosyne
git clone https://github.com/yourusername/mnemosyne.git
cd mnemosyne
cp .env.example .env.production

# Update .env.production with GCS settings
nano .env.production
```

**For GCS (compatible with S3 API):**
```bash
STORAGE_BACKEND=s3
S3_BUCKET_NAME=mnemosyne-documents-YOUR_ID
S3_ENDPOINT_URL=https://storage.googleapis.com
S3_ACCESS_KEY_ID=your_gcs_hmac_key
S3_SECRET_ACCESS_KEY=your_gcs_hmac_secret
```

```bash
./deploy.sh
```

### Cost Estimate (GCP)

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| Compute Engine | e2-standard-4 | ~$120 |
| Cloud Storage | 1TB | ~$20 |
| Network Egress | 1TB | ~$120 |
| **Total** | | **~$260/month** |

---

## Azure

### 1. Create Resource Group

```bash
az group create --name mnemosyne-rg --location eastus
```

### 2. Create Storage Account

```bash
az storage account create \
  --name mnemosynestorage \
  --resource-group mnemosyne-rg \
  --location eastus \
  --sku Standard_LRS

az storage container create \
  --name documents \
  --account-name mnemosynestorage
```

### 3. Create Virtual Machine

```bash
az vm create \
  --resource-group mnemosyne-rg \
  --name mnemosyne-vm \
  --image UbuntuLTS \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys
```

### 4. Configure and Deploy

```bash
# SSH into VM
ssh azureuser@your-vm-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Deploy
git clone https://github.com/yourusername/mnemosyne.git
cd mnemosyne
cp .env.example .env.production
nano .env.production
```

**Azure Blob Storage (S3-compatible):**
```bash
STORAGE_BACKEND=s3
S3_BUCKET_NAME=documents
S3_ENDPOINT_URL=https://mnemosynestorage.blob.core.windows.net
S3_ACCESS_KEY_ID=your_azure_account_name
S3_SECRET_ACCESS_KEY=your_azure_account_key
```

```bash
./deploy.sh
```

### Cost Estimate (Azure)

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| VM | Standard_D4s_v3 | ~$140 |
| Blob Storage | 1TB | ~$18 |
| Bandwidth | 1TB | ~$90 |
| **Total** | | **~$248/month** |

---

## Cost Comparison

| Platform | Monthly Cost | Ease of Setup | Scalability | Best For |
|----------|--------------|---------------|-------------|----------|
| **Railway** | $50 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Startups, MVPs |
| **DigitalOcean** | $68 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Small-Medium business |
| **Render** | $67 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Managed deployments |
| **AWS** | $243 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Enterprise, high scale |
| **GCP** | $260 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ML workloads, BigQuery |
| **Azure** | $248 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Microsoft ecosystem |

---

## Recommendations

### For Startups (Budget: <$100/month)
→ **Railway.app** or **DigitalOcean**
- Easiest setup
- Predictable pricing
- Good performance

### For Growing Companies (Budget: $100-500/month)
→ **DigitalOcean** or **AWS**
- More control
- Better scaling options
- Managed databases available

### For Enterprise (Budget: >$500/month)
→ **AWS**, **GCP**, or **Azure**
- Advanced features (VPC, IAM, compliance)
- Multi-region deployment
- Dedicated support

---

## Next Steps

After deployment:

1. **Configure DNS** to point to your server
2. **Set up SSL** with Let's Encrypt
3. **Enable backups** (automated daily backups)
4. **Set up monitoring** (Grafana + Prometheus included)
5. **Test API endpoints**
6. **Configure rate limiting** (already included)
7. **Set up alerts** (optional)

See [deployment.md](deployment.md) for detailed post-deployment configuration.
