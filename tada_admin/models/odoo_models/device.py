# -*- coding: utf-8 -*-
"""
Odoo model for TADA Devices.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

from ..sdk.chain2gate_sdk import Chain2GateDevice, DeviceType

_logger = logging.getLogger(__name__)


class TadaDevice(models.Model):
    """Odoo model for TADA Devices."""
    
    _name = 'tada.device'
    _description = 'TADA Device'
    _inherit = ['tada.dataclass.mixin']
    _rec_name = 'device_id'
    _order = 'created_at desc'
    
    # SDK integration configuration
    _dataclass_type = Chain2GateDevice
    _sdk_field_mapping = {
        'id': 'device_id',  # Map SDK 'id' field to Odoo 'device_id' field
    }
    
    # Odoo fields matching SDK dataclass
    device_id = fields.Char(string='Device ID', required=True, index=True,
                           help='Unique device identifier')
    m1 = fields.Char(string='M1 POD', index=True,
                    help='M1 Point of Delivery (consumption meter)')
    m2 = fields.Char(string='M2 POD', index=True,
                    help='M2 Point of Delivery (production meter)')
    m2_2 = fields.Char(string='M2_2 POD', help='M2_2 Point of Delivery')
    m2_3 = fields.Char(string='M2_3 POD', help='M2_3 Point of Delivery')
    m2_4 = fields.Char(string='M2_4 POD', help='M2_4 Point of Delivery')
    login_key = fields.Char(string='Login Key', help='Device login key')
    du_name = fields.Char(string='DU Name', required=True, index=True,
                         help='Device unit name')
    hw_version = fields.Char(string='Hardware Version', help='Hardware version')
    sw_version = fields.Char(string='Software Version', help='Software version')
    fw_version = fields.Char(string='Firmware Version', help='Firmware version')
    mac = fields.Char(string='MAC Address', help='Device MAC address')
    k1 = fields.Char(string='K1', help='Security key K1')
    k2 = fields.Char(string='K2', help='Security key K2')
    system_title = fields.Char(string='System Title', help='Device system title')
    group = fields.Char(string='Group', index=True, help='Device group')
    type_name = fields.Char(string='Type Name', index=True, help='Device type name')

    # Multi-company support
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, default=lambda self: self.env.company,
                                 help='Company this customer belongs to')
    
    # Additional computed fields
    has_consumption = fields.Boolean(string='Has Consumption', compute='_compute_meter_types', store=True)
    has_production = fields.Boolean(string='Has Production', compute='_compute_meter_types', store=True)
    
    # Status and monitoring fields
    active = fields.Boolean(string='Active', default=True, help='Device is active')
    last_sync = fields.Datetime(string='Last Sync', help='Last synchronization with API')
    status = fields.Selection([
        ('not_installed', 'Non Installato'),
        ('connecting', 'In Collegamento'),
        ('online', 'Online'),
        ('online_weak_wifi', 'Online - WiFi Debole'),
        ('online_weak_meter_signal', 'Online - Segnale Contatore Debole'),
        ('offline', 'Offline'),
        ('replacing', 'In Sostituzione'),
        ('replaced', 'Sostituito'),
        ('online_meter_update_needed', 'Online - Contatore da Aggiornare'),
        ('online_meter_not_working', 'Online - Contatore Non Funzionante'),
        ('offline_supplier_change', 'Offline - Chiusura Servizio per Cambio Fornitore'),
        ('offline_tada_closure', 'Offline - Chiusura Servizio TADA'),
        ('offline_supply_deactivation', 'Offline - Chiusura Servizio per Disattivazione Fornitura'),
        ('offline_administrative_closure', 'Offline - Chiusura Servizio per Cessazione Amministrativa'),
        ('offline_ownership_transfer', 'Offline - Chiusura Servizio per Voltura')
    ], string='Status', default='not_installed', required=True, index=True)

    # Constraints
    _sql_constraints = [
        ('device_id_company_unique', 'UNIQUE(device_id, company_id)', 'Device ID must be unique per company!'),
        ('mac_company_unique', 'UNIQUE(mac, company_id)', 'MAC address must be unique per company!'),
    ]

    @api.depends('m1', 'm2', 'm2_2', 'm2_3', 'm2_4')
    def _compute_meter_types(self):
        """Compute meter type capabilities."""
        for record in self:
            record.has_consumption = bool(record.m1)
            record.has_production = bool(record.m2 or record.m2_2 or record.m2_3 or record.m2_4)
    
    @api.model
    def sync_from_api(self, device_type=None, company_id=None):
        """Sync devices from TADA API."""
        sdk = self.get_sdk_instance()
        
        try:
            if device_type:
                devices = sdk.get_devices_by_type(DeviceType(device_type))
            else:
                devices = sdk.get_devices()
            
            if isinstance(devices, dict) and devices.get('error'):
                raise UserError(f"API Error: {devices.get('message', 'Unknown error')}")
            
            synced_count = 0
            updated_count = 0
            current_company_id = company_id or self.env.company.id
            
            for device in devices:
                # First try to find by device_id within company
                existing = self.search([
                    ('device_id', '=', device.id),
                    ('company_id', '=', current_company_id)
                ], limit=1)
                
                # If not found by device_id and device has MAC, try to find by MAC within company
                if not existing and hasattr(device, 'mac') and device.mac:
                    existing = self.search([
                        ('mac', '=', device.mac),
                        ('company_id', '=', current_company_id)
                    ], limit=1)
                
                if existing:
                    existing.update_from_dataclass(device)
                    existing.last_sync = fields.Datetime.now()
                    updated_count += 1
                else:
                    new_device = self.from_dataclass(device, current_company_id)
                    new_device.last_sync = fields.Datetime.now()
                    synced_count += 1
            
            message = f'Synced {synced_count} new and updated {updated_count} devices'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Failed to sync devices: {e}")
            raise UserError(f"Sync failed: {str(e)}")
    
    def action_refresh_from_api(self):
        """Refresh this specific device from API."""
        self.ensure_one()
        
        if not self.device_id:
            raise UserError("Cannot refresh device without Device ID.")
        
        sdk = self.get_sdk_instance()
        
        try:
            # Get all devices and find this one
            devices = sdk.get_devices()
            
            if isinstance(devices, dict) and devices.get('error'):
                raise UserError(f"API Error: {devices.get('message', 'Unknown error')}")
            
            # Find the specific device
            device_data = None
            for device in devices:
                if device.id == self.device_id:
                    device_data = device
                    break
            
            if not device_data:
                raise UserError(f"Device {self.device_id} not found in API response.")
            
            # Update record with API response
            self.update_from_dataclass(device_data)
            self.last_sync = fields.Datetime.now()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Device {self.device_id} refreshed successfully',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Failed to refresh device: {e}")
            raise UserError(f"Refresh failed: {str(e)}")
    
    def action_view_associated_requests(self):
        """View association requests for this device."""
        self.ensure_one()
        
        # Find association requests that use this device's serial
        association_requests = self.env['tada.association.request'].search([
            ('serial', '=', self.device_id),
            ('company_id', '=', self.company_id.id)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Association Requests for {self.du_name}',
            'res_model': 'tada.association.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', association_requests.ids)],
            'context': {'default_serial': self.device_id},
        }

    @api.model
    def create_or_update(self, vals):
        """Create new record or update existing one based on device_id or MAC within company."""
        device_id = vals.get('device_id')
        mac = vals.get('mac')
        company_id = vals.get('company_id', self.env.company.id)
        
        existing = None
        
        # First try to find by device_id within company
        if device_id:
            existing = self.search([
                ('device_id', '=', device_id),
                ('company_id', '=', company_id)
            ], limit=1)
        
        # If not found by device_id, try by MAC within company
        if not existing and mac:
            existing = self.search([
                ('mac', '=', mac),
                ('company_id', '=', company_id)
            ], limit=1)
        
        if existing:
            existing.write(vals)
            return existing
        
        return self.create(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set created_at if not provided."""
        for vals in vals_list:
            if 'created_at' not in vals:
                vals['created_at'] = fields.Datetime.now()
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to set updated_at."""
        vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)
    
    @api.model
    def get_device_types(self):
        """Get available device types from SDK."""
        return [(dt.value, dt.value.replace('_', ' ').title()) for dt in DeviceType]