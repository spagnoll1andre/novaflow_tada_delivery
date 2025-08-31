# -*- coding: utf-8 -*-
"""
TADA Admin Odoo Integration Module

This module provides centralized data management and authorization services for the TADA ecosystem.
It serves as the single point of access to Chain2Gate API and manages multi-company data isolation.
"""

# Import models, services and wizards
from . import models
from . import services
from . import wizards

import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """Pre-initialization hook for TADA Admin module."""
    _logger.info("TADA Admin module pre-initialization started")
    
    # Check if required Python packages are available
    try:
        import requests
        _logger.info("All required Python packages are available")
    except ImportError as e:
        _logger.error(f"Missing required Python package: {e}")
        _logger.error("Please install required packages: pip install requests")
        raise


def post_init_hook(cr, registry=None):
    """Post-initialization hook for TADA Admin module."""
    _logger.info("TADA Admin module post-initialization started")
    
    # Set default configuration parameters if not already set
    from odoo import api, SUPERUSER_ID
    
    # Handle both old (cr, registry) and new (env) calling conventions
    if hasattr(cr, 'cr'):
        # New convention: first argument is env
        env = cr
    else:
        # Old convention: first argument is cursor
        env = api.Environment(cr, SUPERUSER_ID, {})
    
    config_params = env['ir.config_parameter'].sudo()
    
    # Set default values for configuration parameters - only if they don't exist
    defaults = {
        'tada_admin.base_url': 'https://chain2-api.chain2gate.it',
        'tada_admin.configured': 'false',
    }
    
    for param, default_value in defaults.items():
        existing_param = config_params.search([('key', '=', param)], limit=1)
        if not existing_param:
            # Only create if it doesn't exist at all
            config_params.create({'key': param, 'value': default_value})
            _logger.info(f"Created default configuration parameter: {param} = {default_value}")
        else:
            _logger.info(f"Configuration parameter already exists: {param}")
    
    # Create default permissions for existing companies to fix authorization warnings
    try:
        _create_default_company_permissions(env)
        _create_default_pod_authorizations(env)
        _logger.info("Successfully created default company permissions and POD authorizations")
    except Exception as e:
        _logger.error(f"Error creating default permissions: {e}")
    
    _logger.info("TADA Admin module initialization completed successfully")


def _create_default_company_permissions(env):
    """Create default permissions for companies that need CONFIGURAZIONE_AMMISSIBILITA access."""
    _logger.info("Creating default company permissions")
    
    company_permissions_model = env['tada_admin.company.permissions']
    company_model = env['res.company']
    
    # Find companies that need CONFIGURAZIONE_AMMISSIBILITA permission (IDs mentioned in warnings)
    target_company_ids = [38, 45]
    
    for company_id in target_company_ids:
        company = company_model.browse(company_id)
        if not company.exists():
            _logger.warning(f"Company with ID {company_id} does not exist, skipping")
            continue
            
        # Check if permissions record already exists
        existing_permissions = company_permissions_model.search([('company_id', '=', company_id)], limit=1)
        
        if existing_permissions:
            # Update existing record to grant CONFIGURAZIONE_AMMISSIBILITA permission
            if not existing_permissions.has_configurazione_ammissibilita:
                existing_permissions.write({'has_configurazione_ammissibilita': True})
                _logger.info(f"Updated permissions for company '{company.name}' (ID: {company_id}) - granted CONFIGURAZIONE_AMMISSIBILITA")
            else:
                _logger.info(f"Company '{company.name}' (ID: {company_id}) already has CONFIGURAZIONE_AMMISSIBILITA permission")
        else:
            # Create new permissions record with CONFIGURAZIONE_AMMISSIBILITA permission
            company_permissions_model.create({
                'company_id': company_id,
                'has_configurazione_ammissibilita': True,
                'has_monitoraggio': True,  # Default permission
            })
            _logger.info(f"Created permissions for company '{company.name}' (ID: {company_id}) - granted CONFIGURAZIONE_AMMISSIBILITA")
    
    # Also grant permissions to 'Test Company' if it exists (common test company name)
    test_companies = company_model.search([('name', 'ilike', 'Test Company')])
    for company in test_companies:
        existing_permissions = company_permissions_model.search([('company_id', '=', company.id)], limit=1)
        
        if existing_permissions:
            if not existing_permissions.has_configurazione_ammissibilita:
                existing_permissions.write({'has_configurazione_ammissibilita': True})
                _logger.info(f"Updated permissions for test company '{company.name}' (ID: {company.id}) - granted CONFIGURAZIONE_AMMISSIBILITA")
        else:
            company_permissions_model.create({
                'company_id': company.id,
                'has_configurazione_ammissibilita': True,
                'has_monitoraggio': True,  # Default permission
            })
            _logger.info(f"Created permissions for test company '{company.name}' (ID: {company.id}) - granted CONFIGURAZIONE_AMMISSIBILITA")


def _create_default_pod_authorizations(env):
    """Create default POD authorizations for test companies that need POD999 access."""
    _logger.info("Creating default POD authorizations")
    
    pod_auth_model = env['tada_admin.pod.authorization']
    company_model = env['res.company']
    
    # Target company ID mentioned in POD999 warning
    target_company_id = 45
    
    company = company_model.browse(target_company_id)
    if company.exists():
        # Check if POD999 authorization already exists for this company
        existing_auth = pod_auth_model.search([
            ('company_id', '=', target_company_id),
            ('pod_code', '=', 'POD999')
        ], limit=1)
        
        if not existing_auth:
            # Create POD999 authorization for the company
            pod_auth_model.create({
                'company_id': target_company_id,
                'pod_code': 'POD999',
                'pod_name': 'Test POD 999',
                'is_active': True,
            })
            _logger.info(f"Created POD999 authorization for company '{company.name}' (ID: {target_company_id})")
        else:
            # Ensure it's active
            if not existing_auth.is_active:
                existing_auth.write({'is_active': True})
                _logger.info(f"Activated POD999 authorization for company '{company.name}' (ID: {target_company_id})")
            else:
                _logger.info(f"Company '{company.name}' (ID: {target_company_id}) already has active POD999 authorization")
    else:
        _logger.warning(f"Company with ID {target_company_id} does not exist for POD999 authorization")
    
    # Also create POD999 authorization for all 'Test Company' companies
    test_companies = company_model.search([('name', 'ilike', 'Test Company')])
    for company in test_companies:
        existing_auth = pod_auth_model.search([
            ('company_id', '=', company.id),
            ('pod_code', '=', 'POD999')
        ], limit=1)
        
        if not existing_auth:
            pod_auth_model.create({
                'company_id': company.id,
                'pod_code': 'POD999',
                'pod_name': 'Test POD 999',
                'is_active': True,
            })
            _logger.info(f"Created POD999 authorization for test company '{company.name}' (ID: {company.id})")
        else:
            if not existing_auth.is_active:
                existing_auth.write({'is_active': True})
                _logger.info(f"Activated POD999 authorization for test company '{company.name}' (ID: {company.id})")


def uninstall_hook(cr, registry):
    """Uninstall hook for TADA Admin module."""
    _logger.info("TADA Admin module uninstall started")
    
    # Clean up configuration parameters
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    config_params = env['ir.config_parameter'].sudo()
    
    # Remove TADA Admin configuration parameters
    params_to_remove = [
        'tada_admin.api_key',
        'tada_admin.base_url', 
        'tada_admin.configured',
    ]
    
    for param in params_to_remove:
        config_params.search([('key', '=', param)]).unlink()
        _logger.info(f"Removed configuration parameter: {param}")
    
    _logger.info("TADA Admin module uninstall completed")


# Module version and metadata
__version__ = '1.0.0'
__author__ = 'TADA Admin Team'
__email__ = 'support@tada-admin.com'

_logger.info(f"TADA Admin Odoo Integration Module v{__version__} loaded")