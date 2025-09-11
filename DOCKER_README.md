# Credit Check Scheduler - Docker Setup

This Docker setup runs the credit check scheduler with even claim IDs by default.

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and run:**
   ```bash
   docker-compose up --build
   ```

2. **Run in background:**
   ```bash
   docker-compose up -d --build
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop:**
   ```bash
   docker-compose down
   ```

### Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t creditcheck-scheduler .
   ```

2. **Run with even claim IDs (default):**
   ```bash
   docker run -d --name creditcheck-scheduler \
     -v $(pwd)/output:/app/output \
     -v $(pwd)/logs:/app/logs \
     creditcheck-scheduler
   ```

3. **Run with odd claim IDs:**
   ```bash
   docker run -d --name creditcheck-scheduler \
     -v $(pwd)/output:/app/output \
     -v $(pwd)/logs:/app/logs \
     creditcheck-scheduler python scheduler.py odd
   ```

## Configuration

### Changing Claim Type

To run with odd claim IDs instead of even, modify the `docker-compose.yml`:

```yaml
services:
  creditcheck-scheduler:
    # ... other config
    command: python scheduler.py odd
```

### Volume Mounts

The following directories are mounted to persist data:
- `./output` → `/app/output` (CSV files)
- `./logs` → `/app/logs` (log files)
- `./overall_checked_claims.csv` → `/app/overall_checked_claims.csv` (processed claims)

## Schedule

- **Claims scraping**: Every hour at :30 (alternates between even/odd)
- **Credit checking**: Every hour at :00

## Monitoring

### View logs in real-time:
```bash
docker-compose logs -f
```

### Check container status:
```bash
docker-compose ps
```

### Access container shell:
```bash
docker-compose exec creditcheck-scheduler bash
```

## Troubleshooting

### Container won't start:
1. Check logs: `docker-compose logs`
2. Ensure Chrome dependencies are installed
3. Verify file permissions on mounted volumes

### Selenium/Chrome issues:
1. The container includes Xvfb for headless operation
2. Chrome is installed and configured for headless mode
3. All necessary system dependencies are included

### File permissions:
```bash
# Fix output directory permissions
sudo chown -R $USER:$USER output/
sudo chown -R $USER:$USER logs/
```
