"""
Comprehensive error recovery system for Pacman Sync Utility Client.

This module provides automated error recovery mechanisms, retry logic,
and graceful degradation strategies for various error conditions.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from shared.exceptions import (
    PacmanSyncError, ErrorCode, ErrorSeverity, RecoveryAction,
    NetworkError, AuthenticationError, SystemIntegrationError
)
from shared.logging_config import AuditLogger, OperationLogger

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategy types."""
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    SCHEDULED_RETRY = "scheduled_retry"
    USER_INTERVENTION = "user_intervention"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    SERVICE_RESTART = "service_restart"
    IGNORE_ERROR = "ignore_error"


class RecoveryResult(Enum):
    """Recovery attempt results."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    RETRY_NEEDED = "retry_needed"
    USER_ACTION_REQUIRED = "user_action_required"
    PERMANENT_FAILURE = "permanent_failure"


@dataclass
class RecoveryAttempt:
    """Information about a recovery attempt."""
    timestamp: datetime
    strategy: RecoveryStrategy
    result: RecoveryResult
    error_code: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0


@dataclass
class ErrorRecoveryConfig:
    """Configuration for error recovery behavior."""
    max_retry_attempts: int = 3
    base_retry_delay: float = 1.0
    max_retry_delay: float = 300.0  # 5 minutes
    exponential_base: float = 2.0
    jitter_factor: float = 0.1
    
    # Error-specific configurations
    network_error_max_retries: int = 5
    auth_error_max_retries: int = 2
    system_error_max_retries: int = 1
    
    # Degradation thresholds
    max_consecutive_failures: int = 5
    degradation_timeout_minutes: int = 30
    
    # Recovery timeouts
    recovery_timeout_seconds: float = 60.0
    user_intervention_timeout_minutes: int = 10


class ErrorRecoverySystem(QObject):
    """
    Comprehensive error recovery system with multiple strategies.
    
    Provides automated recovery mechanisms, retry logic, and graceful
    degradation for various error conditions in the client application.
    """
    
    # Signals
    recovery_started = pyqtSignal(object, object)  # error, strategy
    recovery_completed = pyqtSignal(object, object)  # error, result
    degradation_activated = pyqtSignal(str)  # reason
    user_intervention_required = pyqtSignal(object, str)  # error, instructions
    
    def __init__(self, config: Optional[ErrorRecoveryConfig] = None):
        super().__init__()
        
        self.config = config or ErrorRecoveryConfig()
        
        # Recovery state
        self._recovery_history: List[RecoveryAttempt] = []
        self._active_recoveries: Dict[str, asyncio.Task] = {}
        self._degraded_services: Dict[str, datetime] = {}
        self._consecutive_failures: Dict[str, int] = {}
        
        # Recovery callbacks
        self._recovery_callbacks: Dict[RecoveryAction, Callable] = {}
        self._degradation_callbacks: Dict[str, Callable] = {}
        
        # Timers
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_old_history)
        self._cleanup_timer.start(300000)  # Clean up every 5 minutes
        
        # Logging
        self._audit_logger = AuditLogger("client_recovery")
        self._operation_logger = OperationLogger("client_recovery")
        
        logger.info("Error recovery system initialized")
    
    def register_recovery_callback(self, action: RecoveryAction, callback: Callable):
        """Register a callback for a specific recovery action."""
        self._recovery_callbacks[action] = callback
        logger.debug(f"Recovery callback registered for: {action.value}")
    
    def register_degradation_callback(self, service: str, callback: Callable):
        """Register a callback for service degradation."""
        self._degradation_callbacks[service] = callback
        logger.debug(f"Degradation callback registered for: {service}")
    
    async def handle_error(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]] = None,
        force_strategy: Optional[RecoveryStrategy] = None
    ) -> RecoveryResult:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            error: The error to handle
            context: Additional context information
            force_strategy: Force a specific recovery strategy
            
        Returns:
            Recovery result
        """
        try:
            # Generate unique recovery ID
            recovery_id = f"recovery_{int(time.time() * 1000)}"
            
            # Determine recovery strategy
            strategy = force_strategy or self._determine_recovery_strategy(error, context)
            
            # Log recovery start
            self._audit_logger.log_event(
                event_type="error_recovery",
                message=f"Starting error recovery: {error.error_code.value}",
                additional_context={
                    'recovery_id': recovery_id,
                    'strategy': strategy.value,
                    'error_code': error.error_code.value,
                    'error_severity': error.severity.value
                }
            )
            
            self._operation_logger.log_operation_start(
                operation_type="error_recovery",
                operation_id=recovery_id,
                context={
                    'error_code': error.error_code.value,
                    'strategy': strategy.value,
                    'context': context or {}
                }
            )
            
            # Emit recovery started signal
            self.recovery_started.emit(error, strategy)
            
            # Execute recovery strategy
            start_time = time.time()
            result = await self._execute_recovery_strategy(error, strategy, context, recovery_id)
            duration = time.time() - start_time
            
            # Record recovery attempt
            attempt = RecoveryAttempt(
                timestamp=datetime.now(),
                strategy=strategy,
                result=result,
                error_code=error.error_code.value,
                details=context or {},
                duration_seconds=duration
            )
            self._recovery_history.append(attempt)
            
            # Update failure counters
            self._update_failure_counters(error, result)
            
            # Log recovery completion
            self._operation_logger.log_operation_complete(
                operation_id=recovery_id,
                success=(result == RecoveryResult.SUCCESS),
                duration_seconds=duration,
                result_summary=f"Recovery {result.value}",
                context={'strategy': strategy.value, 'error_code': error.error_code.value}
            )
            
            # Emit recovery completed signal
            self.recovery_completed.emit(error, result)
            
            # Handle degradation if needed
            if result in [RecoveryResult.FAILURE, RecoveryResult.PERMANENT_FAILURE]:
                await self._consider_degradation(error, context)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in recovery system: {e}", exc_info=True)
            return RecoveryResult.FAILURE
    
    def _determine_recovery_strategy(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]]
    ) -> RecoveryStrategy:
        """Determine the best recovery strategy for an error."""
        
        # Check error severity
        if error.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.USER_INTERVENTION
        
        # Check error type and suggested recovery actions
        if isinstance(error, NetworkError):
            return self._determine_network_recovery_strategy(error)
        elif isinstance(error, AuthenticationError):
            return self._determine_auth_recovery_strategy(error)
        elif isinstance(error, SystemIntegrationError):
            return self._determine_system_recovery_strategy(error)
        
        # Check recovery actions suggested by the error
        if RecoveryAction.RETRY_WITH_BACKOFF in error.recovery_actions:
            return RecoveryStrategy.EXPONENTIAL_BACKOFF
        elif RecoveryAction.RETRY in error.recovery_actions:
            return RecoveryStrategy.IMMEDIATE_RETRY
        elif RecoveryAction.USER_INTERVENTION in error.recovery_actions:
            return RecoveryStrategy.USER_INTERVENTION
        elif RecoveryAction.IGNORE in error.recovery_actions:
            return RecoveryStrategy.IGNORE_ERROR
        
        # Default strategy based on error code
        error_code_strategies = {
            ErrorCode.NETWORK_CONNECTION_FAILED: RecoveryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCode.NETWORK_TIMEOUT: RecoveryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCode.AUTH_INVALID_TOKEN: RecoveryStrategy.IMMEDIATE_RETRY,
            ErrorCode.AUTH_TOKEN_EXPIRED: RecoveryStrategy.IMMEDIATE_RETRY,
            ErrorCode.SYSTEM_TRAY_UNAVAILABLE: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ErrorCode.SYSTEM_SERVICE_UNAVAILABLE: RecoveryStrategy.SCHEDULED_RETRY,
            ErrorCode.INTERNAL_SERVICE_UNAVAILABLE: RecoveryStrategy.EXPONENTIAL_BACKOFF
        }
        
        return error_code_strategies.get(error.error_code, RecoveryStrategy.USER_INTERVENTION)
    
    def _determine_network_recovery_strategy(self, error: NetworkError) -> RecoveryStrategy:
        """Determine recovery strategy for network errors."""
        # Check consecutive network failures
        network_failures = self._consecutive_failures.get('network', 0)
        
        if network_failures >= self.config.network_error_max_retries:
            return RecoveryStrategy.GRACEFUL_DEGRADATION
        elif error.error_code == ErrorCode.NETWORK_TIMEOUT:
            return RecoveryStrategy.EXPONENTIAL_BACKOFF
        else:
            return RecoveryStrategy.EXPONENTIAL_BACKOFF
    
    def _determine_auth_recovery_strategy(self, error: AuthenticationError) -> RecoveryStrategy:
        """Determine recovery strategy for authentication errors."""
        auth_failures = self._consecutive_failures.get('auth', 0)
        
        if auth_failures >= self.config.auth_error_max_retries:
            return RecoveryStrategy.USER_INTERVENTION
        else:
            return RecoveryStrategy.IMMEDIATE_RETRY
    
    def _determine_system_recovery_strategy(self, error: SystemIntegrationError) -> RecoveryStrategy:
        """Determine recovery strategy for system integration errors."""
        if error.error_code == ErrorCode.SYSTEM_TRAY_UNAVAILABLE:
            return RecoveryStrategy.GRACEFUL_DEGRADATION
        elif error.error_code == ErrorCode.SYSTEM_PERMISSION_DENIED:
            return RecoveryStrategy.USER_INTERVENTION
        else:
            return RecoveryStrategy.SCHEDULED_RETRY
    
    async def _execute_recovery_strategy(
        self,
        error: PacmanSyncError,
        strategy: RecoveryStrategy,
        context: Optional[Dict[str, Any]],
        recovery_id: str
    ) -> RecoveryResult:
        """Execute the specified recovery strategy."""
        
        try:
            if strategy == RecoveryStrategy.IMMEDIATE_RETRY:
                return await self._immediate_retry(error, context)
            
            elif strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                return await self._exponential_backoff_retry(error, context)
            
            elif strategy == RecoveryStrategy.SCHEDULED_RETRY:
                return await self._scheduled_retry(error, context)
            
            elif strategy == RecoveryStrategy.USER_INTERVENTION:
                return await self._request_user_intervention(error, context)
            
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                return await self._activate_graceful_degradation(error, context)
            
            elif strategy == RecoveryStrategy.SERVICE_RESTART:
                return await self._restart_service(error, context)
            
            elif strategy == RecoveryStrategy.IGNORE_ERROR:
                return RecoveryResult.SUCCESS  # Ignore the error
            
            else:
                logger.warning(f"Unknown recovery strategy: {strategy}")
                return RecoveryResult.FAILURE
                
        except Exception as e:
            logger.error(f"Recovery strategy execution failed: {e}", exc_info=True)
            return RecoveryResult.FAILURE
    
    async def _immediate_retry(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]]
    ) -> RecoveryResult:
        """Execute immediate retry recovery."""
        
        # Find appropriate recovery callback
        for action in error.recovery_actions:
            if action in self._recovery_callbacks:
                try:
                    callback = self._recovery_callbacks[action]
                    success = await self._execute_callback(callback)
                    
                    if success:
                        logger.info(f"Immediate retry successful for: {error.error_code.value}")
                        return RecoveryResult.SUCCESS
                    else:
                        logger.warning(f"Immediate retry failed for: {error.error_code.value}")
                        return RecoveryResult.FAILURE
                        
                except Exception as e:
                    logger.error(f"Immediate retry callback failed: {e}")
                    return RecoveryResult.FAILURE
        
        # No callback available
        logger.warning(f"No recovery callback available for: {error.error_code.value}")
        return RecoveryResult.USER_ACTION_REQUIRED
    
    async def _exponential_backoff_retry(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]]
    ) -> RecoveryResult:
        """Execute exponential backoff retry recovery."""
        
        # Determine retry count for this error type
        error_type = error.error_code.value
        retry_count = self._consecutive_failures.get(error_type, 0)
        
        if retry_count >= self.config.max_retry_attempts:
            logger.warning(f"Max retries exceeded for: {error_type}")
            return RecoveryResult.PERMANENT_FAILURE
        
        # Calculate delay with exponential backoff
        delay = min(
            self.config.base_retry_delay * (self.config.exponential_base ** retry_count),
            self.config.max_retry_delay
        )
        
        # Add jitter
        import random
        jitter = delay * self.config.jitter_factor * (random.random() - 0.5)
        delay += jitter
        
        logger.info(f"Retrying in {delay:.1f} seconds (attempt {retry_count + 1})")
        
        # Wait for delay
        await asyncio.sleep(delay)
        
        # Execute retry
        for action in error.recovery_actions:
            if action in self._recovery_callbacks:
                try:
                    callback = self._recovery_callbacks[action]
                    success = await self._execute_callback(callback)
                    
                    if success:
                        logger.info(f"Exponential backoff retry successful for: {error_type}")
                        return RecoveryResult.SUCCESS
                    else:
                        logger.warning(f"Exponential backoff retry failed for: {error_type}")
                        return RecoveryResult.RETRY_NEEDED
                        
                except Exception as e:
                    logger.error(f"Exponential backoff retry callback failed: {e}")
                    return RecoveryResult.FAILURE
        
        return RecoveryResult.USER_ACTION_REQUIRED
    
    async def _scheduled_retry(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]]
    ) -> RecoveryResult:
        """Execute scheduled retry recovery."""
        
        # Schedule retry for later (using QTimer in real implementation)
        retry_delay = 60.0  # 1 minute default
        
        logger.info(f"Scheduling retry in {retry_delay} seconds for: {error.error_code.value}")
        
        # In a real implementation, this would use QTimer to schedule the retry
        # For now, we'll just indicate that retry is needed
        return RecoveryResult.RETRY_NEEDED
    
    async def _request_user_intervention(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]]
    ) -> RecoveryResult:
        """Request user intervention for error resolution."""
        
        # Generate user-friendly instructions
        instructions = self._generate_user_instructions(error)
        
        logger.info(f"Requesting user intervention for: {error.error_code.value}")
        
        # Emit signal for UI to show user intervention dialog
        self.user_intervention_required.emit(error, instructions)
        
        return RecoveryResult.USER_ACTION_REQUIRED
    
    async def _activate_graceful_degradation(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]]
    ) -> RecoveryResult:
        """Activate graceful degradation for the affected service."""
        
        # Determine which service to degrade
        service = self._determine_affected_service(error)
        
        logger.info(f"Activating graceful degradation for service: {service}")
        
        # Mark service as degraded
        self._degraded_services[service] = datetime.now()
        
        # Execute degradation callback if available
        if service in self._degradation_callbacks:
            try:
                callback = self._degradation_callbacks[service]
                await self._execute_callback(callback)
                
                # Emit degradation signal
                self.degradation_activated.emit(service)
                
                return RecoveryResult.PARTIAL_SUCCESS
                
            except Exception as e:
                logger.error(f"Degradation callback failed for {service}: {e}")
                return RecoveryResult.FAILURE
        
        # No callback available - just mark as degraded
        self.degradation_activated.emit(service)
        return RecoveryResult.PARTIAL_SUCCESS
    
    async def _restart_service(
        self,
        error: PacmanSyncError,
        context: Optional[Dict[str, Any]]
    ) -> RecoveryResult:
        """Restart the affected service."""
        
        service = self._determine_affected_service(error)
        logger.info(f"Attempting to restart service: {service}")
        
        # This would implement actual service restart logic
        # For now, just indicate that user action is required
        return RecoveryResult.USER_ACTION_REQUIRED
    
    async def _execute_callback(self, callback: Callable) -> bool:
        """Execute a recovery callback safely."""
        try:
            if asyncio.iscoroutinefunction(callback):
                result = await callback()
            else:
                result = callback()
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Recovery callback execution failed: {e}")
            return False
    
    def _generate_user_instructions(self, error: PacmanSyncError) -> str:
        """Generate user-friendly instructions for error resolution."""
        
        instructions_map = {
            ErrorCode.AUTH_INVALID_TOKEN: (
                "Authentication failed. Please check your credentials and try again. "
                "You may need to re-register this endpoint with the server."
            ),
            ErrorCode.NETWORK_CONNECTION_FAILED: (
                "Cannot connect to the server. Please check:\n"
                "1. Your network connection\n"
                "2. Server URL configuration\n"
                "3. Firewall settings\n"
                "4. Server availability"
            ),
            ErrorCode.SYSTEM_PERMISSION_DENIED: (
                "Permission denied. Please ensure the application has the necessary "
                "permissions to perform package operations. You may need to run "
                "with elevated privileges."
            ),
            ErrorCode.SYSTEM_TRAY_UNAVAILABLE: (
                "System tray is not available. The application will continue to run "
                "but notifications will be limited. This is normal in some desktop "
                "environments."
            ),
            ErrorCode.PACKAGE_DEPENDENCY_CONFLICT: (
                "Package dependency conflict detected. Please resolve the conflicts "
                "manually using your package manager before attempting synchronization."
            )
        }
        
        return instructions_map.get(
            error.error_code,
            f"An error occurred: {error.user_message}\n\n"
            f"Please check the application logs for more details and contact "
            f"support if the problem persists."
        )
    
    def _determine_affected_service(self, error: PacmanSyncError) -> str:
        """Determine which service is affected by the error."""
        
        if isinstance(error, NetworkError):
            return "network"
        elif isinstance(error, AuthenticationError):
            return "authentication"
        elif isinstance(error, SystemIntegrationError):
            if error.error_code == ErrorCode.SYSTEM_TRAY_UNAVAILABLE:
                return "system_tray"
            else:
                return "system_integration"
        else:
            return "general"
    
    def _update_failure_counters(self, error: PacmanSyncError, result: RecoveryResult):
        """Update failure counters based on recovery result."""
        
        error_type = error.error_code.value
        service = self._determine_affected_service(error)
        
        if result == RecoveryResult.SUCCESS:
            # Reset counters on success
            self._consecutive_failures[error_type] = 0
            self._consecutive_failures[service] = 0
        else:
            # Increment counters on failure
            self._consecutive_failures[error_type] = self._consecutive_failures.get(error_type, 0) + 1
            self._consecutive_failures[service] = self._consecutive_failures.get(service, 0) + 1
    
    async def _consider_degradation(self, error: PacmanSyncError, context: Optional[Dict[str, Any]]):
        """Consider activating degradation based on failure patterns."""
        
        service = self._determine_affected_service(error)
        consecutive_failures = self._consecutive_failures.get(service, 0)
        
        if consecutive_failures >= self.config.max_consecutive_failures:
            logger.warning(f"Too many consecutive failures for {service}, activating degradation")
            await self._activate_graceful_degradation(error, context)
    
    def _cleanup_old_history(self):
        """Clean up old recovery history entries."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            old_count = len(self._recovery_history)
            self._recovery_history = [
                attempt for attempt in self._recovery_history
                if attempt.timestamp > cutoff_time
            ]
            
            cleaned_count = old_count - len(self._recovery_history)
            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} old recovery history entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up recovery history: {e}")
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery system statistics."""
        
        total_attempts = len(self._recovery_history)
        if total_attempts == 0:
            return {"total_attempts": 0}
        
        # Calculate success rate
        successful_attempts = sum(
            1 for attempt in self._recovery_history
            if attempt.result == RecoveryResult.SUCCESS
        )
        success_rate = successful_attempts / total_attempts
        
        # Calculate average recovery time
        total_duration = sum(attempt.duration_seconds for attempt in self._recovery_history)
        avg_duration = total_duration / total_attempts
        
        # Count by strategy
        strategy_counts = {}
        for attempt in self._recovery_history:
            strategy = attempt.strategy.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        # Count by result
        result_counts = {}
        for attempt in self._recovery_history:
            result = attempt.result.value
            result_counts[result] = result_counts.get(result, 0) + 1
        
        return {
            "total_attempts": total_attempts,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "strategy_distribution": strategy_counts,
            "result_distribution": result_counts,
            "consecutive_failures": dict(self._consecutive_failures),
            "degraded_services": {
                service: timestamp.isoformat()
                for service, timestamp in self._degraded_services.items()
            }
        }
    
    def is_service_degraded(self, service: str) -> bool:
        """Check if a service is currently degraded."""
        return service in self._degraded_services
    
    def restore_service(self, service: str):
        """Restore a degraded service."""
        if service in self._degraded_services:
            del self._degraded_services[service]
            logger.info(f"Service restored: {service}")
    
    def clear_failure_counters(self, error_type: Optional[str] = None):
        """Clear failure counters."""
        if error_type:
            self._consecutive_failures.pop(error_type, None)
        else:
            self._consecutive_failures.clear()
        
        logger.info(f"Failure counters cleared: {error_type or 'all'}")