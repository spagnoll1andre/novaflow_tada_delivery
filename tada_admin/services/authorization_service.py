# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import ValidationError, AccessError
import logging

from ..exceptions import AuthorizationError, DataAccessError

_logger = logging.getLogger(__name__)


class AuthorizationService(models.AbstractModel):
    """
    Authorization Service for TADA Admin
    
    This service provides centralized authorization and access control functionality
    for the TADA Admin system. It manages business-specific permissions and ensures
    proper data access control across different TADA functionalities.
    
    Supported Permission Types:
    - PARTNER_ENERGIA: Access to Partner Energia functionality
    - CONFIGURAZIONE_AMMISSIBILITA: Access to Configurazione Ammissibilità features
    - CONFIGURAZIONE_ASSOCIAZIONE: Access to Configurazione Associazione features  
    - MAGAZZINO: Access to Magazzino (warehouse) functionality
    - SPEDIZIONE: Access to Spedizione (shipping) functionality
    - MONITORAGGIO: Access to Monitoraggio (monitoring) functionality
    
    Core Responsibilities:
    - Company permission validation for TADA business features
    - POD access authorization and filtering
    - Data access control validation
    - Cross-company data isolation enforcement
    
    Requirements covered: 2.3, 3.3, 4.1
    """
    _name = 'tada_admin.authorization.service'
    _description = 'TADA Admin Authorization Service'

    @api.model
    def check_company_permission(self, company_id, permission_type):
        """
        Verify if a company has permission for a specific functionality.
        
        This method validates company permissions against the configured
        permission flags in the company permissions model.
        
        Args:
            company_id (int): ID of the company to check permissions for
            permission_type (str): Type of permission to validate
                                 ('monitoring', 'reporting', 'analytics', 'advanced_config')
        
        Returns:
            bool: True if company has the requested permission
            
        Raises:
            AuthorizationError: If company lacks the required permission
            ValidationError: If parameters are invalid
            
        Requirements: 2.3 - Permission validation logic
        """
        try:
            # Validate input parameters
            if not company_id:
                raise ValidationError(_("Company ID is required for permission check"))
            
            if not permission_type:
                raise ValidationError(_("Permission type is required"))
            
            # Validate permission type
            valid_permissions = [
                'PARTNER_ENERGIA',
                'CONFIGURAZIONE_AMMISSIBILITA', 
                'CONFIGURAZIONE_ASSOCIAZIONE',
                'MAGAZZINO',
                'SPEDIZIONE',
                'MONITORAGGIO'
            ]
            if permission_type not in valid_permissions:
                raise ValidationError(
                    _("Invalid permission type '{}'. Valid types: {}").format(
                        permission_type, ', '.join(valid_permissions)
                    )
                )
            
            # Get company permissions model
            permissions_model = self.env['tada_admin.company.permissions']
            
            # Check if company exists and is active
            company = self.env['res.company'].browse(company_id)
            if not company.exists():
                raise ValidationError(_("Company with ID {} does not exist").format(company_id))
            
            if not company.active:
                raise AuthorizationError(
                    company_id, 
                    permission_type,
                    _("Company '{}' is inactive and cannot access any features").format(company.name)
                )
            
            # Check company permission
            has_permission = permissions_model.check_permission(company_id, permission_type)
            
            if not has_permission:
                _logger.warning(
                    "Authorization denied: Company %s (ID: %d) lacks %s permission",
                    company.name, company_id, permission_type
                )
                raise AuthorizationError(
                    company_id,
                    permission_type,
                    _("Company '{}' is not authorized for {} functionality").format(
                        company.name, permission_type
                    )
                )
            
            _logger.info(
                "Authorization granted: Company %s (ID: %d) has %s permission",
                company.name, company_id, permission_type
            )
            
            return True
            
        except (AuthorizationError, ValidationError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            _logger.error(
                "Unexpected error checking permission %s for company %d: %s",
                permission_type, company_id, str(e)
            )
            raise ValidationError(
                _("Error checking company permissions: {}").format(str(e))
            )

    @api.model
    def get_authorized_pods(self, company_id):
        """
        Get list of POD codes that a company is authorized to access.
        
        This method retrieves all active POD authorizations for a specific company,
        providing the foundation for data filtering in other services.
        
        Args:
            company_id (int): ID of the company to get authorized PODs for
            
        Returns:
            list: List of POD codes (strings) that the company can access
            
        Raises:
            ValidationError: If company_id is invalid
            
        Requirements: 3.3 - POD filtering based on company
        """
        try:
            # Validate input parameters
            if not company_id:
                raise ValidationError(_("Company ID is required to get authorized PODs"))
            
            # Check if company exists and is active
            company = self.env['res.company'].browse(company_id)
            if not company.exists():
                raise ValidationError(_("Company with ID {} does not exist").format(company_id))
            
            if not company.active:
                _logger.warning(
                    "Attempted to get PODs for inactive company %s (ID: %d)",
                    company.name, company_id
                )
                return []
            
            # Get POD authorization model
            pod_auth_model = self.env['tada_admin.pod.authorization']
            
            # Get authorized PODs for the company
            authorized_pods = pod_auth_model.get_authorized_pods_for_company(company_id)
            
            _logger.info(
                "Retrieved %d authorized PODs for company %s (ID: %d)",
                len(authorized_pods), company.name, company_id
            )
            
            return authorized_pods
            
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            _logger.error(
                "Unexpected error getting authorized PODs for company %d: %s",
                company_id, str(e)
            )
            raise ValidationError(
                _("Error retrieving authorized PODs: {}").format(str(e))
            )

    @api.model
    def validate_pod_access(self, company_id, pod_ids):
        """
        Validate that a company has access to specific POD IDs.
        
        This method performs access control validation by checking if all
        requested PODs are authorized for the given company.
        
        Args:
            company_id (int): ID of the company requesting access
            pod_ids (list or str): POD ID(s) to validate access for
            
        Returns:
            list: List of authorized POD IDs (subset of input pod_ids)
            
        Raises:
            DataAccessError: If company cannot access any of the requested PODs
            ValidationError: If parameters are invalid
            
        Requirements: 4.1 - Access control validation
        """
        try:
            # Validate input parameters
            if not company_id:
                raise ValidationError(_("Company ID is required for POD access validation"))
            
            if not pod_ids:
                raise ValidationError(_("POD IDs are required for access validation"))
            
            # Normalize pod_ids to list
            if isinstance(pod_ids, str):
                pod_ids = [pod_ids]
            elif not isinstance(pod_ids, list):
                pod_ids = list(pod_ids)
            
            # Remove duplicates and empty values
            pod_ids = list(set(pod for pod in pod_ids if pod))
            
            if not pod_ids:
                raise ValidationError(_("No valid POD IDs provided"))
            
            # Check if company exists and is active
            company = self.env['res.company'].browse(company_id)
            if not company.exists():
                raise ValidationError(_("Company with ID {} does not exist").format(company_id))
            
            if not company.active:
                raise DataAccessError(
                    company_id,
                    pod_ids,
                    _("Company '{}' is inactive and cannot access any PODs").format(company.name)
                )
            
            # Get authorized PODs for the company
            authorized_pods = self.get_authorized_pods(company_id)
            
            # Find unauthorized PODs
            unauthorized_pods = [pod for pod in pod_ids if pod not in authorized_pods]
            
            if unauthorized_pods:
                _logger.warning(
                    "Access denied: Company %s (ID: %d) attempted to access unauthorized PODs: %s",
                    company.name, company_id, ', '.join(unauthorized_pods)
                )
                raise DataAccessError(
                    company_id,
                    unauthorized_pods,
                    _("Company '{}' is not authorized to access PODs: {}").format(
                        company.name, ', '.join(unauthorized_pods)
                    )
                )
            
            # All PODs are authorized
            authorized_pod_list = [pod for pod in pod_ids if pod in authorized_pods]
            
            _logger.info(
                "POD access validated: Company %s (ID: %d) authorized for %d PODs",
                company.name, company_id, len(authorized_pod_list)
            )
            
            return authorized_pod_list
            
        except (DataAccessError, ValidationError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            _logger.error(
                "Unexpected error validating POD access for company %d: %s",
                company_id, str(e)
            )
            raise ValidationError(
                _("Error validating POD access: {}").format(str(e))
            )

    @api.model
    def validate_company_and_permission(self, company_id, permission_type, pod_ids=None):
        """
        Combined validation method that checks both company permissions and POD access.
        
        This is a convenience method that combines permission checking and POD validation
        in a single call for common use cases.
        
        Args:
            company_id (int): ID of the company to validate
            permission_type (str): Type of permission to check
            pod_ids (list, optional): POD IDs to validate access for
            
        Returns:
            dict: Validation results with 'authorized' flag and 'authorized_pods' list
            
        Raises:
            AuthorizationError: If company lacks required permissions
            DataAccessError: If company cannot access requested PODs
            ValidationError: If parameters are invalid
        """
        try:
            # Check company permission first
            self.check_company_permission(company_id, permission_type)
            
            result = {
                'authorized': True,
                'company_id': company_id,
                'permission_type': permission_type
            }
            
            # If POD IDs provided, validate POD access
            if pod_ids:
                authorized_pods = self.validate_pod_access(company_id, pod_ids)
                result['authorized_pods'] = authorized_pods
                result['requested_pods'] = pod_ids if isinstance(pod_ids, list) else [pod_ids]
            else:
                # Get all authorized PODs for the company
                result['authorized_pods'] = self.get_authorized_pods(company_id)
            
            return result
            
        except (AuthorizationError, DataAccessError, ValidationError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            _logger.error(
                "Unexpected error in combined validation for company %d: %s",
                company_id, str(e)
            )
            raise ValidationError(
                _("Error in authorization validation: {}").format(str(e))
            )

    @api.model
    def get_companies_with_permission(self, permission_type):
        """
        Get all companies that have a specific permission.
        
        This method is useful for administrative operations and reporting.
        
        Args:
            permission_type (str): Type of permission to check
            
        Returns:
            recordset: res.company records that have the specified permission
            
        Raises:
            ValidationError: If permission_type is invalid
        """
        try:
            # Validate permission type
            valid_permissions = [
                'PARTNER_ENERGIA',
                'CONFIGURAZIONE_AMMISSIBILITA', 
                'CONFIGURAZIONE_ASSOCIAZIONE',
                'MAGAZZINO',
                'SPEDIZIONE',
                'MONITORAGGIO'
            ]
            if permission_type not in valid_permissions:
                raise ValidationError(
                    _("Invalid permission type '{}'. Valid types: {}").format(
                        permission_type, ', '.join(valid_permissions)
                    )
                )
            
            # Get companies with the specified permission
            permissions_model = self.env['tada_admin.company.permissions']
            companies = permissions_model.get_companies_with_permission(permission_type)
            
            _logger.info(
                "Found %d companies with %s permission",
                len(companies), permission_type
            )
            
            return companies
            
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            _logger.error(
                "Unexpected error getting companies with permission %s: %s",
                permission_type, str(e)
            )
            raise ValidationError(
                _("Error retrieving companies with permission: {}").format(str(e))
            )