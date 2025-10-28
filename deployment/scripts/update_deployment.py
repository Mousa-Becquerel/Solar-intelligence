#!/usr/bin/env python3
"""
Update existing deployment scripts for database integration and security.
This script modifies the existing deployment infrastructure to handle database properly.
"""

import os
import json
import re

def update_deployment_script():
    """Update the existing deploy.sh script to include database setup."""
    
    print("🔄 Updating deployment script for database integration...")
    
    deploy_script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'deployment', 'deploy.sh')
    
    try:
        with open(deploy_script_path, 'r') as f:
            content = f.read()
        
        # Update repository name for Solar Intelligence
        content = content.replace('REPOSITORY_NAME="module-prices-agent"', 'REPOSITORY_NAME="solar-intelligence"')
        content = content.replace('CLUSTER_NAME="module-prices-cluster"', 'CLUSTER_NAME="solar-intelligence-cluster"')
        content = content.replace('SERVICE_NAME="module-prices-service"', 'SERVICE_NAME="solar-intelligence-service"')
        content = content.replace('TASK_FAMILY="module-prices-agent"', 'TASK_FAMILY="solar-intelligence"')
        
        # Add database secret setup after OpenAI API key setup
        database_setup = '''
# Step 3.5: Create database secrets if they don't exist
echo -e "${YELLOW}🗄️ Setting up database secrets...${NC}"

# Database URL secret
if ! aws secretsmanager describe-secret --secret-id "database-url" --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}🔑 Please enter your database URL (PostgreSQL):${NC}"
    echo -e "${YELLOW}Format: postgresql://username:password@host:port/database${NC}"
    read -s DATABASE_URL
    
    aws secretsmanager create-secret \\
        --name "database-url" \\
        --description "Database URL for Solar Intelligence Platform" \\
        --secret-string "$DATABASE_URL" \\
        --region $AWS_REGION
    echo -e "${GREEN}✅ Database URL stored in Secrets Manager${NC}"
else
    echo -e "${GREEN}✅ Database URL secret already exists${NC}"
fi

# Flask secret key
if ! aws secretsmanager describe-secret --secret-id "flask-secret-key" --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}🔑 Please enter your Flask secret key (64-character hex string):${NC}"
    read -s FLASK_SECRET_KEY
    
    aws secretsmanager create-secret \\
        --name "flask-secret-key" \\
        --description "Flask Secret Key for Solar Intelligence Platform" \\
        --secret-string "$FLASK_SECRET_KEY" \\
        --region $AWS_REGION
    echo -e "${GREEN}✅ Flask secret key stored in Secrets Manager${NC}"
else
    echo -e "${GREEN}✅ Flask secret key secret already exists${NC}"
fi

# Weaviate credentials (if needed)
if ! aws secretsmanager describe-secret --secret-id "weaviate-credentials" --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}🔑 Please enter your Weaviate URL:${NC}"
    read WEAVIATE_URL
    echo -e "${YELLOW}🔑 Please enter your Weaviate API key:${NC}"
    read -s WEAVIATE_API_KEY
    
    WEAVIATE_CREDS="{\\"url\\":\\"$WEAVIATE_URL\\",\\"api_key\\":\\"$WEAVIATE_API_KEY\\"}"
    
    aws secretsmanager create-secret \\
        --name "weaviate-credentials" \\
        --description "Weaviate credentials for Solar Intelligence Platform" \\
        --secret-string "$WEAVIATE_CREDS" \\
        --region $AWS_REGION
    echo -e "${GREEN}✅ Weaviate credentials stored in Secrets Manager${NC}"
else
    echo -e "${GREEN}✅ Weaviate credentials secret already exists${NC}"
fi
'''
        
        # Insert database setup after the OpenAI API key setup
        openai_section_end = content.find('echo -e "${GREEN}✅ OpenAI API key secret already exists${NC}"\nfi')
        if openai_section_end != -1:
            insert_pos = content.find('\n', openai_section_end) + 1
            content = content[:insert_pos] + database_setup + content[insert_pos:]
        
        # Update the task definition to include all secrets and proper configuration
        task_def_start = content.find('cat > task-definition.json << EOF')
        task_def_end = content.find('EOF', task_def_start) + 3
        
        new_task_def = '''cat > task-definition.json << EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "$REPOSITORY_NAME",
      "image": "$IMAGE_URI:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        },
        {
          "name": "PORT",
          "value": "5000"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:openai-api-key"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:database-url"
        },
        {
          "name": "FLASK_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:flask-secret-key"
        },
        {
          "name": "WEAVIATE_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:weaviate-credentials:url::"
        },
        {
          "name": "WEAVIATE_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:weaviate-credentials:api_key::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$TASK_FAMILY",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:5000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 120
      }
    }
  ]
}
EOF'''
        
        content = content[:task_def_start] + new_task_def + content[task_def_end:]
        
        # Add database initialization step before service creation
        db_init_step = '''
# Step 7.5: Initialize database
echo -e "${YELLOW}🗄️ Initializing database...${NC}"
echo -e "${YELLOW}📋 Note: Make sure your RDS instance is running and accessible${NC}"
echo -e "${YELLOW}🔧 Database initialization will be handled by the application startup${NC}"
'''
        
        # Insert before ECS service creation
        service_creation_start = content.find('# Step 8: Create or update ECS service')
        if service_creation_start != -1:
            content = content[:service_creation_start] + db_init_step + content[service_creation_start:]
        
        # Update success message
        content = content.replace(
            'echo -e "${GREEN}🎉 Deployment successful!${NC}"',
            '''echo -e "${GREEN}🎉 Deployment successful!${NC}"
        echo -e "${GREEN}📊 Database Health: http://$PUBLIC_IP:5000/database-health${NC}"
        echo -e "${GREEN}👥 Admin Panel: http://$PUBLIC_IP:5000/admin/users${NC}"'''
        )
        
        with open(deploy_script_path, 'w') as f:
            f.write(content)
        
        print("✅ Updated deployment script successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update deployment script: {e}")
        return False

def update_dockerfile():
    """Update Dockerfile to use requirements.txt instead of Poetry for simpler deployment."""
    
    print("🐳 Updating Dockerfile for production deployment...")
    
    dockerfile_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Dockerfile')
    
    try:
        new_dockerfile = '''# Use Python 3.11 slim image for Solar Intelligence Platform
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    curl \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for static files and exports
RUN mkdir -p static/plots exports/data exports/charts datasets

# Create database directory and set permissions
RUN mkdir -p /app/instance && chmod 777 /app/instance

# Set permissions for static directories
RUN chmod 777 /app/static/plots /app/exports/data /app/exports/charts

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

# Run with gunicorn using configuration file
CMD ["gunicorn", "--config", "scripts/deployment/gunicorn.conf.py", "app:app"]
'''
        
        with open(dockerfile_path, 'w') as f:
            f.write(new_dockerfile)
        
        print("✅ Updated Dockerfile successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update Dockerfile: {e}")
        return False

def update_requirements():
    """Ensure all required dependencies are in requirements.txt."""
    
    print("📦 Updating requirements.txt for production...")
    
    requirements_path = os.path.join(os.path.dirname(__file__), '..', '..', 'requirements.txt')
    
    try:
        with open(requirements_path, 'r') as f:
            content = f.read()
        
        # Essential production dependencies
        production_deps = [
            'psycopg[binary]==3.1.8',
            'flask-sqlalchemy==3.0.5',
            'flask-login==0.6.3',
            'gunicorn==21.2.0'
        ]
        
        for dep in production_deps:
            dep_name = dep.split('==')[0]
            if dep_name.lower() not in content.lower():
                content += f'\n{dep}'
        
        with open(requirements_path, 'w') as f:
            f.write(content)
        
        print("✅ Updated requirements.txt successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update requirements.txt: {e}")
        return False

def create_aws_deployment_guide():
    """Create an updated AWS deployment guide specific to our database setup."""
    
    print("📖 Creating updated AWS deployment guide...")
    
    guide_content = '''# AWS Deployment Guide - Solar Intelligence Platform

## 🎯 Complete AWS Deployment with Database

This guide covers the complete deployment of Solar Intelligence platform on AWS with PostgreSQL database.

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured  
3. **Docker** installed locally
4. **PostgreSQL database** (RDS recommended)
5. **API Keys**: OpenAI, Weaviate

## 🗄️ Step 1: Set Up RDS PostgreSQL Database

### Create RDS Instance
```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \\
  --db-instance-identifier solar-intelligence-db \\
  --db-instance-class db.t3.micro \\
  --engine postgres \\
  --engine-version 15.4 \\
  --master-username solar_admin \\
  --master-user-password YOUR_SECURE_PASSWORD \\
  --allocated-storage 20 \\
  --storage-type gp2 \\
  --vpc-security-group-ids sg-your-security-group \\
  --db-subnet-group-name default \\
  --backup-retention-period 7 \\
  --region us-east-1
```

### Security Group Setup
```bash
# Create security group for database
aws ec2 create-security-group \\
  --group-name solar-intelligence-db-sg \\
  --description "Security group for Solar Intelligence RDS"

# Allow PostgreSQL access from ECS tasks
aws ec2 authorize-security-group-ingress \\
  --group-id sg-your-db-security-group \\
  --protocol tcp \\
  --port 5432 \\
  --source-group sg-your-ecs-security-group
```

## 🚀 Step 2: Deploy Application

### Run the Updated Deployment Script
```bash
cd /path/to/solar-intelligence
chmod +x scripts/deployment/deploy.sh
./scripts/deployment/deploy.sh
```

The script will prompt you for:
- OpenAI API Key
- Database URL (format: `postgresql://solar_admin:password@rds-endpoint:5432/postgres`)
- Flask Secret Key (64-character hex string)
- Weaviate URL and API Key

### Manual Database URL Example
```
postgresql://solar_admin:your_password@solar-intelligence-db.cluster-abc123.us-east-1.rds.amazonaws.com:5432/postgres
```

## 🔧 Step 3: Initialize Database

The application will automatically:
1. Create all required tables
2. Set up admin user with secure password
3. Run health checks

### Monitor Database Initialization
```bash
# Check application logs
aws logs tail /ecs/solar-intelligence --follow --region us-east-1

# Check database health
curl http://your-public-ip:5000/database-health
```

## 🏥 Step 4: Verify Deployment

### Health Checks
- **Application**: `http://your-ip:5000/health`
- **Database**: `http://your-ip:5000/database-health`
- **Admin Panel**: `http://your-ip:5000/admin/users`

### Expected Response
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "memory": {...},
  "database": {
    "status": "healthy",
    "type": "postgresql",
    "tables": {
      "users": 1,
      "conversations": 0,
      "messages": 0
    }
  }
}
```

## 🔐 Security Considerations

### 1. Secrets Management
All sensitive data is stored in AWS Secrets Manager:
- `openai-api-key`: OpenAI API key
- `database-url`: Complete PostgreSQL connection string
- `flask-secret-key`: Flask session encryption key
- `weaviate-credentials`: Weaviate URL and API key

### 2. Network Security
- Database in private subnet
- Security groups restrict access
- ECS tasks can only access database through security groups

### 3. IAM Permissions
Required IAM role permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:openai-api-key*",
        "arn:aws:secretsmanager:*:*:secret:database-url*",
        "arn:aws:secretsmanager:*:*:secret:flask-secret-key*",
        "arn:aws:secretsmanager:*:*:secret:weaviate-credentials*"
      ]
    }
  ]
}
```

## 📊 Monitoring & Maintenance

### CloudWatch Logs
- Application logs: `/ecs/solar-intelligence`
- Database logs: RDS console

### Performance Monitoring
- CPU and memory usage in ECS console
- Database performance in RDS console
- Custom metrics via health endpoints

### Backup Strategy
- RDS automated backups (7 days)
- Manual snapshots before updates
- Application data export via admin panel

## 💰 Cost Optimization

### Estimated Monthly Costs
- **RDS db.t3.micro**: ~$13/month
- **ECS Fargate**: ~$30-50/month (depending on usage)
- **Secrets Manager**: ~$1/month (4 secrets)
- **CloudWatch Logs**: ~$5/month
- **Total**: ~$50-70/month

### Optimization Tips
1. Use Reserved Instances for predictable workloads
2. Enable RDS storage autoscaling
3. Set up CloudWatch alarms for cost monitoring
4. Use Spot Instances for development environments

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-your-db-sg

# Verify RDS status
aws rds describe-db-instances --db-instance-identifier solar-intelligence-db
```

#### Application Won't Start
```bash
# Check ECS service events
aws ecs describe-services --cluster solar-intelligence-cluster --services solar-intelligence-service

# Check container logs
aws logs tail /ecs/solar-intelligence --follow
```

#### Secrets Access Issues
```bash
# Verify secret exists
aws secretsmanager describe-secret --secret-id database-url

# Check IAM role permissions
aws iam get-role-policy --role-name ecsTaskExecutionRole --policy-name SecretsManagerAccess
```

## 🚀 Updates and Scaling

### Deploy Updates
```bash
# Rebuild and deploy
./scripts/deployment/deploy.sh

# Force new deployment without rebuild
aws ecs update-service \\
  --cluster solar-intelligence-cluster \\
  --service solar-intelligence-service \\
  --force-new-deployment
```

### Scale Application
```bash
# Increase desired count
aws ecs update-service \\
  --cluster solar-intelligence-cluster \\
  --service solar-intelligence-service \\
  --desired-count 3
```

### Database Scaling
- Vertical: Change instance class in RDS console
- Read replicas: For read-heavy workloads
- Connection pooling: Already configured in application

This deployment setup provides a production-ready, scalable Solar Intelligence platform on AWS!
'''
    
    guide_path = os.path.join(os.path.dirname(__file__), '..', 'AWS_DEPLOYMENT_COMPLETE.md')
    
    try:
        with open(guide_path, 'w') as f:
            f.write(guide_content)
        
        print("✅ Created updated deployment guide")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create deployment guide: {e}")
        return False

def main():
    """Main function to update all deployment components."""
    
    print("🔄 Updating Existing Deployment Infrastructure for Database Integration")
    print("="*80)
    
    success = True
    
    # Update deployment script
    if not update_deployment_script():
        success = False
    
    # Update Dockerfile
    if not update_dockerfile():
        success = False
    
    # Update requirements
    if not update_requirements():
        success = False
    
    # Create deployment guide
    if not create_aws_deployment_guide():
        success = False
    
    if success:
        print("\n🎉 All deployment updates completed successfully!")
        print("\n📋 Updated Components:")
        print("✅ scripts/deployment/deploy.sh - Enhanced with database integration")
        print("✅ Dockerfile - Updated for production with PostgreSQL")
        print("✅ requirements.txt - Added production dependencies")
        print("✅ deployment/AWS_DEPLOYMENT_COMPLETE.md - Complete deployment guide")
        print("\n🚀 Next Steps:")
        print("1. Run deployment/scripts/secure_production.py to secure hardcoded credentials")
        print("2. Set up RDS PostgreSQL instance")
        print("3. Run ./scripts/deployment/deploy.sh for complete deployment")
        print("4. Initialize database with deployment/scripts/init_database.py if needed")
    else:
        print("\n❌ Some updates failed. Please review the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)