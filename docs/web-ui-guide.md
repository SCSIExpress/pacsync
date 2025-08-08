# Web UI Guide

This guide covers how to use the web-based management interface for the Pacman Sync Utility server.

## Accessing the Web UI

1. Open your web browser
2. Navigate to your server URL: `http://your-server:8080`
3. The dashboard will load automatically (no login required for basic setup)

## Dashboard Overview

The main dashboard provides an overview of your entire system:

### System Status Panel
- **Server Status**: Shows if the server is running and healthy
- **Database Status**: Indicates database connectivity and health
- **Active Pools**: Number of configured package pools
- **Connected Endpoints**: Total number of registered endpoints
- **Recent Activity**: Latest synchronization operations

### Quick Actions
- **Create Pool**: Quickly create a new package pool
- **Add Endpoint**: Register a new endpoint
- **View Logs**: Access recent system logs
- **System Settings**: Configure server-wide settings

## Pool Management

### Creating a Package Pool

1. Click **"Create Pool"** on the dashboard or navigate to **Pools** → **Create New**
2. Fill in the pool details:
   - **Pool Name**: Descriptive name (e.g., "Development Workstations")
   - **Description**: Optional detailed description
   - **Sync Policy**: Choose automatic or manual synchronization
   - **Conflict Resolution**: How to handle package conflicts
3. Click **"Create Pool"** to save

### Pool Configuration Options

#### Basic Settings
- **Name**: Pool identifier (must be unique)
- **Description**: Detailed description of the pool's purpose
- **Auto-sync**: Enable automatic synchronization when endpoints join
- **Sync Schedule**: Optional scheduled synchronization times

#### Advanced Settings
- **Excluded Packages**: Packages to never synchronize (e.g., kernel, drivers)
- **Excluded Repositories**: Repositories to ignore during sync
- **Conflict Resolution Strategy**:
  - **Manual**: Require user intervention for conflicts
  - **Newest**: Always use the newest package version
  - **Oldest**: Always use the oldest package version
- **Maximum History**: Number of historical states to maintain

### Managing Existing Pools

#### Pool Details View
Click on any pool name to view detailed information:

- **Pool Information**: Name, description, creation date
- **Endpoint List**: All endpoints assigned to this pool
- **Sync Status**: Current synchronization state
- **Package State**: Target package configuration
- **History**: Previous synchronization operations

#### Pool Actions
- **Edit Pool**: Modify pool settings and configuration
- **Add Endpoints**: Assign new endpoints to the pool
- **Remove Endpoints**: Unassign endpoints from the pool
- **Set Target State**: Define the desired package configuration
- **Sync All**: Trigger synchronization for all endpoints
- **Delete Pool**: Remove the pool (requires confirmation)

### Endpoint Assignment

#### Adding Endpoints to a Pool
1. Navigate to the pool details page
2. Click **"Add Endpoints"**
3. Select endpoints from the available list
4. Choose assignment options:
   - **Auto-sync**: Enable automatic synchronization for these endpoints
   - **Priority**: Set synchronization priority (high, normal, low)
5. Click **"Add Selected"**

#### Endpoint Management
- **View Endpoint Details**: Click on endpoint name for detailed information
- **Change Pool**: Move endpoint to a different pool
- **Remove from Pool**: Unassign endpoint from current pool
- **Force Sync**: Trigger immediate synchronization for specific endpoint

## Endpoint Management

### Endpoint Registration

Endpoints are typically registered automatically by the desktop client, but you can also register them manually:

1. Navigate to **Endpoints** → **Register New**
2. Fill in endpoint details:
   - **Endpoint Name**: Unique identifier for the machine
   - **Hostname**: Network hostname or IP address
   - **Description**: Optional description
   - **Pool Assignment**: Choose initial pool (optional)
3. Click **"Register Endpoint"**
4. Copy the generated API key for client configuration

### Endpoint Status Monitoring

#### Status Indicators
- **🟢 Online**: Endpoint is connected and responsive
- **🟡 Sync Pending**: Synchronization operation in progress
- **🔴 Offline**: Endpoint hasn't reported status recently
- **⚠️ Error**: Last operation failed or endpoint has issues

#### Endpoint Details
Click on any endpoint to view:
- **System Information**: OS version, architecture, pacman version
- **Package State**: Currently installed packages and versions
- **Repository Information**: Available repositories and their status
- **Sync History**: Previous synchronization operations
- **Connection Status**: Last seen time and connection health

### Endpoint Actions
- **Sync Now**: Trigger immediate synchronization
- **Set as Target**: Use this endpoint's state as the pool target
- **Revert**: Restore endpoint to previous state
- **Update Info**: Refresh endpoint information
- **Remove**: Unregister endpoint from the system

## Repository Analysis

### Compatibility Analysis

The repository analysis page shows package compatibility across all endpoints in each pool:

#### Analysis Overview
- **Compatible Packages**: Packages available in all repositories
- **Incompatible Packages**: Packages missing from some repositories
- **Conflicts**: Packages with version conflicts between repositories
- **Exclusions**: Packages automatically excluded from synchronization

#### Detailed Analysis
1. Navigate to **Analysis** → **Repository Compatibility**
2. Select a pool to analyze
3. View the compatibility matrix:
   - **Green**: Package available in all repositories
   - **Yellow**: Package available in some repositories
   - **Red**: Package conflicts or missing dependencies

### Managing Package Exclusions

#### Automatic Exclusions
The system automatically excludes packages that:
- Are not available in all pool repositories
- Have unresolvable version conflicts
- Are marked as system-critical (kernel, bootloader, etc.)

#### Manual Exclusions
1. Navigate to **Analysis** → **Package Exclusions**
2. Click **"Add Exclusion"**
3. Specify:
   - **Package Name**: Exact package name or pattern
   - **Scope**: Pool-specific or global exclusion
   - **Reason**: Description of why package is excluded
4. Click **"Add Exclusion"**

#### Exclusion Management
- **View Exclusions**: List all current exclusions
- **Edit Exclusion**: Modify exclusion rules
- **Remove Exclusion**: Delete exclusion (package will be included in future syncs)
- **Bulk Operations**: Add/remove multiple exclusions at once

## Synchronization Operations

### Manual Synchronization

#### Pool-wide Synchronization
1. Navigate to the pool details page
2. Click **"Sync All Endpoints"**
3. Choose synchronization options:
   - **Sync Type**: Full sync or incremental
   - **Conflict Resolution**: Override pool default if needed
   - **Dry Run**: Preview changes without applying them
4. Click **"Start Synchronization"**

#### Individual Endpoint Sync
1. Navigate to endpoint details
2. Click **"Sync Now"**
3. Monitor progress in real-time
4. View results and any errors

### Synchronization Monitoring

#### Real-time Progress
- **Progress Bar**: Shows overall completion percentage
- **Current Operation**: Displays what's currently being processed
- **Estimated Time**: Remaining time estimate
- **Package Count**: Packages processed vs. total

#### Operation Log
- **Timestamp**: When each operation occurred
- **Action**: What action was performed (install, remove, upgrade)
- **Package**: Which package was affected
- **Status**: Success, failure, or warning
- **Details**: Additional information or error messages

### Setting Target States

#### From Endpoint State
1. Navigate to endpoint details
2. Click **"Set as Pool Target"**
3. Confirm the action
4. All other endpoints in the pool will sync to this state

#### Manual State Definition
1. Navigate to pool details
2. Click **"Define Target State"**
3. Specify packages and versions:
   - **Package Name**: Exact package name
   - **Version**: Specific version or "latest"
   - **Repository**: Source repository
4. Save the target state

## System Administration

### Server Configuration

#### Basic Settings
Navigate to **Settings** → **Server Configuration**:
- **Server Name**: Display name for this server
- **Default Pool**: Pool for new endpoints
- **Auto-cleanup**: Automatically remove old states
- **Notification Settings**: Email or webhook notifications

#### Database Management
- **Database Status**: Connection health and statistics
- **Backup Database**: Create manual backup
- **Cleanup Old Data**: Remove historical data
- **Migration Status**: Database schema version

### User Management (Future Feature)

The web UI is designed to support user authentication and role-based access:
- **Admin Users**: Full system access
- **Pool Managers**: Manage specific pools
- **Read-only Users**: View-only access

### Logging and Monitoring

#### System Logs
Navigate to **Logs** → **System Logs**:
- **Filter by Level**: Debug, Info, Warning, Error
- **Filter by Component**: Server, Database, API, Web UI
- **Time Range**: Specify date/time range
- **Search**: Find specific log entries

#### Operation History
Navigate to **Logs** → **Operation History**:
- **Synchronization Operations**: All sync activities
- **Pool Changes**: Pool creation, modification, deletion
- **Endpoint Activities**: Registration, status changes
- **System Events**: Server starts, shutdowns, errors

## Troubleshooting

### Common Issues

#### Pool Creation Fails
- **Check Database Connection**: Ensure database is accessible
- **Verify Permissions**: Confirm write access to database
- **Review Logs**: Check server logs for specific errors

#### Endpoints Not Appearing
- **Client Configuration**: Verify client is configured with correct server URL
- **Network Connectivity**: Test connection between client and server
- **API Key**: Ensure client has valid API key

#### Synchronization Failures
- **Repository Access**: Verify all endpoints can access required repositories
- **Package Conflicts**: Review compatibility analysis for conflicts
- **Disk Space**: Ensure endpoints have sufficient disk space

### Diagnostic Tools

#### Health Check
Navigate to **System** → **Health Check**:
- **Server Health**: CPU, memory, disk usage
- **Database Health**: Connection status, query performance
- **Endpoint Health**: Connection status for all endpoints

#### System Information
Navigate to **System** → **Information**:
- **Server Version**: Current software version
- **Database Schema**: Database version and migration status
- **Configuration**: Current server configuration (sensitive data hidden)
- **Statistics**: Usage statistics and performance metrics

## Advanced Features

### API Integration

The web UI provides tools for API integration:
- **API Documentation**: Interactive API documentation
- **API Key Management**: Generate and manage API keys
- **Webhook Configuration**: Set up webhooks for external integration

### Bulk Operations

#### Bulk Endpoint Management
- **Select Multiple Endpoints**: Use checkboxes to select endpoints
- **Bulk Actions**: Apply actions to all selected endpoints
- **Batch Synchronization**: Sync multiple endpoints simultaneously

#### Bulk Pool Operations
- **Pool Templates**: Create pools from predefined templates
- **Bulk Configuration**: Apply settings to multiple pools
- **Mass Endpoint Assignment**: Assign multiple endpoints to pools

### Export and Import

#### Configuration Export
- **Export Pool Configuration**: Save pool settings to file
- **Export Endpoint List**: Export endpoint information
- **Full System Export**: Complete system configuration backup

#### Configuration Import
- **Import Pool Configuration**: Restore pools from backup
- **Import Endpoints**: Bulk endpoint registration
- **System Restore**: Restore complete system configuration

## Best Practices

### Pool Organization
- **Use Descriptive Names**: Make pool purposes clear
- **Group Similar Systems**: Keep similar endpoints together
- **Separate Environments**: Use different pools for dev/staging/production

### Monitoring
- **Regular Health Checks**: Monitor system health regularly
- **Review Logs**: Check logs for warnings and errors
- **Monitor Disk Usage**: Ensure adequate storage space

### Maintenance
- **Regular Backups**: Backup database and configuration regularly
- **Clean Old Data**: Remove unnecessary historical data
- **Update Documentation**: Keep pool descriptions current

## Getting Help

If you encounter issues with the web UI:

1. Check the **System Logs** for error messages
2. Review the [Troubleshooting Guide](troubleshooting.md)
3. Use the **Health Check** tool to identify problems
4. Consult the [API Documentation](api-documentation.md) for integration issues

## Next Steps

After mastering the web UI:

1. Set up [Desktop Client](desktop-client-guide.md) on your endpoints
2. Configure [API Integration](api-documentation.md) for automation
3. Explore [Advanced Configuration](configuration.md) options
4. Set up [Monitoring and Alerting](troubleshooting.md#monitoring)