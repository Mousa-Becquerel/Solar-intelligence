# PowerShell deployment script for Solar Intelligence Platform
param(
    [string]$Region = "eu-north-1"
)

# Configuration
$RepositoryName = "datahub_agents"
$ClusterName = "solar-intelligence-cluster"
$ServiceName = "solar-intelligence-service"
$TaskFamily = "solar-intelligence"

Write-Host "🚀 Starting AWS deployment for Solar Intelligence Platform" -ForegroundColor Green

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

# Check AWS CLI
try {
    aws --version | Out-Null
    Write-Host "✅ AWS CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI is required but not installed." -ForegroundColor Red
    exit 1
}

# Check Docker
try {
    docker --version | Out-Null
    Write-Host "✅ Docker found" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is required but not installed." -ForegroundColor Red
    exit 1
}

# Get AWS account ID
Write-Host "📊 Getting AWS account information..." -ForegroundColor Yellow
$AccountId = (aws sts get-caller-identity --query Account --output text)
if (-not $AccountId) {
    Write-Host "❌ Unable to get AWS Account ID. Please check your AWS credentials." -ForegroundColor Red
    exit 1
}
Write-Host "✅ AWS Account ID: $AccountId" -ForegroundColor Green

# ECR repository URI
$ImageUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepositoryName"

# Step 1: ECR repository should already exist
Write-Host "📦 Checking ECR repository..." -ForegroundColor Yellow
try {
    aws ecr describe-repositories --repository-names $RepositoryName --region $Region | Out-Null
    Write-Host "✅ ECR repository exists" -ForegroundColor Green
} catch {
    Write-Host "❌ ECR repository $RepositoryName not found" -ForegroundColor Red
    exit 1
}

# Step 2: Build and push Docker image
Write-Host "🏗️ Building Docker image..." -ForegroundColor Yellow
docker build -t $RepositoryName .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "🏷️ Tagging image..." -ForegroundColor Yellow
docker tag "${RepositoryName}:latest" "${ImageUri}:latest"

Write-Host "🔑 Logging in to ECR..." -ForegroundColor Yellow
$LoginCommand = aws ecr get-login-password --region $Region
if ($LoginCommand) {
    $LoginCommand | docker login --username AWS --password-stdin $ImageUri
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ ECR login failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ Failed to get ECR login token" -ForegroundColor Red
    exit 1
}

Write-Host "📤 Pushing image to ECR..." -ForegroundColor Yellow
docker push "${ImageUri}:latest"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker push failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image pushed successfully" -ForegroundColor Green

# Step 3: Create secrets
Write-Host "🔐 Setting up secrets..." -ForegroundColor Yellow

# OpenAI API Key
$OpenAIExists = aws secretsmanager describe-secret --secret-id "openai-api-key" --region $Region 2>$null
if (-not $OpenAIExists) {
    $OpenAIKey = Read-Host "🔑 Please enter your OpenAI API key" -AsSecureString
    $OpenAIKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($OpenAIKey))
    
    aws secretsmanager create-secret --name "openai-api-key" --description "OpenAI API Key for Solar Intelligence" --secret-string $OpenAIKeyPlain --region $Region
    Write-Host "✅ OpenAI API key stored in Secrets Manager" -ForegroundColor Green
} else {
    Write-Host "✅ OpenAI API key secret already exists" -ForegroundColor Green
}

# Database URL
$DatabaseExists = aws secretsmanager describe-secret --secret-id "database-url" --region $Region 2>$null
if (-not $DatabaseExists) {
    Write-Host "🔑 Please enter your database URL (PostgreSQL):" -ForegroundColor Yellow
    Write-Host "Format: postgresql://solar_admin:SolarIntel2024!@your-endpoint:5432/solar_intelligence" -ForegroundColor Yellow
    $DatabaseUrl = Read-Host "Database URL"
    
    aws secretsmanager create-secret --name "database-url" --description "Database URL for Solar Intelligence Platform" --secret-string $DatabaseUrl --region $Region
    Write-Host "✅ Database URL stored in Secrets Manager" -ForegroundColor Green
} else {
    Write-Host "✅ Database URL secret already exists" -ForegroundColor Green
}

# Flask Secret Key
$FlaskExists = aws secretsmanager describe-secret --secret-id "flask-secret-key" --region $Region 2>$null
if (-not $FlaskExists) {
    Write-Host "🔑 Please enter your Flask secret key:" -ForegroundColor Yellow
    Write-Host "(Use this generated key: 6bdd915f05f3f512b2cf32d34720476cf1f99ad910649750786457a2a18f506d)" -ForegroundColor Yellow
    $FlaskKey = Read-Host "Flask Secret Key"
    
    aws secretsmanager create-secret --name "flask-secret-key" --description "Flask Secret Key for Solar Intelligence Platform" --secret-string $FlaskKey --region $Region
    Write-Host "✅ Flask secret key stored in Secrets Manager" -ForegroundColor Green
} else {
    Write-Host "✅ Flask secret key secret already exists" -ForegroundColor Green
}

# Weaviate credentials
$WeaviateExists = aws secretsmanager describe-secret --secret-id "weaviate-credentials" --region $Region 2>$null
if (-not $WeaviateExists) {
    $WeaviateUrl = Read-Host "🔑 Please enter your Weaviate URL"
    $WeaviateKey = Read-Host "🔑 Please enter your Weaviate API key" -AsSecureString
    $WeaviateKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($WeaviateKey))
    
    $WeaviateCreds = @{
        url = $WeaviateUrl
        api_key = $WeaviateKeyPlain
    } | ConvertTo-Json -Compress
    
    aws secretsmanager create-secret --name "weaviate-credentials" --description "Weaviate credentials for Solar Intelligence Platform" --secret-string $WeaviateCreds --region $Region
    Write-Host "✅ Weaviate credentials stored in Secrets Manager" -ForegroundColor Green
} else {
    Write-Host "✅ Weaviate credentials secret already exists" -ForegroundColor Green
}

# Step 4: Create ECS cluster
Write-Host "🏗️ Setting up ECS cluster..." -ForegroundColor Yellow
$ClusterExists = aws ecs describe-clusters --clusters $ClusterName --region $Region --query 'clusters[0].status' --output text 2>$null
if ($ClusterExists -ne "ACTIVE") {
    aws ecs create-cluster --cluster-name $ClusterName --region $Region
    Write-Host "✅ ECS cluster created" -ForegroundColor Green
} else {
    Write-Host "✅ ECS cluster already exists" -ForegroundColor Green
}

# Step 5: Create CloudWatch log group
Write-Host "📊 Setting up CloudWatch logs..." -ForegroundColor Yellow
aws logs create-log-group --log-group-name "/ecs/$TaskFamily" --region $Region 2>$null
Write-Host "✅ CloudWatch log group ready" -ForegroundColor Green

# Step 6: Create task definition
Write-Host "📝 Creating ECS task definition..." -ForegroundColor Yellow

# Create task definition as a PowerShell object and convert to JSON
$TaskDefinition = @{
    family = $TaskFamily
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = "2048"
    memory = "4096"
    executionRoleArn = "arn:aws:iam::$AccountId`:role/ecsTaskExecutionRole"
    containerDefinitions = @(
        @{
            name = $RepositoryName
            image = "$ImageUri`:latest"
            portMappings = @(
                @{
                    containerPort = 5000
                    protocol = "tcp"
                }
            )
            environment = @(
                @{
                    name = "FLASK_ENV"
                    value = "production"
                },
                @{
                    name = "PORT"
                    value = "5000"
                }
            )
            secrets = @(
                @{
                    name = "OPENAI_API_KEY"
                    valueFrom = "arn:aws:secretsmanager:$Region`:$AccountId`:secret:openai-api-key"
                },
                @{
                    name = "DATABASE_URL"
                    valueFrom = "arn:aws:secretsmanager:$Region`:$AccountId`:secret:database-url"
                },
                @{
                    name = "FLASK_SECRET_KEY"
                    valueFrom = "arn:aws:secretsmanager:$Region`:$AccountId`:secret:flask-secret-key"
                },
                @{
                    name = "WEAVIATE_URL"
                    valueFrom = "arn:aws:secretsmanager:$Region`:$AccountId`:secret:weaviate-credentials:url::"
                },
                @{
                    name = "WEAVIATE_API_KEY"
                    valueFrom = "arn:aws:secretsmanager:$Region`:$AccountId`:secret:weaviate-credentials:api_key::"
                }
            )
            logConfiguration = @{
                logDriver = "awslogs"
                options = @{
                    "awslogs-group" = "/ecs/$TaskFamily"
                    "awslogs-region" = $Region
                    "awslogs-stream-prefix" = "ecs"
                }
            }
            healthCheck = @{
                command = @("CMD-SHELL", "curl -f http://localhost:5000/health || exit 1")
                interval = 30
                timeout = 10
                retries = 3
                startPeriod = 120
            }
        }
    )
}

# Convert to JSON and save
$TaskDefinition | ConvertTo-Json -Depth 10 | Out-File -FilePath "task-definition.json" -Encoding UTF8

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json --region $Region
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to register task definition" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Task definition registered" -ForegroundColor Green

# Step 7: Get VPC information
Write-Host "🌐 Getting VPC information..." -ForegroundColor Yellow
$VpcId = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $Region
$SubnetIds = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VpcId" --query 'Subnets[*].SubnetId' --output text --region $Region
$SubnetIdsList = $SubnetIds -replace '\t', ','

# Create security group
$SgName = "solar-intelligence-sg"
$SecurityGroupId = aws ec2 describe-security-groups --filters "Name=group-name,Values=$SgName" --query 'SecurityGroups[0].GroupId' --output text --region $Region 2>$null

if ($SecurityGroupId -eq "None" -or -not $SecurityGroupId) {
    Write-Host "🛡️ Creating security group..." -ForegroundColor Yellow
    $SecurityGroupId = aws ec2 create-security-group --group-name $SgName --description "Security group for Solar Intelligence" --vpc-id $VpcId --query 'GroupId' --output text --region $Region

    # Allow inbound traffic on port 5000
    aws ec2 authorize-security-group-ingress --group-id $SecurityGroupId --protocol tcp --port 5000 --cidr 0.0.0.0/0 --region $Region
    
    Write-Host "✅ Security group created: $SecurityGroupId" -ForegroundColor Green
} else {
    Write-Host "✅ Using existing security group: $SecurityGroupId" -ForegroundColor Green
}

# Step 8: Create or update ECS service
Write-Host "🚀 Creating/updating ECS service..." -ForegroundColor Yellow
$ServiceExists = aws ecs describe-services --cluster $ClusterName --services $ServiceName --region $Region --query 'services[0].status' --output text 2>$null

if ($ServiceExists -eq "ACTIVE") {
    Write-Host "🔄 Updating existing service..." -ForegroundColor Yellow
    aws ecs update-service --cluster $ClusterName --service $ServiceName --task-definition $TaskFamily --force-new-deployment --region $Region
} else {
    Write-Host "🆕 Creating new service..." -ForegroundColor Yellow
    aws ecs create-service --cluster $ClusterName --service-name $ServiceName --task-definition $TaskFamily --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[$SubnetIdsList],securityGroups=[$SecurityGroupId],assignPublicIp=ENABLED}" --region $Region
}

Write-Host "✅ ECS service created/updated" -ForegroundColor Green

# Step 9: Wait for service to stabilize
Write-Host "⏳ Waiting for service to stabilize..." -ForegroundColor Yellow
aws ecs wait services-stable --cluster $ClusterName --services $ServiceName --region $Region

# Step 10: Get service endpoint
Write-Host "🔍 Getting service endpoint..." -ForegroundColor Yellow
$TaskArn = aws ecs list-tasks --cluster $ClusterName --service-name $ServiceName --region $Region --query 'taskArns[0]' --output text

if ($TaskArn -and $TaskArn -ne "None") {
    $NetworkInterfaceId = aws ecs describe-tasks --cluster $ClusterName --tasks $TaskArn --region $Region --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text
    if ($NetworkInterfaceId) {
        $PublicIp = aws ec2 describe-network-interfaces --network-interface-ids $NetworkInterfaceId --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region $Region
        
        if ($PublicIp -and $PublicIp -ne "None") {
            Write-Host "🎉 Deployment successful!" -ForegroundColor Green
            Write-Host "📍 Your service is available at: http://$PublicIp`:5000" -ForegroundColor Green
            Write-Host "🏥 Health check: http://$PublicIp`:5000/health" -ForegroundColor Green
            Write-Host "🗄️ Database health: http://$PublicIp`:5000/database-health" -ForegroundColor Green
    } else {
            Write-Host "⚠️ Service deployed but public IP not yet available. Check ECS console." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "⚠️ Service deployed but no running tasks found yet. Check ECS console." -ForegroundColor Yellow
}

# Cleanup
Remove-Item "task-definition.json" -ErrorAction SilentlyContinue

Write-Host "✅ Deployment completed!" -ForegroundColor Green
Write-Host "📊 To monitor your service:" -ForegroundColor Yellow
Write-Host "   aws ecs describe-services --cluster $ClusterName --services $ServiceName --region $Region" -ForegroundColor Yellow
Write-Host "📋 To view logs:" -ForegroundColor Yellow
Write-Host "   aws logs tail /ecs/$TaskFamily --follow --region $Region" -ForegroundColor Yellow