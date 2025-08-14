"""
Qt User Interface Windows for Pacman Sync Utility Client.

This module provides Qt windows and dialogs for detailed package information display,
progress tracking, and configuration management.
"""

import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import (
    QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QGroupBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QScrollArea, QFrame, QMessageBox, QFileDialog,
    QDialogButtonBox, QFormLayout, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QApplication, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QSize, QRect, QPropertyAnimation,
    QEasingCurve, QAbstractAnimation
)
from PyQt6.QtGui import (
    QFont, QPixmap, QIcon, QPalette, QColor, QPainter, QBrush, QPen,
    QFontMetrics, QAction, QKeySequence
)

logger = logging.getLogger(__name__)


@dataclass
class PackageInfo:
    """Data class representing package information."""
    name: str
    version: str
    repository: str
    installed_size: int
    description: str
    dependencies: List[str]
    conflicts: List[str]
    provides: List[str]
    install_date: Optional[str] = None
    build_date: Optional[str] = None
    packager: Optional[str] = None
    url: Optional[str] = None
    licenses: List[str] = None


@dataclass
class SyncOperation:
    """Data class representing a sync operation."""
    operation_id: str
    operation_type: str  # 'sync', 'set_latest', 'revert'
    total_packages: int
    processed_packages: int
    current_package: Optional[str]
    status: str  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    error_message: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class OperationStatus(Enum):
    """Enumeration of operation statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PackageDetailsWindow(QMainWindow):
    """
    Main window for displaying detailed package information.
    
    Shows comprehensive package details including dependencies, conflicts,
    and installation information in a native-looking Qt interface.
    """
    
    def __init__(self, packages: List[PackageInfo], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.packages = packages
        self.current_package_index = 0
        
        self.setWindowTitle("Package Details - Pacman Sync Utility")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Center window on screen
        self._center_on_screen()
        
        # Set up UI
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        
        # Load first package
        if self.packages:
            self._load_package(0)
        
        logger.info(f"Package details window initialized with {len(packages)} packages")
    
    def _center_on_screen(self) -> None:
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
    
    def _setup_ui(self) -> None:
        """Set up the main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Package navigation
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self._previous_package)
        self.prev_button.setEnabled(False)
        
        self.package_label = QLabel("Package 1 of 1")
        self.package_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.package_label.font()
        font.setBold(True)
        self.package_label.setFont(font)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self._next_package)
        self.next_button.setEnabled(len(self.packages) > 1)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.package_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)
        
        main_layout.addLayout(nav_layout)
        
        # Package details tabs
        self.tab_widget = QTabWidget()
        
        # Basic Information Tab
        self.basic_tab = self._create_basic_info_tab()
        self.tab_widget.addTab(self.basic_tab, "Basic Information")
        
        # Dependencies Tab
        self.deps_tab = self._create_dependencies_tab()
        self.tab_widget.addTab(self.deps_tab, "Dependencies")
        
        # Files Tab (placeholder for future implementation)
        self.files_tab = self._create_files_tab()
        self.tab_widget.addTab(self.files_tab, "Files")
        
        main_layout.addWidget(self.tab_widget)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_package_info)
        
        self.export_button = QPushButton("Export Info")
        self.export_button.clicked.connect(self._export_package_info)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_basic_info_tab(self) -> QWidget:
        """Create the basic information tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Scrollable area for package info
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        self.basic_form_layout = QFormLayout(content_widget)
        self.basic_form_layout.setSpacing(8)
        self.basic_form_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab
    
    def _create_dependencies_tab(self) -> QWidget:
        """Create the dependencies tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Dependencies tree
        self.deps_tree = QTreeWidget()
        self.deps_tree.setHeaderLabels(["Dependency", "Type", "Status"])
        self.deps_tree.setAlternatingRowColors(True)
        
        # Resize columns
        header = self.deps_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.deps_tree)
        
        return tab
    
    def _create_files_tab(self) -> QWidget:
        """Create the files tab (placeholder)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Placeholder for file list
        placeholder_label = QLabel("File list will be available in a future update.")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: gray; font-style: italic;")
        
        layout.addWidget(placeholder_label)
        
        return tab 
   
    def _setup_menu_bar(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self._refresh_package_info)
        file_menu.addAction(refresh_action)
        
        export_action = QAction("Export...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_package_info)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        close_action = QAction("Close", self)
        close_action.setShortcut(QKeySequence.StandardKey.Close)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        next_action = QAction("Next Package", self)
        next_action.setShortcut(QKeySequence.StandardKey.Forward)
        next_action.triggered.connect(self._next_package)
        view_menu.addAction(next_action)
        
        prev_action = QAction("Previous Package", self)
        prev_action.setShortcut(QKeySequence.StandardKey.Back)
        prev_action.triggered.connect(self._previous_package)
        view_menu.addAction(prev_action)
    
    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        status_bar = self.statusBar()
        status_bar.showMessage("Ready")
    
    def _load_package(self, index: int) -> None:
        """Load package information into the UI."""
        if not (0 <= index < len(self.packages)):
            return
        
        self.current_package_index = index
        package = self.packages[index]
        
        # Update navigation
        self.package_label.setText(f"Package {index + 1} of {len(self.packages)}")
        self.prev_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < len(self.packages) - 1)
        
        # Update window title
        self.setWindowTitle(f"Package Details - {package.name} - Pacman Sync Utility")
        
        # Clear and populate basic info
        self._clear_form_layout(self.basic_form_layout)
        
        # Add basic information fields
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(name_font.pointSize() + 2)
        
        name_widget = QLabel(package.name)
        name_widget.setFont(name_font)
        self.basic_form_layout.addRow("Package Name:", name_widget)
        
        version_widget = QLabel(package.version)
        version_font = QFont()
        version_font.setBold(True)
        version_widget.setFont(version_font)
        self.basic_form_layout.addRow("Version:", version_widget)
        
        self.basic_form_layout.addRow("Repository:", QLabel(package.repository))
        
        # Format size
        size_mb = package.installed_size / (1024 * 1024)
        size_text = f"{size_mb:.2f} MB ({package.installed_size:,} bytes)"
        self.basic_form_layout.addRow("Installed Size:", QLabel(size_text))
        
        # Description
        desc_widget = QTextEdit()
        desc_widget.setPlainText(package.description)
        desc_widget.setMaximumHeight(80)
        desc_widget.setReadOnly(True)
        self.basic_form_layout.addRow("Description:", desc_widget)
        
        # Optional fields
        if package.install_date:
            self.basic_form_layout.addRow("Install Date:", QLabel(package.install_date))
        
        if package.build_date:
            self.basic_form_layout.addRow("Build Date:", QLabel(package.build_date))
        
        if package.packager:
            self.basic_form_layout.addRow("Packager:", QLabel(package.packager))
        
        if package.url:
            url_label = QLabel(f'<a href="{package.url}">{package.url}</a>')
            url_label.setOpenExternalLinks(True)
            self.basic_form_layout.addRow("URL:", url_label)
        
        if package.licenses:
            licenses_text = ", ".join(package.licenses)
            self.basic_form_layout.addRow("Licenses:", QLabel(licenses_text))
        
        # Update dependencies tree
        self._update_dependencies_tree(package)
        
        # Update status bar
        self.statusBar().showMessage(f"Loaded package: {package.name}")
        
        logger.debug(f"Loaded package details for {package.name}")
    
    def _clear_form_layout(self, layout: QFormLayout) -> None:
        """Clear all widgets from a form layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _update_dependencies_tree(self, package: PackageInfo) -> None:
        """Update the dependencies tree widget."""
        self.deps_tree.clear()
        
        # Add dependencies
        if package.dependencies:
            deps_root = QTreeWidgetItem(self.deps_tree, ["Dependencies", "", ""])
            deps_root.setExpanded(True)
            
            for dep in package.dependencies:
                dep_item = QTreeWidgetItem(deps_root, [dep, "Dependency", "Required"])
                dep_item.setIcon(0, self._get_dependency_icon("dependency"))
        
        # Add conflicts
        if package.conflicts:
            conflicts_root = QTreeWidgetItem(self.deps_tree, ["Conflicts", "", ""])
            conflicts_root.setExpanded(True)
            
            for conflict in package.conflicts:
                conflict_item = QTreeWidgetItem(conflicts_root, [conflict, "Conflict", "Blocked"])
                conflict_item.setIcon(0, self._get_dependency_icon("conflict"))
        
        # Add provides
        if package.provides:
            provides_root = QTreeWidgetItem(self.deps_tree, ["Provides", "", ""])
            provides_root.setExpanded(True)
            
            for provide in package.provides:
                provide_item = QTreeWidgetItem(provides_root, [provide, "Provides", "Available"])
                provide_item.setIcon(0, self._get_dependency_icon("provides"))
    
    def _get_dependency_icon(self, dep_type: str) -> QIcon:
        """Get an icon for the dependency type."""
        # Create simple colored icons for different dependency types
        pixmap = QPixmap(16, 16)
        
        color_map = {
            "dependency": "#0088FF",  # Blue
            "conflict": "#FF0000",    # Red
            "provides": "#00AA00"     # Green
        }
        
        color = color_map.get(dep_type, "#888888")
        pixmap.fill(QColor(color))
        
        return QIcon(pixmap)
    
    def _previous_package(self) -> None:
        """Navigate to the previous package."""
        if self.current_package_index > 0:
            self._load_package(self.current_package_index - 1)
    
    def _next_package(self) -> None:
        """Navigate to the next package."""
        if self.current_package_index < len(self.packages) - 1:
            self._load_package(self.current_package_index + 1)
    
    def _refresh_package_info(self) -> None:
        """Refresh the current package information."""
        # In a real implementation, this would reload package data from the system
        self.statusBar().showMessage("Package information refreshed", 2000)
        logger.info("Package information refresh requested")
    
    def _export_package_info(self) -> None:
        """Export package information to a file."""
        if not self.packages:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Package Information",
            f"package_info_{self.packages[self.current_package_index].name}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    package = self.packages[self.current_package_index]
                    f.write(f"Package Information Export\n")
                    f.write(f"========================\n\n")
                    f.write(f"Name: {package.name}\n")
                    f.write(f"Version: {package.version}\n")
                    f.write(f"Repository: {package.repository}\n")
                    f.write(f"Installed Size: {package.installed_size} bytes\n")
                    f.write(f"Description: {package.description}\n")
                    
                    if package.dependencies:
                        f.write(f"\nDependencies:\n")
                        for dep in package.dependencies:
                            f.write(f"  - {dep}\n")
                    
                    if package.conflicts:
                        f.write(f"\nConflicts:\n")
                        for conflict in package.conflicts:
                            f.write(f"  - {conflict}\n")
                    
                    if package.provides:
                        f.write(f"\nProvides:\n")
                        for provide in package.provides:
                            f.write(f"  - {provide}\n")
                
                self.statusBar().showMessage(f"Package information exported to {filename}", 3000)
                logger.info(f"Package information exported to {filename}")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export package information:\n{str(e)}"
                )
                logger.error(f"Failed to export package information: {e}")

class SyncProgressDialog(QDialog):
    """
    Progress dialog for sync operations with cancellation support.
    
    Displays real-time progress of package synchronization operations
    with the ability to cancel ongoing operations.
    """
    
    # Signals
    cancel_requested = pyqtSignal()
    
    def __init__(self, operation: SyncOperation, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.operation = operation
        self.is_cancelled = False
        
        self.setWindowTitle(f"Sync Operation - {operation.operation_type.title()}")
        self.setModal(True)
        self.setMinimumSize(500, 300)
        self.resize(600, 350)
        
        # Prevent closing with X button during operation
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )
        
        self._setup_ui()
        self._center_on_parent()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_progress)
        self.update_timer.start(500)  # Update every 500ms
        
        logger.info(f"Sync progress dialog initialized for operation {operation.operation_id}")
    
    def _center_on_parent(self) -> None:
        """Center the dialog on its parent or screen."""
        if self.parent():
            parent_geometry = self.parent().geometry()
            dialog_geometry = self.frameGeometry()
            center_point = parent_geometry.center()
            dialog_geometry.moveCenter(center_point)
            self.move(dialog_geometry.topLeft())
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                dialog_geometry = self.frameGeometry()
                center_point = screen_geometry.center()
                dialog_geometry.moveCenter(center_point)
                self.move(dialog_geometry.topLeft())
    
    def _setup_ui(self) -> None:
        """Set up the progress dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Operation title
        title_label = QLabel(f"Synchronization Operation: {self.operation.operation_type.title()}")
        title_font = title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Operation details group
        details_group = QGroupBox("Operation Details")
        details_layout = QFormLayout(details_group)
        
        self.operation_id_label = QLabel(self.operation.operation_id)
        details_layout.addRow("Operation ID:", self.operation_id_label)
        
        self.status_label = QLabel(self.operation.status.title())
        details_layout.addRow("Status:", self.status_label)
        
        self.start_time_label = QLabel(self.operation.start_time or "Not started")
        details_layout.addRow("Started:", self.start_time_label)
        
        layout.addWidget(details_group)
        
        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimum(0)
        self.overall_progress.setMaximum(self.operation.total_packages)
        self.overall_progress.setValue(self.operation.processed_packages)
        self.overall_progress.setFormat("%v / %m packages (%p%)")
        progress_layout.addWidget(self.overall_progress)
        
        # Current package
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current Package:"))
        self.current_package_label = QLabel(self.operation.current_package or "None")
        current_package_font = self.current_package_label.font()
        current_package_font.setBold(True)
        self.current_package_label.setFont(current_package_font)
        current_layout.addWidget(self.current_package_label)
        current_layout.addStretch()
        progress_layout.addLayout(current_layout)
        
        layout.addWidget(progress_group)
        
        # Log output
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Error display (initially hidden)
        self.error_group = QGroupBox("Error Details")
        self.error_group.setVisible(False)
        error_layout = QVBoxLayout(self.error_group)
        
        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setMaximumHeight(80)
        self.error_text.setStyleSheet("color: red;")
        error_layout.addWidget(self.error_text)
        
        layout.addWidget(self.error_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel Operation")
        self.cancel_button.clicked.connect(self._cancel_operation)
        self.cancel_button.setStyleSheet("QPushButton { background-color: #ff6b6b; }")
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)  # Disabled until operation completes
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # Initial log entry
        self._add_log_entry(f"Operation {self.operation.operation_id} initialized")
    
    def _update_progress(self) -> None:
        """Update the progress display."""
        # Update progress bar
        self.overall_progress.setValue(self.operation.processed_packages)
        
        # Update current package
        if self.operation.current_package:
            self.current_package_label.setText(self.operation.current_package)
        
        # Update status
        self.status_label.setText(self.operation.status.title())
        
        # Update start time
        if self.operation.start_time:
            self.start_time_label.setText(self.operation.start_time)
        
        # Handle different operation states
        if self.operation.status == OperationStatus.COMPLETED.value:
            self._handle_operation_completed()
        elif self.operation.status == OperationStatus.FAILED.value:
            self._handle_operation_failed()
        elif self.operation.status == OperationStatus.CANCELLED.value:
            self._handle_operation_cancelled()
    
    def _handle_operation_completed(self) -> None:
        """Handle successful operation completion."""
        self.update_timer.stop()
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Update window title
        self.setWindowTitle("Sync Operation - Completed")
        
        # Add completion log
        self._add_log_entry("Operation completed successfully!")
        
        # Show completion message
        completion_time = self.operation.end_time or "Unknown"
        self._add_log_entry(f"Completed at: {completion_time}")
        
        # Re-enable close button
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowCloseButtonHint
        )
        
        logger.info(f"Sync operation {self.operation.operation_id} completed successfully")
    
    def _handle_operation_failed(self) -> None:
        """Handle operation failure."""
        self.update_timer.stop()
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Update window title
        self.setWindowTitle("Sync Operation - Failed")
        
        # Show error details
        if self.operation.error_message:
            self.error_group.setVisible(True)
            self.error_text.setPlainText(self.operation.error_message)
            self._add_log_entry(f"Operation failed: {self.operation.error_message}")
        else:
            self._add_log_entry("Operation failed with unknown error")
        
        # Re-enable close button
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowCloseButtonHint
        )
        
        logger.error(f"Sync operation {self.operation.operation_id} failed: {self.operation.error_message}")
    
    def _handle_operation_cancelled(self) -> None:
        """Handle operation cancellation."""
        self.update_timer.stop()
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Update window title
        self.setWindowTitle("Sync Operation - Cancelled")
        
        # Add cancellation log
        self._add_log_entry("Operation was cancelled by user")
        
        # Re-enable close button
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowCloseButtonHint
        )
        
        logger.info(f"Sync operation {self.operation.operation_id} was cancelled")
    
    def _cancel_operation(self) -> None:
        """Cancel the ongoing operation."""
        if self.is_cancelled:
            return
        
        reply = QMessageBox.question(
            self,
            "Cancel Operation",
            "Are you sure you want to cancel this synchronization operation?\n\n"
            "Cancelling may leave your system in an inconsistent state.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.is_cancelled = True
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Cancelling...")
            
            self._add_log_entry("Cancellation requested by user...")
            
            # Emit cancel signal
            self.cancel_requested.emit()
            
            logger.info(f"User requested cancellation of operation {self.operation.operation_id}")
    
    def _add_log_entry(self, message: str) -> None:
        """Add an entry to the operation log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_text.append(log_entry)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_operation(self, operation: SyncOperation) -> None:
        """Update the operation data and refresh the display."""
        self.operation = operation
        self._update_progress()
    
    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
        if self.operation.status in [OperationStatus.PENDING.value, OperationStatus.RUNNING.value]:
            # Don't allow closing during active operation
            event.ignore()
        else:
            event.accept()
class ConfigurationWindow(QDialog):
    """
    Configuration window for endpoint settings and preferences.
    
    Provides a comprehensive interface for configuring client settings,
    server connection, and synchronization preferences.
    """
    
    # Signals
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, current_config: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_config = current_config.copy()
        self.modified_config = current_config.copy()
        
        self.setWindowTitle("Configuration - Pacman Sync Utility")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        self._setup_ui()
        self._load_current_settings()
        self._center_on_parent()
        
        logger.info("Configuration window initialized")
    
    def _center_on_parent(self) -> None:
        """Center the dialog on its parent or screen."""
        if self.parent():
            parent_geometry = self.parent().geometry()
            dialog_geometry = self.frameGeometry()
            center_point = parent_geometry.center()
            dialog_geometry.moveCenter(center_point)
            self.move(dialog_geometry.topLeft())
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                dialog_geometry = self.frameGeometry()
                center_point = screen_geometry.center()
                dialog_geometry.moveCenter(center_point)
                self.move(dialog_geometry.topLeft())
    
    def _setup_ui(self) -> None:
        """Set up the configuration window UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Configuration tabs
        self.tab_widget = QTabWidget()
        
        # Server Configuration Tab
        self.server_tab = self._create_server_tab()
        self.tab_widget.addTab(self.server_tab, "Server")
        
        # Client Configuration Tab
        self.client_tab = self._create_client_tab()
        self.tab_widget.addTab(self.client_tab, "Client")
        
        # Synchronization Tab
        self.sync_tab = self._create_sync_tab()
        self.tab_widget.addTab(self.sync_tab, "Synchronization")
        
        # Interface Tab
        self.interface_tab = self._create_interface_tab()
        self.tab_widget.addTab(self.interface_tab, "Interface")
        
        layout.addWidget(self.tab_widget)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        
        button_box.accepted.connect(self._accept_changes)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_changes)
        button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._restore_defaults)
        
        layout.addWidget(button_box)
    
    def _create_server_tab(self) -> QWidget:
        """Create the server configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Server connection group
        server_group = QGroupBox("Server Connection")
        server_layout = QFormLayout(server_group)
        
        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("http://localhost:8080")
        server_layout.addRow("Server URL:", self.server_url_edit)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter API key")
        server_layout.addRow("API Key:", self.api_key_edit)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setValue(30)
        server_layout.addRow("Connection Timeout:", self.timeout_spin)
        
        self.retry_attempts_spin = QSpinBox()
        self.retry_attempts_spin.setRange(1, 10)
        self.retry_attempts_spin.setValue(3)
        server_layout.addRow("Retry Attempts:", self.retry_attempts_spin)
        
        layout.addWidget(server_group)
        
        # SSL/TLS group
        ssl_group = QGroupBox("SSL/TLS Settings")
        ssl_layout = QFormLayout(ssl_group)
        
        self.verify_ssl_check = QCheckBox("Verify SSL certificates")
        self.verify_ssl_check.setChecked(True)
        ssl_layout.addRow(self.verify_ssl_check)
        
        self.ssl_cert_path_edit = QLineEdit()
        self.ssl_cert_path_edit.setPlaceholderText("Path to SSL certificate file")
        ssl_cert_button = QPushButton("Browse...")
        ssl_cert_button.clicked.connect(self._browse_ssl_cert)
        
        ssl_cert_layout = QHBoxLayout()
        ssl_cert_layout.addWidget(self.ssl_cert_path_edit)
        ssl_cert_layout.addWidget(ssl_cert_button)
        ssl_layout.addRow("SSL Certificate:", ssl_cert_layout)
        
        layout.addWidget(ssl_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_client_tab(self) -> QWidget:
        """Create the client configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Endpoint identification group
        endpoint_group = QGroupBox("Endpoint Identification")
        endpoint_layout = QFormLayout(endpoint_group)
        
        self.endpoint_name_edit = QLineEdit()
        self.endpoint_name_edit.setPlaceholderText("my-desktop")
        endpoint_layout.addRow("Endpoint Name:", self.endpoint_name_edit)
        
        # Pool assignment info (read-only, assigned by server)
        self.pool_info_label = QLabel("Assigned by server after registration")
        self.pool_info_label.setStyleSheet("color: gray; font-style: italic;")
        endpoint_layout.addRow("Pool Assignment:", self.pool_info_label)
        
        self.hostname_edit = QLineEdit()
        self.hostname_edit.setPlaceholderText("Auto-detected")
        self.hostname_edit.setReadOnly(True)
        endpoint_layout.addRow("Hostname:", self.hostname_edit)
        
        layout.addWidget(endpoint_group)
        
        # Update settings group
        update_group = QGroupBox("Update Settings")
        update_layout = QFormLayout(update_group)
        
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(30, 3600)
        self.update_interval_spin.setSuffix(" seconds")
        self.update_interval_spin.setValue(300)
        update_layout.addRow("Status Update Interval:", self.update_interval_spin)
        
        self.auto_register_check = QCheckBox("Automatically register with server")
        self.auto_register_check.setChecked(True)
        update_layout.addRow(self.auto_register_check)
        
        layout.addWidget(update_group)
        
        # Logging group
        logging_group = QGroupBox("Logging")
        logging_layout = QFormLayout(logging_group)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        self.log_file_edit = QLineEdit()
        self.log_file_edit.setPlaceholderText("Leave empty for console logging")
        log_file_button = QPushButton("Browse...")
        log_file_button.clicked.connect(self._browse_log_file)
        
        log_file_layout = QHBoxLayout()
        log_file_layout.addWidget(self.log_file_edit)
        log_file_layout.addWidget(log_file_button)
        logging_layout.addRow("Log File:", log_file_layout)
        
        layout.addWidget(logging_group)
        
        layout.addStretch()
        
        return tab 
   
    def _create_sync_tab(self) -> QWidget:
        """Create the synchronization configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Sync behavior group
        sync_group = QGroupBox("Synchronization Behavior")
        sync_layout = QFormLayout(sync_group)
        
        self.auto_sync_check = QCheckBox("Enable automatic synchronization")
        sync_layout.addRow(self.auto_sync_check)
        
        self.sync_on_startup_check = QCheckBox("Sync on application startup")
        sync_layout.addRow(self.sync_on_startup_check)
        
        self.confirm_operations_check = QCheckBox("Confirm operations before execution")
        self.confirm_operations_check.setChecked(True)
        sync_layout.addRow(self.confirm_operations_check)
        
        layout.addWidget(sync_group)
        
        # Package exclusions group
        exclusions_group = QGroupBox("Package Exclusions")
        exclusions_layout = QVBoxLayout(exclusions_group)
        
        exclusions_label = QLabel("Packages to exclude from synchronization (one per line):")
        exclusions_layout.addWidget(exclusions_label)
        
        self.exclusions_text = QTextEdit()
        self.exclusions_text.setMaximumHeight(100)
        self.exclusions_text.setPlaceholderText("linux\nlinux-headers\ngrub")
        exclusions_layout.addWidget(self.exclusions_text)
        
        layout.addWidget(exclusions_group)
        
        # Conflict resolution group
        conflict_group = QGroupBox("Conflict Resolution")
        conflict_layout = QFormLayout(conflict_group)
        
        self.conflict_resolution_combo = QComboBox()
        self.conflict_resolution_combo.addItems([
            "Ask user (manual)",
            "Use newest version",
            "Use oldest version",
            "Skip conflicting packages"
        ])
        conflict_layout.addRow("Conflict Resolution:", self.conflict_resolution_combo)
        
        layout.addWidget(conflict_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_interface_tab(self) -> QWidget:
        """Create the interface configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # System tray group
        tray_group = QGroupBox("System Tray")
        tray_layout = QFormLayout(tray_group)
        
        self.show_notifications_check = QCheckBox("Show desktop notifications")
        self.show_notifications_check.setChecked(True)
        tray_layout.addRow(self.show_notifications_check)
        
        self.minimize_to_tray_check = QCheckBox("Minimize to system tray")
        self.minimize_to_tray_check.setChecked(True)
        tray_layout.addRow(self.minimize_to_tray_check)
        
        self.start_minimized_check = QCheckBox("Start minimized to tray")
        tray_layout.addRow(self.start_minimized_check)
        
        layout.addWidget(tray_group)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System Default", "Light", "Dark"])
        appearance_layout.addRow("Theme:", self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        appearance_layout.addRow("Font Size:", self.font_size_spin)
        
        layout.addWidget(appearance_group)
        
        # WayBar integration group
        waybar_group = QGroupBox("WayBar Integration")
        waybar_layout = QFormLayout(waybar_group)
        
        self.enable_waybar_check = QCheckBox("Enable WayBar integration")
        waybar_layout.addRow(self.enable_waybar_check)
        
        self.waybar_format_edit = QLineEdit()
        self.waybar_format_edit.setPlaceholderText('{"text": "{status}", "class": "{class}"}')
        waybar_layout.addRow("Output Format:", self.waybar_format_edit)
        
        layout.addWidget(waybar_group)
        
        layout.addStretch()
        
        return tab
    
    def _load_current_settings(self) -> None:
        """Load current settings into the UI controls."""
        # Server settings
        self.server_url_edit.setText(self.current_config.get('server_url', ''))
        self.api_key_edit.setText(self.current_config.get('api_key', ''))
        self.timeout_spin.setValue(self.current_config.get('timeout', 30))
        self.retry_attempts_spin.setValue(self.current_config.get('retry_attempts', 3))
        self.verify_ssl_check.setChecked(self.current_config.get('verify_ssl', True))
        self.ssl_cert_path_edit.setText(self.current_config.get('ssl_cert_path', ''))
        
        # Client settings
        self.endpoint_name_edit.setText(self.current_config.get('endpoint_name', ''))
        
        # Update pool info display
        current_pool = self.current_config.get('pool_id', '')
        if current_pool:
            self.pool_info_label.setText(f"Currently assigned to: {current_pool}")
            self.pool_info_label.setStyleSheet("color: green;")
        else:
            self.pool_info_label.setText("Not yet assigned - will be assigned after registration")
            self.pool_info_label.setStyleSheet("color: gray; font-style: italic;")
        
        # Auto-detect hostname
        import socket
        self.hostname_edit.setText(socket.gethostname())
        
        self.update_interval_spin.setValue(self.current_config.get('update_interval', 300))
        self.auto_register_check.setChecked(self.current_config.get('auto_register', True))
        self.log_level_combo.setCurrentText(self.current_config.get('log_level', 'INFO'))
        self.log_file_edit.setText(self.current_config.get('log_file', ''))
        
        # Sync settings
        self.auto_sync_check.setChecked(self.current_config.get('auto_sync', False))
        self.sync_on_startup_check.setChecked(self.current_config.get('sync_on_startup', False))
        self.confirm_operations_check.setChecked(self.current_config.get('confirm_operations', True))
        
        exclusions = self.current_config.get('exclude_packages', [])
        self.exclusions_text.setPlainText('\n'.join(exclusions))
        
        conflict_resolution = self.current_config.get('conflict_resolution', 'manual')
        conflict_map = {
            'manual': 0,
            'newest': 1,
            'oldest': 2,
            'skip': 3
        }
        self.conflict_resolution_combo.setCurrentIndex(conflict_map.get(conflict_resolution, 0))
        
        # Interface settings
        self.show_notifications_check.setChecked(self.current_config.get('show_notifications', True))
        self.minimize_to_tray_check.setChecked(self.current_config.get('minimize_to_tray', True))
        self.start_minimized_check.setChecked(self.current_config.get('start_minimized', False))
        self.theme_combo.setCurrentText(self.current_config.get('theme', 'System Default'))
        self.font_size_spin.setValue(self.current_config.get('font_size', 10))
        self.enable_waybar_check.setChecked(self.current_config.get('enable_waybar', False))
        self.waybar_format_edit.setText(self.current_config.get('waybar_format', ''))
    
    def _collect_settings(self) -> Dict[str, Any]:
        """Collect settings from UI controls."""
        settings = {}
        
        # Server settings
        settings['server_url'] = self.server_url_edit.text().strip()
        settings['api_key'] = self.api_key_edit.text().strip()
        settings['timeout'] = self.timeout_spin.value()
        settings['retry_attempts'] = self.retry_attempts_spin.value()
        settings['verify_ssl'] = self.verify_ssl_check.isChecked()
        settings['ssl_cert_path'] = self.ssl_cert_path_edit.text().strip()
        
        # Client settings
        settings['endpoint_name'] = self.endpoint_name_edit.text().strip()
        # Note: pool_id is not collected from UI - it's assigned by server
        settings['update_interval'] = self.update_interval_spin.value()
        settings['auto_register'] = self.auto_register_check.isChecked()
        settings['log_level'] = self.log_level_combo.currentText()
        settings['log_file'] = self.log_file_edit.text().strip()
        
        # Sync settings
        settings['auto_sync'] = self.auto_sync_check.isChecked()
        settings['sync_on_startup'] = self.sync_on_startup_check.isChecked()
        settings['confirm_operations'] = self.confirm_operations_check.isChecked()
        
        exclusions_text = self.exclusions_text.toPlainText().strip()
        settings['exclude_packages'] = [line.strip() for line in exclusions_text.split('\n') if line.strip()]
        
        conflict_map = ['manual', 'newest', 'oldest', 'skip']
        settings['conflict_resolution'] = conflict_map[self.conflict_resolution_combo.currentIndex()]
        
        # Interface settings
        settings['show_notifications'] = self.show_notifications_check.isChecked()
        settings['minimize_to_tray'] = self.minimize_to_tray_check.isChecked()
        settings['start_minimized'] = self.start_minimized_check.isChecked()
        settings['theme'] = self.theme_combo.currentText()
        settings['font_size'] = self.font_size_spin.value()
        settings['enable_waybar'] = self.enable_waybar_check.isChecked()
        settings['waybar_format'] = self.waybar_format_edit.text().strip()
        
        return settings
    
    def _validate_settings(self, settings: Dict[str, Any]) -> tuple[bool, str]:
        """Validate the collected settings."""
        # Validate server URL
        if not settings['server_url']:
            return False, "Server URL is required"
        
        if not settings['server_url'].startswith(('http://', 'https://')):
            return False, "Server URL must start with http:// or https://"
        
        # Validate endpoint name
        if not settings['endpoint_name']:
            return False, "Endpoint name is required"
        
        # Note: Pool ID validation removed - assigned by server
        
        # Validate timeout
        if settings['timeout'] < 5:
            return False, "Connection timeout must be at least 5 seconds"
        
        return True, ""
    
    def _browse_ssl_cert(self) -> None:
        """Browse for SSL certificate file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select SSL Certificate",
            "",
            "Certificate Files (*.crt *.pem *.cer);;All Files (*)"
        )
        if filename:
            self.ssl_cert_path_edit.setText(filename)
    
    def _browse_log_file(self) -> None:
        """Browse for log file location."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File",
            "pacman_sync.log",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )
        if filename:
            self.log_file_edit.setText(filename)
    
    def _apply_changes(self) -> None:
        """Apply the current settings without closing the dialog."""
        settings = self._collect_settings()
        is_valid, error_message = self._validate_settings(settings)
        
        if not is_valid:
            QMessageBox.warning(self, "Invalid Settings", error_message)
            return
        
        self.modified_config = settings
        self.settings_changed.emit(settings)
        
        QMessageBox.information(
            self,
            "Settings Applied",
            "Configuration settings have been applied and are now active.\n\n"
            "Changes to server connection, update intervals, and notification "
            "preferences take effect immediately."
        )
        
        logger.info("Configuration settings applied")
    
    def _accept_changes(self) -> None:
        """Accept and apply changes, then close the dialog."""
        settings = self._collect_settings()
        is_valid, error_message = self._validate_settings(settings)
        
        if not is_valid:
            QMessageBox.warning(self, "Invalid Settings", error_message)
            return
        
        self.modified_config = settings
        self.settings_changed.emit(settings)
        self.accept()
        
        logger.info("Configuration settings accepted and applied")
    
    def _restore_defaults(self) -> None:
        """Restore default settings."""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore all settings to their default values?\n\n"
            "This will overwrite your current configuration.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Default configuration
            default_config = {
                'server_url': 'http://localhost:8080',
                'api_key': '',
                'timeout': 30,
                'retry_attempts': 3,
                'verify_ssl': True,
                'ssl_cert_path': '',
                'endpoint_name': 'my-desktop',
                'pool_id': '',  # Assigned by server
                'update_interval': 300,
                'auto_register': True,
                'log_level': 'INFO',
                'log_file': '',
                'auto_sync': False,
                'sync_on_startup': False,
                'confirm_operations': True,
                'exclude_packages': [],
                'conflict_resolution': 'manual',
                'show_notifications': True,
                'minimize_to_tray': True,
                'start_minimized': False,
                'theme': 'System Default',
                'font_size': 10,
                'enable_waybar': False,
                'waybar_format': ''
            }
            
            self.current_config = default_config
            self._load_current_settings()
            
            logger.info("Configuration settings restored to defaults")
    
    def get_modified_config(self) -> Dict[str, Any]:
        """Get the modified configuration."""
        return self.modified_config