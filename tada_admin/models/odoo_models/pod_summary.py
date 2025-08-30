# -*- coding: utf-8 -*-
"""
POD Summary Model - Comprehensive POD information aggregator

This model provides a unified view of all information related to a specific POD (Point of Delivery).
A POD represents a unique electricity meter identifier that remains constant even when customers change.
Each POD Summary record represents a unique combination of (POD, CUSTOMER).
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class TadaPodSummary(models.Model):
    """
    POD Summary Model - Comprehensive view of POD-related information.
    
    This model serves as a central hub for all information related to a specific POD,
    including customer details, device information, and request history.
    
    Key Features:
    - Unique POD + Customer combination tracking
    - Aggregated device information for the POD
    - Complete request history (admissibility, association, disassociation)
    - Real-time status computation
    - Company-based authorization and filtering
    """
    
    _name = 'tada_admin.pod.summary'
    _description = 'POD Summary - Comprehensive POD Information'
    _rec_name = 'display_name'
    _order = 'pod_code, customer_fiscal_code, last_activity_date desc'
    
    # Core POD Information
    pod_code = fields.Char(
        string='POD Code', 
        required=True, 
        index=True,
        help='Point of Delivery identifier - unique electricity meter ID'
    )
    
    # Customer Information
    customer_id = fields.Many2one(
        'tada.customer', 
        string='Customer', 
        required=True,
        ondelete='cascade',
        help='Associated customer record'
    )
    customer_fiscal_code = fields.Char(
        string='Customer Fiscal Code',
        related='customer_id.fiscal_code',
        store=True,
        index=True,
        help='Customer fiscal code for quick filtering'
    )
    customer_name = fields.Char(
        string='Customer Name',
        compute='_compute_customer_info',
        store=True,
        help='Customer display name'
    )
    customer_email = fields.Char(
        string='Customer Email',
        related='customer_id.email',
        store=True,
        help='Customer email address'
    )
    customer_user_type = fields.Selection(
        related='customer_id.user_type',
        store=True,
        help='Customer type (Prosumer/Consumer)'
    )
    
    # POD Status and Activity
    pod_status = fields.Selection([
        ('customer_created', 'Customer Created'),
        # Admissibility statuses (Chain2Gate API: PENDING | AWAITING | ADMISSIBLE | NOT_ADMISSIBLE | REFUSED)
        ('admissibility_pending', 'Admissibility Pending'),
        ('admissibility_awaiting', 'Admissibility Awaiting'),
        ('admissibility_admissible', 'Admissibility Admissible'),
        ('admissibility_not_admissible', 'Admissibility Not Admissible'),
        ('admissibility_refused', 'Admissibility Refused'),
        # Shipping statuses
        ('shipping_requested', 'Shipping Requested'),
        ('shipping_dispatched', 'Shipping Dispatched'),
        ('shipping_failed', 'Shipping Failed'),
        ('shipping_delivered', 'Shipping Delivered'),
        # Association statuses (Chain2Gate API: PENDING | AWAITING | ASSOCIATED | TAKEN_IN_CHARGE | REFUSED)
        ('association_pending', 'Association Pending'),
        ('association_awaiting', 'Association Awaiting'),
        ('association_associated', 'Association Associated'),
        ('association_taken_in_charge', 'Association Taken in Charge'),
        ('association_refused', 'Association Refused'),
        # Dissociation statuses (Chain2Gate API: PENDING | AWAITING | DISASSOCIATED)
        ('dissociation_pending', 'Dissociation Pending'),
        ('dissociation_awaiting', 'Dissociation Awaiting'),
        ('dissociation_disassociated', 'Dissociation Disassociated'),
        ('customer_deleted', 'Customer Deleted')
    ], string='POD Status', required=True, default='customer_created', index=True,
       help='Current status of the customer in the device lifecycle process')
    
    has_active_associations = fields.Boolean(
        string='Has Active Associations',
        default=False,
        help='Whether POD has active device associations'
    )
    
    last_activity_date = fields.Datetime(
        string='Last Activity',
        compute='_compute_activity_info',
        store=True,
        index=True,
        help='Date of most recent activity (request, device update, etc.)'
    )
    
    # Device Information (aggregated)
    device_count = fields.Integer(
        string='Device Count',
        compute='_compute_device_info',
        store=True,
        help='Number of devices associated with this POD'
    )
    
    device_ids = fields.Many2many(
        'tada.device',
        'pod_summary_device_rel',
        'pod_summary_id',
        'device_id',
        string='Associated Devices',
        compute='_compute_device_info',
        store=True,
        help='Devices associated with this POD'
    )
    
    primary_device_id = fields.Many2one(
        'tada.device',
        string='Primary Device',
        compute='_compute_device_info',
        store=True,
        help='Primary device for this POD'
    )
    
    device_types = fields.Char(
        string='Device Types',
        compute='_compute_device_info',
        store=True,
        help='Comma-separated list of device types'
    )
    
    # Request Information (aggregated)
    admissibility_request_ids = fields.Many2many(
        'tada.admissibility.request',
        'pod_summary_admissibility_rel',
        'pod_summary_id',
        'admissibility_request_id',
        string='Admissibility Requests',
        compute='_compute_request_relations',
        store=True,
        help='Admissibility requests for this POD and customer'
    )
    
    association_request_ids = fields.Many2many(
        'tada.association.request',
        'pod_summary_association_rel',
        'pod_summary_id',
        'association_request_id',
        string='Association Requests',
        compute='_compute_request_relations',
        store=True,
        help='Association requests for this POD and customer'
    )
    
    disassociation_request_ids = fields.Many2many(
        'tada.disassociation.request',
        'pod_summary_disassociation_rel',
        'pod_summary_id',
        'disassociation_request_id',
        string='Disassociation Requests',
        compute='_compute_request_relations',
        store=True,
        help='Disassociation requests for this POD and customer'
    )
    
    # Request Counts
    admissibility_count = fields.Integer(
        string='Admissibility Count',
        compute='_compute_request_counts',
        store=True
    )
    association_count = fields.Integer(
        string='Association Count',
        compute='_compute_request_counts',
        store=True
    )
    disassociation_count = fields.Integer(
        string='Disassociation Count',
        compute='_compute_request_counts',
        store=True
    )
    
    # Latest Request Information
    latest_request_type = fields.Char(
        string='Latest Request Type',
        compute='_compute_latest_request_info',
        store=True,
        help='Type of the most recent request'
    )
    latest_request_status = fields.Char(
        string='Latest Request Status',
        compute='_compute_latest_request_info',
        store=True,
        help='Status of the most recent request'
    )
    latest_request_date = fields.Datetime(
        string='Latest Request Date',
        compute='_compute_latest_request_info',
        store=True,
        help='Date of the most recent request'
    )
    
    # Display and Computed Fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Human-readable identifier for this POD summary'
    )
    
    # Metadata
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help='Company that owns this POD data'
    )
    
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        help='Record creation timestamp'
    )
    
    updated_at = fields.Datetime(
        string='Updated At',
        default=fields.Datetime.now,
        help='Record last update timestamp'
    )
    
    # Constraints
    _sql_constraints = [
        ('pod_customer_company_unique', 
         'UNIQUE(pod_code, customer_id, company_id)', 
         'POD + Customer combination must be unique per company!'),
    ]
    
    @api.depends('customer_id.first_name', 'customer_id.last_name', 'customer_id.display_name')
    def _compute_customer_info(self):
        """Compute customer information fields."""
        for record in self:
            if record.customer_id:
                record.customer_name = record.customer_id.display_name
            else:
                record.customer_name = ''
    
    @api.depends('pod_code', 'customer_fiscal_code', 'company_id')
    def _compute_request_relations(self):
        """Compute request relationships based on POD code and customer fiscal code."""
        for record in self:
            if not record.pod_code or not record.customer_fiscal_code:
                record.admissibility_request_ids = [(5, 0, 0)]
                record.association_request_ids = [(5, 0, 0)]
                record.disassociation_request_ids = [(5, 0, 0)]
                continue
            
            # Find admissibility requests
            admissibility_requests = self.env['tada.admissibility.request'].search([
                ('pod', '=', record.pod_code),
                ('fiscal_code', '=', record.customer_fiscal_code),
                ('company_id', '=', record.company_id.id)
            ])
            record.admissibility_request_ids = [(6, 0, admissibility_requests.ids)]
            
            # Find association requests
            association_requests = self.env['tada.association.request'].search([
                ('pod', '=', record.pod_code),
                ('fiscal_code', '=', record.customer_fiscal_code),
                ('company_id', '=', record.company_id.id)
            ])
            record.association_request_ids = [(6, 0, association_requests.ids)]
            
            # Find disassociation requests
            disassociation_requests = self.env['tada.disassociation.request'].search([
                ('pod', '=', record.pod_code),
                ('fiscal_code', '=', record.customer_fiscal_code),
                ('company_id', '=', record.company_id.id)
            ])
            record.disassociation_request_ids = [(6, 0, disassociation_requests.ids)]
    
    @api.model
    def _recompute_pod_summaries_for_request(self, pod_code, fiscal_code, company_id):
        """Helper method to trigger recomputation when request records change."""
        if pod_code and fiscal_code and company_id:
            pod_summaries = self.search([
                ('pod_code', '=', pod_code),
                ('customer_fiscal_code', '=', fiscal_code),
                ('company_id', '=', company_id)
            ])
            if pod_summaries:
                # Update status from requests and trigger recomputation
                for pod_summary in pod_summaries:
                    pod_summary.update_status_from_requests()
                # Also update the timestamp to trigger other computed fields
                pod_summaries.write({'updated_at': fields.Datetime.now()})
    
    # Permission methods based on status progression
    @api.depends('pod_status')
    def _compute_permissions(self):
        """Compute what actions are allowed based on current status"""
        for record in self:
            # Can request admissibility if customer is created or admissibility was refused/not_admissible
            record.can_request_admissibility = record.pod_status in [
                'customer_created', 'admissibility_refused', 'admissibility_not_admissible'
            ]
            
            # Can request shipping if admissibility is admissible or shipping failed
            record.can_request_shipping = record.pod_status in [
                'admissibility_admissible', 'shipping_failed'
            ]
            
            # Can request association if shipping is delivered or association was refused
            record.can_request_association = record.pod_status in [
                'shipping_delivered', 'association_refused'
            ]
            
            # Can request dissociation if association is associated/taken_in_charge
            record.can_request_dissociation = record.pod_status in [
                'association_associated', 'association_taken_in_charge'
            ]
    
    # Permission fields
    can_request_admissibility = fields.Boolean(
        string='Can Request Admissibility',
        compute='_compute_permissions',
        help='True if admissibility request can be made'
    )
    
    can_request_shipping = fields.Boolean(
        string='Can Request Shipping',
        compute='_compute_permissions',
        help='True if shipping request can be made'
    )
    
    can_request_association = fields.Boolean(
        string='Can Request Association',
        compute='_compute_permissions',
        help='True if association request can be made'
    )
    
    can_request_dissociation = fields.Boolean(
        string='Can Request Dissociation',
        compute='_compute_permissions',
        help='True if dissociation request can be made'
    )
    
    def can_transition_to_status(self, new_status):
        """
        Check if POD can transition to the given status
        Returns True if transition is allowed, False otherwise
        """
        current_status = self.pod_status
        
        # Define allowed transitions based on the old file logic
        allowed_transitions = {
            'customer_created': ['admissibility_pending', 'customer_deleted'],
            # Admissibility flow
            'admissibility_pending': ['admissibility_awaiting', 'admissibility_admissible', 'admissibility_not_admissible', 'admissibility_refused', 'customer_deleted'],
            'admissibility_awaiting': ['admissibility_admissible', 'admissibility_not_admissible', 'admissibility_refused', 'customer_deleted'],
            'admissibility_admissible': ['shipping_requested', 'customer_deleted'],
            'admissibility_not_admissible': ['admissibility_pending', 'customer_deleted'],
            'admissibility_refused': ['admissibility_pending', 'customer_deleted'],
            # Shipping flow
            'shipping_requested': ['shipping_dispatched', 'shipping_failed', 'customer_deleted'],
            'shipping_dispatched': ['shipping_delivered', 'shipping_failed', 'customer_deleted'],
            'shipping_failed': ['shipping_requested', 'customer_deleted'],
            'shipping_delivered': ['association_pending', 'customer_deleted'],
            # Association flow
            'association_pending': ['association_awaiting', 'association_associated', 'association_taken_in_charge', 'association_refused', 'customer_deleted'],
            'association_awaiting': ['association_associated', 'association_taken_in_charge', 'association_refused', 'customer_deleted'],
            'association_associated': ['dissociation_pending', 'customer_deleted'],
            'association_taken_in_charge': ['dissociation_pending', 'customer_deleted'],
            'association_refused': ['association_pending', 'customer_deleted'],
            # Dissociation flow
            'dissociation_pending': ['dissociation_awaiting', 'dissociation_disassociated', 'customer_deleted'],
            'dissociation_awaiting': ['dissociation_disassociated', 'customer_deleted'],
            'dissociation_disassociated': ['customer_deleted'],
            'customer_deleted': []  # No transitions allowed from deleted state
        }
        
        return new_status in allowed_transitions.get(current_status, [])
    
    def get_next_possible_statuses(self):
        """Get list of possible next statuses for this POD"""
        current_status = self.pod_status
        
        allowed_transitions = {
            'customer_created': ['admissibility_pending', 'customer_deleted'],
            # Admissibility flow
            'admissibility_pending': ['admissibility_awaiting', 'admissibility_admissible', 'admissibility_not_admissible', 'admissibility_refused', 'customer_deleted'],
            'admissibility_awaiting': ['admissibility_admissible', 'admissibility_not_admissible', 'admissibility_refused', 'customer_deleted'],
            'admissibility_admissible': ['shipping_requested', 'customer_deleted'],
            'admissibility_not_admissible': ['admissibility_pending', 'customer_deleted'],
            'admissibility_refused': ['admissibility_pending', 'customer_deleted'],
            # Shipping flow
            'shipping_requested': ['shipping_dispatched', 'shipping_failed', 'customer_deleted'],
            'shipping_dispatched': ['shipping_delivered', 'shipping_failed', 'customer_deleted'],
            'shipping_failed': ['shipping_requested', 'customer_deleted'],
            'shipping_delivered': ['association_pending', 'customer_deleted'],
            # Association flow
            'association_pending': ['association_awaiting', 'association_associated', 'association_taken_in_charge', 'association_refused', 'customer_deleted'],
            'association_awaiting': ['association_associated', 'association_taken_in_charge', 'association_refused', 'customer_deleted'],
            'association_associated': ['dissociation_pending', 'customer_deleted'],
            'association_taken_in_charge': ['dissociation_pending', 'customer_deleted'],
            'association_refused': ['association_pending', 'customer_deleted'],
            # Dissociation flow
            'dissociation_pending': ['dissociation_awaiting', 'dissociation_disassociated', 'customer_deleted'],
            'dissociation_awaiting': ['dissociation_disassociated', 'customer_deleted'],
            'dissociation_disassociated': ['customer_deleted'],
            'customer_deleted': []
        }
        
        return allowed_transitions.get(current_status, [])
    
    def update_status_from_requests(self):
        """
        Update POD status based on the status of related requests.
        This method is called automatically when request statuses change.
        """
        self.ensure_one()
        
        old_status = self.pod_status
        
        # Update the status using the computation logic
        self._update_pod_status()
        
        # Log status changes for debugging
        if old_status != self.pod_status:
            _logger.info(
                f"POD Summary {self.display_name} - Status updated from {old_status} to {self.pod_status}"
            )
        
    
    @api.model
    def update_all_pod_statuses(self):
        """
        Batch update all POD statuses based on their requests.
        This can be called from a cron job.
        """
        active_pods = self.search([('pod_status', '!=', 'customer_deleted')])
        updated_count = 0
        
        for pod in active_pods:
            old_status = pod.pod_status
            pod.update_status_from_requests()
            if pod.pod_status != old_status:
                updated_count += 1
                _logger.info(
                    f"Batch update: POD {pod.display_name} status changed from {old_status} to {pod.pod_status}"
                )
        
        _logger.info(
            f"Batch POD status update completed: {updated_count} PODs updated out of {len(active_pods)} total"
        )
        return updated_count
    
    @api.depends('pod_code', 'customer_name')
    def _compute_display_name(self):
        """Compute display name for better UX."""
        for record in self:
            if record.customer_name:
                record.display_name = f"{record.pod_code} - {record.customer_name}"
            else:
                record.display_name = record.pod_code or 'POD Summary'
    
    def _update_pod_status(self):
        """
        Compute POD status based on the latest request status in the lifecycle.
        Status progression follows: Customer Created -> Admissibility -> Shipping -> Association -> Dissociation
        """
        for record in self:
            if not record.pod_code or not record.customer_fiscal_code:
                record.pod_status = 'customer_created'
                record.has_active_associations = False
                continue
            
            # Find all request types directly from database, ordered by creation date
            admissibility_requests = self.env['tada.admissibility.request'].search([
                ('pod', '=', record.pod_code),
                ('fiscal_code', '=', record.customer_fiscal_code),
                ('company_id', '=', record.company_id.id)
            ], order='created_at desc')
            
            association_requests = self.env['tada.association.request'].search([
                ('pod', '=', record.pod_code),
                ('fiscal_code', '=', record.customer_fiscal_code),
                ('company_id', '=', record.company_id.id)
            ], order='created_at desc')
            
            disassociation_requests = self.env['tada.disassociation.request'].search([
                ('pod', '=', record.pod_code),
                ('fiscal_code', '=', record.customer_fiscal_code),
                ('company_id', '=', record.company_id.id)
            ], order='created_at desc')
            
            # Determine status based on the progression and latest request statuses
            new_status = 'customer_created'
            
            # Check dissociation requests first (highest priority - end of lifecycle)
            if disassociation_requests:
                latest_disassoc = disassociation_requests[0]
                if latest_disassoc.status == 'DISASSOCIATED':
                    new_status = 'dissociation_disassociated'
                elif latest_disassoc.status == 'AWAITING':
                    new_status = 'dissociation_awaiting'
                elif latest_disassoc.status == 'PENDING':
                    new_status = 'dissociation_pending'
                else:
                    # If dissociation exists but status is unknown, check association
                    new_status = record._get_association_status(association_requests)
            
            # Check association requests (middle of lifecycle)
            elif association_requests:
                new_status = record._get_association_status(association_requests)
            
            # Check admissibility requests (beginning of lifecycle)
            elif admissibility_requests:
                latest_admiss = admissibility_requests[0]
                if latest_admiss.status == 'ADMISSIBLE':
                    new_status = 'admissibility_admissible'
                elif latest_admiss.status == 'AWAITING':
                    new_status = 'admissibility_awaiting'
                elif latest_admiss.status == 'NOT_ADMISSIBLE':
                    new_status = 'admissibility_not_admissible'
                elif latest_admiss.status == 'REFUSED':
                    new_status = 'admissibility_refused'
                elif latest_admiss.status == 'PENDING':
                    new_status = 'admissibility_pending'
            
            # Set has_active_associations based on association status
            has_active = new_status in [
                'association_associated', 
                'association_taken_in_charge'
            ]
            
            # Write the values to the database
            record.write({
                'pod_status': new_status,
                'has_active_associations': has_active
            })
    
    def _get_association_status(self, association_requests):
        """Helper method to determine association status"""
        if not association_requests:
            return 'customer_created'
        
        latest_assoc = association_requests[0]
        if latest_assoc.status == 'ASSOCIATED':
            return 'association_associated'
        elif latest_assoc.status == 'TAKEN_IN_CHARGE':
            return 'association_taken_in_charge'
        elif latest_assoc.status == 'AWAITING':
            return 'association_awaiting'
        elif latest_assoc.status == 'REFUSED':
            return 'association_refused'
        elif latest_assoc.status == 'PENDING':
            return 'association_pending'
        else:
            return 'association_pending'
    
    def _get_shipping_status(self):
        """
        Helper method to determine shipping status.
        This is a mock implementation for future shipping integration.
        """
        # TODO: Implement when shipping models are added
        # For now, check if admissibility is admissible and assume shipping delivered
        if self.pod_status == 'admissibility_admissible':
            # Mock: assume shipping is delivered after admissibility is approved
            return 'shipping_delivered'
        return None
    
    # Mock shipping action methods (for future implementation)
    def action_request_shipping(self):
        """Mock method to request shipping"""
        if self.can_request_shipping:
            # TODO: Implement actual shipping request logic
            _logger.info(f"Shipping requested for POD {self.pod_code}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Shipping request initiated for POD {self.pod_code}',
                    'type': 'info',
                }
            }
        else:
            raise UserError("Shipping cannot be requested in current status")
    
    def action_mark_shipping_delivered(self):
        """Mock method to mark shipping as delivered"""
        if self.pod_status in ['shipping_requested', 'shipping_dispatched']:
            # TODO: Implement actual shipping delivery logic
            _logger.info(f"Shipping marked as delivered for POD {self.pod_code}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Shipping marked as delivered for POD {self.pod_code}',
                    'type': 'success',
                }
            }
        else:
            raise UserError("Shipping delivery can only be marked from requested/dispatched status")
    
    @api.depends('pod_code', 'customer_fiscal_code', 'company_id')
    def _compute_device_info(self):
        """Compute device information for this POD."""
        for record in self:
            if not record.pod_code:
                record.device_count = 0
                record.device_ids = [(5, 0, 0)]  # Clear all
                record.primary_device_id = False
                record.device_types = ''
                continue
            
            # Find devices associated with this POD
            devices = self.env['tada.device'].search([
                ('company_id', '=', record.company_id.id),
                '|', '|', '|', '|',
                ('m1', '=', record.pod_code),
                ('m2', '=', record.pod_code),
                ('m2_2', '=', record.pod_code),
                ('m2_3', '=', record.pod_code),
                ('m2_4', '=', record.pod_code)
            ])
            
            record.device_count = len(devices)
            record.device_ids = [(6, 0, devices.ids)]
            
            # Set primary device (first active device, or first device if none active)
            active_devices = devices.filtered('active')
            record.primary_device_id = active_devices[0] if active_devices else (devices[0] if devices else False)
            
            # Collect device types
            device_types = list(set(devices.mapped('type_name')))
            record.device_types = ', '.join(filter(None, device_types))
    
    @api.depends('admissibility_request_ids', 'association_request_ids', 'disassociation_request_ids')
    def _compute_request_counts(self):
        """Compute request counts."""
        for record in self:
            record.admissibility_count = len(record.admissibility_request_ids)
            record.association_count = len(record.association_request_ids)
            record.disassociation_count = len(record.disassociation_request_ids)
    
    @api.depends('admissibility_request_ids.created_at', 'association_request_ids.created_at', 
                 'disassociation_request_ids.created_at', 'device_ids.updated_at')
    def _compute_latest_request_info(self):
        """Compute information about the latest request."""
        for record in self:
            all_requests = []
            
            # Collect all requests with their info
            for req in record.admissibility_request_ids:
                if req.created_at:
                    all_requests.append({
                        'date': req.created_at,
                        'type': 'Admissibility',
                        'status': req.status
                    })
            
            for req in record.association_request_ids:
                if req.created_at:
                    all_requests.append({
                        'date': req.created_at,
                        'type': 'Association',
                        'status': req.status
                    })
            
            for req in record.disassociation_request_ids:
                if req.created_at:
                    all_requests.append({
                        'date': req.created_at,
                        'type': 'Disassociation',
                        'status': req.status
                    })
            
            if all_requests:
                # Sort by date and get the latest
                latest = max(all_requests, key=lambda x: x['date'])
                record.latest_request_type = latest['type']
                record.latest_request_status = latest['status']
                record.latest_request_date = latest['date']
            else:
                record.latest_request_type = ''
                record.latest_request_status = ''
                record.latest_request_date = False
    
    @api.depends('latest_request_date', 'device_ids.updated_at')
    def _compute_activity_info(self):
        """Compute last activity information."""
        for record in self:
            activity_dates = []
            
            if record.latest_request_date:
                activity_dates.append(record.latest_request_date)
            
            # Include device update dates
            for device in record.device_ids:
                if device.updated_at:
                    activity_dates.append(device.updated_at)
            
            record.last_activity_date = max(activity_dates) if activity_dates else record.created_at
    
    @api.model
    def create_or_update_pod_summary(self, pod_code, customer_id, company_id=None):
        """
        Create or update POD summary for a specific POD + Customer combination.
        
        Args:
            pod_code (str): POD identifier
            customer_id (int): Customer record ID
            company_id (int, optional): Company ID
            
        Returns:
            recordset: POD summary record
        """
        if not company_id:
            company_id = self.env.company.id
        
        # Validate authorization
        auth_service = self.env['tada_admin.authorization.service']
        try:
            auth_service.validate_pod_access(company_id, [pod_code])
        except Exception as e:
            _logger.warning("POD access validation failed for %s: %s", pod_code, str(e))
            # Continue anyway for internal operations
        
        # Find existing record
        existing = self.search([
            ('pod_code', '=', pod_code),
            ('customer_id', '=', customer_id),
            ('company_id', '=', company_id)
        ], limit=1)
        
        if existing:
            # Update timestamp to trigger recomputation
            existing.write({'updated_at': fields.Datetime.now()})
            return existing
        else:
            # Create new record
            return self.create({
                'pod_code': pod_code,
                'customer_id': customer_id,
                'company_id': company_id
            })
    
    @api.model
    def sync_pod_summaries(self, company_id=None):
        """
        Synchronize POD summaries based on existing association requests.
        
        This method creates POD summary records for all unique POD + Customer
        combinations found in association requests.
        
        Args:
            company_id (int, optional): Company ID to sync for
            
        Returns:
            dict: Sync results
        """
        if not company_id:
            company_id = self.env.company.id
        
        try:
            # Validate company authorization
            auth_service = self.env['tada_admin.authorization.service']
            auth_service.check_company_permission(company_id, 'PARTNER_ENERGIA')
            
            # Get all association requests for the company
            association_requests = self.env['tada.association.request'].search([
                ('company_id', '=', company_id),
                ('pod', '!=', False),
                ('fiscal_code', '!=', False)
            ])
            
            created_count = 0
            updated_count = 0
            error_count = 0
            
            # Group by POD + fiscal_code combination
            pod_customer_combinations = {}
            for req in association_requests:
                key = (req.pod, req.fiscal_code)
                if key not in pod_customer_combinations:
                    pod_customer_combinations[key] = req
            
            for (pod_code, fiscal_code), req in pod_customer_combinations.items():
                try:
                    # Find or create customer
                    customer = self.env['tada.customer'].search([
                        ('fiscal_code', '=', fiscal_code),
                        ('company_id', '=', company_id)
                    ], limit=1)
                    
                    if not customer:
                        # Create customer if not exists
                        customer = self.env['tada.customer'].create({
                            'fiscal_code': fiscal_code,
                            'first_name': req.first_name,
                            'last_name': req.last_name,
                            'email': req.email,
                            'user_type': req.user_type,
                            'company_id': company_id
                        })
                    
                    # Create or update POD summary
                    existing = self.search([
                        ('pod_code', '=', pod_code),
                        ('customer_id', '=', customer.id),
                        ('company_id', '=', company_id)
                    ], limit=1)
                    
                    if existing:
                        existing.write({'updated_at': fields.Datetime.now()})
                        updated_count += 1
                    else:
                        self.create({
                            'pod_code': pod_code,
                            'customer_id': customer.id,
                            'company_id': company_id
                        })
                        created_count += 1
                        
                except Exception as e:
                    _logger.error("Error syncing POD summary for %s + %s: %s", pod_code, fiscal_code, str(e))
                    error_count += 1
            
            return {
                'created': created_count,
                'updated': updated_count,
                'errors': error_count,
                'total_combinations': len(pod_customer_combinations)
            }
            
        except Exception as e:
            _logger.error("Error syncing POD summaries: %s", str(e))
            raise UserError(_("Failed to sync POD summaries: {}").format(str(e)))
    
    @api.model
    def populate_from_all_requests(self, company_id=None):
        """
        Populate POD summaries from all types of requests (comprehensive method).
        
        This method creates POD summary records for all unique POD + Customer
        combinations found in any type of request (admissibility, association, disassociation).
        
        Args:
            company_id (int, optional): Company ID to sync for
            
        Returns:
            dict: Action result for UI notification
        """
        if not company_id:
            company_id = self.env.company.id
        
        try:
            # Get all request types
            admissibility_requests = self.env['tada.admissibility.request'].search([
                ('company_id', '=', company_id),
                ('pod', '!=', False),
                ('fiscal_code', '!=', False)
            ])
            
            association_requests = self.env['tada.association.request'].search([
                ('company_id', '=', company_id),
                ('pod', '!=', False),
                ('fiscal_code', '!=', False)
            ])
            
            disassociation_requests = self.env['tada.disassociation.request'].search([
                ('company_id', '=', company_id),
                ('pod', '!=', False),
                ('fiscal_code', '!=', False)
            ])
            
            # Collect all unique POD + fiscal_code combinations
            pod_customer_combinations = {}
            
            # From admissibility requests
            for req in admissibility_requests:
                key = (req.pod, req.fiscal_code)
                if key not in pod_customer_combinations:
                    pod_customer_combinations[key] = {
                        'pod': req.pod,
                        'fiscal_code': req.fiscal_code,
                        'first_name': getattr(req, 'first_name', ''),
                        'last_name': getattr(req, 'last_name', ''),
                        'email': getattr(req, 'email', ''),
                        'user_type': getattr(req, 'user_type', 'CONSUMER'),
                        'source': 'admissibility'
                    }
            
            # From association requests (prefer these as they have more complete data)
            for req in association_requests:
                key = (req.pod, req.fiscal_code)
                pod_customer_combinations[key] = {
                    'pod': req.pod,
                    'fiscal_code': req.fiscal_code,
                    'first_name': req.first_name or '',
                    'last_name': req.last_name or '',
                    'email': req.email or '',
                    'user_type': req.user_type or 'CONSUMER',
                    'source': 'association'
                }
            
            # From disassociation requests
            for req in disassociation_requests:
                key = (req.pod, req.fiscal_code)
                if key not in pod_customer_combinations:
                    pod_customer_combinations[key] = {
                        'pod': req.pod,
                        'fiscal_code': req.fiscal_code,
                        'first_name': req.first_name or '',
                        'last_name': req.last_name or '',
                        'email': req.email or '',
                        'user_type': req.user_type or 'CONSUMER',
                        'source': 'disassociation'
                    }
            
            created_count = 0
            updated_count = 0
            error_count = 0
            customer_created_count = 0
            
            for (pod_code, fiscal_code), data in pod_customer_combinations.items():
                try:
                    # Find or create customer
                    customer = self.env['tada.customer'].search([
                        ('fiscal_code', '=', fiscal_code),
                        ('company_id', '=', company_id)
                    ], limit=1)
                    
                    if not customer:
                        # Create customer if not exists
                        customer_data = {
                            'fiscal_code': fiscal_code,
                            'company_id': company_id
                        }
                        
                        if data['first_name']:
                            customer_data['first_name'] = data['first_name']
                        if data['last_name']:
                            customer_data['last_name'] = data['last_name']
                        if data['email']:
                            customer_data['email'] = data['email']
                        if data['user_type']:
                            customer_data['user_type'] = data['user_type']
                        
                        customer = self.env['tada.customer'].create(customer_data)
                        customer_created_count += 1
                    
                    # Create or update POD summary
                    existing = self.search([
                        ('pod_code', '=', pod_code),
                        ('customer_id', '=', customer.id),
                        ('company_id', '=', company_id)
                    ], limit=1)
                    
                    if existing:
                        existing.write({'updated_at': fields.Datetime.now()})
                        updated_count += 1
                    else:
                        self.create({
                            'pod_code': pod_code,
                            'customer_id': customer.id,
                            'company_id': company_id
                        })
                        created_count += 1
                        
                except Exception as e:
                    _logger.error("Error processing POD summary for %s + %s: %s", pod_code, fiscal_code, str(e))
                    error_count += 1
            
            # Prepare result message
            message_parts = []
            if created_count > 0:
                message_parts.append(f"Created {created_count} POD summaries")
            if updated_count > 0:
                message_parts.append(f"Updated {updated_count} POD summaries")
            if customer_created_count > 0:
                message_parts.append(f"Created {customer_created_count} customers")
            if error_count > 0:
                message_parts.append(f"{error_count} errors occurred")
            
            message = ". ".join(message_parts) if message_parts else "No changes needed"
            message += f". Processed {len(pod_customer_combinations)} unique POD+Customer combinations."
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success' if error_count == 0 else 'warning',
                }
            }
            
        except Exception as e:
            _logger.error("Error populating POD summaries: %s", str(e))
            raise UserError(_("Failed to populate POD summaries: {}").format(str(e)))
    
    # Action Methods
    def action_view_customer(self):
        """View the associated customer record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Details'),
            'res_model': 'tada.customer',
            'res_id': self.customer_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_devices(self):
        """View devices associated with this POD."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('POD Devices - {}').format(self.pod_code),
            'res_model': 'tada.device',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.device_ids.ids)],
            'context': {'default_company_id': self.company_id.id},
        }
    
    def action_view_admissibility_requests(self):
        """View admissibility requests for this POD + Customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Admissibility Requests - {}').format(self.display_name),
            'res_model': 'tada.admissibility.request',
            'view_mode': 'list,form',
            'domain': [
                ('pod', '=', self.pod_code),
                ('fiscal_code', '=', self.customer_fiscal_code),
                ('company_id', '=', self.company_id.id)
            ],
            'context': {
                'default_pod': self.pod_code,
                'default_fiscal_code': self.customer_fiscal_code,
                'default_company_id': self.company_id.id
            },
        }
    
    def action_view_association_requests(self):
        """View association requests for this POD + Customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Association Requests - {}').format(self.display_name),
            'res_model': 'tada.association.request',
            'view_mode': 'list,form',
            'domain': [
                ('pod', '=', self.pod_code),
                ('fiscal_code', '=', self.customer_fiscal_code),
                ('company_id', '=', self.company_id.id)
            ],
            'context': {
                'default_pod': self.pod_code,
                'default_fiscal_code': self.customer_fiscal_code,
                'default_company_id': self.company_id.id
            },
        }
    
    def action_view_disassociation_requests(self):
        """View disassociation requests for this POD + Customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Disassociation Requests - {}').format(self.display_name),
            'res_model': 'tada.disassociation.request',
            'view_mode': 'list,form',
            'domain': [
                ('pod', '=', self.pod_code),
                ('fiscal_code', '=', self.customer_fiscal_code),
                ('company_id', '=', self.company_id.id)
            ],
            'context': {
                'default_pod': self.pod_code,
                'default_fiscal_code': self.customer_fiscal_code,
                'default_company_id': self.company_id.id
            },
        }
    
    def action_refresh_from_chain2gate(self):
        """Refresh POD data from Chain2Gate."""
        self.ensure_one()
        
        try:
            # Use the data service to get fresh POD data
            data_service = self.env['tada_admin.data.service']
            pod_data = data_service.get_pod_data(
                pod_ids=[self.pod_code],
                company_id=self.company_id.id,
                data_type='monitoring'
            )
            
            # Trigger recomputation by updating timestamp
            self.write({'updated_at': fields.Datetime.now()})
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('POD {} refreshed successfully from Chain2Gate').format(self.pod_code),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error("Error refreshing POD %s from Chain2Gate: %s", self.pod_code, str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Failed to refresh POD {}: {}').format(self.pod_code, str(e)),
                    'type': 'danger',
                }
            }
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set timestamps."""
        for vals in vals_list:
            if 'created_at' not in vals:
                vals['created_at'] = fields.Datetime.now()
            if 'updated_at' not in vals:
                vals['updated_at'] = fields.Datetime.now()
        
        records = super().create(vals_list)
        
        # Update status for each new record
        for record in records:
            record._update_pod_status()
        
        return records
    
    def write(self, vals):
        """Override write to update timestamp."""
        vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)