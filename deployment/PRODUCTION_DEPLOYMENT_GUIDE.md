# Production Deployment Guide

This guide covers deploying the enhanced Calendar API system with comprehensive monitoring, logging, and alerting capabilities.

## Overview

The production deployment includes:
- Enhanced FastAPI service with health checks and performance monitoring
- Prometheus metrics collection and alerting
- Grafana dashboards for visualization
- Loki log aggregation with Promtail
- Alertmanager for notification management
- Docker Compose orchestration

## Prerequisites

### System Requirements
- Docker and Docker Compose
- Minimum 2GB RAM, 2 CPU cores
- 10GB available disk space
- Network access for external dependencies

### Environment Setup
```bash
# Create deployment directory
mkdir -p /opt/calendar-api
cd /opt/calendar-api

# Clone or copy application files
# Ensure all files from the deployment/ directory are present
```

## Deployment Steps

### 1. Environment Configuration

Create environment file:
```bash
cat > .env << EOF
# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_DIR=/app/logs

# Performance Settings
ENABLE_METRICS=true
CACHE_TTL_HOURS=24
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Monitoring Configuration
HEALTH_CHECK_INTERVAL=30
PERFORMANCE_MONITORING=true
PROMETHEUS_ENABLED=true

# Security Settings
API_SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Database Configuration (if needed)
# DATABASE_URL=postgresql://user:pass@localhost/calendar_api

# LLM Configuration (optional)
# OLLAMA_BASE_URL=http://localhost:11434
# OPENAI_API_KEY=your-openai-key
EOF
```

### 2. Directory Structure Setup

Create required directories:
```bash
mkdir -p logs cache monitoring/grafana/{dashboards,datasources}
chmod 755 logs cache
```

### 3. Configure Monitoring

#### Grafana Datasources
```bash
cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
EOF
```

#### Grafana Dashboard
```bash
cat > monitoring/grafana/dashboards/calendar-api.json << EOF
{
  "dashboard": {
    "id": null,
    "title": "Calendar API Monitoring",
    "tags": ["calendar-api"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Parsing Accuracy",
        "type": "singlestat",
        "targets": [
          {
            "expr": "parsing_accuracy_score",
            "legendFormat": "Accuracy"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "cache_hit_rate",
            "legendFormat": "Hit Rate"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF
```

### 4. Deploy Services

Start the complete stack:
```bash
# Build and start all services
docker-compose -f deployment/docker-compose.prod.yml up -d

# Verify services are running
docker-compose -f deployment/docker-compose.prod.yml ps

# Check logs
docker-compose -f deployment/docker-compose.prod.yml logs -f calendar-api
```

### 5. Verify Deployment

#### Health Checks
```bash
# API health check
curl http://localhost:8000/healthz

# Detailed health with metrics
curl http://localhost:8000/healthz | jq

# Prometheus metrics
curl http://localhost:8000/metrics

# Cache statistics
curl http://localhost:8000/cache/stats | jq
```

#### Service Endpoints
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Alertmanager**: http://localhost:9093

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- `parsing_accuracy_score` - Current parsing accuracy
- `parsing_confidence_score` - Distribution of confidence scores
- `component_latency_seconds` - Component processing latency
- `cache_hit_rate` - Cache performance
- `llm_service_available` - LLM service availability

#### System Metrics
- `system_memory_usage_bytes` - Memory usage
- `system_cpu_usage_percent` - CPU utilization
- `api_uptime_seconds` - Service uptime

#### Error Metrics
- `parsing_errors_total` - Parsing errors by type
- `api_errors_total` - API errors by code

### Alert Configuration

Key alerts are configured in `monitoring/alert_rules.yml`:

1. **High Error Rate** - >10% error rate for 2 minutes
2. **High Response Time** - 95th percentile >2 seconds for 5 minutes
3. **Service Down** - Service unavailable for 1 minute
4. **High Memory Usage** - >800MB for 5 minutes
5. **Low Parsing Accuracy** - <70% accuracy for 10 minutes
6. **Low Cache Hit Rate** - <30% hit rate for 15 minutes
7. **LLM Service Unavailable** - LLM service down for 5 minutes
8. **High Component Latency** - 95th percentile >1 second for 5 minutes

### Log Aggregation

Logs are collected by Promtail and sent to Loki:

#### Log Types
- **Application Logs**: `/app/logs/calendar-api.log`
- **Error Logs**: `/app/logs/calendar-api-errors.log`
- **Parsing Decisions**: `/app/logs/parsing-decisions.log`
- **Performance Metrics**: `/app/logs/performance-metrics.log`

#### Log Queries in Grafana
```logql
# All application logs
{job="calendar-api"}

# Error logs only
{job="calendar-api"} |= "ERROR"

# Parsing decisions
{job="calendar-api"} | json | component="parsing_router"

# High latency requests
{job="calendar-api"} | json | duration_ms > 1000
```

## Performance Tuning

### Resource Allocation

#### Memory Settings
```yaml
# In docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 1G      # Adjust based on usage
    reservations:
      memory: 512M
```

#### CPU Settings
```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'     # Adjust based on load
    reservations:
      cpus: '0.25'
```

### Application Tuning

#### Cache Configuration
```bash
# Environment variables
CACHE_TTL_HOURS=24          # Cache time-to-live
CACHE_MAX_SIZE_MB=100       # Maximum cache size
```

#### Rate Limiting
```bash
RATE_LIMIT_PER_MINUTE=60    # Requests per minute per IP
RATE_LIMIT_PER_HOUR=1000    # Requests per hour per IP
```

#### Worker Configuration
```bash
# Gunicorn workers (in Dockerfile.prod)
--workers 4                  # Adjust based on CPU cores
--worker-class uvicorn.workers.UvicornWorker
```

## Security Considerations

### Network Security
- Use HTTPS in production with proper SSL certificates
- Configure firewall rules to restrict access
- Use reverse proxy (nginx/traefik) for SSL termination

### Application Security
- Set strong `API_SECRET_KEY`
- Configure CORS origins properly
- Enable rate limiting
- Regular security updates

### Monitoring Security
- Change default Grafana admin password
- Restrict access to monitoring endpoints
- Use authentication for Prometheus/Grafana

## Backup and Recovery

### Data Backup
```bash
# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Backup monitoring data
docker run --rm -v prometheus_data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup-$(date +%Y%m%d).tar.gz /data
```

### Recovery Procedures
1. Stop services: `docker-compose down`
2. Restore data volumes
3. Start services: `docker-compose up -d`
4. Verify health checks

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose logs calendar-api

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

#### High Memory Usage
```bash
# Monitor memory usage
docker stats calendar-api

# Check for memory leaks in logs
grep -i "memory\|oom" logs/calendar-api.log
```

#### Poor Performance
```bash
# Check component latencies
curl http://localhost:8000/metrics | grep component_latency

# Monitor cache hit rate
curl http://localhost:8000/cache/stats
```

#### Monitoring Issues
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify Grafana datasources
curl -u admin:admin123 http://localhost:3000/api/datasources
```

### Log Analysis

#### Find Parsing Errors
```bash
grep "parsing_error" logs/calendar-api.log | jq
```

#### Analyze Performance
```bash
grep "duration_ms" logs/performance-metrics.log | jq '.duration_ms' | sort -n
```

#### Check Component Health
```bash
grep "component.*failed" logs/calendar-api.log
```

## Maintenance

### Regular Tasks

#### Daily
- Check service health and alerts
- Monitor resource usage
- Review error logs

#### Weekly
- Analyze performance trends
- Update golden test set if needed
- Review and rotate logs

#### Monthly
- Update dependencies
- Review and tune alert thresholds
- Backup monitoring data
- Performance optimization review

### Updates and Upgrades

#### Application Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f deployment/docker-compose.prod.yml build calendar-api
docker-compose -f deployment/docker-compose.prod.yml up -d calendar-api
```

#### Monitoring Stack Updates
```bash
# Update monitoring services
docker-compose -f deployment/docker-compose.prod.yml pull prometheus grafana loki
docker-compose -f deployment/docker-compose.prod.yml up -d prometheus grafana loki
```

## Support and Monitoring

### Key Dashboards
- **Overview Dashboard**: Service health, request rates, error rates
- **Performance Dashboard**: Response times, component latencies, cache performance
- **Accuracy Dashboard**: Parsing accuracy, confidence distributions
- **System Dashboard**: Resource usage, uptime, alerts

### Alert Channels
Configure in `monitoring/alertmanager.yml`:
- Email notifications for critical alerts
- Slack integration for team notifications
- Webhook integration for custom handling

### Contact Information
- **Operations Team**: ops@yourdomain.com
- **Development Team**: dev@yourdomain.com
- **Emergency Contact**: +1-xxx-xxx-xxxx

This deployment provides comprehensive monitoring, logging, and alerting for the Calendar API system, ensuring reliable operation and quick issue resolution in production environments.