# Deployment Guide: Morning Coffee Full Stack Application

This guide provides detailed instructions for deploying the complete Morning Coffee application stack, including the backend microservices, Spark TTS, and the React frontend with Supabase integration.

## System Architecture Overview

The complete application stack consists of:

1. **Backend Services**:
   - Flask API server (Main application)
   - Spark TTS service
   - Redis for state management
   - Optional local LLM service

2. **Frontend Application**:
   - React application with Supabase authentication
   - Served via Nginx

3. **External Services**:
   - Telnyx for voice and SMS
   - AssemblyAI for speech recognition
   - Supabase for authentication and database
   - Optional cloud LLM provider (OpenAI or Claude)

## Prerequisites

- Docker and Docker Compose
- A Supabase account and project
- Telnyx account with phone number
- AssemblyAI API key
- Domain name (for production)
- SSL certificates (for production)

## Deployment Options

### 1. Docker Compose Deployment (Recommended for Small-Scale)

This is the simplest deployment method, suitable for development or small-scale production environments.

#### Steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/morning-coffee.git
   cd morning-coffee
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Update the docker-compose.yml file**:
   Make sure the Supabase configuration is included in the frontend service.

4. **Build and start the containers**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

5. **Verify deployment**:
   ```bash
   docker-compose ps
   ```

### 2. Kubernetes Deployment (Recommended for Production)

For production environments with higher scalability requirements, Kubernetes is recommended.

#### Prerequisites:
- Kubernetes cluster (GKE, EKS, AKS, or self-hosted)
- kubectl configured
- Helm installed

#### Steps:

1. **Prepare Kubernetes configuration files**:
   Create Kubernetes manifests for each service in the `kubernetes/` directory.

2. **Create Kubernetes secrets**:
   ```bash
   kubectl create secret generic morning-coffee-secrets \
     --from-literal=TELNYX_API_KEY=your_telnyx_api_key \
     --from-literal=ASSEMBLYAI_API_KEY=your_assemblyai_api_key \
     --from-literal=OPENAI_API_KEY=your_openai_api_key \
     --from-literal=SUPABASE_URL=your_supabase_url \
     --from-literal=SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

3. **Deploy Redis**:
   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm install redis bitnami/redis
   ```

4. **Deploy the application**:
   ```bash
   kubectl apply -f kubernetes/namespace.yaml
   kubectl apply -f kubernetes/spark-tts.yaml
   kubectl apply -f kubernetes/app.yaml
   kubectl apply -f kubernetes/frontend.yaml
   ```

5. **Configure Ingress**:
   ```bash
   kubectl apply -f kubernetes/ingress.yaml
   ```

6. **Verify deployment**:
   ```bash
   kubectl get pods -n morning-coffee
   ```

### 3. Cloud Platform Deployment

#### Option A: AWS Deployment

Deploy using AWS ECS (Elastic Container Service) for containerized applications:

1. **Set up ECR repositories**:
   Create ECR repositories for each container image.

2. **Push container images**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account-id.dkr.ecr.us-east-1.amazonaws.com
   
   docker tag morning-coffee-app:latest your-account-id.dkr.ecr.us-east-1.amazonaws.com/morning-coffee-app:latest
   docker push your-account-id.dkr.ecr.us-east-1.amazonaws.com/morning-coffee-app:latest
   
   # Repeat for other images
   ```

3. **Create ECS Task Definitions**:
   Define task definitions for each service with appropriate environment variables.

4. **Create ECS Service**:
   Create services for each task definition with desired count.

5. **Set up ALB**:
   Configure Application Load Balancer for the frontend service.

#### Option B: Google Cloud Platform

Deploy using Google Cloud Run for containerized applications:

1. **Push container images to GCR**:
   ```bash
   gcloud auth configure-docker
   
   docker tag morning-coffee-app:latest gcr.io/your-project-id/morning-coffee-app:latest
   docker push gcr.io/your-project-id/morning-coffee-app:latest
   
   # Repeat for other images
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy morning-coffee-app \
     --image gcr.io/your-project-id/morning-coffee-app:latest \
     --platform managed \
     --allow-unauthenticated \
     --set-env-vars="TELNYX_API_KEY=your_telnyx_api_key,..."
   
   # Repeat for other services
   ```

3. **Set up VPC connector** for services to communicate with each other.

## Supabase Configuration

### 1. Create Supabase Project

1. Sign up at [supabase.com](https://supabase.com) and create a new project
2. Note down your project URL and anon key

### 2. Initialize Database Schema

1. Go to the SQL Editor in your Supabase dashboard
2. Create tables and set up RLS policies:
   - Copy the SQL from the `supabase-sql-setup.sql` file
   - Run the SQL in the SQL Editor

### 3. Configure Authentication

1. Navigate to Authentication > Settings
2. Configure Site URL to your frontend domain
3. Set up email templates
4. Enable the authentication providers you want to use (Email, Google, GitHub, etc.)

### 4. Set up Storage (optional)

1. Navigate to Storage in your Supabase dashboard
2. Create buckets for user uploads:
   - `affirmations` - for custom affirmation audio
   - `recordings` - for call recordings
3. Set up appropriate bucket policies

## SSL Configuration

For production deployments, SSL is required. Configure SSL using one of these methods:

### Option 1: Let's Encrypt with Certbot

```bash
sudo apt-get install certbot
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Option 2: Using Existing Certificates

If you have existing certificates:

```bash
# Update your nginx.conf
ssl_certificate /path/to/fullchain.pem;
ssl_certificate_key /path/to/privkey.pem;
```

## Monitoring and Logging

Set up monitoring and logging for production environments:

### 1. Prometheus and Grafana

1. Deploy Prometheus for metrics collection
2. Set up Grafana for visualization
3. Configure dashboards for monitoring container health, API performance, etc.

### 2. ELK Stack (Elasticsearch, Logstash, Kibana)

For centralized logging:

1. Deploy ELK stack
2. Configure Filebeat on application servers
3. Set up dashboards in Kibana

### 3. Cloud Provider Monitoring

Alternatively, use cloud provider monitoring solutions:

- AWS: CloudWatch
- GCP: Cloud Monitoring and Logging
- Azure: Azure Monitor

## Backup Strategy

Implement a backup strategy for your data:

1. **Supabase Database**:
   - Enable point-in-time recovery
   - Schedule regular database exports

2. **Telnyx Data**:
   - Enable call recording archiving if needed

3. **Application State**:
   - Configure Redis persistence
   - Implement backup procedures for Redis data

## Security Considerations

Ensure your deployment follows security best practices:

1. **Network Security**:
   - Use private networks for internal communication
   - Implement proper firewall rules
   - Use VPC for cloud deployments

2. **API Security**:
   - Implement rate limiting
   - Use CORS properly
   - Validate all inputs

3. **Authentication Security**:
   - Use HTTPS for all endpoints
   - Implement proper session management
   - Enable MFA where possible

4. **Infrastructure Security**:
   - Keep all dependencies updated
   - Use minimal container images
   - Scan containers for vulnerabilities

## Scaling Considerations

For high-traffic deployments, consider these scaling strategies:

1. **Horizontal Scaling**:
   - Scale the Flask API and frontend services horizontally
   - Use Kubernetes HPA (Horizontal Pod Autoscaler)

2. **Database Scaling**:
   - Monitor Supabase performance
   - Consider upgrading to a larger plan if needed

3. **Redis Scaling**:
   - Implement Redis Cluster for high availability
   - Monitor memory usage

4. **TTS Service Scaling**:
   - Deploy multiple Spark TTS instances
   - Implement load balancing

## Updating the Application

To update the application:

1. **Pull the latest code**:
   ```bash
   git pull origin main
   ```

2. **Rebuild containers**:
   ```bash
   docker-compose build
   ```

3. **Update containers**:
   ```bash
   docker-compose up -d
   ```

For Kubernetes:
```bash
kubectl apply -f kubernetes/
```

## Troubleshooting

Common issues and solutions:

### Telnyx Webhook Issues

If Telnyx webhooks aren't being received:
1. Check your Telnyx webhook URL configuration
2. Ensure your server is publicly accessible
3. Check the Telnyx portal for webhook delivery failures

### TTS Service Issues

If the TTS service is not working:
1. Check if the Spark TTS container is running
2. Verify GPU access if configured for GPU acceleration
3. Check logs for model loading errors

### Database Issues

For Supabase connection issues:
1. Verify your Supabase credentials
2. Check network connectivity to Supabase
3. Look for errors in the application logs

### Frontend Issues

If the frontend is not loading:
1. Check Nginx configuration
2. Verify that the React app was built correctly
3. Check for JavaScript console errors

## Support and Maintenance

For ongoing support:

1. **Regular Updates**:
   - Keep dependencies updated
   - Apply security patches promptly

2. **Monitoring**:
   - Review logs regularly
   - Set up alerts for abnormal conditions

3. **Performance Optimization**:
   - Profile the application periodically
   - Optimize queries and API endpoints
