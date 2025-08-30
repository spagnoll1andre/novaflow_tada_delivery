# -*- coding: utf-8 -*-
"""
API error handling utilities for TADA ERP.
"""

import logging
import time
from functools import wraps
from typing import Any, Dict, Optional, Callable, Union
from requests.exceptions import (
    RequestException, ConnectionError, Timeout, HTTPError,
    TooManyRedirects, URLRequired, InvalidURL
)
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API-related errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.response_data = response_data or {}


class APIErrorHandler:
    """Centralized API error handling for TADA ERP."""
    
    # HTTP status code to user-friendly message mapping
    STATUS_MESSAGES = {
        400: "Bad request - please check your input data",
        401: "Authentication failed - please check your API key",
        403: "Access forbidden - insufficient permissions",
        404: "Resource not found - the requested item does not exist",
        405: "Method not allowed - invalid operation",
        408: "Request timeout - the server took too long to respond",
        409: "Conflict - the resource already exists or is in use",
        422: "Validation error - please check your input data",
        429: "Too many requests - please wait before trying again",
        500: "Internal server error - please try again later",
        502: "Bad gateway - service temporarily unavailable",
        503: "Service unavailable - please try again later",
        504: "Gateway timeout - service temporarily unavailable",
    }
    
    # Error codes that should trigger a retry
    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    
    # Error codes that indicate authentication issues
    AUTH_ERROR_CODES = {401, 403}
    
    # Error codes that indicate client errors (don't retry)
    CLIENT_ERROR_CODES = {400, 404, 405, 409, 422}
    
    @classmethod
    def handle_api_response(cls, response: Any, operation: str = "API call") -> Any:
        """
        Handle API response and extract data or raise appropriate errors.
        
        Args:
            response: The API response (dict or other)
            operation: Description of the operation for error messages
            
        Returns:
            The response data if successful
            
        Raises:
            APIError: If the response indicates an error
        """
        if isinstance(response, dict):
            # Check for error in response
            if response.get('error'):
                error_message = response.get('message', 'Unknown API error')
                error_code = response.get('code')
                status_code = response.get('status_code')
                
                raise APIError(
                    message=f"{operation} failed: {error_message}",
                    error_code=error_code,
                    status_code=status_code,
                    response_data=response
                )
            
            # Return data if available, otherwise return the whole response
            return response.get('data', response)
        
        return response
    
    @classmethod
    def handle_request_exception(cls, exception: Exception, operation: str = "API call") -> None:
        """
        Handle request exceptions and convert to user-friendly errors.
        
        Args:
            exception: The exception that occurred
            operation: Description of the operation for error messages
            
        Raises:
            APIError: Converted user-friendly error
        """
        if isinstance(exception, ConnectionError):
            raise APIError(
                message=f"{operation} failed: Unable to connect to the API server. "
                       "Please check your internet connection and try again.",
                error_code="CONNECTION_ERROR"
            )
        
        elif isinstance(exception, Timeout):
            raise APIError(
                message=f"{operation} failed: Request timed out. "
                       "The server is taking too long to respond. Please try again.",
                error_code="TIMEOUT_ERROR"
            )
        
        elif isinstance(exception, HTTPError):
            status_code = getattr(exception.response, 'status_code', None)
            message = cls.STATUS_MESSAGES.get(status_code, f"HTTP error {status_code}")
            
            raise APIError(
                message=f"{operation} failed: {message}",
                error_code="HTTP_ERROR",
                status_code=status_code
            )
        
        elif isinstance(exception, TooManyRedirects):
            raise APIError(
                message=f"{operation} failed: Too many redirects. "
                       "The API endpoint configuration may be incorrect.",
                error_code="REDIRECT_ERROR"
            )
        
        elif isinstance(exception, (URLRequired, InvalidURL)):
            raise APIError(
                message=f"{operation} failed: Invalid API URL configuration. "
                       "Please check the base URL in company settings.",
                error_code="URL_ERROR"
            )
        
        elif isinstance(exception, RequestException):
            raise APIError(
                message=f"{operation} failed: Network error occurred. "
                       "Please check your connection and try again.",
                error_code="NETWORK_ERROR"
            )
        
        else:
            # Generic error handling
            raise APIError(
                message=f"{operation} failed: {str(exception)}",
                error_code="UNKNOWN_ERROR"
            )
    
    @classmethod
    def is_retryable_error(cls, error: Union[APIError, Exception]) -> bool:
        """
        Check if an error is retryable.
        
        Args:
            error: The error to check
            
        Returns:
            True if the error should be retried
        """
        if isinstance(error, APIError):
            return (
                error.status_code in cls.RETRYABLE_STATUS_CODES or
                error.error_code in ['CONNECTION_ERROR', 'TIMEOUT_ERROR', 'NETWORK_ERROR']
            )
        
        if isinstance(error, (ConnectionError, Timeout)):
            return True
        
        if isinstance(error, HTTPError):
            status_code = getattr(error.response, 'status_code', None)
            return status_code in cls.RETRYABLE_STATUS_CODES
        
        return False
    
    @classmethod
    def is_auth_error(cls, error: Union[APIError, Exception]) -> bool:
        """
        Check if an error is related to authentication.
        
        Args:
            error: The error to check
            
        Returns:
            True if the error is authentication-related
        """
        if isinstance(error, APIError):
            return error.status_code in cls.AUTH_ERROR_CODES
        
        if isinstance(error, HTTPError):
            status_code = getattr(error.response, 'status_code', None)
            return status_code in cls.AUTH_ERROR_CODES
        
        return False
    
    @classmethod
    def convert_to_user_error(cls, error: APIError, context: str = "") -> UserError:
        """
        Convert APIError to Odoo UserError with user-friendly message.
        
        Args:
            error: The APIError to convert
            context: Additional context for the error message
            
        Returns:
            UserError with user-friendly message
        """
        message = str(error)
        if context:
            message = f"{context}: {message}"
        
        # Add helpful suggestions based on error type
        if cls.is_auth_error(error):
            message += "\n\nPlease check your API key configuration in company settings."
        
        elif error.error_code == "CONNECTION_ERROR":
            message += "\n\nPlease check:\n" \
                      "• Your internet connection\n" \
                      "• The API base URL in company settings\n" \
                      "• Firewall settings"
        
        elif error.status_code == 429:
            message += "\n\nPlease wait a few minutes before trying again."
        
        return UserError(message)


def with_api_error_handling(operation: str = "API operation", max_retries: int = 3, 
                           retry_delay: float = 1.0, backoff_factor: float = 2.0):
    """
    Decorator for API methods that provides automatic error handling and retry logic.
    
    Args:
        operation: Description of the operation for error messages
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for retry delay (exponential backoff)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            delay = retry_delay
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Handle API response
                    if hasattr(result, '__dict__') or isinstance(result, dict):
                        return APIErrorHandler.handle_api_response(result, operation)
                    
                    return result
                
                except Exception as e:
                    last_error = e
                    
                    # Convert request exceptions to APIError
                    if isinstance(e, RequestException):
                        try:
                            APIErrorHandler.handle_request_exception(e, operation)
                        except APIError as api_error:
                            last_error = api_error
                    
                    # Check if we should retry
                    if attempt < max_retries and APIErrorHandler.is_retryable_error(last_error):
                        _logger.warning(
                            f"{operation} failed (attempt {attempt + 1}/{max_retries + 1}): {last_error}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                        continue
                    
                    # No more retries or non-retryable error
                    break
            
            # Convert to user-friendly error
            if isinstance(last_error, APIError):
                raise APIErrorHandler.convert_to_user_error(last_error, operation)
            else:
                # Handle unexpected errors
                _logger.error(f"{operation} failed with unexpected error: {last_error}")
                raise UserError(f"{operation} failed: {str(last_error)}")
        
        return wrapper
    return decorator


def log_api_call(operation: str, **kwargs):
    """
    Log API call details for debugging.
    
    Args:
        operation: Description of the API operation
        **kwargs: Additional parameters to log
    """
    log_data = {'operation': operation}
    log_data.update(kwargs)
    
    # Remove sensitive data from logs
    sensitive_keys = ['api_key', 'password', 'token', 'secret']
    for key in sensitive_keys:
        if key in log_data:
            log_data[key] = '***REDACTED***'
    
    _logger.info(f"API Call: {log_data}")


def validate_api_configuration(company):
    """
    Validate API configuration for a company.
    
    Args:
        company: The company record to validate
        
    Raises:
        ValidationError: If configuration is invalid
    """
    if not company.tada_api_key:
        raise ValidationError(
            f"TADA API key is not configured for company '{company.name}'. "
            "Please configure it in company settings."
        )
    
    if not company.tada_base_url:
        raise ValidationError(
            f"TADA API base URL is not configured for company '{company.name}'. "
            "Please configure it in company settings."
        )
    
    # Basic URL validation
    if not company.tada_base_url.startswith(('http://', 'https://')):
        raise ValidationError(
            f"Invalid TADA API base URL for company '{company.name}'. "
            "URL must start with http:// or https://"
        )


def with_non_blocking_validation(func):
    """
    Decorator to execute a function with non-blocking fiscal code validation.
    
    This sets the 'skip_fiscal_code_validation' context flag to prevent
    ValidationError from being raised during API sync operations.
    """
    def wrapper(self, *args, **kwargs):
        # Set context to skip fiscal code validation
        sync_context = self.env.context.copy()
        sync_context['skip_fiscal_code_validation'] = True
        return func(self.with_context(sync_context), *args, **kwargs)
    
    return wrapper