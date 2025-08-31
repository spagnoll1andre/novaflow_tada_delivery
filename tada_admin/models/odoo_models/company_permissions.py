# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CompanyPermissions(models.Model):
    _name = 'tada_admin.company.permissions'
    _description = 'Company Permissions for TADA Features'
    _rec_name = 'company_id'
    _order = 'company_id'

    # Core fields
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        required=True, 
        ondelete='cascade',
        help='Company for which permissions are defined'
    )
    
    # Permission flags
    is_partner_energia = fields.Boolean(
        string='Partner Energia Access',
        default=False,
        help='Allow access to Partner Energia functionality'
    )
    has_configurazione_ammissibilita = fields.Boolean(
        string='Configurazione Ammissibilità Access',
        default=False,
        help='Allow access to Configurazione Ammissibilità functionality'
    )
    has_configurazione_associazione = fields.Boolean(
        string='Configurazione Associazione Access',
        default=False,
        help='Allow access to Configurazione Associazione functionality'
    )
    has_magazzino = fields.Boolean(
        string='Magazzino Access',
        default=False,
        help='Allow access to Magazzino functionality'
    )
    has_spedizione = fields.Boolean(
        string='Spedizione Access',
        default=False,
        help='Allow access to Spedizione functionality'
    )
    has_monitoraggio = fields.Boolean(
        string='Monitoraggio Access',
        default=True,
        help='Allow access to Monitoraggio functionality'
    )
    
    # Audit fields
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True,
        help='Date when permissions were created'
    )
    last_modified = fields.Datetime(
        string='Last Modified',
        default=fields.Datetime.now,
        readonly=True,
        help='Date when permissions were last modified'
    )
    modified_by = fields.Many2one(
        'res.users',
        string='Modified By',
        default=lambda self: self.env.user,
        readonly=True,
        help='User who last modified the permissions'
    )
    
    # SQL constraints
    _sql_constraints = [
        ('unique_company_permissions', 
         'unique(company_id)', 
         'Each company can only have one permissions record.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set audit fields"""
        now = fields.Datetime.now()
        user_id = self.env.user.id
        
        for vals in vals_list:
            vals['created_date'] = now
            vals['modified_by'] = user_id
            
        return super(CompanyPermissions, self).create(vals_list)

    def write(self, vals):
        """Override write to update audit fields"""
        vals['last_modified'] = fields.Datetime.now()
        vals['modified_by'] = self.env.user.id
        return super(CompanyPermissions, self).write(vals)

    @api.constrains('company_id')
    def _check_company_exists(self):
        """Validate that company exists and is active"""
        for record in self:
            if not record.company_id:
                raise ValidationError("Company is required for permissions.")
            if not record.company_id.active:
                raise ValidationError("Cannot create permissions for inactive company.")

    def get_company_permissions(self, company_id):
        """
        Get permissions for a specific company
        
        Args:
            company_id (int): ID of the company
            
        Returns:
            dict: Dictionary with permission flags
        """
        permission_record = self.search([('company_id', '=', company_id)], limit=1)
        
        if not permission_record:
            # Return default permissions if no record exists
            return {
                'is_partner_energia': False,
                'has_configurazione_ammissibilita': False,
                'has_configurazione_associazione': False,
                'has_magazzino': False,
                'has_spedizione': False,
                'has_monitoraggio': True,  # Default to True as per design
            }
        
        return {
            'is_partner_energia': permission_record.is_partner_energia,
            'has_configurazione_ammissibilita': permission_record.has_configurazione_ammissibilita,
            'has_configurazione_associazione': permission_record.has_configurazione_associazione,
            'has_magazzino': permission_record.has_magazzino,
            'has_spedizione': permission_record.has_spedizione,
            'has_monitoraggio': permission_record.has_monitoraggio,
        }

    def check_permission(self, company_id, permission_type):
        """
        Check if a company has a specific permission
        
        Args:
            company_id (int): ID of the company
            permission_type (str): Type of permission to check
            
        Returns:
            bool: True if company has permission, False otherwise
            
        Raises:
            ValidationError: If permission_type is invalid
        """
        valid_permissions = [
            'PARTNER_ENERGIA',
            'CONFIGURAZIONE_AMMISSIBILITA', 
            'CONFIGURAZIONE_ASSOCIAZIONE',
            'MAGAZZINO',
            'SPEDIZIONE',
            'MONITORAGGIO'
        ]
        if permission_type not in valid_permissions:
            raise ValidationError(f"Invalid permission type: {permission_type}")
        
        permissions = self.get_company_permissions(company_id)
        
        # Map permission types to field names
        permission_field_mapping = {
            'PARTNER_ENERGIA': 'is_partner_energia',
            'CONFIGURAZIONE_AMMISSIBILITA': 'has_configurazione_ammissibilita',
            'CONFIGURAZIONE_ASSOCIAZIONE': 'has_configurazione_associazione',
            'MAGAZZINO': 'has_magazzino',
            'SPEDIZIONE': 'has_spedizione',
            'MONITORAGGIO': 'has_monitoraggio'
        }
        
        permission_key = permission_field_mapping.get(permission_type)
        if not permission_key:
            raise ValidationError(f"No field mapping for permission type: {permission_type}")
        
        return permissions.get(permission_key, False)

    def set_company_permissions(self, company_id, permissions_dict):
        """
        Set permissions for a company (create or update)
        
        Args:
            company_id (int): ID of the company
            permissions_dict (dict): Dictionary with permission flags
            
        Returns:
            recordset: The created or updated permission record
        """
        existing_record = self.search([('company_id', '=', company_id)], limit=1)
        
        # Validate permission keys
        valid_keys = [
            'is_partner_energia',
            'has_configurazione_ammissibilita',
            'has_configurazione_associazione',
            'has_magazzino',
            'has_spedizione',
            'has_monitoraggio'
        ]
        for key in permissions_dict:
            if key not in valid_keys:
                raise ValidationError(f"Invalid permission key: {key}")
        
        if existing_record:
            # Update existing record
            existing_record.write(permissions_dict)
            return existing_record
        else:
            # Create new record
            vals = {'company_id': company_id}
            vals.update(permissions_dict)
            return self.create(vals)

    @api.model
    def get_companies_with_permission(self, permission_type):
        """
        Get all companies that have a specific permission
        
        Args:
            permission_type (str): Type of permission to check
            
        Returns:
            recordset: Companies with the specified permission
        """
        valid_permissions = [
            'PARTNER_ENERGIA',
            'CONFIGURAZIONE_AMMISSIBILITA', 
            'CONFIGURAZIONE_ASSOCIAZIONE',
            'MAGAZZINO',
            'SPEDIZIONE',
            'MONITORAGGIO'
        ]
        if permission_type not in valid_permissions:
            raise ValidationError(f"Invalid permission type: {permission_type}")
        
        # Map permission types to field names
        permission_field_mapping = {
            'PARTNER_ENERGIA': 'is_partner_energia',
            'CONFIGURAZIONE_AMMISSIBILITA': 'has_configurazione_ammissibilita',
            'CONFIGURAZIONE_ASSOCIAZIONE': 'has_configurazione_associazione',
            'MAGAZZINO': 'has_magazzino',
            'SPEDIZIONE': 'has_spedizione',
            'MONITORAGGIO': 'has_monitoraggio'
        }
        
        permission_field = permission_field_mapping.get(permission_type)
        if not permission_field:
            raise ValidationError(f"No field mapping for permission type: {permission_type}")
        
        domain = [(permission_field, '=', True)]
        
        permission_records = self.search(domain)
        return permission_records.mapped('company_id')