# -*- coding: utf-8 -*-
"""
Multi-company access validation utilities for TADA ERP.
"""

import logging
from typing import List, Optional, Union
from odoo import models
from odoo.exceptions import AccessError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class MultiCompanyValidator:
    """Multi-company access validation utilities."""
    
    @classmethod
    def validate_company_access(cls, records, user_company=None, operation="access"):
        """
        Validate that user can access records from their company only.
        
        Args:
            records: Odoo recordset to validate
            user_company: User's current company (optional, will use env.company)
            operation: Description of the operation for error messages
            
        Raises:
            AccessError: If user tries to access records from other companies
        """
        if not records:
            return
        
        # Get user's current company
        if user_company is None:
            user_company = records.env.company
        
        # Check each record
        invalid_records = []
        for record in records:
            if hasattr(record, 'company_id') and record.company_id:
                if record.company_id != user_company:
                    invalid_records.append(record)
        
        if invalid_records:
            # Create detailed error message
            record_details = []
            for record in invalid_records[:5]:  # Limit to first 5 for readability
                record_name = getattr(record, 'display_name', None) or \
                             getattr(record, 'name', None) or \
                             f"ID {record.id}"
                record_details.append(f"'{record_name}' (Company: {record.company_id.name})")
            
            if len(invalid_records) > 5:
                record_details.append(f"... and {len(invalid_records) - 5} more")
            
            raise AccessError(
                f"Access denied for {operation}. You cannot access records from other companies.\n\n"
                f"Your company: {user_company.name}\n"
                f"Attempted to access records from:\n" + "\n".join(f"• {detail}" for detail in record_details)
            )
    
    @classmethod
    def validate_company_consistency(cls, records, field_name='company_id'):
        """
        Validate that all records belong to the same company.
        
        Args:
            records: Odoo recordset to validate
            field_name: Name of the company field
            
        Raises:
            ValidationError: If records belong to different companies
        """
        if not records or len(records) <= 1:
            return
        
        companies = set()
        for record in records:
            if hasattr(record, field_name):
                company = getattr(record, field_name)
                if company:
                    companies.add(company.id)
        
        if len(companies) > 1:
            company_names = [records.env['res.company'].browse(cid).name for cid in companies]
            raise ValidationError(
                f"All records must belong to the same company. "
                f"Found records from companies: {', '.join(company_names)}"
            )
    
    @classmethod
    def ensure_company_context(cls, records, company_id=None):
        """
        Ensure records are accessed in the correct company context.
        
        Args:
            records: Odoo recordset
            company_id: Company ID to set in context (optional)
            
        Returns:
            Recordset with correct company context
        """
        if not records:
            return records
        
        if company_id is None:
            # Use the company from the first record
            first_record = records[0]
            if hasattr(first_record, 'company_id') and first_record.company_id:
                company_id = first_record.company_id.id
            else:
                company_id = records.env.company.id
        
        # Set company context
        return records.with_context(allowed_company_ids=[company_id])
    
    @classmethod
    def filter_by_company(cls, records, company_id=None, field_name='company_id'):
        """
        Filter records to only include those from the specified company.
        
        Args:
            records: Odoo recordset to filter
            company_id: Company ID to filter by (optional, uses env.company)
            field_name: Name of the company field
            
        Returns:
            Filtered recordset
        """
        if not records:
            return records
        
        if company_id is None:
            company_id = records.env.company.id
        
        return records.filtered(lambda r: getattr(r, field_name, False) and getattr(r, field_name).id == company_id)
    
    @classmethod
    def validate_fiscal_code_uniqueness_per_company(cls, model, fiscal_code, company_id, record_id=None):
        """
        Validate fiscal code uniqueness within company boundaries.
        
        Args:
            model: The Odoo model instance
            fiscal_code: The fiscal code to check
            company_id: The company ID
            record_id: Current record ID to exclude from search (optional)
            
        Raises:
            ValidationError: If fiscal code already exists in the company
        """
        if not fiscal_code or not company_id:
            return
        
        domain = [
            ('fiscal_code', '=', fiscal_code),
            ('company_id', '=', company_id)
        ]
        
        if record_id:
            domain.append(('id', '!=', record_id))
        
        existing = model.search(domain, limit=1)
        if existing:
            company_name = model.env['res.company'].browse(company_id).name
            existing_name = getattr(existing, 'display_name', None) or \
                           getattr(existing, 'name', None) or \
                           f"Record ID {existing.id}"
            
            raise ValidationError(
                f"Fiscal code '{fiscal_code}' already exists in company '{company_name}' "
                f"(used by: {existing_name}). Each fiscal code must be unique within a company."
            )
    
    @classmethod
    def validate_related_records_company(cls, main_record, related_records, relation_name):
        """
        Validate that related records belong to the same company as the main record.
        
        Args:
            main_record: The main record
            related_records: Related records to validate
            relation_name: Name of the relation for error messages
            
        Raises:
            ValidationError: If related records belong to different companies
        """
        if not main_record or not related_records:
            return
        
        main_company = getattr(main_record, 'company_id', None)
        if not main_company:
            return
        
        invalid_records = []
        for record in related_records:
            record_company = getattr(record, 'company_id', None)
            if record_company and record_company != main_company:
                invalid_records.append(record)
        
        if invalid_records:
            record_names = []
            for record in invalid_records[:3]:  # Limit for readability
                record_name = getattr(record, 'display_name', None) or \
                             getattr(record, 'name', None) or \
                             f"ID {record.id}"
                record_names.append(f"'{record_name}' ({record.company_id.name})")
            
            if len(invalid_records) > 3:
                record_names.append(f"... and {len(invalid_records) - 3} more")
            
            raise ValidationError(
                f"All {relation_name} must belong to the same company as the main record.\n\n"
                f"Main record company: {main_company.name}\n"
                f"Invalid {relation_name}:\n" + "\n".join(f"• {name}" for name in record_names)
            )


def validate_company_access(records, operation="access"):
    """
    Decorator-friendly function to validate company access.
    
    Args:
        records: Odoo recordset to validate
        operation: Description of the operation for error messages
    """
    MultiCompanyValidator.validate_company_access(records, operation=operation)


def ensure_company_isolation(func):
    """
    Decorator to ensure company isolation for model methods.
    
    This decorator automatically validates that the user can only access
    records from their current company.
    """
    def wrapper(self, *args, **kwargs):
        # Validate company access for self (if it's a recordset)
        if hasattr(self, '_name') and hasattr(self, 'company_id'):
            MultiCompanyValidator.validate_company_access(self, operation=func.__name__)
        
        # Execute the original method
        result = func(self, *args, **kwargs)
        
        # Validate company access for result (if it's a recordset)
        if hasattr(result, '_name') and hasattr(result, 'company_id'):
            MultiCompanyValidator.validate_company_access(result, operation=f"{func.__name__} result")
        
        return result
    
    return wrapper


class MultiCompanyMixin(models.AbstractModel):
    """
    Abstract mixin that provides multi-company validation methods.
    
    This mixin can be inherited by models that need enhanced multi-company validation.
    """
    
    _name = 'tada.multicompany.mixin'
    _description = 'Multi-Company Validation Mixin'
    
    def _validate_company_access(self, operation="access"):
        """Validate company access for this recordset."""
        MultiCompanyValidator.validate_company_access(self, operation=operation)
    
    def _validate_company_consistency(self):
        """Validate that all records in this recordset belong to the same company."""
        MultiCompanyValidator.validate_company_consistency(self)
    
    def _ensure_company_context(self, company_id=None):
        """Ensure records are accessed in the correct company context."""
        return MultiCompanyValidator.ensure_company_context(self, company_id)
    
    def _filter_by_company(self, company_id=None):
        """Filter records to only include those from the specified company."""
        return MultiCompanyValidator.filter_by_company(self, company_id)
    
    def _validate_related_records_company(self, related_records, relation_name):
        """Validate that related records belong to the same company."""
        for record in self:
            MultiCompanyValidator.validate_related_records_company(
                record, related_records, relation_name
            )
    
    def read(self, fields=None, load='_classic_read'):
        """Override read to validate company access."""
        self._validate_company_access("read")
        return super().read(fields=fields, load=load)
    
    def write(self, vals):
        """Override write to validate company access."""
        self._validate_company_access("write")
        
        # If company_id is being changed, validate the change
        if 'company_id' in vals:
            new_company_id = vals['company_id']
            current_user_company = self.env.company.id
            
            if new_company_id != current_user_company:
                raise AccessError(
                    f"You cannot change the company of records to a different company. "
                    f"Your current company: {self.env.company.name}"
                )
        
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