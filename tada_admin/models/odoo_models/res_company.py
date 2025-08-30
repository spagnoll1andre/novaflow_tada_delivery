# -*- coding: utf-8 -*-
"""
Company extension for TADA Admin integration.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    # TADA Admin API Configuration
    tada_api_key = fields.Char(
        string='TADA API Key',
        help='API key for TADA Admin API authentication (x-api-key header)'
    )
    
    tada_base_url = fields.Char(
        string='TADA Base URL',
        default='https://chain2-api.chain2gate.it',
        help='Base URL for TADA Admin API endpoints'
    )
    
    tada_active = fields.Boolean(
        string='TADA Integration Active',
        default=False,
        help='Enable/disable TADA Admin integration for this company'
    )
    
    tada_last_sync = fields.Datetime(
        string='Last Sync',
        help='Last successful synchronization with TADA API'
    )
    
    tada_connection_status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('configured', 'Configured'),
        ('connected', 'Connected'),
        ('error', 'Connection Error')
    ], string='Connection Status', default='not_configured', compute='_compute_tada_connection_status')
    
    tada_status_message = fields.Text(
        string='Status Message',
        compute='_compute_tada_connection_status'
    )

    @api.depends('tada_api_key', 'tada_base_url', 'tada_active')
    def _compute_tada_connection_status(self):
        """Compute TADA connection status and message"""
        for record in self:
            if not record.tada_active:
                record.tada_connection_status = 'not_configured'
                record.tada_status_message = 'TADA Admin integration is disabled'
            elif not record.tada_api_key or not record.tada_base_url:
                record.tada_connection_status = 'not_configured'
                record.tada_status_message = 'API key or base URL not configured'
            else:
                record.tada_connection_status = 'configured'
                record.tada_status_message = 'Configuration complete - ready to test connection'

    @api.constrains('tada_base_url')
    def _check_tada_base_url(self):
        """Validate TADA base URL format"""
        for record in self:
            if record.tada_base_url and not record.tada_base_url.startswith(('http://', 'https://')):
                raise ValidationError(_('TADA Base URL must start with http:// or https://'))

    def validate_tada_api_configuration(self):
        """Validate TADA API configuration for this company"""
        self.ensure_one()
        
        if not self.tada_api_key:
            raise ValidationError(_('TADA API Key is required for API configuration'))
        
        if not self.tada_base_url:
            raise ValidationError(_('TADA Base URL is required for API configuration'))
        
        return True

    def test_tada_api_connection(self):
        """Test connection to TADA API with current configuration"""
        self.ensure_one()
        
        # Validate configuration first
        self.validate_tada_api_configuration()
        
        try:
            # Test API connection with a simple endpoint
            headers = {
                'x-api-key': self.tada_api_key,
                'Content-Type': 'application/json'
            }
            
            # Use a basic endpoint to test connectivity
            test_url = f"{self.tada_base_url.rstrip('/')}/health"
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': _('Connection successful')
                }
            else:
                return {
                    'success': False,
                    'message': _('Connection failed: HTTP %s') % response.status_code
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': _('Connection timeout - please check the URL and network connectivity')
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': _('Connection error - please check the URL and network connectivity')
            }
        except Exception as e:
            return {
                'success': False,
                'message': _('Connection failed: %s') % str(e)
            }

    def get_tada_api_headers(self):
        """Get API headers for TADA API calls"""
        self.ensure_one()
        
        if not self.tada_api_key:
            raise ValidationError(_('TADA API Key not configured for company %s') % self.name)
        
        return {
            'x-api-key': self.tada_api_key,
            'Content-Type': 'application/json'
        }

    def action_test_tada_connection(self):
        """Action method to test TADA API connection from company form"""
        self.ensure_one()
        
        try:
            result = self.test_tada_api_connection()
            
            if result['success']:
                # Update connection status
                self.write({
                    'tada_connection_status': 'connected',
                    'tada_status_message': 'Connection verified successfully'
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('TADA Admin connection test successful!'),
                        'type': 'success',
                    }
                }
            else:
                # Update connection status to error
                self.write({
                    'tada_connection_status': 'error',
                    'tada_status_message': f'Connection failed: {result["message"]}'
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Connection test failed: %s') % result['message'],
                        'type': 'danger',
                    }
                }
                
        except Exception as e:
            # Update connection status to error
            self.write({
                'tada_connection_status': 'error',
                'tada_status_message': f'Connection failed: {str(e)}'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Connection test failed: %s') % str(e),
                    'type': 'danger',
                }
            }

    def update_tada_last_sync(self):
        """Update the last sync timestamp"""
        self.ensure_one()
        self.tada_last_sync = fields.Datetime.now()
        _logger.info(f"Updated TADA last sync for company {self.name}")

    def get_tada_sync_status(self):
        """Get formatted sync status information"""
        self.ensure_one()
        
        if not self.tada_last_sync:
            return _('Never synchronized')
        
        # Calculate time difference
        from datetime import datetime, timedelta
        now = fields.Datetime.now()
        diff = now - self.tada_last_sync
        
        if diff < timedelta(minutes=1):
            return _('Just now')
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return _('%d minutes ago') % minutes
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return _('%d hours ago') % hours
        else:
            days = diff.days
            return _('%d days ago') % days

    def action_open_tada_config_wizard(self):
        """Open TADA configuration wizard"""
        self.ensure_one()
        
        wizard = self.env['tada.config.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _('TADA Admin Configuration Wizard'),
            'res_model': 'tada.config.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_tada_menu(self):
        """Open TADA Admin main menu"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('TADA Admin'),
            'res_model': 'tada.customer',
            'view_mode': 'list,form',
            'target': 'current',
        }
