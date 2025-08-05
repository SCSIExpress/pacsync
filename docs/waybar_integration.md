# WayBar Integration for Pacman Sync Utility

This document describes how to integrate the Pacman Sync Utility with WayBar for efficient status monitoring and control.

## Overview

The WayBar integration provides:

- **JSON Status Output**: Real-time sync status in WayBar-compatible JSON format
- **Click Action Handlers**: Mouse click actions for sync operations
- **Efficient Status Querying**: Non-blocking status updates optimized for status bars
- **Customizable Display**: Configurable icons, colors, and tooltips

## Quick Setup

1. **Add the module to your WayBar configuration**:
   ```json
   {
     "modules-right": ["pacman-sync", "network", "battery", "clock"],
     "pacman-sync": {
       "exec": "python /path/to/pacman-sync-utility/client/main.py --status --json",
       "interval": 30,
       "return-type": "json",
       "format": "{icon}",
       "tooltip": true,
       "on-click": "python /path/to/pacman-sync-utility/client/main.py --waybar-click left --waybar-action sync"
     }
   }
   ```

2. **Add CSS styling** (optional):
   ```css
   #pacman-sync {
     background-color: #2e3440;
     color: #d8dee9;
     border-radius: 5px;
     padding: 0 10px;
   }
   
   #pacman-sync.in-sync { background-color: #a3be8c; }
   #pacman-sync.ahead { background-color: #ebcb8b; }
   #pacman-sync.behind { background-color: #5e81ac; }
   #pacman-sync.offline { background-color: #4c566a; }
   #pacman-sync.syncing { background-color: #88c0d0; }
   #pacman-sync.error { background-color: #bf616a; }
   ```

## Command Line Interface

### Status Output

```bash
# Basic status (human-readable)
python client/main.py --status

# JSON status for WayBar
python client/main.py --status --json

# Verbose JSON with detailed tooltip
python client/main.py --status --json --verbose
```

### Click Actions

```bash
# Handle left click with sync action
python client/main.py --waybar-click left --waybar-action sync

# Handle right click with menu action
python client/main.py --waybar-click right --waybar-action show_menu

# Handle middle click with set latest action
python client/main.py --waybar-click middle --waybar-action set_latest
```

### Configuration

```bash
# Generate WayBar configuration template
python client/main.py --waybar-config

# Run as continuous daemon (advanced usage)
python client/main.py --waybar-daemon
```

## JSON Status Format

The status output follows WayBar's JSON format specification:

```json
{
  "text": "✓",
  "alt": "in_sync",
  "class": ["pacman-sync", "in-sync"],
  "tooltip": "Status: In Sync\\nEndpoint: my-desktop\\nServer: http://localhost:8080\\nConnected: Yes\\nUpdated: 2m ago"
}
```

### Status States

| State | Icon | Alt | Description |
|-------|------|-----|-------------|
| `in_sync` | ✓ | in_sync | Packages are synchronized |
| `ahead` | ↑ | ahead | Ahead of pool (newer packages) |
| `behind` | ↓ | behind | Behind pool (older packages) |
| `offline` | ⚠ | offline | Cannot connect to server |
| `syncing` | ⟳ | syncing | Synchronization in progress |
| `error` | ✗ | error | Synchronization error |
| `unknown` | ? | unknown | No status information available |

### CSS Classes

- `pacman-sync`: Base class for all states
- `in-sync`, `ahead`, `behind`, `offline`, `syncing`, `error`, `unknown`: State-specific classes
- `stale`: Added when status information is outdated

## Click Actions

### Supported Buttons

- `left`: Primary action (default: show status)
- `right`: Context menu (default: show menu)
- `middle`: Quick action (default: sync)
- `scroll_up`: Refresh action
- `scroll_down`: Refresh action

### Available Actions

- `show_status`: Display detailed status information
- `show_menu`: Show available menu options
- `sync`: Sync to latest pool state
- `set_latest`: Set current state as pool latest
- `revert`: Revert to previous state
- `refresh`: Refresh status information

## WayBar Configuration Examples

### Basic Configuration

```json
{
  "pacman-sync": {
    "exec": "python /path/to/client/main.py --status --json",
    "interval": 30,
    "return-type": "json",
    "format": "{icon}",
    "tooltip": true
  }
}
```

### Advanced Configuration with Click Actions

```json
{
  "pacman-sync": {
    "exec": "python /path/to/client/main.py --status --json",
    "exec-if": "which pacman",
    "interval": 30,
    "return-type": "json",
    "format": "{icon}",
    "format-icons": {
      "in_sync": "✓",
      "ahead": "↑",
      "behind": "↓",
      "offline": "⚠",
      "syncing": "⟳",
      "error": "✗",
      "unknown": "?"
    },
    "tooltip": true,
    "on-click": "python /path/to/client/main.py --waybar-click left --waybar-action sync",
    "on-click-right": "python /path/to/client/main.py --waybar-click right --waybar-action show_menu",
    "on-click-middle": "python /path/to/client/main.py --waybar-click middle --waybar-action set_latest",
    "signal": 10
  }
}
```

### Signal-Based Updates

You can trigger immediate updates using signals:

```bash
# Send signal to update WayBar module
pkill -SIGUSR1 waybar
```

## CSS Styling

### Basic Styling

```css
#pacman-sync {
    background-color: #2e3440;
    color: #d8dee9;
    border-radius: 5px;
    padding: 0 10px;
    margin: 0 5px;
    min-width: 30px;
    text-align: center;
}
```

### State-Specific Styling

```css
#pacman-sync.in-sync {
    background-color: #a3be8c;
    color: #2e3440;
}

#pacman-sync.ahead {
    background-color: #ebcb8b;
    color: #2e3440;
}

#pacman-sync.behind {
    background-color: #5e81ac;
    color: #eceff4;
}

#pacman-sync.offline {
    background-color: #4c566a;
    color: #d8dee9;
}

#pacman-sync.syncing {
    background-color: #88c0d0;
    color: #2e3440;
    animation: pulse 2s infinite;
}

#pacman-sync.error {
    background-color: #bf616a;
    color: #eceff4;
}
```

### Animation for Syncing State

```css
@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

#pacman-sync.syncing {
    animation: pulse 2s infinite;
}
```

## Troubleshooting

### Common Issues

1. **Module not appearing**: Check that the path to `main.py` is correct
2. **No status updates**: Verify that the client is running and can connect to the server
3. **Click actions not working**: Ensure the click command paths are correct
4. **JSON parsing errors**: Check that the `--json` flag is used correctly

### Debug Commands

```bash
# Test JSON output
python client/main.py --status --json

# Test click action
python client/main.py --waybar-click left --waybar-action sync --json

# Generate configuration template
python client/main.py --waybar-config

# Check status with verbose output
python client/main.py --status --verbose
```

### Log Files

WayBar integration logs are written to:
- `/tmp/pacman-sync-waybar.log` (daemon mode)
- Standard error output (command mode)

## Performance Considerations

- **Update Interval**: Set to 30-60 seconds to balance responsiveness and system load
- **Status Caching**: Status is cached locally to avoid server requests on every update
- **Efficient Queries**: JSON output is optimized to minimize processing time
- **Non-blocking**: Status queries don't block WayBar updates

## Integration with Other Tools

### Notification Systems

The WayBar integration works alongside desktop notifications:

```bash
# Enable notifications in client configuration
show_notifications = true
```

### System Tray

WayBar integration complements the system tray icon:

```bash
# Run both WayBar and system tray
python client/main.py  # GUI mode with system tray
```

### Command Line Tools

WayBar click actions can trigger any supported CLI operation:

```bash
# Custom click action
"on-click": "python /path/to/client/main.py --sync --quiet"
```

## Security Considerations

- **Path Security**: Use absolute paths in WayBar configuration
- **Permission Checks**: Ensure the client has appropriate permissions
- **Network Security**: Status queries respect client authentication settings
- **Input Validation**: All click actions are validated before execution

## Examples

See the following example files:
- `docs/waybar_config_example.json`: Complete WayBar configuration
- `docs/waybar_style_example.css`: CSS styling examples
- `test_waybar_integration.py`: Integration test suite