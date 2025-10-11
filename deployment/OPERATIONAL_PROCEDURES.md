# Operational Procedures

This document outlines standard operational procedures for the Calendar API production system, including monitoring, incident response, maintenance, and troubleshooting.

## Daily Operations

### Morning Health Check (9:00 AM)

1. **Service Status Verification**
   ```bash
   # Check all services are running
   docker-compose -f deployment/docker-compose.prod.yml ps
   
   # Verify API health
   curl -f http://localhost:8000/healthz || echo "API health check failed"
   
   # Check monitoring stack
   curl -f http://localhost:9090/-/healthy || echo "Prometheus health check failed"
   curl -f http://localhost:3000/api/health || echo "Grafana health check failed"
   ```

2. **Performance Metrics Review**
   - Open Grafana dashboard: http://localhost:3000
   - Review overnight metrics:
     - Request volume and error rates
     - Response time trends
     - Parsing accuracy scores
     - Cache hit rates
     - System resource usage

3. **Alert Review**
   ```bash
   # Check active alerts
   curl http://localhost:9093/api/v1/alerts | jq '.data[] | select(.status.state == "active")'
   
   # Review alert history from last 24 hours
   # Check Grafana alerts panel
   ```

4. **Log Analysis**
   ```bash
   # Check for errors in the last 24 hours
   grep "ERROR" logs/calendar-api.log | tail -20
   
   # Review parsing decision logs
   tail -50 logs/parsing-decisions.log | jq
   
   # Check for performance issues
   grep "duration_ms.*[0-9]{4,}" logs/performance-metrics.log | tail -10
   ```

### Evening Summary (6:00 PM)

1. **Daily Metrics Summary**
   - Total requests processed
   - Average response time
   - Error rate percentage
   - Parsing accuracy score
   - Cache performance
   - System uptime

2. **Issue Documentation**
   - Document any incidents or issues
   - Update runbooks if needed
   - Plan maintenance activities

## Incident Response

### Severity Levels

#### Critical (P1) - Service Down
- **Response Time**: 15 minutes
- **Escalation**: Immediate
- **Examples**: API completely unavailable, data corruption

#### High (P2) - Degraded Performance
- **Response Time**: 1 hour
- **Escalation**: 2 hours if unresolved
- **Examples**: High error rates, slow response times, parsing accuracy drop

#### Medium (P3) - Minor Issues
- **Response Time**: 4 hours
- **Escalation**: Next business day
- **Examples**: Cache performance issues, non-critical component failures

#### Low (P4) - Maintenance
- **Response Time**: Next business day
- **Escalation**: Weekly review
- **Examples**: Log rotation, minor optimizations

### Incident Response Procedures

#### 1. Initial Response (First 15 minutes)
```bash
# Immediate assessment
echo "=== INCIDENT RESPONSE CHECKLIST ==="
echo "1. Verify incident scope and impact"
curl -f http://localhost:8000/healthz
echo "2. Check service status"
docker-compose -f deployment/docker-compose.prod.yml ps
echo "3. Review recent alerts"
curl http://localhost:9093/api/v1/alerts | jq '.data[] | select(.status.state == "active")'
echo "4. Check system resources"
docker stats --no-stream
```

#### 2. Diagnosis (15-30 minutes)
```bash
# Detailed investigation
echo "=== DIAGNOSIS PHASE ==="
echo "1. Check application logs"
tail -100 logs/calendar-api-errors.log
echo "2. Review performance metrics"
curl http://localhost:8000/metrics | grep -E "(error|latency|memory)"
echo "3. Analyze component health"
grep "component.*failed" logs/calendar-api.log | tail -20
echo "4. Check external dependencies"
# Test LLM service, database connections, etc.
```

#### 3. Mitigation (30-60 minutes)
```bash
# Common mitigation steps
echo "=== MITIGATION ACTIONS ==="

# Restart services if needed
echo "Restarting services..."
docker-compose -f deployment/docker-compose.prod.yml restart calendar-api

# Scale resources if needed
echo "Checking resource limits..."
docker update --memory=2g --cpus=1.0 $(docker-compose ps -q calendar-api)

# Clear cache if corrupted
echo "Clearing cache if needed..."
curl -X DELETE http://localhost:8000/cache/clear

# Enable degraded mode if necessary
echo "Enabling degraded mode..."
# Set environment variable to disable LLM enhancement
```

#### 4. Communication
- **Internal**: Update team via Slack/email
- **External**: Update status page if customer-facing
- **Documentation**: Log incident details

### Common Incident Scenarios

#### High Error Rate (>10%)
```bash
# Investigation steps
echo "=== HIGH ERROR RATE INVESTIGATION ==="

# Check error distribution
curl http://localhost:8000/metrics | grep http_requests_total | grep "5.."

# Review recent error logs
grep "ERROR" logs/calendar-api.log | tail -50 | jq

# Check for specific error patterns
grep -E "(timeout|connection|parsing_error)" logs/calendar-api.log | tail -20

# Mitigation options
# 1. Restart service
# 2. Disable LLM enhancement temporarily
# 3. Increase timeout values
# 4. Scale resources
```

#### High Response Time (>2 seconds)
```bash
# Performance investigation
echo "=== HIGH RESPONSE TIME INVESTIGATION ==="

# Check component latencies
curl http://localhost:8000/metrics | grep component_latency_seconds

# Review performance logs
grep "duration_ms" logs/performance-metrics.log | tail -20 | jq

# Check system resources
docker stats --no-stream
free -h
iostat -x 1 3

# Mitigation options
# 1. Increase cache TTL
# 2. Optimize component processing
# 3. Scale horizontally
# 4. Tune garbage collection
```

#### Low Parsing Accuracy (<70%)
```bash
# Accuracy investigation
echo "=== LOW PARSING ACCURACY INVESTIGATION ==="

# Check recent parsing decisions
tail -100 logs/parsing-decisions.log | jq '.confidence_breakdown'

# Review golden test results
python -c "
from services.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
# Run accuracy evaluation
"

# Check for data quality issues
grep "low_confidence" logs/parsing-decisions.log | tail -20

# Mitigation options
# 1. Update golden test set
# 2. Retrain models if applicable
# 3. Adjust confidence thresholds
# 4. Enable manual review mode
```

## Maintenance Procedures

### Weekly Maintenance (Sundays 2:00 AM)

#### 1. Log Rotation and Cleanup
```bash
#!/bin/bash
echo "=== WEEKLY MAINTENANCE - LOG ROTATION ==="

# Rotate application logs
cd /opt/calendar-api
find logs/ -name "*.log" -size +100M -exec gzip {} \;
find logs/ -name "*.log.gz" -mtime +30 -delete

# Clean up old Docker images
docker image prune -f
docker volume prune -f

# Backup important logs
tar -czf backups/logs-$(date +%Y%m%d).tar.gz logs/
```

#### 2. Performance Analysis
```bash
#!/bin/bash
echo "=== WEEKLY MAINTENANCE - PERFORMANCE ANALYSIS ==="

# Generate weekly performance report
python scripts/generate_performance_report.py --period=week

# Update golden test set if needed
python scripts/update_golden_set.py --auto-update

# Check for memory leaks
docker stats --no-stream | grep calendar-api
```

#### 3. Security Updates
```bash
#!/bin/bash
echo "=== WEEKLY MAINTENANCE - SECURITY UPDATES ==="

# Update base images
docker-compose -f deployment/docker-compose.prod.yml pull

# Check for security vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image calendar-api:latest

# Update dependencies if needed
pip list --outdated
```

### Monthly Maintenance (First Sunday 1:00 AM)

#### 1. Full System Backup
```bash
#!/bin/bash
echo "=== MONTHLY MAINTENANCE - FULL BACKUP ==="

# Stop services for consistent backup
docker-compose -f deployment/docker-compose.prod.yml stop

# Backup all data
tar -czf backups/full-backup-$(date +%Y%m%d).tar.gz \
  logs/ cache/ monitoring/ deployment/

# Backup Docker volumes
docker run --rm -v prometheus_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz /data

# Restart services
docker-compose -f deployment/docker-compose.prod.yml start
```

#### 2. Performance Optimization Review
```bash
#!/bin/bash
echo "=== MONTHLY MAINTENANCE - PERFORMANCE REVIEW ==="

# Analyze monthly performance trends
python scripts/monthly_performance_analysis.py

# Review and update alert thresholds
python scripts/optimize_alert_thresholds.py

# Update capacity planning
python scripts/capacity_planning_analysis.py
```

#### 3. Dependency Updates
```bash
#!/bin/bash
echo "=== MONTHLY MAINTENANCE - DEPENDENCY UPDATES ==="

# Update Python dependencies
pip install --upgrade -r requirements.txt

# Update monitoring stack
docker-compose -f deployment/docker-compose.prod.yml pull

# Test updates in staging environment first
# Deploy to production after validation
```

## Monitoring and Alerting

### Key Performance Indicators (KPIs)

#### Service Level Objectives (SLOs)
- **Availability**: 99.9% uptime
- **Response Time**: 95th percentile < 2 seconds
- **Error Rate**: < 1% of requests
- **Parsing Accuracy**: > 85% overall

#### Monitoring Dashboards

1. **Executive Dashboard**
   - Service availability
   - Request volume trends
   - Error rate trends
   - User satisfaction metrics

2. **Operations Dashboard**
   - Real-time service health
   - Resource utilization
   - Alert status
   - Performance metrics

3. **Development Dashboard**
   - Parsing accuracy trends
   - Component performance
   - Error analysis
   - Feature usage statistics

### Alert Management

#### Alert Escalation Matrix
```
Level 1: On-call engineer (0-15 minutes)
Level 2: Team lead (15-60 minutes)
Level 3: Engineering manager (1-4 hours)
Level 4: Director of Engineering (4+ hours)
```

#### Alert Tuning Guidelines
- Review alert thresholds monthly
- Reduce false positives
- Ensure actionable alerts only
- Document alert response procedures

## Troubleshooting Guide

### Performance Issues

#### High CPU Usage
```bash
# Investigation
top -p $(pgrep -f calendar-api)
docker stats calendar-api

# Common causes and solutions
# 1. High request volume -> Scale horizontally
# 2. Inefficient parsing -> Profile and optimize
# 3. Memory pressure -> Increase memory limits
# 4. Background tasks -> Optimize scheduling
```

#### High Memory Usage
```bash
# Investigation
docker stats calendar-api
ps aux | grep calendar-api

# Memory leak detection
python -c "
import psutil
import time
process = psutil.Process()
for i in range(10):
    print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
    time.sleep(60)
"

# Solutions
# 1. Restart service if memory leak
# 2. Increase memory limits
# 3. Optimize cache size
# 4. Profile memory usage
```

#### Slow Response Times
```bash
# Investigation
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/parse

# Component profiling
grep "component_latency" logs/performance-metrics.log | tail -20

# Solutions
# 1. Optimize slow components
# 2. Increase cache hit rate
# 3. Tune database queries
# 4. Scale resources
```

### Service Issues

#### Service Won't Start
```bash
# Check Docker logs
docker-compose -f deployment/docker-compose.prod.yml logs calendar-api

# Common issues
# 1. Port conflicts -> Change port mapping
# 2. Missing environment variables -> Check .env file
# 3. Resource constraints -> Increase limits
# 4. Configuration errors -> Validate config
```

#### Database Connection Issues
```bash
# Test database connectivity
python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://user:pass@localhost/db')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"

# Solutions
# 1. Check database service status
# 2. Verify connection parameters
# 3. Check network connectivity
# 4. Review database logs
```

### Data Issues

#### Cache Corruption
```bash
# Clear cache
curl -X DELETE http://localhost:8000/cache/clear

# Verify cache operation
curl http://localhost:8000/cache/stats

# Monitor cache performance
watch -n 5 'curl -s http://localhost:8000/cache/stats | jq .hit_ratio'
```

#### Parsing Accuracy Drop
```bash
# Run golden test evaluation
python scripts/run_golden_tests.py

# Analyze recent parsing decisions
tail -100 logs/parsing-decisions.log | jq '.confidence_breakdown'

# Check for data quality issues
grep "parsing_error" logs/calendar-api.log | tail -20
```

## Emergency Procedures

### Complete Service Outage
1. **Immediate Actions** (0-5 minutes)
   - Verify outage scope
   - Check infrastructure status
   - Activate incident response team

2. **Recovery Actions** (5-15 minutes)
   - Restart all services
   - Check dependencies
   - Verify data integrity

3. **Communication** (15-30 minutes)
   - Notify stakeholders
   - Update status page
   - Provide regular updates

### Data Corruption
1. **Stop all write operations**
2. **Assess corruption scope**
3. **Restore from latest backup**
4. **Verify data integrity**
5. **Resume operations**

### Security Incident
1. **Isolate affected systems**
2. **Preserve evidence**
3. **Notify security team**
4. **Follow security incident response plan**

## Contact Information

### On-Call Rotation
- **Primary**: +1-xxx-xxx-xxxx
- **Secondary**: +1-xxx-xxx-xxxx
- **Escalation**: +1-xxx-xxx-xxxx

### Team Contacts
- **Operations Team**: ops@yourdomain.com
- **Development Team**: dev@yourdomain.com
- **Security Team**: security@yourdomain.com
- **Management**: management@yourdomain.com

### External Vendors
- **Cloud Provider**: support@cloudprovider.com
- **Monitoring Service**: support@monitoring.com
- **Security Service**: support@security.com

This operational procedures document should be reviewed and updated quarterly to ensure it remains current with system changes and operational learnings.