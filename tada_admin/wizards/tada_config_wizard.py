# -*- coding: utf-8 -*-
"""
Configuration wizard for TADA Admin integration.

This wizard helps users set up the TADA Admin integration by configuring
API keys and testing the connection.
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging

from ..models.sdk.chain2gate_sdk import Chain2GateSDK

_logger = logging.getLogger(__name__)


class TadaConfigWizard(models.TransientModel):
    """Configuration wizard for TADA Admin integration."""
    
    _name = 'tada.config.wizard'
    _description = 'TADA Admin Configuration Wizard'
    
    # Configuration fields
    api_key = fields.Char(string='TADA API Key', required=True,
                         help='Your Chain2Gate API key for accessing the API')
    base_url = fields.Char(string='API Base URL', 
                          default='https://chain2-api.chain2gate.it',
                          help='Chain2Gate API base URL')
    
    # Test results
    connection_status = fields.Text(string='Connection Test Result', readonly=True)
    
    # Wizard state
    state = fields.Selection([
        ('config', 'Configuration'),
        ('test', 'Testing'),
        ('complete', 'Complete')
    ], default='config', string='State')
    
    @api.model
    def default_get(self, fields_list):
        """Load existing configuration if available."""
        defaults = super().default_get(fields_list)
        
        # Load existing API key from company
        company = self.env.company
        if company.tada_api_key:
            defaults['api_key'] = company.tada_api_key
        
        # Load existing base URL from company
        if company.tada_base_url:
            defaults['base_url'] = company.tada_base_url
        
        return defaults
    
    def test_connection(self):
        """Test the Chain2Gate API connection."""
        self.ensure_one()
        
        try:
            # Create SDK instance for testing
            sdk = Chain2GateSDK(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # Test basic API connection
            _logger.info("Testing TADA Admin API connection...")
            result = sdk.debug_response("/admissibility")
            
            if result.get('error'):
                self.connection_status = f"❌ Connection failed: {result.get('message', 'Unknown error')}"
                _logger.error(f"API connection failed: {result.get('message')}")
            else:
                self.connection_status = "✅ API connection successful!"
                
                # Test a simple API call
                try:
                    requests = sdk.get_admissibility_requests()
                    if isinstance(requests, list):
                        self.connection_status += f"\n✅ Retrieved {len(requests)} admissibility requests"
                        _logger.info(f"Successfully retrieved {len(requests)} admissibility requests")
                    elif isinstance(requests, dict) and requests.get('error'):
                        self.connection_status += f"\n⚠️ API call warning: {requests.get('message')}"
                        _logger.warning(f"API call warning: {requests.get('message')}")
                    else:
                        self.connection_status += "\n✅ API calls working correctly"
                        _logger.info("API calls working correctly")
                except Exception as api_error:
                    self.connection_status += f"\n⚠️ API call error: {str(api_error)}"
                    _logger.error(f"API call error: {str(api_error)}")
            
        except Exception as e:
            _logger.error(f"Connection test failed: {e}")
            self.connection_status = f"❌ Connection test failed: {str(e)}"
            
            # Provide helpful error messages for common issues
            if "Connection refused" in str(e):
                self.connection_status += "\n💡 Tip: Check if the API URL is correct and accessible"
            elif "Unauthorized" in str(e) or "401" in str(e):
                self.connection_status += "\n💡 Tip: Check if your API key is valid"
            elif "timeout" in str(e).lower():
                self.connection_status += "\n💡 Tip: Check your network connection and try again"
        
        self.state = 'test'
        return self._return_wizard()
    

    
    def save_configuration(self):
        """Save the configuration to company settings."""
        self.ensure_one()
        
        # Save configuration to current company
        company = self.env.company
        company.write({
            'tada_api_key': self.api_key,
            'tada_base_url': self.base_url,
            'tada_active': True,
        })
        
        self.state = 'complete'
        
        _logger.info(f"TADA Admin configuration saved for company {company.name}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'TADA Admin configuration saved successfully!',
                'type': 'success',
            }
        }
    
    def _return_wizard(self):
        """Return the wizard view."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'chain2gate.config.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def open_tada_menu(self):
        """Open the TADA Admin main menu."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'TADA Admin',
            'res_model': 'tada.admissibility.request',
            'view_mode': 'list,form',
            'target': 'current',
        }


class TadaSettings(models.TransientModel):
    """Settings model for TADA Admin configuration."""
    
    _name = 'tada.settings'
    _description = 'TADA Admin Settings'
    _inherit = 'res.config.settings'
    
    # Configuration fields linked to company
    tada_api_key = fields.Char(
        string='TADA API Key',
        related='company_id.tada_api_key',
        readonly=False,
        help='Your Chain2Gate API key for accessing the API'
    )
    
    tada_base_url = fields.Char(
        string='API Base URL',
        related='company_id.tada_base_url',
        readonly=False,
        help='Chain2Gate API base URL'
    )
    
    tada_active = fields.Boolean(
        string='TADA Integration Active',
        related='company_id.tada_active',
        readonly=False,
        help='Indicates if TADA ERP integration is active for this company'
    )
    
    def open_config_wizard(self):
        """Open the configuration wizard."""
        wizard = self.env['tada.config.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'TADA Admin Configuration Wizard',
            'res_model': 'tada.config.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def test_connection(self):
        """Test the TADA Admin connection."""
        if not self.tada_api_key:
            raise UserError("Please configure the API key first.")
        
        try:
            sdk = Chain2GateSDK(
                api_key=self.tada_api_key,
                base_url=self.tada_base_url
            )
            
            # Test API connection
            result = sdk.debug_response("/admissibility")
            
            if result.get('error'):
                raise UserError(f"Connection failed: {result.get('message', 'Unknown error')}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'TADA Admin connection test successful!',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            raise UserError(f"Connection test failed: {str(e)}")