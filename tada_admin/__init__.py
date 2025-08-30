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
    
    _logger.info("TADA Admin module initialization completed successfully")


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