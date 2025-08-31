# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PODAuthorization(models.Model):
    _name = 'tada_admin.pod.authorization'
    _description = 'POD Authorization for Companies'
    _rec_name = 'display_name'
    _order = 'company_id, pod_code'

    # Core fields
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        ondelete='cascade',
        help='Company authorized to access this POD'
    )
    pod_code = fields.Char(
        string='POD Code',
        required=True,
        help='Unique POD identifier code'
    )
    pod_name = fields.Char(
        string='POD Name',
        help='Human readable POD name'
    )
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this POD authorization is currently active'
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=False,
        help='Computed display name for POD authorization'
    )

    # Chain2Gate sync fields
    chain2gate_id = fields.Char(
        string='Chain2Gate ID',
        help='External Chain2Gate identifier for this POD'
    )
    last_sync = fields.Datetime(
        string='Last Sync',
        help='Last synchronization timestamp with Chain2Gate'
    )

    # Audit fields
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True
    )
    last_modified = fields.Datetime(
        string='Last Modified',
        default=fields.Datetime.now,
        readonly=True
    )
    modified_by = fields.Many2one(
        'res.users',
        string='Modified By',
        default=lambda self: self.env.user,
        readonly=True
    )

    # SQL constraints
    _sql_constraints = [
        ('unique_company_pod', 
         'unique(company_id, pod_code)', 
         'POD can only be assigned to one company'),
        ('pod_code_not_empty',
         'check(length(trim(pod_code)) > 0)',
         'POD code cannot be empty')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to update audit fields"""
        now = fields.Datetime.now()
        user_id = self.env.user.id
        
        for vals in vals_list:
            vals['created_date'] = now
            vals['last_modified'] = now
            vals['modified_by'] = user_id
            
        return super(PODAuthorization, self).create(vals_list)

    def write(self, vals):
        """Override write to update audit fields"""
        vals['last_modified'] = fields.Datetime.now()
        vals['modified_by'] = self.env.user.id
        return super(PODAuthorization, self).write(vals)

    @api.constrains('pod_code')
    def _check_pod_code_format(self):
        """Validate POD code format"""
        for record in self:
            if record.pod_code:
                # Remove whitespace and check if empty
                pod_code = record.pod_code.strip()
                if not pod_code:
                    raise ValidationError("POD code cannot be empty or contain only whitespace")
                
                # Update the record with trimmed value
                if pod_code != record.pod_code:
                    record.pod_code = pod_code

    @api.constrains('company_id', 'pod_code')
    def _check_unique_company_pod(self):
        """Additional validation for company-POD uniqueness"""
        for record in self:
            if record.company_id and record.pod_code:
                existing = self.search([
                    ('company_id', '=', record.company_id.id),
                    ('pod_code', '=', record.pod_code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(
                        f"POD '{record.pod_code}' is already assigned to company '{record.company_id.name}'"
                    )

    def sync_with_chain2gate(self):
        """Sync POD data with Chain2Gate API"""
        # This method will be implemented when Chain2Gate integration is added
        # For now, just update the last_sync timestamp
        self.write({
            'last_sync': fields.Datetime.now()
        })
        return True

    def deactivate_pod(self):
        """Deactivate POD authorization"""
        self.write({'is_active': False})
        return True

    def activate_pod(self):
        """Activate POD authorization"""
        self.write({'is_active': True})
        return True

    @api.model
    def get_authorized_pods_for_company(self, company_id):
        """Get all active POD codes authorized for a specific company"""
        if not company_id:
            return []
        
        pods = self.search([
            ('company_id', '=', company_id),
            ('is_active', '=', True)
        ])
        return pods.mapped('pod_code')

    @api.model
    def is_pod_authorized_for_company(self, company_id, pod_code):
        """Check if a specific POD is authorized for a company"""
        if not company_id or not pod_code:
            return False
        
        authorization = self.search([
            ('company_id', '=', company_id),
            ('pod_code', '=', pod_code),
            ('is_active', '=', True)
        ], limit=1)
        
        return bool(authorization)

    @api.depends('pod_code', 'pod_name', 'company_id.name')
    def _compute_display_name(self):
        """Compute display name for POD Authorization records"""
        for record in self:
            name = record.pod_code or ''
            if record.pod_name:
                name += f" ({record.pod_name})"
            if record.company_id:
                name += f" - {record.company_id.name}"
            record.display_name = name