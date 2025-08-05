"""
Qt client package for Pacman Sync Utility.

This package provides Qt-based desktop integration including system tray
support and native UI components.
"""

from .application import PacmanSyncApplication, SyncStatus, SyncStatusIndicator

__all__ = ['PacmanSyncApplication', 'SyncStatus', 'SyncStatusIndicator']