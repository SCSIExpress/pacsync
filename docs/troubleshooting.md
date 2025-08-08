# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Pacman Sync Utility.

## Quick Diagnostic Commands

Before diving into specific issues, run these diagnostic commands:

```bash
# Server diagnostics
python3 -m server.main --check-config
python3 -m server.database.connection --test
curl http://your-server:8080/health/live

# Client diagnostics
python3 -m client.main --check-config
python3 -m client.main --test-connection
python3 -m client.main --status --debug
```

## Server Issues

### Server Won't Start

#### Symptoms
- Server process exits immediately
- "Connection refused" errors from clients
- No response from health check endpoints

#### Diagnostic Steps

1. **Check Configuration**
   ```bash
   # Validate server configuration
   python3 -m server.main --check-config --verbose
   
   # Check for syntax errors
   python3 -c "import configparser; configparser.ConfigParser().read('/etc/pacman-sync/server.conf')"
   ```

2. **Test Database Connection**
   ```bash
   # Test PostgreSQL connection
   python3 -m server.database.connection --test
   
   # Check database credentials
   psql -h localhost -U pacman_sync -d pacman_sync_db -c "SELECT 1;"
   ```

3. **Check Port Availability**
   ```bash
   # Check if port is in use
   sudo netstat -tlnp | grep :8080
   
   # Test port binding
   python3 -c "import socket; s=socket.socket(); s.bind(('0.0.0.0', 8080)); print('Port available')"
   ```

4. **Review Logs**
   ```bash
   # Check systemd logs
   sudo journalctl -u pacman-sync-server --no-pager -n 50
   
   # Check application logs
   tail -f /var/log/pacman-sync/server.log
   ```

#### Common Solutions

**Database Connection Issues:**
```bash
# Fix PostgreSQL connection
sudo systemctl start postgresql
sudo -u postgres createdb pacman_sync_db
sudo -u postgres createuser -P pacman_sync

# Update connection string in config
sudo nano /etc/pacman-sync/server.conf
```

**Permission Issues:**
```bash
# Fix file permissions
sudo chown -R pacman-sync:pacman-sync /opt/pacman-sync
sudo chmod +x /opt/pacman-sync/server/main.py

# Fix log directory permissions
sudo mkdir -p /var/log/pacman-sync
sudo chown pacman-sync:pacman-sync /var/log/pacman-sync
```

**Port Conflicts:**
```bash
# Change server port in configuration
sudo nano /etc/pacman-sync/server.conf
# Set: port = 8081

# Or kill conflicting process
sudo lsof -ti:8080 | xargs sudo kill -9
```

### Database Issues

#### Database Connection Failures

**Symptoms:**
- "Connection refused" database errors
- Timeout errors during database operations
- Migration failures

**Solutions:**

1. **PostgreSQL Setup**
   ```bash
   # Install and start PostgreSQL
   sudo pacman -S postgresql
   sudo -u postgres initdb -D /var/lib/postgres/data
   sudo systemctl enable --now postgresql
   
   # Create database and user
   sudo -u postgres createuser -P pacman_sync
   sudo -u postgres createdb -O pacman_sync pacman_sync_db
   
   # Test connection
   psql -h localhost -U pacman_sync -d pacman_sync_db -c "SELECT version();"
   ```

2. **SQLite Issues**
   ```bash
   # Check SQLite file permissions
   ls -la /var/lib/pacman-sync/database.db
   
   # Fix permissions
   sudo chown pacman-sync:pacman-sync /var/lib/pacman-sync/database.db
   sudo chmod 664 /var/lib/pacman-sync/database.db
   ```

3. **Connection Pool Issues**
   ```bash
   # Reduce connection pool size in config
   sudo nano /etc/pacman-sync/server.conf
   # Set: pool_size = 5
   # Set: max_overflow = 10
   ```

#### Migration Failures

**Symptoms:**
- "Table doesn't exist" errors
- Schema version mismatches
- Migration timeout errors

**Solutions:**

1. **Manual Migration**
   ```bash
   # Run migrations manually
   python3 -m server.database.migrations --apply-all
   
   # Check migration status
   python3 -m server.database.migrations --status
   
   # Reset migrations (CAUTION: destroys data)
   python3 -m server.database.migrations --reset --confirm
   ```

2. **Schema Repair**
   ```bash
   # Backup database first
   pg_dump -h localhost -U pacman_sync pacman_sync_db > backup.sql
   
   # Drop and recreate schema
   python3 -m server.database.schema --recreate --confirm
   ```

### Web UI Issues

#### Web UI Not Loading

**Symptoms:**
- Blank page or 404 errors
- Static files not found
- JavaScript errors in browser console

**Solutions:**

1. **Check Static Files**
   ```bash
   # Verify static files exist
   ls -la /opt/pacman-sync/server/web/dist/
   
   # Rebuild web UI
   cd /opt/pacman-sync/server/web
   npm install
   npm run build
   ```

2. **Check Web Server Configuration**
   ```bash
   # Verify web UI is enabled in config
   grep -A 5 "\[web_ui\]" /etc/pacman-sync/server.conf
   
   # Test direct file access
   curl http://localhost:8080/static/index.html
   ```

#### API Errors in Web UI

**Symptoms:**
- "Failed to fetch" errors
- Authentication errors
- CORS errors in browser console

**Solutions:**

1. **CORS Configuration**
   ```bash
   # Enable CORS in server config
   sudo nano /etc/pacman-sync/server.conf
   # Add: enable_cors = true
   # Add: cors_origins = http://localhost:3000,https://your-domain.com
   ```

2. **API Key Issues**
   ```bash
   # Generate new API key for web UI
   python3 -m server.auth.generate_key --name "web-ui" --permissions admin
   ```

## Client Issues

### System Tray Icon Not Appearing

#### Symptoms
- No system tray icon visible
- Client appears to start but no GUI
- "System tray not available" errors

#### Diagnostic Steps

1. **Test System Tray Support**
   ```bash
   # Test tray availability
   python3 -m client.qt.application --test-tray
   
   # Check desktop environment
   echo $XDG_CURRENT_DESKTOP
   echo $DESKTOP_SESSION
   ```

2. **Check Required Packages**
   ```bash
   # Install system tray support packages
   sudo pacman -S libappindicator-gtk3 libayatana-appindicator
   
   # For KDE
   sudo pacman -S plasma-workspace
   
   # For GNOME
   sudo pacman -S gnome-shell-extension-appindicator
   ```

3. **Test Qt Installation**
   ```bash
   # Test Qt components
   python3 -c "from PyQt6.QtWidgets import QApplication, QSystemTrayIcon; print('Qt OK')"
   
   # Test system tray specifically
   python3 -c "from PyQt6.QtWidgets import QApplication, QSystemTrayIcon; app=QApplication([]); print('Tray available:', QSystemTrayIcon.isSystemTrayAvailable())"
   ```

#### Solutions

**Missing System Tray Support:**
```bash
# For GNOME with Wayland
sudo pacman -S gnome-shell-extension-appindicator
gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com

# For KDE
sudo pacman -S plasma-workspace
systemctl --user restart plasma-plasmashell

# For other DEs, install libappindicator
sudo pacman -S libappindicator-gtk3
```

**Run Without System Tray:**
```bash
# Run client without tray icon
python3 -m client.main --no-tray

# Use CLI mode instead
python3 -m client.main --status
python3 -m client.main --sync
```

### Client Cannot Connect to Server

#### Symptoms
- "Connection refused" errors
- Timeout errors
- Authentication failures

#### Diagnostic Steps

1. **Test Network Connectivity**
   ```bash
   # Test basic connectivity
   ping your-server-hostname
   
   # Test HTTP connectivity
   curl -v http://your-server:8080/health/live
   
   # Test with timeout
   curl --connect-timeout 10 http://your-server:8080/health/live
   ```

2. **Check Client Configuration**
   ```bash
   # Validate client config
   python3 -m client.main --check-config --verbose
   
   # Show effective configuration
   python3 -m client.main --show-config
   ```

3. **Test API Authentication**
   ```bash
   # Test API key
   python3 -m client.api_client --test-auth
   
   # Manual API test
   curl -H "Authorization: Bearer your-api-key" \
        http://your-server:8080/api/v1/endpoints
   ```

#### Solutions

**Network Issues:**
```bash
# Check firewall rules
sudo iptables -L | grep 8080
sudo ufw status

# Add firewall rule if needed
sudo ufw allow 8080/tcp

# Check DNS resolution
nslookup your-server-hostname
```

**Configuration Issues:**
```bash
# Fix server URL in client config
nano ~/.config/pacman-sync/client.conf
# Set: url = http://correct-server:8080

# Generate new API key
python3 -m server.auth.generate_key --endpoint-name "$(hostname)"
```

**SSL/TLS Issues:**
```bash
# For HTTPS servers with self-signed certificates
echo "verify_ssl = false" >> ~/.config/pacman-sync/client.conf

# Or add certificate to system trust store
sudo cp server-cert.pem /etc/ca-certificates/trust-source/anchors/
sudo trust extract-compat
```

### Pacman Integration Issues

#### Symptoms
- "Permission denied" when running pacman
- Package operations fail
- Pacman database lock errors

#### Solutions

1. **Sudo Configuration**
   ```bash
   # Add user to sudoers for pacman
   echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/pacman" | sudo tee /etc/sudoers.d/pacman-sync
   
   # Test sudo access
   sudo -n pacman -Q | head -5
   ```

2. **Pacman Lock Issues**
   ```bash
   # Check for pacman lock
   ls -la /var/lib/pacman/db.lck
   
   # Remove stale lock (CAUTION: ensure no pacman is running)
   sudo rm -f /var/lib/pacman/db.lck
   
   # Check for running pacman processes
   ps aux | grep pacman
   ```

3. **Database Corruption**
   ```bash
   # Check pacman database
   sudo pacman -Dk
   
   # Refresh package databases
   sudo pacman -Sy
   
   # Rebuild package database (last resort)
   sudo pacman-db-upgrade
   ```

## Synchronization Issues

### Sync Operations Fail

#### Package Conflicts

**Symptoms:**
- "Conflicting dependencies" errors
- "Package not found" errors
- Partial sync completion

**Solutions:**

1. **Repository Analysis**
   ```bash
   # Check repository compatibility
   python3 -m client.main --analyze-repos
   
   # Update repository databases
   sudo pacman -Sy
   
   # Check for repository issues
   pacman -Ss nonexistent-package
   ```

2. **Conflict Resolution**
   ```bash
   # Run sync with conflict resolution
   python3 -m client.main --sync --resolve-conflicts auto
   
   # Manual conflict resolution
   python3 -m client.main --sync --interactive
   
   # Exclude problematic packages
   python3 -m client.main --sync --exclude problematic-package
   ```

3. **Package Exclusions**
   ```bash
   # Add permanent exclusions to config
   nano ~/.config/pacman-sync/client.conf
   # Add: exclude_packages = linux,nvidia-dkms,custom-package
   
   # Temporary exclusion
   python3 -m client.main --sync --exclude linux,nvidia-dkms
   ```

#### Disk Space Issues

**Symptoms:**
- "No space left on device" errors
- Sync stops during package download
- Cache directory full

**Solutions:**

1. **Clean Package Cache**
   ```bash
   # Clean pacman cache
   sudo pacman -Sc
   
   # Clean all cached packages
   sudo pacman -Scc
   
   # Check disk space
   df -h /var/cache/pacman/pkg
   ```

2. **Increase Disk Space**
   ```bash
   # Check disk usage
   du -sh /var/cache/pacman/pkg
   du -sh ~/.cache/
   
   # Move cache to larger partition
   sudo mkdir /home/pacman-cache
   sudo ln -sf /home/pacman-cache /var/cache/pacman/pkg
   ```

### Pool State Issues

#### Endpoints Out of Sync

**Symptoms:**
- Endpoints show different sync states
- "State mismatch" errors
- Inconsistent package versions across pool

**Solutions:**

1. **Force State Refresh**
   ```bash
   # Refresh endpoint state
   python3 -m client.main --refresh-state
   
   # Force server sync
   python3 -m client.main --sync --force
   ```

2. **Reset Pool State**
   ```bash
   # Set current endpoint as pool target
   python3 -m client.main --set-latest --force
   
   # Or sync to specific endpoint's state
   python3 -m client.main --sync-to-endpoint other-endpoint-id
   ```

3. **Repository Compatibility Check**
   ```bash
   # Check repository differences
   python3 -m client.main --compare-repos
   
   # Update repository analysis
   curl -X POST http://server:8080/api/v1/pools/pool-id/analyze
   ```

## Performance Issues

### Slow Synchronization

#### Symptoms
- Sync operations take very long
- High CPU/memory usage during sync
- Network timeouts

#### Solutions

1. **Network Optimization**
   ```bash
   # Increase timeout values
   nano ~/.config/pacman-sync/client.conf
   # Add: timeout = 300
   # Add: retry_attempts = 5
   
   # Use faster mirrors
   sudo pacman-mirrors --fasttrack
   ```

2. **Parallel Downloads**
   ```bash
   # Enable parallel downloads in pacman
   sudo nano /etc/pacman.conf
   # Uncomment: ParallelDownloads = 5
   ```

3. **Resource Limits**
   ```bash
   # Check system resources during sync
   htop
   iotop
   
   # Limit sync concurrency
   nano ~/.config/pacman-sync/client.conf
   # Add: max_concurrent_operations = 2
   ```

### High Memory Usage

#### Symptoms
- System becomes unresponsive during sync
- Out of memory errors
- Swap usage increases significantly

#### Solutions

1. **Memory Optimization**
   ```bash
   # Reduce package cache size
   sudo nano /etc/pacman.conf
   # Add: CacheDir = /tmp/pacman-cache
   
   # Increase swap space
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

2. **Process Limits**
   ```bash
   # Limit client memory usage
   systemctl --user edit pacman-sync-client
   # Add:
   # [Service]
   # MemoryMax=512M
   # MemoryHigh=256M
   ```

## Monitoring and Logging

### Enable Debug Logging

#### Server Debug Logging
```bash
# Enable debug in server config
sudo nano /etc/pacman-sync/server.conf
# Set: level = DEBUG

# Restart server
sudo systemctl restart pacman-sync-server

# Monitor logs
sudo journalctl -u pacman-sync-server -f
```

#### Client Debug Logging
```bash
# Run client with debug
python3 -m client.main --debug --verbose

# Enable debug in config
nano ~/.config/pacman-sync/client.conf
# Set: level = DEBUG

# Monitor client logs
journalctl --user -u pacman-sync-client -f
```

### Log Analysis

#### Common Log Patterns

**Connection Issues:**
```bash
# Search for connection errors
grep -i "connection" /var/log/pacman-sync/server.log
grep -i "timeout" ~/.local/share/pacman-sync/client.log
```

**Authentication Issues:**
```bash
# Search for auth errors
grep -i "unauthorized\|forbidden" /var/log/pacman-sync/server.log
grep -i "auth" ~/.local/share/pacman-sync/client.log
```

**Database Issues:**
```bash
# Search for database errors
grep -i "database\|sql" /var/log/pacman-sync/server.log
```

#### Log Rotation

```bash
# Set up log rotation
sudo nano /etc/logrotate.d/pacman-sync

# Add:
/var/log/pacman-sync/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 pacman-sync pacman-sync
    postrotate
        systemctl reload pacman-sync-server
    endscript
}
```

### Health Monitoring

#### System Health Checks

```bash
# Server health check script
#!/bin/bash
# health-check.sh

SERVER_URL="http://localhost:8080"

# Check server health
if curl -f "$SERVER_URL/health/live" >/dev/null 2>&1; then
    echo "✓ Server is healthy"
else
    echo "✗ Server health check failed"
    exit 1
fi

# Check database
if curl -f "$SERVER_URL/health/ready" >/dev/null 2>&1; then
    echo "✓ Database is healthy"
else
    echo "✗ Database health check failed"
    exit 1
fi

# Check client connectivity
if python3 -m client.main --test-connection --quiet; then
    echo "✓ Client connectivity OK"
else
    echo "✗ Client connectivity failed"
    exit 1
fi
```

#### Automated Monitoring

```bash
# Add to crontab for regular health checks
# crontab -e
*/5 * * * * /usr/local/bin/health-check.sh || echo "Health check failed" | mail -s "Pacman Sync Alert" admin@example.com
```

### Prometheus Monitoring

#### Metrics Collection

```bash
# Enable metrics in server config
sudo nano /etc/pacman-sync/server.conf
# Add:
# [metrics]
# enabled = true
# endpoint = /metrics

# Scrape metrics
curl http://localhost:8080/metrics
```

#### Grafana Dashboard

Example Prometheus queries:
```promql
# Sync operation success rate
rate(pacman_sync_operations_total{status="success"}[5m]) / rate(pacman_sync_operations_total[5m])

# Average sync duration
rate(pacman_sync_operation_duration_seconds_sum[5m]) / rate(pacman_sync_operation_duration_seconds_count[5m])

# Endpoint status
pacman_sync_endpoints_by_status
```

## Recovery Procedures

### Database Recovery

#### Backup and Restore

```bash
# Create database backup
pg_dump -h localhost -U pacman_sync pacman_sync_db > backup-$(date +%Y%m%d).sql

# Restore from backup
sudo systemctl stop pacman-sync-server
sudo -u postgres dropdb pacman_sync_db
sudo -u postgres createdb -O pacman_sync pacman_sync_db
psql -h localhost -U pacman_sync -d pacman_sync_db < backup-20240115.sql
sudo systemctl start pacman-sync-server
```

#### Corruption Recovery

```bash
# Check database integrity
sudo -u postgres vacuumdb --analyze --verbose pacman_sync_db

# Repair corruption (PostgreSQL)
sudo -u postgres reindexdb pacman_sync_db

# For SQLite
sqlite3 /var/lib/pacman-sync/database.db "PRAGMA integrity_check;"
sqlite3 /var/lib/pacman-sync/database.db "VACUUM;"
```

### Configuration Recovery

#### Reset to Defaults

```bash
# Backup current config
cp ~/.config/pacman-sync/client.conf ~/.config/pacman-sync/client.conf.backup

# Reset to defaults
python3 -m client.main --reset-config

# Restore specific settings
python3 -m client.main --set-config server.url=http://your-server:8080
python3 -m client.main --set-config client.endpoint_name=$(hostname)
```

### System Recovery

#### Complete Reinstallation

```bash
# Stop services
sudo systemctl stop pacman-sync-server
systemctl --user stop pacman-sync-client

# Backup data
sudo tar -czf pacman-sync-backup.tar.gz \
    /etc/pacman-sync/ \
    /var/lib/pacman-sync/ \
    ~/.config/pacman-sync/

# Remove installation
sudo rm -rf /opt/pacman-sync
sudo rm -rf /etc/pacman-sync
rm -rf ~/.config/pacman-sync
rm -rf ~/.local/share/pacman-sync

# Reinstall
sudo ./install.sh --server --client --systemd

# Restore configuration
sudo tar -xzf pacman-sync-backup.tar.gz -C /
```

## Getting Additional Help

### Diagnostic Report Generation

```bash
# Generate comprehensive diagnostic report
python3 -m client.main --diagnose --full --report diagnostic-report.txt

# Include system information
python3 -m client.main --diagnose --system-info --report system-diagnostic.txt

# Server diagnostic report
python3 -m server.main --diagnose --report server-diagnostic.txt
```

### Community Support

1. **GitHub Issues**: Report bugs and request features
2. **Documentation**: Check latest documentation updates
3. **Logs**: Always include relevant log excerpts in support requests
4. **System Info**: Include OS version, Python version, and package versions

### Professional Support

For production deployments requiring professional support:

1. **Monitoring Setup**: Implement comprehensive monitoring
2. **Backup Strategies**: Set up automated backups
3. **Performance Tuning**: Optimize for your specific environment
4. **Security Hardening**: Implement security best practices

## Prevention Best Practices

### Regular Maintenance

```bash
# Weekly maintenance script
#!/bin/bash
# weekly-maintenance.sh

# Clean old logs
find /var/log/pacman-sync/ -name "*.log" -mtime +30 -delete

# Backup database
pg_dump -h localhost -U pacman_sync pacman_sync_db > /backup/weekly-$(date +%Y%m%d).sql

# Clean old backups
find /backup/ -name "weekly-*.sql" -mtime +90 -delete

# Update repository analysis
curl -X POST http://localhost:8080/api/v1/pools/*/analyze

# Health check
python3 -m client.main --test-all
```

### Monitoring Setup

```bash
# Set up monitoring alerts
# Add to crontab:
0 */6 * * * /usr/local/bin/health-check.sh || echo "Health check failed at $(date)" >> /var/log/pacman-sync/alerts.log
```

### Configuration Management

```bash
# Version control for configurations
cd /etc/pacman-sync
git init
git add .
git commit -m "Initial configuration"

# Track changes
git add -A && git commit -m "Updated configuration $(date)"
```