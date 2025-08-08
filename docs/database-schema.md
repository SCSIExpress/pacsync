# Database Schema Documentation

This document describes the database schema used by the Pacman Sync Utility, including table structures, relationships, and migration procedures.

## Overview

The Pacman Sync Utility uses a relational database to store:
- **Package Pools**: Groups of endpoints with synchronized package states
- **Endpoints**: Individual client machines registered with the server
- **Package States**: Snapshots of package installations at specific points in time
- **Repository Information**: Available packages and repositories for each endpoint
- **Sync Operations**: History of synchronization operations and their results

## Supported Databases

- **PostgreSQL 12+** (Recommended for production)
- **SQLite 3.35+** (Development and single-user deployments)

## Core Tables

### pools

Stores package pool definitions and configuration.

```sql
CREATE TABLE pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_pools_name ON pools(name);
CREATE INDEX idx_pools_created_at ON pools(created_at);
```

**Settings JSONB Structure:**
```json
{
    "auto_sync": false,
    "conflict_resolution": "manual",
    "excluded_packages": ["linux", "nvidia"],
    "excluded_repos": ["testing"],
    "max_history": 50,
    "sync_schedule": "0 2 * * *"
}
```

### endpoints

Stores registered client endpoints and their current status.

```sql
CREATE TABLE endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    hostname VARCHAR(255) NOT NULL,
    pool_id UUID REFERENCES pools(id) ON DELETE SET NULL,
    api_key_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'offline',
    sync_status VARCHAR(50) DEFAULT 'unknown',
    system_info JSONB DEFAULT '{}',
    last_seen TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_endpoints_pool_id ON endpoints(pool_id);
CREATE INDEX idx_endpoints_name ON endpoints(name);
CREATE INDEX idx_endpoints_status ON endpoints(status);
CREATE INDEX idx_endpoints_last_seen ON endpoints(last_seen);
```

**System Info JSONB Structure:**
```json
{
    "architecture": "x86_64",
    "pacman_version": "6.0.2",
    "kernel": "6.1.12-arch1-1",
    "total_packages": 1247,
    "available_repos": ["core", "extra", "community"],
    "python_version": "3.11.1",
    "client_version": "1.0.0"
}
```

**Status Values:**
- `online`: Endpoint is connected and responsive
- `offline`: Endpoint hasn't been seen recently
- `error`: Endpoint reported an error condition

**Sync Status Values:**
- `in_sync`: Endpoint matches pool target state
- `behind`: Endpoint has older packages than target
- `ahead`: Endpoint has newer packages than target
- `sync_pending`: Synchronization operation in progress
- `unknown`: Sync status not yet determined

### package_states

Stores snapshots of package installations for endpoints and pools.

```sql
CREATE TABLE package_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID REFERENCES pools(id) ON DELETE CASCADE,
    endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
    state_data JSONB NOT NULL,
    is_target BOOLEAN DEFAULT FALSE,
    message TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_package_states_pool_id ON package_states(pool_id);
CREATE INDEX idx_package_states_endpoint_id ON package_states(endpoint_id);
CREATE INDEX idx_package_states_is_target ON package_states(is_target);
CREATE INDEX idx_package_states_created_at ON package_states(created_at);

-- Ensure only one target state per pool
CREATE UNIQUE INDEX idx_package_states_unique_target 
ON package_states(pool_id) WHERE is_target = TRUE;
```

**State Data JSONB Structure:**
```json
{
    "packages": {
        "firefox": {
            "version": "110.0-1",
            "repository": "extra",
            "size": 52428800,
            "dependencies": ["gtk3", "libxt", "dbus-glib"],
            "install_date": "2024-01-15T10:30:00Z"
        },
        "chromium": {
            "version": "109.0.5414.119-1",
            "repository": "extra",
            "size": 89128960,
            "dependencies": ["gtk3", "nss", "libxss"],
            "install_date": "2024-01-14T15:20:00Z"
        }
    },
    "metadata": {
        "total_packages": 1247,
        "total_size": 8589934592,
        "capture_method": "pacman_query",
        "excluded_packages": ["linux", "nvidia"]
    }
}
```

### repositories

Stores repository information and available packages for each endpoint.

```sql
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
    repo_name VARCHAR(255) NOT NULL,
    repo_url VARCHAR(500),
    packages JSONB DEFAULT '{}',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_repositories_endpoint_id ON repositories(endpoint_id);
CREATE INDEX idx_repositories_repo_name ON repositories(repo_name);
CREATE INDEX idx_repositories_last_updated ON repositories(last_updated);

-- Unique constraint for endpoint-repo combination
CREATE UNIQUE INDEX idx_repositories_endpoint_repo 
ON repositories(endpoint_id, repo_name);
```

**Packages JSONB Structure:**
```json
{
    "packages": {
        "firefox": {
            "version": "110.0-1",
            "description": "Standalone web browser from mozilla.org",
            "size": 52428800,
            "dependencies": ["gtk3", "libxt", "dbus-glib"],
            "last_modified": "2024-01-15T08:00:00Z"
        }
    },
    "metadata": {
        "total_packages": 12450,
        "last_sync": "2024-01-15T10:00:00Z",
        "sync_method": "pacman_database"
    }
}
```

### sync_operations

Logs all synchronization operations and their results.

```sql
CREATE TABLE sync_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID REFERENCES pools(id) ON DELETE CASCADE,
    endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    details JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sync_operations_pool_id ON sync_operations(pool_id);
CREATE INDEX idx_sync_operations_endpoint_id ON sync_operations(endpoint_id);
CREATE INDEX idx_sync_operations_status ON sync_operations(status);
CREATE INDEX idx_sync_operations_started_at ON sync_operations(started_at);
CREATE INDEX idx_sync_operations_type ON sync_operations(operation_type);
```

**Operation Types:**
- `sync_to_latest`: Sync endpoint to pool target state
- `set_as_latest`: Set endpoint state as pool target
- `revert_to_previous`: Revert to previous state
- `repository_analysis`: Analyze repository compatibility

**Status Values:**
- `pending`: Operation queued but not started
- `in_progress`: Operation currently running
- `completed`: Operation finished successfully
- `failed`: Operation failed with errors
- `cancelled`: Operation was cancelled by user

**Details JSONB Structure:**
```json
{
    "packages_to_install": ["firefox", "chromium"],
    "packages_to_remove": ["old-package"],
    "packages_to_upgrade": ["git", "vim"],
    "total_packages": 25,
    "estimated_size": 104857600,
    "dry_run": false,
    "force": false,
    "exclude_packages": ["linux"],
    "conflict_resolution": "newest"
}
```

## Auxiliary Tables

### api_keys

Stores API keys for endpoint authentication.

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    permissions JSONB DEFAULT '{}',
    last_used TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_api_keys_endpoint_id ON api_keys(endpoint_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at);
```

### system_events

Logs system-wide events and administrative actions.

```sql
CREATE TABLE system_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'info',
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    user_id VARCHAR(255),
    endpoint_id UUID REFERENCES endpoints(id) ON DELETE SET NULL,
    pool_id UUID REFERENCES pools(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_system_events_type ON system_events(event_type);
CREATE INDEX idx_system_events_severity ON system_events(severity);
CREATE INDEX idx_system_events_created_at ON system_events(created_at);
CREATE INDEX idx_system_events_endpoint_id ON system_events(endpoint_id);
CREATE INDEX idx_system_events_pool_id ON system_events(pool_id);
```

## Database Migrations

### Migration System

The application uses a custom migration system to manage schema changes:

```python
# server/database/migrations.py
class Migration:
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
    
    def up(self, connection):
        """Apply migration"""
        raise NotImplementedError
    
    def down(self, connection):
        """Rollback migration"""
        raise NotImplementedError
```

### Migration History

```sql
CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Available Migrations

#### Migration 001: Initial Schema
```python
class Migration001(Migration):
    def __init__(self):
        super().__init__("001", "Initial database schema")
    
    def up(self, connection):
        # Create all initial tables
        connection.execute("""
            CREATE TABLE pools (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                settings JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        # ... more table creation
```

#### Migration 002: Add Repository Analysis
```python
class Migration002(Migration):
    def __init__(self):
        super().__init__("002", "Add repository analysis tables")
    
    def up(self, connection):
        connection.execute("""
            CREATE TABLE repositories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
                repo_name VARCHAR(255) NOT NULL,
                repo_url VARCHAR(500),
                packages JSONB DEFAULT '{}',
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
```

### Running Migrations

```bash
# Apply all pending migrations
python -m server.database.migrations --apply-all

# Apply specific migration
python -m server.database.migrations --apply 002

# Rollback last migration
python -m server.database.migrations --rollback

# Check migration status
python -m server.database.migrations --status

# Create new migration
python -m server.database.migrations --create "Add user authentication"
```

## Database Maintenance

### Regular Maintenance Tasks

#### Vacuum and Analyze (PostgreSQL)
```sql
-- Full vacuum (requires exclusive lock)
VACUUM FULL;

-- Regular vacuum
VACUUM ANALYZE;

-- Vacuum specific tables
VACUUM ANALYZE sync_operations;
VACUUM ANALYZE package_states;
```

#### Index Maintenance
```sql
-- Rebuild indexes
REINDEX DATABASE pacman_sync_db;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;
```

#### Cleanup Old Data
```sql
-- Clean old sync operations (keep 90 days)
DELETE FROM sync_operations 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Clean old package states (keep 50 per pool)
WITH ranked_states AS (
    SELECT id, 
           ROW_NUMBER() OVER (PARTITION BY pool_id ORDER BY created_at DESC) as rn
    FROM package_states 
    WHERE is_target = FALSE
)
DELETE FROM package_states 
WHERE id IN (
    SELECT id FROM ranked_states WHERE rn > 50
);

-- Clean old system events (keep 30 days)
DELETE FROM system_events 
WHERE created_at < NOW() - INTERVAL '30 days'
AND severity NOT IN ('error', 'critical');
```

### Performance Optimization

#### Query Optimization
```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM sync_operations 
WHERE endpoint_id = 'uuid-here' 
ORDER BY started_at DESC LIMIT 10;

-- Create partial indexes for common queries
CREATE INDEX idx_sync_operations_recent 
ON sync_operations(endpoint_id, started_at DESC) 
WHERE started_at > NOW() - INTERVAL '30 days';
```

#### Connection Pooling
```python
# server/database/connection.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Backup and Recovery

#### Backup Procedures
```bash
# Full database backup
pg_dump -h localhost -U pacman_sync -d pacman_sync_db \
    --format=custom --compress=9 \
    --file=backup-$(date +%Y%m%d).dump

# Schema-only backup
pg_dump -h localhost -U pacman_sync -d pacman_sync_db \
    --schema-only --file=schema-backup.sql

# Data-only backup
pg_dump -h localhost -U pacman_sync -d pacman_sync_db \
    --data-only --file=data-backup.sql

# Specific table backup
pg_dump -h localhost -U pacman_sync -d pacman_sync_db \
    --table=package_states --file=package-states-backup.sql
```

#### Recovery Procedures
```bash
# Full database restore
pg_restore -h localhost -U pacman_sync -d pacman_sync_db \
    --clean --if-exists backup-20240115.dump

# Restore specific table
pg_restore -h localhost -U pacman_sync -d pacman_sync_db \
    --table=package_states backup-20240115.dump
```

## Database Configuration

### PostgreSQL Configuration

#### postgresql.conf Optimizations
```ini
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 100
shared_preload_libraries = 'pg_stat_statements'

# Logging
log_statement = 'mod'
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on

# Performance
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

#### pg_hba.conf Security
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   pacman_sync_db  pacman_sync                             md5
host    pacman_sync_db  pacman_sync     127.0.0.1/32            md5
host    pacman_sync_db  pacman_sync     ::1/128                 md5
```

### SQLite Configuration

#### SQLite Optimizations
```python
# server/database/sqlite_config.py
import sqlite3

def configure_sqlite(connection):
    # Enable WAL mode for better concurrency
    connection.execute("PRAGMA journal_mode=WAL")
    
    # Increase cache size
    connection.execute("PRAGMA cache_size=10000")
    
    # Enable foreign key constraints
    connection.execute("PRAGMA foreign_keys=ON")
    
    # Optimize for speed
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
```

## Monitoring and Metrics

### Database Metrics

#### PostgreSQL Monitoring Queries
```sql
-- Connection statistics
SELECT state, count(*) 
FROM pg_stat_activity 
WHERE datname = 'pacman_sync_db' 
GROUP BY state;

-- Table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;

-- Slow queries
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

#### Health Check Queries
```sql
-- Basic connectivity test
SELECT 1 as connected;

-- Check recent activity
SELECT COUNT(*) as recent_operations
FROM sync_operations 
WHERE started_at > NOW() - INTERVAL '1 hour';

-- Check database size
SELECT pg_size_pretty(pg_database_size('pacman_sync_db')) as database_size;
```

### Alerting Thresholds

```python
# server/database/monitoring.py
ALERT_THRESHOLDS = {
    'connection_count': 80,  # Alert if > 80% of max_connections
    'database_size_gb': 10,  # Alert if database > 10GB
    'slow_query_ms': 5000,   # Alert if queries > 5 seconds
    'failed_operations_rate': 0.1,  # Alert if > 10% operations fail
}
```

## Troubleshooting

### Common Issues

#### Connection Pool Exhaustion
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'pacman_sync_db';

-- Kill long-running queries
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'pacman_sync_db' 
AND state = 'active' 
AND query_start < NOW() - INTERVAL '1 hour';
```

#### Lock Contention
```sql
-- Check for locks
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

#### Disk Space Issues
```sql
-- Check table and index sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Recovery Procedures

#### Corrupted Index Recovery
```sql
-- Rebuild all indexes
REINDEX DATABASE pacman_sync_db;

-- Rebuild specific index
REINDEX INDEX idx_package_states_pool_id;
```

#### Data Consistency Checks
```sql
-- Check foreign key constraints
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint 
WHERE contype = 'f' 
AND NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = conname
);

-- Check for orphaned records
SELECT COUNT(*) FROM endpoints WHERE pool_id NOT IN (SELECT id FROM pools);
SELECT COUNT(*) FROM package_states WHERE endpoint_id NOT IN (SELECT id FROM endpoints);
```

## Next Steps

After understanding the database schema:

1. Review [API Documentation](api-documentation.md) for data access patterns
2. Check [Configuration Guide](configuration.md) for database settings
3. Set up [Monitoring](troubleshooting.md#monitoring) for database health
4. Implement [Backup Procedures](#backup-and-recovery) for data protection