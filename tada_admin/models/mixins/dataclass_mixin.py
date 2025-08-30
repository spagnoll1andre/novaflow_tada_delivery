# -*- coding: utf-8 -*-
"""
Abstract mixin that provides dataclass integration for TADA ERP SDK models in Odoo.
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError, AccessError
from typing import Type, Dict, Any, Optional, List, Union
import logging
from datetime import datetime
from dataclasses import asdict, fields as dataclass_fields
from enum import Enum

from ..sdk.chain2gate_sdk import Chain2GateSDK
from ...utils.api_error_handler import (
    APIErrorHandler, validate_api_configuration, log_api_call, with_api_error_handling
)
from ...utils.multi_company_validator import MultiCompanyValidator, ensure_company_isolation

_logger = logging.getLogger(__name__)


class TadaDataclassModelMixin(models.AbstractModel):
    """
    Abstract mixin that provides dataclass integration for TADA ERP SDK models in Odoo.
    
    This mixin handles:
    - Conversion between Odoo records and SDK dataclasses
    - Company-specific API configuration
    - Seamless integration with Chain2Gate SDK methods
    """
    
    _name = 'tada.dataclass.mixin'
    _description = 'TADA ERP Dataclass Integration Mixin'
    
    # Company context for multi-company support
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company, index=True)
    
    # Metadata fields
    created_at = fields.Datetime(string='Created At', readonly=True, default=fields.Datetime.now)
    updated_at = fields.Datetime(string='Updated At', readonly=True, default=fields.Datetime.now)
    
    # SDK integration
    _dataclass_type: Type = None  # Override in concrete models
    _sdk_field_mapping: Dict[str, str] = {}  # Odoo field -> SDK field mapping
    
    def _is_enum_field(self, field_type) -> bool:
        """Check if a field type is an enum."""
        try:
            return isinstance(field_type, type) and issubclass(field_type, Enum)
        except TypeError:
            return False
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats using built-in datetime."""
        if not value:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Common datetime formats to try
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO format with microseconds and Z
                '%Y-%m-%dT%H:%M:%SZ',     # ISO format without microseconds
                '%Y-%m-%dT%H:%M:%S.%f',   # ISO format with microseconds, no Z
                '%Y-%m-%dT%H:%M:%S',      # ISO format without microseconds, no Z
                '%Y-%m-%d %H:%M:%S',      # Standard format
                '%Y-%m-%d',               # Date only
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            
            _logger.warning(f"Failed to parse datetime '{value}' with any known format")
            return None
        
        return None
    
    def _prepare_dataclass_data(self) -> Dict[str, Any]:
        """Prepare data for dataclass creation"""
        data = {}
        
        # Create reverse mapping for dataclass -> Odoo field lookup
        reverse_mapping = {v: k for k, v in self._sdk_field_mapping.items()}
        
        # Get all dataclass fields
        if self._dataclass_type:
            dc_fields = {f.name: f for f in dataclass_fields(self._dataclass_type)}
            
            for dc_field_name, dc_field in dc_fields.items():
                # Map dataclass field to Odoo field (reverse of the SDK mapping)
                odoo_field_name = reverse_mapping.get(dc_field_name, dc_field_name)
                
                if hasattr(self, odoo_field_name):
                    value = getattr(self, odoo_field_name)
                    
                    # Handle different field types
                    if isinstance(value, models.BaseModel):
                        # Many2one field
                        if value:
                            if hasattr(value, 'name'):
                                data[dc_field_name] = value.name
                            else:
                                data[dc_field_name] = str(value.id)
                        else:
                            data[dc_field_name] = None
                    elif self._is_enum_field(dc_field.type) and value:
                        # Handle enum fields - convert string to enum
                        try:
                            data[dc_field_name] = dc_field.type(value)
                        except (ValueError, TypeError):
                            _logger.warning(f"Invalid enum value '{value}' for field {dc_field_name}")
                            data[dc_field_name] = None
                    elif hasattr(dc_field.type, '__origin__') and dc_field.type.__origin__ is Union:
                        # Handle Optional fields
                        data[dc_field_name] = value
                    else:
                        data[dc_field_name] = value
                else:
                    # Set default value if field doesn't exist
                    if dc_field.default is not None:
                        data[dc_field_name] = dc_field.default
                    else:
                        data[dc_field_name] = None
        
        return data
    
    def to_dataclass(self):
        """Convert Odoo record to SDK dataclass instance."""
        if not self._dataclass_type:
            raise NotImplementedError("_dataclass_type must be defined in concrete model")
        
        data = self._prepare_dataclass_data()
        return self._dataclass_type(**data)
    
    @api.model
    def from_dataclass(self, dataclass_instance, company_id=None):
        """Create Odoo record from SDK dataclass instance (plain text storage)."""
        if not isinstance(dataclass_instance, self._dataclass_type):
            raise ValueError(f"Expected {self._dataclass_type.__name__}, got {type(dataclass_instance).__name__}")
        
        data = asdict(dataclass_instance)
        odoo_data = {}
        
        # Convert dataclass data to Odoo format
        for dc_field_name, value in data.items():
            odoo_field_name = self._sdk_field_mapping.get(dc_field_name, dc_field_name)
            
            # Skip list/relationship fields - they should be handled by specific models
            if isinstance(value, list):
                continue
            
            if isinstance(value, Enum):
                # Convert enum to string value
                odoo_data[odoo_field_name] = value.value
            elif odoo_field_name.endswith('_at') or 'date' in odoo_field_name.lower():
                # Handle datetime fields
                parsed_dt = self._parse_datetime(value)
                if parsed_dt:
                    odoo_data[odoo_field_name] = parsed_dt
                else:
                    odoo_data[odoo_field_name] = value
            else:
                odoo_data[odoo_field_name] = value
        
        # Set company
        if company_id:
            odoo_data['company_id'] = company_id
        elif not odoo_data.get('company_id'):
            odoo_data['company_id'] = self.env.company.id
        
        # Set timestamps
        odoo_data['created_at'] = fields.Datetime.now()
        odoo_data['updated_at'] = fields.Datetime.now()
        
        # Use create_or_update if available (for models with unique constraints)
        if hasattr(self, 'create_or_update'):
            return self.create_or_update(odoo_data)
        else:
            return self.create(odoo_data)
    
    def update_from_dataclass(self, dataclass_instance):
        """Update Odoo record from SDK dataclass instance (plain text storage)."""
        if not isinstance(dataclass_instance, self._dataclass_type):
            raise ValueError(f"Expected {self._dataclass_type.__name__}, got {type(dataclass_instance).__name__}")
        
        data = asdict(dataclass_instance)
        odoo_data = {}
        
        for dc_field_name, value in data.items():
            odoo_field_name = self._sdk_field_mapping.get(dc_field_name, dc_field_name)
            
            # Skip list/relationship fields - they should be handled by specific models
            if isinstance(value, list):
                continue
            
            if isinstance(value, Enum):
                # Convert enum to string value
                odoo_data[odoo_field_name] = value.value
            elif odoo_field_name.endswith('_at') or 'date' in odoo_field_name.lower():
                # Handle datetime fields
                parsed_dt = self._parse_datetime(value)
                if parsed_dt:
                    odoo_data[odoo_field_name] = parsed_dt
                else:
                    odoo_data[odoo_field_name] = value
            else:
                odoo_data[odoo_field_name] = value
        
        odoo_data['updated_at'] = fields.Datetime.now()
        self.write(odoo_data)
    
    def get_sdk_instance(self) -> Chain2GateSDK:
        """Get SDK instance configured for this company."""
        # Get API configuration from company settings
        company = self.company_id or self.env.company
        
        # Validate API configuration
        validate_api_configuration(company)
        
        base_url = company.tada_base_url or "https://chain2-api.chain2gate.it"
        
        # Log API configuration (without sensitive data)
        log_api_call(
            operation="SDK Instance Creation",
            company=company.name,
            base_url=base_url,
            has_api_key=bool(company.tada_api_key)
        )
        
        return Chain2GateSDK(
            api_key=company.tada_api_key,
            base_url=base_url
        )
    
    def _validate_company_access(self, operation="access"):
        """Validate that user can only access records from their company."""
        MultiCompanyValidator.validate_company_access(self, operation=operation)
    
    def _validate_company_consistency(self):
        """Validate that all records belong to the same company."""
        MultiCompanyValidator.validate_company_consistency(self)
    
    def _ensure_company_context(self, company_id=None):
        """Ensure records are accessed in the correct company context."""
        return MultiCompanyValidator.ensure_company_context(self, company_id)
    
    def _filter_by_company(self, company_id=None):
        """Filter records to only include those from the specified company."""
        return MultiCompanyValidator.filter_by_company(self, company_id)
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search to enforce company boundaries."""
        # Add company filter to search domain if not already present
        has_company_filter = any(
            isinstance(clause, (list, tuple)) and len(clause) >= 3 and clause[0] == 'company_id'
            for clause in (args or [])
        )
        
        if not has_company_filter:
            company_domain = [('company_id', '=', self.env.company.id)]
            if args:
                args = company_domain + args
            else:
                args = company_domain
        
        return super().search(args, offset=offset, limit=limit, order=order)
    
    @api.model
    def search_count(self, args, limit=None):
        """Override search_count to enforce company boundaries."""
        # Add company filter to search domain if not already present
        has_company_filter = any(
            isinstance(clause, (list, tuple)) and len(clause) >= 3 and clause[0] == 'company_id'
            for clause in (args or [])
        )
        
        if not has_company_filter:
            company_domain = [('company_id', '=', self.env.company.id)]
            if args:
                args = company_domain + args
            else:
                args = company_domain
        
        return super().search_count(args, limit=limit)
    
    def read(self, fields=None, load='_classic_read'):
        """Override read to validate company access."""
        self._validate_company_access("read")
        return super().read(fields=fields, load=load)
    
    def write(self, vals):
        """Override write to validate company access and update timestamp."""
        self._validate_company_access("write")
        
        # Validate company change attempts
        if 'company_id' in vals:
            new_company_id = vals['company_id']
            current_user_company = self.env.company.id
            
            # Allow setting company_id if it matches current user's company
            if new_company_id != current_user_company:
                # Check if user has access to the target company
                user_companies = self.env.user.company_ids.ids
                if new_company_id not in user_companies:
                    raise AccessError(
                        f"You cannot change records to company ID {new_company_id} "
                        f"because you don't have access to that company."
                    )
                
                # Log company change for audit
                for record in self:
                    old_company = record.company_id.name if record.company_id else "None"
                    new_company = self.env['res.company'].browse(new_company_id).name
                    _logger.info(
                        f"Company change: {record._name} ID {record.id} "
                        f"from '{old_company}' to '{new_company}' by user {self.env.user.name}"
                    )
        
        vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)
    
    def unlink(self):
        """Override unlink to validate company access."""
        self._validate_company_access("delete")
        return super().unlink()
    
    def copy(self, default=None):
        """Override copy to ensure company consistency."""
        self._validate_company_access("copy")
        
        # Ensure copied record belongs to current company
        if default is None:
            default = {}
        if 'company_id' not in default:
            default['company_id'] = self.env.company.id
        
        return super().copy(default=default)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure company consistency."""
        current_company_id = self.env.company.id
        
        for vals in vals_list:
            # Set company_id if not provided
            if 'company_id' not in vals:
                vals['company_id'] = current_company_id
            else:
                # Validate that user can create records for the specified company
                target_company_id = vals['company_id']
                if target_company_id != current_company_id:
                    user_companies = self.env.user.company_ids.ids
                    if target_company_id not in user_companies:
                        raise AccessError(
                            f"You cannot create records for company ID {target_company_id} "
                            f"because you don't have access to that company."
                        )
            
            # Set timestamps
            if 'created_at' not in vals:
                vals['created_at'] = fields.Datetime.now()
            if 'updated_at' not in vals:
                vals['updated_at'] = fields.Datetime.now()
        
        return super().create(vals_list)