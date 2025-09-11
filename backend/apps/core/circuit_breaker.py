"""
Circuit breaker implementation for external service calls.

Prevents cascading failures by failing fast when services are unavailable.
"""
import functools
import logging
import time
from enum import Enum
from typing import Callable, Optional, Any, Union, Type, Tuple, Dict
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service is down, calls fail immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Unique identifier for this circuit
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
            success_threshold: Successful calls needed to close circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        # Cache keys
        self._state_key = f"circuit:{name}:state"
        self._failure_count_key = f"circuit:{name}:failures"
        self._success_count_key = f"circuit:{name}:successes"
        self._last_failure_key = f"circuit:{name}:last_failure"
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        state_value = cache.get(self._state_key, CircuitState.CLOSED.value)
        return CircuitState(state_value)
    
    @state.setter
    def state(self, value: CircuitState):
        """Set circuit state"""
        cache.set(self._state_key, value.value, timeout=None)
        logger.info("Circuit %s state changed to %s", self.name, value.value)
    
    @property
    def failure_count(self) -> int:
        """Get failure count"""
        return cache.get(self._failure_count_key, 0)
    
    @failure_count.setter
    def failure_count(self, value: int):
        """Set failure count"""
        cache.set(self._failure_count_key, value, timeout=3600)
    
    @property
    def success_count(self) -> int:
        """Get success count"""
        return cache.get(self._success_count_key, 0)
    
    @success_count.setter
    def success_count(self, value: int):
        """Set success count"""
        cache.set(self._success_count_key, value, timeout=3600)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenException: If circuit is open
            Original exception: If circuit is closed and function fails
        """
        state = self.state
        
        if state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit %s entering half-open state", self.name)
            else:
                raise CircuitOpenException(f"Circuit {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:  # type: ignore[misc]
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        last_failure = cache.get(self._last_failure_key)
        if last_failure is None:
            return True
        
        return (time.time() - last_failure) >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        state = self.state
        
        if state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit %s closed after recovery", self.name)
        
        elif state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        state = self.state
        
        self.failure_count += 1
        cache.set(self._last_failure_key, time.time(), timeout=3600)
        
        if state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
            logger.warning("Circuit %s reopened after test failure", self.name)
            
        elif state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    "Circuit %s opened after %s failures",
                    self.name,
                    self.failure_count
                )
    
    def reset(self):
        """Manually reset the circuit"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        cache.delete(self._last_failure_key)
        logger.info("Circuit %s manually reset", self.name)
    
    def get_status(self) -> dict:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "thresholds": {
                "failure": self.failure_threshold,
                "success": self.success_threshold,
            },
        }


class CircuitOpenException(Exception):
    """Exception raised when circuit is open"""
    pass


def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    success_threshold: int = 2,
    fallback: Optional[Callable] = None,
):
    """
    Decorator to add circuit breaker to functions.
    
    Args:
        name: Circuit name (defaults to function name)
        failure_threshold: Failures before opening
        recovery_timeout: Recovery timeout in seconds
        expected_exception: Exception to catch
        success_threshold: Successes needed to close
        fallback: Fallback function when circuit is open
    
    Example:
        @circuit_breaker(name="external_api", failure_threshold=3)
        def call_external_api():
            return requests.get("https://api.example.com/data")
    """
    def decorator(func):
        circuit_name = name or f"{func.__module__}.{func.__name__}"
        breaker = CircuitBreaker(
            name=circuit_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold,
        )
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitOpenException:
                if fallback:
                    logger.info("Using fallback for %s", circuit_name)
                    return fallback(*args, **kwargs)
                raise
        
        # Add methods to check status
        wrapper.circuit_breaker = breaker
        wrapper.reset_circuit = breaker.reset
        wrapper.circuit_status = breaker.get_status
        
        return wrapper
    return decorator


# Pre-configured circuit breakers for common services

email_circuit_breaker = functools.partial(
    circuit_breaker,
    name="email_service",
    failure_threshold=3,
    recovery_timeout=120,
    expected_exception=(ConnectionError, TimeoutError),
)

storage_circuit_breaker = functools.partial(
    circuit_breaker,
    name="storage_service",
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(ConnectionError, TimeoutError),
)

search_circuit_breaker = functools.partial(
    circuit_breaker,
    name="search_service",
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=(ConnectionError, TimeoutError),
)

external_api_circuit_breaker = functools.partial(
    circuit_breaker,
    name="external_api",
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(ConnectionError, TimeoutError),
)


class CircuitBreakerManager:
    """Manager for all circuit breakers in the system"""
    
    _breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def register(cls, breaker: CircuitBreaker):
        """Register a circuit breaker"""
        cls._breakers[breaker.name] = breaker
    
    @classmethod
    def get(cls, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name"""
        return cls._breakers.get(name)
    
    @classmethod
    def get_all_status(cls) -> dict:
        """Get status of all circuit breakers"""
        return {
            name: breaker.get_status()
            for name, breaker in cls._breakers.items()
        }
    
    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers"""
        for breaker in cls._breakers.values():
            breaker.reset()
    
    @classmethod
    def open_circuits_count(cls) -> int:
        """Count open circuits"""
        return sum(
            1 for breaker in cls._breakers.values()
            if breaker.state == CircuitState.OPEN
        )