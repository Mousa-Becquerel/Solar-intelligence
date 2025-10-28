#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-eu-north-1}"
REPOSITORY_NAME="datahub_agents"
CLUSTER_NAME="solar-intelligence-cluster"
SERVICE_NAME="solar-intelligence-service"
TASK_FAMILY="solar-intelligence"

echo -e "${GREEN}🚀 Starting AWS deployment for Solar Intelligence Platform${NC}"

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

command -v aws >/dev/null 2>&1 || { echo -e "${RED}❌ AWS CLI is required but not installed.${NC}" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker is required but not installed.${NC}" >&2; exit 1; }

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Unable to get AWS Account ID. Please check your AWS credentials.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# ECR repository URI
IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME"

# Step 1: Create ECR repository if it doesn't exist
echo -e "${YELLOW}📦 Setting up ECR repository...${NC}"
aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $AWS_REGION >/dev/null 2>&1 || {
    echo -e "${YELLOW}📦 Creating ECR repository...${NC}"
    aws ecr create-repository --repository-name $REPOSITORY_NAME --region $AWS_REGION
    echo -e "${GREEN}✅ ECR repository created${NC}"
}

# Step 2: Build and push Docker image
echo -e "${YELLOW}🏗️ Building Docker image...${NC}"
docker build -t $REPOSITORY_NAME .

echo -e "${YELLOW}🏷️ Tagging image...${NC}"
docker tag $REPOSITORY_NAME:latest $IMAGE_URI:latest

echo -e "${YELLOW}🔑 Logging in to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $IMAGE_URI

echo -e "${YELLOW}📤 Pushing image to ECR...${NC}"
docker push $IMAGE_URI:latest
echo -e "${GREEN}✅ Image pushed successfully${NC}"

# Step 3: Create OpenAI API key secret if it doesn't exist
echo -e "${YELLOW}🔐 Setting up secrets...${NC}"
if ! aws secretsmanager describe-secret --secret-id "openai-api-key" --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}🔑 Please enter your OpenAI API key:${NC}"
    read -s OPENAI_API_KEY
    
    aws secretsmanager create-secret \
        --name "openai-api-key" \
        --description "OpenAI API Key for Module Prices Agent" \
        --secret-string "$OPENAI_API_KEY" \
        --region $AWS_REGION
    echo -e "${GREEN}✅ OpenAI API key stored in Secrets Manager${NC}"
else
    echo -e "${GREEN}✅ OpenAI API key secret already exists${NC}"
fi

# Step 3.5: Create database secrets if they don't exist
echo -e "${YELLOW}🗄️ Setting up database secrets...${NC}"

# Database URL secret
if ! aws secretsmanager describe-secret --secret-id "database-url" --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}🔑 Please enter your database URL (PostgreSQL):${NC}"
    echo -e "${YELLOW}Format: postgresql://username:password@host:port/database${NC}"
    read -s DATABASE_URL
    
    aws secretsmanager create-secret \
        --name "database-url" \
        --description "Database URL for Solar Intelligence Platform" \
        --secret-string "$DATABASE_URL" \
        --region $AWS_REGION
    echo -e "${GREEN}✅ Database URL stored in Secrets Manager${NC}"
else
    echo -e "${GREEN}✅ Database URL secret already exists${NC}"
fi

# Flask secret key
if ! aws secretsmanager describe-secret --secret-id "flask-secret-key" --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}🔑 Please enter your Flask secret key:${NC}"
    echo -e "${YELLOW}(Use this generated key: 6bdd915f05f3f512b2cf32d34720476cf1f99ad910649750786457a2a18f506d)${NC}"
    read -s FLASK_SECRET_KEY
    
    aws secretsmanager create-secret \
        --name "flask-secret-key" \
        --description "Flask Secret Key for Solar Intelligence Platform" \
        --secret-string "$FLASK_SECRET_KEY" \
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
    
    WEAVIATE_CREDS="{\"url\":\"$WEAVIATE_URL\",\"api_key\":\"$WEAVIATE_API_KEY\"}"
    
    aws secretsmanager create-secret \
        --name "weaviate-credentials" \
        --description "Weaviate credentials for Solar Intelligence Platform" \
        --secret-string "$WEAVIATE_CREDS" \
        --region $AWS_REGION
    echo -e "${GREEN}✅ Weaviate credentials stored in Secrets Manager${NC}"
else
    echo -e "${GREEN}✅ Weaviate credentials secret already exists${NC}"
fi

# Step 4: Create ECS cluster if it doesn't exist
echo -e "${YELLOW}🏗️ Setting up ECS cluster...${NC}"
if ! aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION
    echo -e "${GREEN}✅ ECS cluster created${NC}"
else
    echo -e "${GREEN}✅ ECS cluster already exists${NC}"
fi

# Step 5: Create CloudWatch log group
echo -e "${YELLOW}📊 Setting up CloudWatch logs...${NC}"
aws logs create-log-group --log-group-name "/ecs/$TASK_FAMILY" --region $AWS_REGION 2>/dev/null || {
    echo -e "${GREEN}✅ CloudWatch log group already exists${NC}"
}

# Step 6: Create task definition
echo -e "${YELLOW}📝 Creating ECS task definition...${NC}"
cat > task-definition.json << EOF
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
EOF

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json --region $AWS_REGION
echo -e "${GREEN}✅ Task definition registered${NC}"

# Step 7: Get default VPC and subnets
echo -e "${YELLOW}🌐 Getting VPC information...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $AWS_REGION | tr '\t' ',')

# Create security group if it doesn't exist
SG_NAME="module-prices-sg"
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION 2>/dev/null)

if [ "$SECURITY_GROUP_ID" = "None" ] || [ -z "$SECURITY_GROUP_ID" ]; then
    echo -e "${YELLOW}🛡️ Creating security group...${NC}"
    SECURITY_GROUP_ID=$(aws ec2 create-security-group \
        --group-name $SG_NAME \
        --description "Security group for Module Prices Agent" \
        --vpc-id $VPC_ID \
        --query 'GroupId' \
        --output text \
        --region $AWS_REGION)
    
    # Allow inbound traffic on port 5000
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 5000 \
        --cidr 0.0.0.0/0 \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ Security group created: $SECURITY_GROUP_ID${NC}"
else
    echo -e "${GREEN}✅ Using existing security group: $SECURITY_GROUP_ID${NC}"
fi

# Step 8: Create or update ECS service
echo -e "${YELLOW}🚀 Creating/updating ECS service...${NC}"
if aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo -e "${YELLOW}🔄 Updating existing service...${NC}"
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --force-new-deployment \
        --region $AWS_REGION
else
    echo -e "${YELLOW}🆕 Creating new service...${NC}"
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
        --region $AWS_REGION
fi

echo -e "${GREEN}✅ ECS service created/updated${NC}"

# Step 9: Wait for service to stabilize
echo -e "${YELLOW}⏳ Waiting for service to stabilize...${NC}"
aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION

# Step 10: Get service endpoint
echo -e "${YELLOW}🔍 Getting service endpoint...${NC}"
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $AWS_REGION --query 'taskArns[0]' --output text)
if [ "$TASK_ARN" != "None" ] && [ -n "$TASK_ARN" ]; then
    PUBLIC_IP=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --region $AWS_REGION --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region $AWS_REGION)
    
    if [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "None" ]; then
        echo -e "${GREEN}🎉 Deployment successful!${NC}"
        echo -e "${GREEN}📍 Your service is available at: http://$PUBLIC_IP:5000${NC}"
        echo -e "${GREEN}🏥 Health check: http://$PUBLIC_IP:5000/health${NC}"
    else
        echo -e "${YELLOW}⚠️ Service deployed but public IP not yet available. Check ECS console.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Service deployed but no running tasks found yet. Check ECS console.${NC}"
fi

# Cleanup
rm -f task-definition.json

echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${YELLOW}📊 To monitor your service:${NC}"
echo -e "${YELLOW}   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION${NC}"
echo -e "${YELLOW}📋 To view logs:${NC}"
echo -e "${YELLOW}   aws logs tail /ecs/$TASK_FAMILY --follow --region $AWS_REGION${NC}" 