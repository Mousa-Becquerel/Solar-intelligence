# 🚀 Quick AWS Deployment Setup

## 📋 Prerequisites Setup

### 1. Install Required Tools
```bash
# Install AWS CLI
pip install awscli

# Install Docker Desktop (Windows)
# Download from: https://docs.docker.com/desktop/install/windows-install/

# Verify installations
aws --version
docker --version
```

### 2. Configure AWS Credentials
```bash
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region (e.g., us-east-1)
# - Default output format (json)
```

## 🎯 Deploy to AWS (3 Steps)

### Step 1: Prepare for Deployment
```bash
cd Weaviate_datahub/cursor_langchain_enhanced

# Test locally first (optional)
docker build -t module-prices-agent .
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key module-prices-agent
```

### Step 2: Run Deployment Script
```bash
# On Windows PowerShell
./deploy.sh

# On WSL/Linux/Mac
bash deploy.sh
```

### Step 3: Access Your Service
After deployment completes, you'll see:
```
🎉 Deployment successful!
📍 Your service is available at: http://X.X.X.X:5000
🏥 Health check: http://X.X.X.X:5000/health
```

## 💰 Expected Costs

| Deployment Option | Monthly Cost | RAM | CPU |
|------------------|--------------|-----|-----|
| **ECS Fargate** (Recommended) | $50-100 | 2GB | 1 vCPU |
| **EC2 t3.medium** | $25-40 | 4GB | 2 vCPU |
| **App Runner** | $35-50 | 2GB | 1 vCPU |

*Based on your memory test: peak usage ~400MB, recommended 2GB with safety margin*

## 🔧 Troubleshooting

### Common Issues:

1. **AWS Credentials Error**
   ```bash
   aws sts get-caller-identity  # Test credentials
   ```

2. **Docker Build Fails**
   ```bash
   # Check if Docker is running
   docker version
   ```

3. **Service Won't Start**
   ```bash
   # Check logs
   aws logs tail /ecs/module-prices-agent --follow
   ```

4. **Health Check Fails**
   ```bash
   # Test health endpoint
   curl http://your-ip:5000/health
   ```

## 📊 Monitor Your Service

```bash
# Check service status
aws ecs describe-services --cluster module-prices-cluster --services module-prices-service

# View logs
aws logs tail /ecs/module-prices-agent --follow

# Check costs
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost
```

## 🎯 Production Optimization

1. **Auto Scaling**: Add auto-scaling based on CPU/memory
2. **Load Balancer**: Add ALB for high availability  
3. **Domain**: Add custom domain with Route 53
4. **HTTPS**: Add SSL certificate with ACM
5. **Monitoring**: Add CloudWatch dashboards

---

**Need Help?** Check the full deployment guide: `aws_deployment_guide.md` 