# -*- coding: utf-8 -*-
"""
Odoo model for TADA Disassociation Requests with plain text storage.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

from ..sdk.chain2gate_sdk import DisassociationRequest, Status, PodMType, UserType
from ...utils.fiscal_code_validator import validate_fiscal_code

_logger = logging.getLogger(__name__)


class TadaDisassociationRequest(models.Model):
    """Odoo model for TADA Disassociation Requests with plain text storage."""
    
    _name = 'tada.disassociation.request'
    _description = 'TADA Disassociation Request'
    _inherit = ['tada.dataclass.mixin']
    _rec_name = 'pod'
    _order = 'created_at desc'
    
    # SDK integration configuration
    _dataclass_type = DisassociationRequest
    _sdk_field_mapping = {
        'id': 'request_id',  # Map SDK 'id' field to Odoo 'request_id' field
    }
    
    # Odoo fields matching SDK dataclass (plain text)
    request_id = fields.Char(string='Request ID', required=True, index=True)
    pod = fields.Char(string='POD', required=True, index=True,
                     help='Point of Delivery identifier')
    serial = fields.Char(string='Serial Number', required=True, index=True,
                        help='Device serial number')
    request_type = fields.Char(string='Request Type')
    pod_m_type = fields.Selection([
        ('M1', 'M1 - Consumption'),
        ('M2', 'M2 - Production'),
        ('M2_2', 'M2_2'),
        ('M2_3', 'M2_3'),
        ('M2_4', 'M2_4'),
    ], string='POD M Type', required=True, help='Type of meter connection')
    user_type = fields.Selection([
        ('PROSUMER', 'Prosumer'),
        ('CONSUMER', 'Consumer'),
    ], string='User Type', required=True, help='Customer type')
    
    # Plain text personal fields
    first_name = fields.Char(string='First Name',
                            help='Customer first name')
    last_name = fields.Char(string='Last Name',
                           help='Customer last name')
    email = fields.Char(string='Email',
                       help='Customer email')
    fiscal_code = fields.Char(string='Fiscal Code', required=True, index=True,
                             help='Customer fiscal code')
    
    # Other fields
    contract_signed = fields.Boolean(string='Contract Signed', default=False)
    product = fields.Char(string='Product')
    status = fields.Selection([
        ('PENDING', 'Pending'),
        ('AWAITING', 'Awaiting'),
        ('ADMISSIBLE', 'Admissible'),
        ('NOT_ADMISSIBLE', 'Not Admissible'),
        ('REFUSED', 'Refused'),
        ('ASSOCIATED', 'Associated'),
        ('TAKEN_IN_CHARGE', 'Taken in Charge'),
        ('DISASSOCIATED', 'Disassociated'),
    ], string='Status', required=True, default='PENDING', index=True)
    group = fields.Char(string='Group', index=True)
    
    # Customer relationship
    customer_id = fields.Many2one('tada.customer', string='Customer', 
                                 help='Related customer record')
    
    # Display name computed field
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=False)
    
    # Constraints
    _sql_constraints = [
        ('request_id_company_unique', 'UNIQUE(request_id, company_id)', 'Request ID must be unique per company!'),
        ('pod_serial_company_unique', 'UNIQUE(pod, serial, company_id)', 
         'POD and Serial combination must be unique per company!'),
    ]
    
    @api.constrains('fiscal_code')
    def _check_fiscal_code(self):
        """Validate fiscal code format."""
        for record in self:
            if record.fiscal_code:
                # Check if we're in an API sync context (non-blocking mode)
                is_api_sync = self.env.context.get('skip_fiscal_code_validation', False)
                
                try:
                    normalized_fiscal_code = validate_fiscal_code(
                        record.fiscal_code, 
                        raise_on_error=not is_api_sync
                    )
                    # Update the field with normalized value if different
                    if normalized_fiscal_code != record.fiscal_code:
                        record.fiscal_code = normalized_fiscal_code
                except ValidationError as e:
                    if not is_api_sync:
                        raise ValidationError(f"Invalid fiscal code '{record.fiscal_code}': {str(e)}")
                    # In API sync mode, just log the error and continue
                    _logger.warning(f"Skipping validation for invalid fiscal code '{record.fiscal_code}': {str(e)}")
    
    @api.depends('first_name', 'last_name', 'pod')
    def _compute_display_name(self):
        """Compute display name for better UX."""
        for record in self:
            name_parts = []
            if record.first_name:
                name_parts.append(record.first_name)
            if record.last_name:
                name_parts.append(record.last_name)
            
            if name_parts:
                record.display_name = f"{' '.join(name_parts)} ({record.pod}) - DISASSOCIATION"
            else:
                record.display_name = f"{record.pod} - DISASSOCIATION" if record.pod else 'Disassociation Request'
    
    @api.model
    def sync_from_api(self, company_id=None):
        """Sync disassociation requests from TADA API."""
        sdk = self.get_sdk_instance()
        
        try:
            requests = sdk.get_disassociation_requests()
            if isinstance(requests, dict) and requests.get('error'):
                raise UserError(f"API Error: {requests.get('message', 'Unknown error')}")
            
            synced_count = 0
            updated_count = 0
            skipped_count = 0
            current_company_id = company_id or self.env.company.id
            
            # Use context to skip fiscal code validation during sync
            sync_context = self.env.context.copy()
            sync_context['skip_fiscal_code_validation'] = True
            
            for request in requests:
                # Use a savepoint for each record to handle individual failures
                try:
                    with self.env.cr.savepoint():
                        # First try to find by request_id within company
                        existing = self.with_context(sync_context).search([
                            ('request_id', '=', request.id),
                            ('company_id', '=', current_company_id)
                        ], limit=1)
                        
                        # If not found by request_id, try to find by POD, serial and company
                        if not existing and hasattr(request, 'pod') and hasattr(request, 'serial'):
                            existing = self.with_context(sync_context).search([
                                ('pod', '=', request.pod),
                                ('serial', '=', request.serial),
                                ('company_id', '=', current_company_id)
                            ], limit=1)
                        
                        if existing:
                            existing.with_context(sync_context).update_from_dataclass(request)
                            updated_count += 1
                        else:
                            self.with_context(sync_context).from_dataclass(request, current_company_id)
                            synced_count += 1
                            
                except Exception as e:
                    # Log the error but continue with other records
                    # The savepoint automatically rolls back this individual record's changes
                    _logger.warning(f"Failed to sync disassociation request {getattr(request, 'id', 'unknown')}: {str(e)}")
                    skipped_count += 1
                    continue
            
            message = f'Synced {synced_count} new and updated {updated_count} disassociation requests'
            if skipped_count > 0:
                message += f' (skipped {skipped_count} due to errors)'
                
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success' if skipped_count == 0 else 'warning',
                }
            }
        except Exception as e:
            _logger.error(f"Failed to sync disassociation requests: {e}")
            raise UserError(f"Sync failed: {str(e)}")
    
    def create_api_request(self):
        """Create disassociation request via API."""
        self.ensure_one()
        
        if self.request_id:
            raise UserError("This request has already been created via API.")
        
        if not all([self.pod, self.serial, self.pod_m_type, self.fiscal_code]):
            raise UserError("POD, Serial, POD M Type, and Fiscal Code are required.")
        
        sdk = self.get_sdk_instance()
        
        try:
            result = sdk.create_disassociation_request(
                pod=self.pod,
                serial=self.serial,
                pod_m_type=PodMType(self.pod_m_type),
                fiscal_code=self.fiscal_code,
                user_type=UserType(self.user_type) if self.user_type else None,
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.email
            )
            
            if isinstance(result, dict) and result.get('error'):
                raise UserError(f"API Error: {result.get('message', 'Unknown error')}")
            
            # Update record with API response
            self.update_from_dataclass(result)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Disassociation request created: {result.id}',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Failed to create disassociation request: {e}")
            raise UserError(f"Creation failed: {str(e)}")
    
    def action_refresh_from_api(self):
        """Refresh this specific request from API."""
        self.ensure_one()
        
        if not self.request_id:
            raise UserError("Cannot refresh request without API ID.")
        
        sdk = self.get_sdk_instance()
        
        try:
            result = sdk.get_disassociation_request(self.request_id)
            
            if isinstance(result, dict) and result.get('error'):
                raise UserError(f"API Error: {result.get('message', 'Unknown error')}")
            
            # Update record with API response
            self.update_from_dataclass(result)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Request {self.request_id} refreshed successfully',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Failed to refresh disassociation request: {e}")
            raise UserError(f"Refresh failed: {str(e)}")
    
    def action_view_original_association(self):
        """View the original association request for this disassociation."""
        self.ensure_one()
        
        # Find association request with same POD and serial within company
        association = self.env['tada.association.request'].search([
            ('pod', '=', self.pod),
            ('serial', '=', self.serial),
            ('fiscal_code', '=', self.fiscal_code),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not association:
            raise UserError("No matching association request found.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Original Association Request',
            'res_model': 'tada.association.request',
            'res_id': association.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.model
    def create_or_update(self, vals):
        """Create new record or update existing one based on POD, serial and company."""
        pod = vals.get('pod')
        serial = vals.get('serial')
        company_id = vals.get('company_id', self.env.company.id)
        
        if pod and serial:
            existing = self.search([
                ('pod', '=', pod),
                ('serial', '=', serial),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if existing:
                existing.write(vals)
                return existing
        
        return self.create(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set created_at and trigger POD summary recomputation."""
        for vals in vals_list:
            if 'created_at' not in vals:
                vals['created_at'] = fields.Datetime.now()
        
        records = super().create(vals_list)
        
        # Trigger POD summary recomputation for new records
        for record in records:
            if record.pod and record.fiscal_code:
                self.env['tada_admin.pod.summary']._recompute_pod_summaries_for_request(
                    record.pod, record.fiscal_code, record.company_id.id
                )
        
        return records
    
    def unlink(self):
        """Override unlink to trigger POD summary recomputation."""
        # Store info before deletion
        pod_info = [(r.pod, r.fiscal_code, r.company_id.id) for r in self if r.pod and r.fiscal_code]
        
        result = super().unlink()
        
        # Trigger recomputation after deletion
        for pod, fiscal_code, company_id in pod_info:
            self.env['tada_admin.pod.summary']._recompute_pod_summaries_for_request(
                pod, fiscal_code, company_id
            )
        
        return result
    
    def write(self, vals):
        """Override write to set updated_at and trigger POD summary recomputation."""
        vals['updated_at'] = fields.Datetime.now()
        result = super().write(vals)
        
        # Trigger POD summary recomputation if relevant fields changed
        if any(field in vals for field in ['pod', 'fiscal_code', 'status', 'company_id']):
            for record in self:
                if record.pod and record.fiscal_code:
                    self.env['tada_admin.pod.summary']._recompute_pod_summaries_for_request(
                        record.pod, record.fiscal_code, record.company_id.id
                    )
        
        return result
    
    @api.onchange('pod_m_type')
    def _onchange_pod_m_type(self):
        """Update user type suggestion based on POD M type."""
        if self.pod_m_type == 'M1':
            # M1 is typically for consumption only
            if not self.user_type:
                self.user_type = 'CONSUMER'
        elif self.pod_m_type in ['M2', 'M2_2', 'M2_3', 'M2_4']:
            # M2 types are typically for production
            if not self.user_type:
                self.user_type = 'PROSUMER'