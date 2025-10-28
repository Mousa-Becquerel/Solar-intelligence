# Manual deployment steps for Solar Intelligence Platform
# Run each section separately

param(
    [string]$Region = "eu-north-1"
)

# Configuration
$RepositoryName = "datahub_agents"
$ClusterName = "solar-intelligence-cluster"
$ServiceName = "solar-intelligence-service"
$TaskFamily = "solar-intelligence"

Write-Host "🚀 Solar Intelligence Manual Deployment Steps" -ForegroundColor Green
Write-Host "Run each section separately by copying and pasting" -ForegroundColor Yellow

Write-Host "`n=== STEP 1: Get Account ID ===" -ForegroundColor Cyan
Write-Host "aws sts get-caller-identity --query Account --output text" -ForegroundColor White

Write-Host "`n=== STEP 2: Build and Push Docker Image ===" -ForegroundColor Cyan
Write-Host "docker build -t $RepositoryName ." -ForegroundColor White
Write-Host "aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin 196621412948.dkr.ecr.$Region.amazonaws.com" -ForegroundColor White
Write-Host "docker tag ${RepositoryName}:latest 196621412948.dkr.ecr.$Region.amazonaws.com/${RepositoryName}:latest" -ForegroundColor White
Write-Host "docker push 196621412948.dkr.ecr.$Region.amazonaws.com/${RepositoryName}:latest" -ForegroundColor White

Write-Host "`n=== STEP 3: Create Secrets ===" -ForegroundColor Cyan
Write-Host "You'll need to create these secrets manually. Run these commands one by one:" -ForegroundColor Yellow

Write-Host "`n3a. OpenAI API Key:" -ForegroundColor Yellow
Write-Host 'aws secretsmanager create-secret --name "openai-api-key" --description "OpenAI API Key" --secret-string "YOUR_OPENAI_KEY" --region ' + $Region -ForegroundColor White

Write-Host "`n3b. Database URL:" -ForegroundColor Yellow
Write-Host "First, get your RDS endpoint from AWS Console, then:" -ForegroundColor Yellow
Write-Host 'aws secretsmanager create-secret --name "database-url" --description "Database URL" --secret-string "postgresql://solar_admin:SolarIntel2024!@YOUR_RDS_ENDPOINT:5432/solar_intelligence" --region ' + $Region -ForegroundColor White

Write-Host "`n3c. Flask Secret Key:" -ForegroundColor Yellow
Write-Host 'aws secretsmanager create-secret --name "flask-secret-key" --description "Flask Secret Key" --secret-string "6bdd915f05f3f512b2cf32d34720476cf1f99ad910649750786457a2a18f506d" --region ' + $Region -ForegroundColor White

Write-Host "`n3d. Weaviate Credentials:" -ForegroundColor Yellow
Write-Host 'aws secretsmanager create-secret --name "weaviate-credentials" --description "Weaviate credentials" --secret-string "{\"url\":\"YOUR_WEAVIATE_URL\",\"api_key\":\"YOUR_WEAVIATE_KEY\"}" --region ' + $Region -ForegroundColor White

Write-Host "`n=== STEP 4: Create ECS Resources ===" -ForegroundColor Cyan
Write-Host "aws ecs create-cluster --cluster-name $ClusterName --region $Region" -ForegroundColor White
Write-Host "aws logs create-log-group --log-group-name /ecs/$TaskFamily --region $Region" -ForegroundColor White

Write-Host "`n=== STEP 5: Create Task Definition JSON File ===" -ForegroundColor Cyan
Write-Host "I'll create a task-definition.json file for you..." -ForegroundColor Yellow