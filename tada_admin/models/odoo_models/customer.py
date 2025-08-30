# -*- coding: utf-8 -*-
"""
Odoo model for TADA Customer with plain text storage and aggregated data.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

from ..sdk.chain2gate_sdk import Customer, UserType
from ...utils.fiscal_code_validator import validate_fiscal_code, check_fiscal_code_uniqueness
from ...utils.api_error_handler import with_api_error_handling, log_api_call
from ...utils.multi_company_validator import MultiCompanyValidator, ensure_company_isolation

_logger = logging.getLogger(__name__)


class TadaCustomer(models.Model):
    """Odoo model for TADA Customer with plain text storage and aggregated data."""
    
    _name = 'tada.customer'
    _description = 'TADA Customer'
    _inherit = ['tada.dataclass.mixin']
    _rec_name = 'display_name'
    _order = 'display_name, created_at desc'
    
    # SDK integration configuration
    _dataclass_type = Customer
    
    # Plain text fields
    fiscal_code = fields.Char(string='Fiscal Code', required=True, index=True,
                             help='Customer fiscal code')
    first_name = fields.Char(string='First Name',
                            help='Customer first name')
    last_name = fields.Char(string='Last Name',
                           help='Customer last name')
    email = fields.Char(string='Email',
                       help='Customer email')
    phone = fields.Char(string='Phone',
                       help='Customer phone')
    user_type = fields.Selection([
        ('PROSUMER', 'Prosumer'),
        ('CONSUMER', 'Consumer'),
    ], string='User Type', help='Customer type')
    group = fields.Char(string='Group', index=True)
    
    # Display name computed field
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Aggregated data - One2many relationships to requests and devices
    admissibility_request_ids = fields.One2many(
        'tada.admissibility.request', 'customer_id',
        string='Admissibility Requests'
    )
    association_request_ids = fields.One2many(
        'tada.association.request', 'customer_id',
        string='Association Requests'
    )
    disassociation_request_ids = fields.One2many(
        'tada.disassociation.request', 'customer_id',
        string='Disassociation Requests'
    )
    device_ids = fields.Many2many(
        'tada.device', 'customer_device_rel', 'customer_id', 'device_id',
        string='Associated Devices'
    )
    
    # Statistics computed fields
    admissibility_count = fields.Integer(string='Admissibility Count', 
                                        compute='_compute_request_counts', store=True)
    association_count = fields.Integer(string='Association Count', 
                                      compute='_compute_request_counts', store=True)
    disassociation_count = fields.Integer(string='Disassociation Count', 
                                         compute='_compute_request_counts', store=True)
    device_count = fields.Integer(string='Device Count', 
                                 compute='_compute_device_count', store=True)
    
    # Status fields
    has_active_associations = fields.Boolean(string='Has Active Associations', 
                                            compute='_compute_status_fields', store=True)
    latest_request_date = fields.Datetime(string='Latest Request Date', 
                                         compute='_compute_status_fields', store=True)
    
    # Constraints
    _sql_constraints = [
        ('fiscal_code_company_unique', 'UNIQUE(fiscal_code, company_id)', 
         'Fiscal code must be unique per company!'),
    ]
    
    @api.depends('first_name', 'last_name', 'fiscal_code')
    def _compute_display_name(self):
        """Compute display name for better UX."""
        for record in self:
            name_parts = []
            if record.first_name:
                name_parts.append(record.first_name)
            if record.last_name:
                name_parts.append(record.last_name)
            
            if name_parts:
                record.display_name = f"{' '.join(name_parts)} ({record.fiscal_code})"
            else:
                record.display_name = record.fiscal_code or 'Customer'
    
    @api.depends('admissibility_request_ids', 'association_request_ids', 'disassociation_request_ids')
    def _compute_request_counts(self):
        """Compute request counts."""
        for record in self:
            record.admissibility_count = len(record.admissibility_request_ids)
            record.association_count = len(record.association_request_ids)
            record.disassociation_count = len(record.disassociation_request_ids)
    
    @api.depends('device_ids')
    def _compute_device_count(self):
        """Compute device count."""
        for record in self:
            record.device_count = len(record.device_ids)
    
    @api.depends('association_request_ids.status', 'disassociation_request_ids.status',
                 'admissibility_request_ids.created_at', 'association_request_ids.created_at',
                 'disassociation_request_ids.created_at')
    def _compute_status_fields(self):
        """Compute status fields."""
        for record in self:
            # Check for active associations
            active_associations = record.association_request_ids.filtered(
                lambda r: r.status in ['ASSOCIATED', 'TAKEN_IN_CHARGE']
            )
            active_disassociations = record.disassociation_request_ids.filtered(
                lambda r: r.status == 'DISASSOCIATED'
            )
            record.has_active_associations = len(active_associations) > len(active_disassociations)
            
            # Find latest request date
            all_dates = []
            for req in record.admissibility_request_ids:
                if req.created_at:
                    all_dates.append(req.created_at)
            for req in record.association_request_ids:
                if req.created_at:
                    all_dates.append(req.created_at)
            for req in record.disassociation_request_ids:
                if req.created_at:
                    all_dates.append(req.created_at)
            
            record.latest_request_date = max(all_dates) if all_dates else None
    
    @api.constrains('fiscal_code', 'company_id')
    def _check_fiscal_code(self):
        """Validate fiscal code format and uniqueness within company."""
        for record in self:
            if not record.fiscal_code:
                raise ValidationError("Fiscal code is required")
            
            # Check if we're in an API sync context (non-blocking mode)
            is_api_sync = self.env.context.get('skip_fiscal_code_validation', False)
            
            # Validate format and normalize
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
            
            # Check uniqueness within company using multi-company validator
            # Skip uniqueness check during API sync to avoid blocking
            if not is_api_sync:
                MultiCompanyValidator.validate_fiscal_code_uniqueness_per_company(
                    self, record.fiscal_code, record.company_id.id, record.id
                )
    
    @api.constrains('company_id')
    def _check_company_consistency(self):
        """Validate company consistency with related records."""
        for record in self:
            if not record.company_id:
                continue
            
            # Validate that all related requests belong to the same company
            if record.admissibility_request_ids:
                MultiCompanyValidator.validate_related_records_company(
                    record, record.admissibility_request_ids, "admissibility requests"
                )
            
            if record.association_request_ids:
                MultiCompanyValidator.validate_related_records_company(
                    record, record.association_request_ids, "association requests"
                )
            
            if record.disassociation_request_ids:
                MultiCompanyValidator.validate_related_records_company(
                    record, record.disassociation_request_ids, "disassociation requests"
                )
            
            if record.device_ids:
                MultiCompanyValidator.validate_related_records_company(
                    record, record.device_ids, "devices"
                )

    @api.model
    def sync_customer_from_api(self, fiscal_code=None, company_id=None):
        """Sync customer data from TADA API. If no fiscal_code provided, sync all customers from local data."""
        log_api_call(
            operation="Customer Sync",
            fiscal_code=fiscal_code,
            company_id=company_id,
            sync_type="single" if fiscal_code else "all_local"
        )
        
        if fiscal_code:
            # Sync specific customer from API
            return self._sync_single_customer(fiscal_code, company_id)
        else:
            # Sync all customers from local data (fast)
            return self._sync_all_customers(company_id)
    
    @api.model
    @with_api_error_handling("Sync all customers from API", max_retries=2)
    def sync_all_customers_from_api(self, company_id=None):
        """Sync all customers by making API calls (slower but more up-to-date)."""
        log_api_call(
            operation="Sync All Customers from API",
            company_id=company_id
        )
        
        sdk = self.get_sdk_instance()
        
        # Collect all unique fiscal codes from API requests
        fiscal_codes = set()
        
        # Get fiscal codes from admissibility requests
        admissibility_requests = sdk.get_admissibility_requests()
        if not (isinstance(admissibility_requests, dict) and admissibility_requests.get('error')):
            for req in admissibility_requests:
                if req.fiscal_code:
                    fiscal_codes.add(req.fiscal_code)
        
        # Get fiscal codes from association requests
        association_requests = sdk.get_association_requests()
        if not (isinstance(association_requests, dict) and association_requests.get('error')):
            for req in association_requests:
                if req.fiscal_code:
                    fiscal_codes.add(req.fiscal_code)
        
        # Get fiscal codes from disassociation requests
        disassociation_requests = sdk.get_disassociation_requests()
        if not (isinstance(disassociation_requests, dict) and disassociation_requests.get('error')):
            for req in disassociation_requests:
                if req.fiscal_code:
                    fiscal_codes.add(req.fiscal_code)
        
        if not fiscal_codes:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No customers found in API',
                    'type': 'warning',
                }
            }
        
        # Sync each customer from API
        synced_count = 0
        failed_count = 0
        
        for fiscal_code in fiscal_codes:
            try:
                result = self._sync_single_customer(fiscal_code, company_id)
                if result.get('type') == 'ir.actions.client' and 'success' in result.get('params', {}).get('message', ''):
                    synced_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                _logger.error(f"Failed to sync customer {fiscal_code}: {e}")
                failed_count += 1
        
        message = f'Synced {synced_count} customers successfully from API'
        if failed_count > 0:
            message += f', {failed_count} failed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success' if synced_count > 0 else 'warning',
            }
        }
    
    @api.model
    @with_api_error_handling("Sync single customer from API", max_retries=3)
    def _sync_single_customer(self, fiscal_code, company_id=None):
        """Sync specific customer data from TADA API."""
        log_api_call(
            operation="Sync Single Customer",
            fiscal_code=fiscal_code,
            company_id=company_id
        )
        
        sdk = self.get_sdk_instance()
        
        customer_info = sdk.get_customer_info(fiscal_code)
        
        # Find or create customer record using create_or_update
        customer_data = self._prepare_customer_data_from_dataclass(customer_info, company_id)
        customer_record = self.create_or_update(customer_data)
        
        # Link related requests and devices
        customer_record._link_related_records()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Customer {fiscal_code} synced successfully',
                'type': 'success',
            }
        }
    
    @api.model
    def _sync_all_customers(self, company_id=None):
        """Sync all customers from local request records (much faster than API calls)."""
        try:
            if not company_id:
                company_id = self.env.company.id
            
            # Collect all unique fiscal codes from local request records
            fiscal_codes = set()
            
            # Get fiscal codes from local admissibility requests
            admissibility_requests = self.env['tada.admissibility.request'].search([
                ('company_id', '=', company_id)
            ])
            for req in admissibility_requests:
                if req.fiscal_code:
                    fiscal_codes.add(req.fiscal_code)
            
            # Get fiscal codes from local association requests
            association_requests = self.env['tada.association.request'].search([
                ('company_id', '=', company_id)
            ])
            for req in association_requests:
                if req.fiscal_code:
                    fiscal_codes.add(req.fiscal_code)
            
            # Get fiscal codes from local disassociation requests
            disassociation_requests = self.env['tada.disassociation.request'].search([
                ('company_id', '=', company_id)
            ])
            for req in disassociation_requests:
                if req.fiscal_code:
                    fiscal_codes.add(req.fiscal_code)
            
            if not fiscal_codes:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'No customers found in local requests. Please sync requests first.',
                        'type': 'warning',
                    }
                }
            
            # Create customers from local data
            synced_count = 0
            failed_count = 0
            
            for fiscal_code in fiscal_codes:
                try:
                    # Build customer info from local requests
                    customer_info = self._build_customer_from_local_requests(fiscal_code, company_id)
                    
                    if not customer_info:
                        _logger.warning(f"No customer info found for fiscal code: {fiscal_code}")
                        failed_count += 1
                        continue
                    
                    # Find or create customer record
                    customer_data = self._prepare_customer_data_from_dataclass(customer_info, company_id)
                    customer_record = self.create_or_update(customer_data)
                    
                    # Link related requests and devices
                    customer_record._link_related_records()
                    synced_count += 1
                    
                except Exception as e:
                    _logger.error(f"Failed to sync customer {fiscal_code}: {e}")
                    failed_count += 1
            
            message = f'Synced {synced_count} customers successfully from local data'
            if failed_count > 0:
                message += f', {failed_count} failed'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success' if synced_count > 0 else 'warning',
                }
            }
            
        except Exception as e:
            _logger.error(f"Failed to sync all customers from local data: {e}")
            raise UserError(f"Sync all customers failed: {str(e)}")
    
    @api.model
    def _build_customer_from_local_requests(self, fiscal_code, company_id):
        """Build a Customer dataclass instance from local request records."""
        from ..sdk.chain2gate_sdk import Customer, UserType
        
        # Get all requests for this fiscal code
        admissibility_requests = self.env['tada.admissibility.request'].search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', company_id)
        ])
        
        association_requests = self.env['tada.association.request'].search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', company_id)
        ])
        
        disassociation_requests = self.env['tada.disassociation.request'].search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', company_id)
        ])
        
        # Extract customer details from the first available request with personal info
        first_name = None
        last_name = None
        email = None
        user_type = None
        group = None
        
        # Try to get personal info from association requests first (most complete)
        for req in association_requests:
            if req.first_name:
                first_name = req.first_name
                last_name = req.last_name
                email = req.email
                user_type = UserType(req.user_type) if req.user_type else None
                group = req.group
                break
        
        # If not found, try disassociation requests
        if not first_name:
            for req in disassociation_requests:
                if req.first_name:
                    first_name = req.first_name
                    last_name = req.last_name
                    email = req.email
                    user_type = UserType(req.user_type) if req.user_type else None
                    group = req.group
                    break
        
        # Create Customer dataclass instance
        customer = Customer(
            fiscal_code=fiscal_code,
            first_name=first_name,
            last_name=last_name,
            email=email,
            user_type=user_type,
            group=group
        )
        
        # For now, we don't need to populate the request lists in the customer object
        # since we're only using it to create the customer record, not to sync the requests
        customer.admissibility_requests = []
        customer.association_requests = []
        customer.disassociation_requests = []
        customer.devices = []
        
        return customer
    
    def _prepare_customer_data_from_dataclass(self, dataclass_instance, company_id=None):
        """Prepare customer data from dataclass for create_or_update."""
        from dataclasses import asdict
        from enum import Enum
        
        data = asdict(dataclass_instance)
        odoo_data = {}
        
        # Validate that we have a fiscal code
        if not data.get('fiscal_code'):
            raise UserError(f"Cannot create customer without fiscal code. Data: {data}")
        
        # List of relationship fields that should be skipped during data preparation
        relationship_fields = ['admissibility_requests', 'association_requests', 'disassociation_requests', 'devices']
        
        for dc_field_name, value in data.items():
            # Skip relationship fields - they will be handled separately
            if dc_field_name in relationship_fields:
                continue
                
            # Store all data in plain text
            if isinstance(value, Enum):
                odoo_data[dc_field_name] = value.value
            elif dc_field_name.endswith('_at') or 'date' in dc_field_name.lower():
                parsed_dt = self._parse_datetime(value)
                if parsed_dt:
                    odoo_data[dc_field_name] = parsed_dt
                else:
                    odoo_data[dc_field_name] = value
            else:
                odoo_data[dc_field_name] = value
        
        if company_id:
            odoo_data['company_id'] = company_id
        elif not odoo_data.get('company_id'):
            odoo_data['company_id'] = self.env.company.id
        
        # Ensure fiscal_code is set
        if not odoo_data.get('fiscal_code'):
            raise UserError(f"Fiscal code missing for customer {data.get('fiscal_code')}")
        
        return odoo_data
    
    def _link_related_records(self):
        """Link related requests and devices to this customer."""
        self.ensure_one()
        
        # Validate company access
        self._validate_company_access("link related records")
        
        # Use plain text fiscal code for searching
        fiscal_code = self.fiscal_code
        
        # Link admissibility requests (only from same company)
        admissibility_requests = self.env['tada.admissibility.request'].search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', self.company_id.id)
        ])
        for req in admissibility_requests:
            # Validate company consistency before linking
            if req.company_id != self.company_id:
                _logger.warning(
                    f"Skipping admissibility request {req.id} - company mismatch: "
                    f"customer company {self.company_id.name}, request company {req.company_id.name}"
                )
                continue
            req.customer_id = self.id
        
        # Link association requests (only from same company)
        association_requests = self.env['tada.association.request'].search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', self.company_id.id)
        ])
        for req in association_requests:
            # Validate company consistency before linking
            if req.company_id != self.company_id:
                _logger.warning(
                    f"Skipping association request {req.id} - company mismatch: "
                    f"customer company {self.company_id.name}, request company {req.company_id.name}"
                )
                continue
            req.customer_id = self.id
        
        # Link disassociation requests (only from same company)
        disassociation_requests = self.env['tada.disassociation.request'].search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', self.company_id.id)
        ])
        for req in disassociation_requests:
            # Validate company consistency before linking
            if req.company_id != self.company_id:
                _logger.warning(
                    f"Skipping disassociation request {req.id} - company mismatch: "
                    f"customer company {self.company_id.name}, request company {req.company_id.name}"
                )
                continue
            req.customer_id = self.id
        
        # Link devices based on association requests (only from same company)
        device_serials = set()
        for req in association_requests:
            if req.serial and req.status in ['ASSOCIATED', 'TAKEN_IN_CHARGE']:
                device_serials.add(req.serial)
        
        if device_serials:
            devices = self.env['tada.device'].search([
                ('device_id', 'in', list(device_serials)),
                ('company_id', '=', self.company_id.id)
            ])
            # Validate that all devices belong to the same company
            if devices:
                MultiCompanyValidator.validate_related_records_company(
                    self, devices, "devices"
                )
            self.device_ids = [(6, 0, devices.ids)]
    
    def action_view_admissibility_requests(self):
        """View admissibility requests for this customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Admissibility Requests - {self.display_name}',
            'res_model': 'tada.admissibility.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.admissibility_request_ids.ids)],
            'context': {'default_fiscal_code': self.fiscal_code},
        }
    
    def action_view_association_requests(self):
        """View association requests for this customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Association Requests - {self.display_name}',
            'res_model': 'tada.association.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.association_request_ids.ids)],
            'context': {
                'default_fiscal_code': self.fiscal_code,
                'default_first_name': self.first_name,
                'default_last_name': self.last_name,
                'default_email': self.email,
            },
        }
    
    def action_view_disassociation_requests(self):
        """View disassociation requests for this customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Disassociation Requests - {self.display_name}',
            'res_model': 'tada.disassociation.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.disassociation_request_ids.ids)],
            'context': {
                'default_fiscal_code': self.fiscal_code,
                'default_first_name': self.first_name,
                'default_last_name': self.last_name,
                'default_email': self.email,
            },
        }
    
    def action_view_devices(self):
        """View devices associated with this customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Devices - {self.display_name}',
            'res_model': 'tada.device',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.device_ids.ids)],
        }
    
    def action_refresh_from_api(self):
        """Refresh customer data from API."""
        self.ensure_one()
        return self.sync_customer_from_api(self.fiscal_code, self.company_id.id)
    
    @api.model
    def create_or_update(self, vals):
        """Create new record or update existing one based on fiscal code and company."""
        fiscal_code = vals.get('fiscal_code')
        company_id = vals.get('company_id', self.env.company.id)
        
        if not fiscal_code:
            raise UserError("Cannot create or update customer without fiscal code")
        
        existing = self.search([
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', company_id)
        ], limit=1)
        
        if existing:
            # Update existing record
            existing.write(vals)
            existing._link_related_records()
            return existing
        else:
            # Create new record
            record = self.create(vals)
            record._link_related_records()
            return record
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set created_at if not provided."""
        for vals in vals_list:
            if 'created_at' not in vals:
                vals['created_at'] = fields.Datetime.now()
        records = super().create(vals_list)
        # Link related records after creation
        for record in records:
            record._link_related_records()
        return records
    
    def write(self, vals):
        """Override write to set updated_at."""
        vals['updated_at'] = fields.Datetime.now()
        result = super().write(vals)
        # Re-link related records if fiscal code changed
        if 'fiscal_code' in vals:
            for record in self:
                record._link_related_records()
        return result