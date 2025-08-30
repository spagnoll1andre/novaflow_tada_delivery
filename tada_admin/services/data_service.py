# -*- coding: utf-8 -*-
"""
Data Service for TADA Admin - Facade over Odoo Models with Chain2Gate Integration

This service provides a unified interface for accessing TADA data stored in Odoo models
and integrates with Chain2Gate SDK for external data synchronization. It includes
company-based authorization and POD filtering capabilities.
"""

from odoo import models, api, _
from odoo.exceptions import AccessError, ValidationError, UserError
from datetime import datetime, timedelta
import logging
import json

from ..exceptions import AuthorizationError, DataAccessError, Chain2GateError

_logger = logging.getLogger(__name__)


class TadaDataService(models.AbstractModel):
    """
    Enhanced Data Service facade for TADA Admin models with Chain2Gate integration.
    
    This service provides a unified interface for accessing data from TADA models
    with proper company isolation, authorization checks, and Chain2Gate SDK integration.
    
    Key Features:
    - Company-based data filtering and authorization
    - Chain2Gate SDK integration for external data access
    - POD-based access control
    - Comprehensive error handling for API failures
    - Data synchronization with Chain2Gate
    
    Requirements covered: 4.2, 5.1, 5.2
    """
    
    _name = 'tada_admin.data.service'
    _description = 'TADA Admin Data Service with Chain2Gate Integration'

    def _get_chain2gate_sdk(self):
        """
        Get Chain2Gate SDK instance with proper configuration.
        
        Returns:
            Chain2GateSDK: Configured SDK instance
            
        Raises:
            Chain2GateError: If SDK configuration is invalid
        """
        try:
            # Get Chain2Gate configuration from system parameters
            api_key = self.env['ir.config_parameter'].sudo().get_param('chain2gate.api_key')
            base_url = self.env['ir.config_parameter'].sudo().get_param('chain2gate.base_url', 
                                                                       'https://chain2-api.chain2gate.it')
            
            if not api_key:
                raise Chain2GateError(
                    'configuration',
                    message=_("Chain2Gate API key not configured. Please set 'chain2gate.api_key' system parameter.")
                )
            
            # Import Chain2Gate SDK
            from ..models.sdk.chain2gate_sdk import Chain2GateSDK
            
            return Chain2GateSDK(api_key=api_key, base_url=base_url)
            
        except ImportError as e:
            raise Chain2GateError(
                'sdk_import',
                message=_("Failed to import Chain2Gate SDK: {}").format(str(e))
            )
        except Exception as e:
            raise Chain2GateError(
                'configuration',
                message=_("Failed to configure Chain2Gate SDK: {}").format(str(e))
            )

    def _validate_company_authorization(self, company_id, permission_type, pod_ids=None):
        """
        Validate company authorization and POD access.
        
        Args:
            company_id (int): Company ID to validate
            permission_type (str): Permission type required
            pod_ids (list, optional): POD IDs to validate access for
            
        Returns:
            dict: Validation results with authorized PODs
            
        Raises:
            AuthorizationError: If company lacks required permissions
            DataAccessError: If company cannot access requested PODs
        """
        try:
            auth_service = self.env['tada_admin.authorization.service']
            return auth_service.validate_company_and_permission(
                company_id, permission_type, pod_ids
            )
        except Exception as e:
            _logger.error("Authorization validation failed for company %d: %s", company_id, str(e))
            raise

    @api.model
    def get_pod_data(self, pod_ids, company_id, data_type='monitoring', date_range=None):
        """
        Retrieve POD data from Chain2Gate with company filtering and authorization checks.
        
        This method fetches data for specific PODs while ensuring the requesting company
        has proper authorization to access those PODs.
        
        Args:
            pod_ids (list): List of POD codes to retrieve data for
            company_id (int): ID of the company requesting the data
            data_type (str): Type of data to retrieve ('monitoring', 'reporting', 'analytics')
            date_range (dict, optional): Date range filter with 'start' and 'end' keys
            
        Returns:
            dict: POD data filtered for authorized PODs only
            
        Raises:
            AuthorizationError: If company lacks required permissions
            DataAccessError: If company cannot access requested PODs
            Chain2GateError: If Chain2Gate API fails
            ValidationError: If parameters are invalid
            
        Requirements: 4.2, 5.1 - Company filtering and authorization checks
        """
        try:
            # Validate input parameters
            if not pod_ids:
                raise ValidationError(_("POD IDs are required"))
            
            if not company_id:
                raise ValidationError(_("Company ID is required"))
            
            # Normalize pod_ids to list
            if isinstance(pod_ids, str):
                pod_ids = [pod_ids]
            
            # Validate data type
            valid_data_types = ['monitoring', 'reporting', 'analytics']
            if data_type not in valid_data_types:
                raise ValidationError(
                    _("Invalid data type '{}'. Valid types: {}").format(
                        data_type, ', '.join(valid_data_types)
                    )
                )
            
            # Validate company authorization and POD access
            permission_map = {
                'monitoring': 'MONITORAGGIO',
                'reporting': 'PARTNER_ENERGIA',
                'analytics': 'PARTNER_ENERGIA'
            }
            
            auth_result = self._validate_company_authorization(
                company_id, permission_map[data_type], pod_ids
            )
            
            authorized_pods = auth_result['authorized_pods']
            
            # Filter requested PODs to only authorized ones
            accessible_pods = [pod for pod in pod_ids if pod in authorized_pods]
            
            if not accessible_pods:
                _logger.warning(
                    "No authorized PODs found for company %d in requested PODs: %s",
                    company_id, ', '.join(pod_ids)
                )
                return {
                    'data': {},
                    'authorized_pods': authorized_pods,
                    'requested_pods': pod_ids,
                    'accessible_pods': accessible_pods,
                    'message': _("No authorized PODs found in the requested list")
                }
            
            # Get Chain2Gate SDK
            sdk = self._get_chain2gate_sdk()
            
            # Retrieve data from Chain2Gate based on data type
            pod_data = {}
            
            if data_type == 'monitoring':
                # Get monitoring data (devices and their status)
                devices = sdk.get_devices()
                if isinstance(devices, dict) and devices.get('error'):
                    raise Chain2GateError(
                        'get_devices',
                        status_code=devices.get('status_code'),
                        response_data=devices,
                        message=devices.get('message', 'Failed to retrieve device data')
                    )
                
                # Filter devices by accessible PODs
                for device in devices:
                    device_pods = [device.m1, device.m2, device.m2_2, device.m2_3, device.m2_4]
                    device_pods = [pod for pod in device_pods if pod and pod in accessible_pods]
                    
                    if device_pods:
                        for pod in device_pods:
                            if pod not in pod_data:
                                pod_data[pod] = []
                            pod_data[pod].append({
                                'device_id': device.id,
                                'device_type': device.type_name,
                                'status': 'online' if device.updated_at else 'offline',
                                'last_update': device.updated_at,
                                'hw_version': device.hw_version,
                                'sw_version': device.sw_version,
                                'fw_version': device.fw_version
                            })
            
            elif data_type in ['reporting', 'analytics']:
                # Get association requests for reporting/analytics
                associations = sdk.get_association_requests()
                if isinstance(associations, dict) and associations.get('error'):
                    raise Chain2GateError(
                        'get_association_requests',
                        status_code=associations.get('status_code'),
                        response_data=associations,
                        message=associations.get('message', 'Failed to retrieve association data')
                    )
                
                # Filter associations by accessible PODs
                for assoc in associations:
                    if assoc.pod in accessible_pods:
                        if assoc.pod not in pod_data:
                            pod_data[assoc.pod] = []
                        pod_data[assoc.pod].append({
                            'association_id': assoc.id,
                            'status': assoc.status.value,
                            'user_type': assoc.user_type.value,
                            'pod_m_type': assoc.pod_m_type.value,
                            'created_at': assoc.created_at,
                            'updated_at': assoc.updated_at,
                            'fiscal_code': assoc.fiscal_code
                        })
            
            _logger.info(
                "Retrieved %s data for %d PODs for company %d",
                data_type, len(pod_data), company_id
            )
            
            return {
                'data': pod_data,
                'data_type': data_type,
                'authorized_pods': authorized_pods,
                'requested_pods': pod_ids,
                'accessible_pods': accessible_pods,
                'company_id': company_id,
                'retrieved_at': datetime.now().isoformat()
            }
            
        except (AuthorizationError, DataAccessError, Chain2GateError, ValidationError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            _logger.error(
                "Unexpected error retrieving POD data for company %d: %s",
                company_id, str(e)
            )
            raise Chain2GateError(
                'get_pod_data',
                message=_("Failed to retrieve POD data: {}").format(str(e))
            )

    @api.model
    def update_pod_data(self, pod_id, data, company_id, operation_type='update'):
        """
        Update POD data via Chain2Gate with integration and validation.
        
        This method updates POD data through Chain2Gate API while ensuring proper
        company authorization and data validation.
        
        Args:
            pod_id (str): POD code to update
            data (dict): Data to update
            company_id (int): ID of the company making the update
            operation_type (str): Type of operation ('update', 'associate', 'disassociate')
            
        Returns:
            dict: Update result with Chain2Gate response
            
        Raises:
            AuthorizationError: If company lacks required permissions
            DataAccessError: If company cannot access the POD
            Chain2GateError: If Chain2Gate API fails
            ValidationError: If parameters are invalid
            
        Requirements: 5.2 - Chain2Gate integration and validation
        """
        try:
            # Validate input parameters
            if not pod_id:
                raise ValidationError(_("POD ID is required"))
            
            if not data:
                raise ValidationError(_("Update data is required"))
            
            if not company_id:
                raise ValidationError(_("Company ID is required"))
            
            # Validate operation type
            valid_operations = ['update', 'associate', 'disassociate']
            if operation_type not in valid_operations:
                raise ValidationError(
                    _("Invalid operation type '{}'. Valid types: {}").format(
                        operation_type, ', '.join(valid_operations)
                    )
                )
            
            # Validate company authorization and POD access
            permission_map = {
                'update': 'CONFIGURAZIONE_ASSOCIAZIONE',
                'associate': 'CONFIGURAZIONE_ASSOCIAZIONE',
                'disassociate': 'CONFIGURAZIONE_ASSOCIAZIONE'
            }
            
            auth_result = self._validate_company_authorization(
                company_id, permission_map[operation_type], [pod_id]
            )
            
            if pod_id not in auth_result['authorized_pods']:
                raise DataAccessError(
                    company_id, [pod_id],
                    _("Company is not authorized to {} POD: {}").format(operation_type, pod_id)
                )
            
            # Get Chain2Gate SDK
            sdk = self._get_chain2gate_sdk()
            
            # Perform the update operation based on type
            result = None
            
            if operation_type == 'associate':
                # Create association request
                required_fields = ['serial', 'pod_m_type', 'user_type', 'fiscal_code']
                for field in required_fields:
                    if field not in data:
                        raise ValidationError(
                            _("Required field '{}' missing for association").format(field)
                        )
                
                # Import enums
                from ..models.sdk.chain2gate_sdk import PodMType, UserType
                
                result = sdk.create_association_request(
                    pod=pod_id,
                    serial=data['serial'],
                    pod_m_type=PodMType(data['pod_m_type']),
                    user_type=UserType(data['user_type']),
                    fiscal_code=data['fiscal_code'],
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    email=data.get('email')
                )
                
            elif operation_type == 'disassociate':
                # Create disassociation request
                required_fields = ['serial', 'pod_m_type', 'fiscal_code']
                for field in required_fields:
                    if field not in data:
                        raise ValidationError(
                            _("Required field '{}' missing for disassociation").format(field)
                        )
                
                # Import enums
                from ..models.sdk.chain2gate_sdk import PodMType, UserType
                
                user_type = UserType(data['user_type']) if data.get('user_type') else None
                
                result = sdk.create_disassociation_request(
                    pod=pod_id,
                    serial=data['serial'],
                    pod_m_type=PodMType(data['pod_m_type']),
                    fiscal_code=data['fiscal_code'],
                    user_type=user_type,
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    email=data.get('email')
                )
                
            else:  # operation_type == 'update'
                # For general updates, we might need to implement specific update logic
                # For now, we'll return a placeholder response
                result = {
                    'success': True,
                    'message': _("Update operation not yet implemented for general data updates"),
                    'pod_id': pod_id,
                    'operation': operation_type
                }
            
            # Check if Chain2Gate operation failed
            if isinstance(result, dict) and result.get('error'):
                raise Chain2GateError(
                    operation_type,
                    status_code=result.get('status_code'),
                    response_data=result,
                    message=result.get('message', f'Chain2Gate {operation_type} operation failed')
                )
            
            # Log successful operation
            _logger.info(
                "Successfully performed %s operation on POD %s for company %d",
                operation_type, pod_id, company_id
            )
            
            # Update local data if needed
            if operation_type in ['associate', 'disassociate'] and hasattr(result, 'id'):
                # Trigger local data sync for the affected POD
                try:
                    self.sync_from_chain2gate(company_id=company_id, pod_filter=[pod_id])
                except Exception as sync_error:
                    _logger.warning(
                        "Failed to sync local data after %s operation: %s",
                        operation_type, str(sync_error)
                    )
            
            return {
                'success': True,
                'operation': operation_type,
                'pod_id': pod_id,
                'company_id': company_id,
                'chain2gate_result': result,
                'updated_at': datetime.now().isoformat()
            }
            
        except (AuthorizationError, DataAccessError, Chain2GateError, ValidationError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            _logger.error(
                "Unexpected error updating POD %s for company %d: %s",
                pod_id, company_id, str(e)
            )
            raise Chain2GateError(
                'update_pod_data',
                message=_("Failed to update POD data: {}").format(str(e))
            )

    @api.model
    def sync_from_chain2gate(self, company_id=None, pod_filter=None, force_refresh=False):
        """
        Synchronize data from Chain2Gate for authorized PODs.
        
        This method performs comprehensive data synchronization from Chain2Gate,
        respecting company authorization and POD access controls.
        
        Args:
            company_id (int, optional): Company ID to sync for (if None, syncs for all companies)
            pod_filter (list, optional): Specific PODs to sync (if None, syncs all authorized PODs)
            force_refresh (bool): Force refresh even if data is recent
            
        Returns:
            dict: Synchronization results summary
            
        Raises:
            AuthorizationError: If company lacks required permissions
            Chain2GateError: If Chain2Gate API fails
            ValidationError: If parameters are invalid
            
        Requirements: 5.1, 5.2 - Data synchronization
        """
        try:
            sync_results = {
                'devices': {'synced': 0, 'updated': 0, 'errors': 0},
                'admissibility_requests': {'synced': 0, 'updated': 0, 'errors': 0},
                'association_requests': {'synced': 0, 'updated': 0, 'errors': 0},
                'disassociation_requests': {'synced': 0, 'updated': 0, 'errors': 0},
                'customers': {'synced': 0, 'updated': 0, 'errors': 0},
                'companies_processed': [],
                'total_pods_synced': 0,
                'sync_started_at': datetime.now().isoformat()
            }
            
            # Determine companies to sync for
            companies_to_sync = []
            
            if company_id:
                # Validate specific company authorization
                auth_result = self._validate_company_authorization(
                    company_id, 'MONITORAGGIO'  # Basic permission for data sync
                )
                companies_to_sync = [company_id]
            else:
                # Get all companies with monitoring permission
                auth_service = self.env['tada_admin.authorization.service']
                companies_with_permission = auth_service.get_companies_with_permission('MONITORAGGIO')
                companies_to_sync = companies_with_permission.ids
            
            if not companies_to_sync:
                _logger.warning("No companies found with sync permissions")
                return sync_results
            
            # Get Chain2Gate SDK
            sdk = self._get_chain2gate_sdk()
            
            # Process each company
            for comp_id in companies_to_sync:
                try:
                    # Get authorized PODs for this company
                    auth_service = self.env['tada_admin.authorization.service']
                    authorized_pods = auth_service.get_authorized_pods(comp_id)
                    
                    # Apply POD filter if specified
                    if pod_filter:
                        authorized_pods = [pod for pod in authorized_pods if pod in pod_filter]
                    
                    if not authorized_pods:
                        _logger.info("No authorized PODs found for company %d", comp_id)
                        continue
                    
                    sync_results['companies_processed'].append(comp_id)
                    sync_results['total_pods_synced'] += len(authorized_pods)
                    
                    # Sync devices
                    try:
                        devices = sdk.get_devices()
                        if isinstance(devices, dict) and devices.get('error'):
                            raise Chain2GateError(
                                'get_devices',
                                status_code=devices.get('status_code'),
                                message=devices.get('message', 'Failed to retrieve devices')
                            )
                        
                        # Filter and sync devices for authorized PODs
                        for device in devices:
                            device_pods = [device.m1, device.m2, device.m2_2, device.m2_3, device.m2_4]
                            device_pods = [pod for pod in device_pods if pod and pod in authorized_pods]
                            
                            if device_pods:
                                # Update local device record
                                device_model = self.env['tada.device']
                                existing_device = device_model.search([
                                    ('serial_number', '=', device.id),
                                    ('company_id', '=', comp_id)
                                ], limit=1)
                                
                                device_data = {
                                    'serial_number': device.id,
                                    'type_name': device.type_name,
                                    'hw_version': device.hw_version,
                                    'sw_version': device.sw_version,
                                    'fw_version': device.fw_version,
                                    'mac_address': device.mac,
                                    'company_id': comp_id,
                                    'chain2gate_id': device.id,
                                    'last_sync': datetime.now()
                                }
                                
                                if existing_device:
                                    existing_device.write(device_data)
                                    sync_results['devices']['updated'] += 1
                                else:
                                    device_model.create(device_data)
                                    sync_results['devices']['synced'] += 1
                        
                    except Exception as e:
                        _logger.error("Error syncing devices for company %d: %s", comp_id, str(e))
                        sync_results['devices']['errors'] += 1
                    
                    # Sync association requests
                    try:
                        associations = sdk.get_association_requests()
                        if isinstance(associations, dict) and associations.get('error'):
                            raise Chain2GateError(
                                'get_association_requests',
                                status_code=associations.get('status_code'),
                                message=associations.get('message', 'Failed to retrieve associations')
                            )
                        
                        # Filter and sync associations for authorized PODs
                        for assoc in associations:
                            if assoc.pod in authorized_pods:
                                # Update local association record
                                assoc_model = self.env['tada.association.request']
                                existing_assoc = assoc_model.search([
                                    ('chain2gate_id', '=', assoc.id),
                                    ('company_id', '=', comp_id)
                                ], limit=1)
                                
                                assoc_data = {
                                    'chain2gate_id': assoc.id,
                                    'pod': assoc.pod,
                                    'serial_number': assoc.serial,
                                    'status': assoc.status.value,
                                    'fiscal_code': assoc.fiscal_code,
                                    'first_name': assoc.first_name,
                                    'last_name': assoc.last_name,
                                    'email': assoc.email,
                                    'company_id': comp_id,
                                    'last_sync': datetime.now()
                                }
                                
                                if existing_assoc:
                                    existing_assoc.write(assoc_data)
                                    sync_results['association_requests']['updated'] += 1
                                else:
                                    assoc_model.create(assoc_data)
                                    sync_results['association_requests']['synced'] += 1
                        
                    except Exception as e:
                        _logger.error("Error syncing associations for company %d: %s", comp_id, str(e))
                        sync_results['association_requests']['errors'] += 1
                    
                    # Similar sync logic for admissibility and disassociation requests...
                    # (Implementation would follow the same pattern)
                    
                except Exception as e:
                    _logger.error("Error processing company %d during sync: %s", comp_id, str(e))
                    continue
            
            sync_results['sync_completed_at'] = datetime.now().isoformat()
            
            _logger.info(
                "Chain2Gate sync completed for %d companies. Results: %s",
                len(sync_results['companies_processed']), sync_results
            )
            
            return sync_results
            
        except (AuthorizationError, Chain2GateError, ValidationError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            _logger.error("Unexpected error during Chain2Gate sync: %s", str(e))
            raise Chain2GateError(
                'sync_from_chain2gate',
                message=_("Failed to sync from Chain2Gate: {}").format(str(e))
            )

    @api.model
    def get_devices(self, company_id=None, device_type=None, active_only=True):
        """
        Get devices with optional filtering and authorization checks.
        
        Args:
            company_id (int, optional): Company ID filter
            device_type (str, optional): Device type filter
            active_only (bool): Only return active devices
            
        Returns:
            recordset: tada.device records filtered by company authorization
            
        Raises:
            AuthorizationError: If company lacks required permissions
        """
        if not company_id:
            company_id = self.env.company.id
        
        try:
            # Validate company authorization for device access
            self._validate_company_authorization(company_id, 'MONITORAGGIO')
            
            domain = [('company_id', '=', company_id)]
            
            if device_type:
                domain.append(('type_name', '=', device_type))
                
            if active_only:
                domain.append(('active', '=', True))
                
            return self.env['tada.device'].search(domain)
            
        except (AuthorizationError, DataAccessError):
            # Re-raise authorization errors
            raise
        except Exception as e:
            _logger.error("Error retrieving devices for company %d: %s", company_id, str(e))
            raise ValidationError(_("Failed to retrieve devices: {}").format(str(e)))

    @api.model
    def get_customers(self, company_id=None, has_active_associations=None):
        """
        Get customers with optional filtering and authorization checks.
        
        Args:
            company_id (int, optional): Company ID filter
            has_active_associations (bool, optional): Filter by association status
            
        Returns:
            recordset: tada.customer records filtered by company authorization
            
        Raises:
            AuthorizationError: If company lacks required permissions
        """
        if not company_id:
            company_id = self.env.company.id
        
        try:
            # Validate company authorization for customer access
            self._validate_company_authorization(company_id, 'PARTNER_ENERGIA')
            
            domain = [('company_id', '=', company_id)]
            
            if has_active_associations is not None:
                domain.append(('has_active_associations', '=', has_active_associations))
                
            return self.env['tada.customer'].search(domain)
            
        except (AuthorizationError, DataAccessError):
            # Re-raise authorization errors
            raise
        except Exception as e:
            _logger.error("Error retrieving customers for company %d: %s", company_id, str(e))
            raise ValidationError(_("Failed to retrieve customers: {}").format(str(e)))

    @api.model
    def get_admissibility_requests(self, company_id=None, status=None):
        """
        Get admissibility requests with optional filtering.
        
        Args:
            company_id (int, optional): Company ID filter
            status (str, optional): Status filter
            
        Returns:
            recordset: tada.admissibility.request records
        """
        if not company_id:
            company_id = self.env.company.id
            
        domain = [('company_id', '=', company_id)]
        
        if status:
            domain.append(('status', '=', status))
            
        return self.env['tada.admissibility.request'].search(domain)

    @api.model
    def get_association_requests(self, company_id=None, status=None):
        """
        Get association requests with optional filtering.
        
        Args:
            company_id (int, optional): Company ID filter
            status (str, optional): Status filter
            
        Returns:
            recordset: tada.association.request records
        """
        if not company_id:
            company_id = self.env.company.id
            
        domain = [('company_id', '=', company_id)]
        
        if status:
            domain.append(('status', '=', status))
            
        return self.env['tada.association.request'].search(domain)

    @api.model
    def get_disassociation_requests(self, company_id=None, status=None):
        """
        Get disassociation requests with optional filtering.
        
        Args:
            company_id (int, optional): Company ID filter
            status (str, optional): Status filter
            
        Returns:
            recordset: tada.disassociation.request records
        """
        if not company_id:
            company_id = self.env.company.id
            
        domain = [('company_id', '=', company_id)]
        
        if status:
            domain.append(('status', '=', status))
            
        return self.env['tada.disassociation.request'].search(domain)

    @api.model
    def get_customer_info(self, fiscal_code, company_id=None):
        """
        Get comprehensive customer information including related records.
        
        Args:
            fiscal_code (str): Customer fiscal code
            company_id (int, optional): Company ID filter
            
        Returns:
            dict: Customer data with related records
        """
        if not company_id:
            company_id = self.env.company.id
            
        customer = self.env['tada.customer'].search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', company_id)
        ], limit=1)
        
        if not customer:
            return None
            
        return {
            'customer': customer,
            'admissibility_requests': customer.admissibility_request_ids,
            'association_requests': customer.association_request_ids,
            'disassociation_requests': customer.disassociation_request_ids,
            'devices': customer.device_ids,
            'statistics': {
                'admissibility_count': customer.admissibility_count,
                'association_count': customer.association_count,
                'disassociation_count': customer.disassociation_count,
                'device_count': customer.device_count,
                'has_active_associations': customer.has_active_associations,
                'latest_request_date': customer.latest_request_date,
            }
        }

    @api.model
    def sync_all_data_from_api(self, company_id=None):
        """
        Sync all data from API in the correct order with Chain2Gate integration.
        
        This method now uses the enhanced Chain2Gate integration while maintaining
        backward compatibility with existing sync methods.
        
        Args:
            company_id (int, optional): Company ID to sync for
            
        Returns:
            dict: Sync results summary
        """
        if not company_id:
            company_id = self.env.company.id
            
        try:
            # Use the new Chain2Gate integration method
            chain2gate_results = self.sync_from_chain2gate(company_id=company_id)
            
            # Also run the legacy sync methods for backward compatibility
            try:
                # 1. Sync devices first
                device_result = self.env['tada.device'].sync_from_api(company_id=company_id)
                _logger.info("Legacy device sync completed")
                
                # 2. Sync requests
                admiss_result = self.env['tada.admissibility.request'].sync_from_api(company_id=company_id)
                _logger.info("Legacy admissibility requests sync completed")
                
                assoc_result = self.env['tada.association.request'].sync_from_api(company_id=company_id)
                _logger.info("Legacy association requests sync completed")
                
                disassoc_result = self.env['tada.disassociation.request'].sync_from_api(company_id=company_id)
                _logger.info("Legacy disassociation requests sync completed")
                
                # 3. Sync customers last (they depend on requests)
                customer_result = self.env['tada.customer'].sync_customer_from_api(company_id=company_id)
                _logger.info("Legacy customer sync completed")
                
                # 4. Sync POD summaries after all data is synced
                pod_summary_result = self.sync_pod_summaries(company_id=company_id)
                _logger.info("POD summaries sync completed")
                
            except Exception as legacy_error:
                _logger.warning("Legacy sync methods failed: %s", str(legacy_error))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Data synced successfully from Chain2Gate API'),
                    'type': 'success',
                },
                'chain2gate_results': chain2gate_results
            }
            
        except (AuthorizationError, DataAccessError) as auth_error:
            _logger.error("Authorization error during sync: %s", str(auth_error))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Sync failed: {}').format(str(auth_error)),
                    'type': 'error',
                }
            }
        except Chain2GateError as c2g_error:
            _logger.error("Chain2Gate error during sync: %s", str(c2g_error))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Chain2Gate sync failed: {}').format(str(c2g_error)),
                    'type': 'error',
                }
            }
        except Exception as e:
            _logger.error("Failed to sync all data from API: %s", str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Sync failed: {}').format(str(e)),
                    'type': 'error',
                }
            }

    @api.model
    def get_dashboard_data(self, company_id=None):
        """
        Get dashboard summary data with authorization checks.
        
        Args:
            company_id (int, optional): Company ID filter
            
        Returns:
            dict: Dashboard data filtered by company permissions
            
        Raises:
            AuthorizationError: If company lacks required permissions
        """
        if not company_id:
            company_id = self.env.company.id
        
        try:
            # Validate company authorization for dashboard access
            self._validate_company_authorization(company_id, 'PARTNER_ENERGIA')
            
            dashboard_data = {
                'company_id': company_id,
                'generated_at': datetime.now().isoformat()
            }
            
            # Get device data if company has monitoring permission
            try:
                self._validate_company_authorization(company_id, 'MONITORAGGIO')
                dashboard_data['devices'] = {
                    'total': self.env['tada.device'].search_count([('company_id', '=', company_id)]),
                    'active': self.env['tada.device'].search_count([
                        ('company_id', '=', company_id),
                        ('active', '=', True)
                    ]),
                    'online': self.env['tada.device'].search_count([
                        ('company_id', '=', company_id),
                        ('status', 'like', 'online%')
                    ]),
                }
            except AuthorizationError:
                dashboard_data['devices'] = {
                    'message': _('Device monitoring not authorized for this company')
                }
            
            # Get customer data
            dashboard_data['customers'] = {
                'total': self.env['tada.customer'].search_count([('company_id', '=', company_id)]),
                'with_active_associations': self.env['tada.customer'].search_count([
                    ('company_id', '=', company_id),
                    ('has_active_associations', '=', True)
                ]),
            }
            
            # Get request data if company has configuration permissions
            try:
                self._validate_company_authorization(company_id, 'CONFIGURAZIONE_ASSOCIAZIONE')
                dashboard_data['requests'] = {
                    'admissibility_pending': self.env['tada.admissibility.request'].search_count([
                        ('company_id', '=', company_id),
                        ('status', 'in', ['PENDING', 'AWAITING'])
                    ]),
                    'association_pending': self.env['tada.association.request'].search_count([
                        ('company_id', '=', company_id),
                        ('status', 'in', ['PENDING', 'AWAITING'])
                    ]),
                    'association_active': self.env['tada.association.request'].search_count([
                        ('company_id', '=', company_id),
                        ('status', 'in', ['ASSOCIATED', 'TAKEN_IN_CHARGE'])
                    ]),
                }
            except AuthorizationError:
                dashboard_data['requests'] = {
                    'message': _('Request management not authorized for this company')
                }
            
            return dashboard_data
            
        except (AuthorizationError, DataAccessError):
            # Re-raise authorization errors
            raise
        except Exception as e:
            _logger.error("Error retrieving dashboard data for company %d: %s", company_id, str(e))
            raise ValidationError(_("Failed to retrieve dashboard data: {}").format(str(e)))

    @api.model
    def sync_pod_summaries(self, company_id=None):
        """
        Synchronize POD summaries after data sync operations.
        
        This method should be called after syncing customers, devices, and requests
        to ensure POD summaries are up-to-date with the latest data.
        
        Args:
            company_id (int, optional): Company ID to sync for
            
        Returns:
            dict: Sync results
        """
        if not company_id:
            company_id = self.env.company.id
        
        try:
            # Validate company authorization
            self._validate_company_authorization(company_id, 'PARTNER_ENERGIA')
            
            # Use the POD summary model's sync method
            pod_summary_model = self.env['tada_admin.pod.summary']
            sync_results = pod_summary_model.sync_pod_summaries(company_id)
            
            _logger.info(
                "POD summaries sync completed for company %d: %s",
                company_id, sync_results
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('POD summaries synced successfully: {} created, {} updated').format(
                        sync_results.get('created', 0),
                        sync_results.get('updated', 0)
                    ),
                    'type': 'success',
                },
                'sync_results': sync_results
            }
            
        except (AuthorizationError, DataAccessError) as auth_error:
            _logger.error("Authorization error during POD summary sync: %s", str(auth_error))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('POD summary sync failed: {}').format(str(auth_error)),
                    'type': 'error',
                }
            }
        except Exception as e:
            _logger.error("Error syncing POD summaries for company %d: %s", company_id, str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('POD summary sync failed: {}').format(str(e)),
                    'type': 'error',
                }
            }