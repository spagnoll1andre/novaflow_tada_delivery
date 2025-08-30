# -*- coding: utf-8 -*-
"""
Custom exceptions for TADA Admin module
"""


class AuthorizationError(Exception):
    """
    Exception raised when a company or user lacks authorization for a specific operation.
    
    This exception is used to handle cases where:
    - A company doesn't have permission for a specific feature
    - A user doesn't have the required access rights
    - Authorization validation fails
    """
    
    def __init__(self, company_id, permission_type, message=None):
        """
        Initialize AuthorizationError
        
        Args:
            company_id (int): ID of the company that lacks authorization
            permission_type (str): Type of permission that was denied
            message (str, optional): Custom error message
        """
        self.company_id = company_id
        self.permission_type = permission_type
        
        if message is None:
            message = f"Company {company_id} is not authorized for {permission_type}"
        
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return self.message


class DataAccessError(Exception):
    """
    Exception raised when a company attempts to access POD data they're not authorized for.
    
    This exception is used to handle cases where:
    - A company tries to access PODs not assigned to them
    - POD access validation fails
    - Data filtering reveals unauthorized access attempts
    """
    
    def __init__(self, company_id, pod_ids, message=None):
        """
        Initialize DataAccessError
        
        Args:
            company_id (int): ID of the company attempting unauthorized access
            pod_ids (list): List of POD IDs that were accessed without authorization
            message (str, optional): Custom error message
        """
        self.company_id = company_id
        self.pod_ids = pod_ids if isinstance(pod_ids, list) else [pod_ids]
        
        if message is None:
            pod_list = ', '.join(str(pod) for pod in self.pod_ids)
            message = f"Company {company_id} cannot access PODs: {pod_list}"
        
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return self.message


class Chain2GateError(Exception):
    """
    Exception raised when Chain2Gate API operations fail.
    
    This exception is used to handle cases where:
    - Chain2Gate API calls return error status codes
    - Network connectivity issues with Chain2Gate
    - Data synchronization failures
    """
    
    def __init__(self, operation, status_code=None, response_data=None, message=None):
        """
        Initialize Chain2GateError
        
        Args:
            operation (str): The operation that failed (e.g., 'sync_data', 'update_pod')
            status_code (int, optional): HTTP status code from Chain2Gate API
            response_data (dict, optional): Response data from Chain2Gate API
            message (str, optional): Custom error message
        """
        self.operation = operation
        self.status_code = status_code
        self.response_data = response_data
        
        if message is None:
            if status_code:
                message = f"Chain2Gate {operation} failed with status {status_code}"
            else:
                message = f"Chain2Gate {operation} failed"
        
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return self.message