# Qt User Interface Windows

This document describes the Qt-based user interface windows implemented for the Pacman Sync Utility client.

## Overview

The client provides three main Qt windows for user interaction:

1. **PackageDetailsWindow** - Detailed package information display
2. **SyncProgressDialog** - Progress tracking for sync operations  
3. **ConfigurationWindow** - Application settings management

## PackageDetailsWindow

### Purpose
Displays comprehensive information about installed packages with navigation between multiple packages.

### Features
- **Tabbed Interface**: Basic Info, Dependencies, Files
- **Package Navigation**: Previous/Next buttons for multiple packages
- **Export Functionality**: Save package information to text file
- **Menu Bar**: File operations and navigation shortcuts
- **Status Bar**: Current operation feedback

### Usage
```python
from client.qt.windows import PackageDetailsWindow, PackageInfo

packages = [PackageInfo(...), ...]
window = PackageDetailsWindow(packages)
window.show()
```

## SyncProgressDialog

### Purpose
Shows real-time progress of package synchronization operations with cancellation support.

### Features
- **Progress Tracking**: Visual progress bar with package counts
- **Current Package Display**: Shows which package is being processed
- **Operation Log**: Timestamped log of operation events
- **Cancellation Support**: Cancel button with confirmation dialog
- **Error Display**: Shows error details when operations fail
- **Modal Dialog**: Prevents other operations during sync

### Usage
```python
from client.qt.windows import SyncProgressDialog, SyncOperation

operation = SyncOperation(...)
dialog = SyncProgressDialog(operation)
dialog.cancel_requested.connect(handle_cancel)
dialog.exec()
```

## ConfigurationWindow

### Purpose
Comprehensive settings management with tabbed interface for all client configuration options.

### Features
- **Server Tab**: URL, API key, timeout, SSL settings
- **Client Tab**: Endpoint identification, logging, update intervals
- **Sync Tab**: Synchronization behavior, package exclusions, conflict resolution
- **Interface Tab**: System tray, appearance, WayBar integration
- **Settings Validation**: Input validation with error messages
- **Apply/Restore**: Apply changes without closing or restore defaults

### Usage
```python
from client.qt.windows import ConfigurationWindow

config = {...}  # Current configuration dict
window = ConfigurationWindow(config)
window.settings_changed.connect(handle_settings_change)
window.exec()
```

## System Tray Integration

The Qt windows are integrated with the system tray context menu:

- **Show Details**: Opens PackageDetailsWindow with current package information
- **Configuration...**: Opens ConfigurationWindow with current settings

## Requirements

- PyQt6 >= 6.5.0
- Python >= 3.8

## Installation

### Arch Linux
```bash
sudo pacman -S python-pyqt6
```

### Other Systems
```bash
pip install PyQt6
```

## Development

### Testing Windows
Use the provided test scripts:

```bash
# Test all windows
python test_qt_windows.py all

# Test individual windows
python test_qt_windows.py package
python test_qt_windows.py progress  
python test_qt_windows.py config
```

### Demo
```bash
python demo_qt_windows.py
```

## Architecture

All Qt windows follow these design principles:

1. **Native Qt Widgets**: Use standard Qt components for native look and feel
2. **Signal-Slot Pattern**: Proper Qt signal handling for user interactions
3. **Modal Dialogs**: Progress and configuration windows are modal
4. **Error Handling**: Comprehensive validation and error reporting
5. **Accessibility**: Keyboard shortcuts and proper tab order
6. **Cross-Platform**: Works on Linux, Windows, and macOS