# -*- coding: utf-8 -*-
"""
Odoo model for TADA Partner Settings - Customization and branding for partners.
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class TadaPartnerSettings(models.Model):
    """Partner customization settings for branding and personalization."""

    _name = 'tada.partner.settings'
    _description = 'TADA Partner Settings'
    _rec_name = 'partner_name'
    _order = 'partner_name'

    # Basic partner information
    partner_name = fields.Char(string='Partner Name', required=True,
                               help='Name of the partner company')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 help='Related company for this partner')

    # Partner type and classification
    partner_type = fields.Selection([
        ('energy', 'Partner Energetico'),
        ('other', 'Altro Partner')
    ], string='Tipo Partner', required=True, default='other',
        help='Type of partner business')

    # Branding and customization
    logo = fields.Binary(string='Logo Partner',
                         help='Partner logo for dashboard customization')
    logo_filename = fields.Char(string='Logo Filename')

    # Color scheme
    background_color = fields.Char(string='Colore Sfondo',
                                   default='#F8F9FA',
                                   help='Background color for partner dashboard (hex format)')
    accent_color = fields.Char(string='Colore Elementi Cliccabili',
                               default='#4A90E2',
                               help='Accent color for clickable elements (hex format)')
    text_color = fields.Char(string='Colore Testo',
                             default='#333333',
                             help='Text color for partner dashboard (hex format)')

    # Advanced customization
    custom_css = fields.Text(string='CSS Personalizzato',
                             help='Custom CSS for advanced styling')

    # Contact information
    contact_email = fields.Char(string='Email Contatto',
                                help='Primary contact email for this partner')
    contact_phone = fields.Char(string='Telefono Contatto',
                                help='Primary contact phone for this partner')

    # Status and metadata
    active = fields.Boolean(string='Attivo', default=True,
                            help='Whether this partner is active')
    created_at = fields.Datetime(string='Creato il', default=fields.Datetime.now,
                                 help='When this partner settings was created')
    notes = fields.Text(string='Note',
                        help='Additional notes about this partner')

    # Computed fields
    logo_url = fields.Char(string='Logo URL', compute='_compute_logo_url', store=False,
                           help='URL to access the partner logo')
    css_variables = fields.Text(string='CSS Variables', compute='_compute_css_variables', store=False,
                                help='CSS variables for theming')

    # Constraints - OTTIMIZZATO
    _sql_constraints = [
        ('company_unique', 'UNIQUE(company_id)', 'Each company can have only one partner settings record!'),
    ]

    @api.depends('company_id', 'logo')
    def _compute_logo_url(self):
        """Compute the URL to access the partner logo."""
        for record in self:
            if record.company_id and record.logo:
                record.logo_url = f'/web/image/res.company/{record.company_id.id}/logo'
            else:
                record.logo_url = '/web/static/img/placeholder.png'

    @api.depends('background_color', 'accent_color', 'text_color')
    def _compute_css_variables(self):
        """Compute CSS variables for theming."""
        for record in self:
            css_vars = f"""
                --partner-bg-color: {record.background_color or '#F8F9FA'};
                --partner-accent-color: {record.accent_color or '#4A90E2'};
                --partner-text-color: {record.text_color or '#333333'};
                --partner-accent-hover: {record._darken_color(record.accent_color or '#4A90E2', 0.1)};
            """
            record.css_variables = css_vars.strip()

    def _darken_color(self, hex_color, factor=0.1):
        """Darken a hex color by a given factor."""
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')

            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            # Darken
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))

            # Convert back to hex
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    @api.constrains('background_color', 'accent_color', 'text_color')
    def _check_color_format(self):
        """Validate color format (hex)."""
        for record in self:
            colors = [
                ('background_color', record.background_color),
                ('accent_color', record.accent_color),
                ('text_color', record.text_color)
            ]

            for field_name, color in colors:
                if color and not self._is_valid_hex_color(color):
                    raise ValidationError(f"Il colore {field_name} deve essere in formato hex (es. #FF0000)")

    def _is_valid_hex_color(self, color):
        """Check if a string is a valid hex color."""
        if not color:
            return True

        # Remove # if present
        color = color.lstrip('#')

        # Check length and characters
        if len(color) != 6:
            return False

        try:
            int(color, 16)
            return True
        except ValueError:
            return False

    @api.model
    def create_default_settings(self, company_id, partner_data=None):
        """Create default settings for a new partner company."""
        if partner_data is None:
            partner_data = {}

        company = self.env['res.company'].browse(company_id)

        settings_data = {
            'partner_name': partner_data.get('name', company.name),
            'company_id': company_id,
            'partner_type': partner_data.get('partner_type', 'other'),
            'background_color': partner_data.get('background_color', '#F8F9FA'),
            'accent_color': partner_data.get('accent_color', '#4A90E2'),
            'text_color': partner_data.get('text_color', '#333333'),
            'contact_email': partner_data.get('email', company.email),
            'contact_phone': partner_data.get('phone', company.phone),
            'notes': f'Settings created automatically for partner {company.name}'
        }

        # Handle logo
        if partner_data.get('logo'):
            settings_data['logo'] = partner_data['logo']
            settings_data['logo_filename'] = partner_data.get('logo_filename', 'logo.png')

        return self.create(settings_data)

    @api.model
    def prepare_for_wizard_integration(self):
        """Prepare partner settings for wizard integration in Phase 2."""
        # This method will be called by the wizard to ensure
        # partner settings are created automatically
        return {
            'default_colors': {
                'background_color': '#F8F9FA',
                'accent_color': '#4A90E2',
                'text_color': '#333333'
            },
            'partner_types': [
                ('energy', 'Partner Energetico'),
                ('other', 'Altro Partner')
            ]
        }

    def get_theme_css(self):
        """Get the complete CSS theme for this partner."""
        self.ensure_one()

        base_css = f"""
        .partner-theme-{self.company_id.id} {{
            {self.css_variables}
        }}

        .partner-theme-{self.company_id.id} .partner-header {{
            background-color: var(--partner-accent-color);
            color: white;
        }}

        .partner-theme-{self.company_id.id} .btn-primary {{
            background-color: var(--partner-accent-color);
            border-color: var(--partner-accent-color);
        }}

        .partner-theme-{self.company_id.id} .btn-primary:hover {{
            background-color: var(--partner-accent-hover);
            border-color: var(--partner-accent-hover);
        }}

        .partner-theme-{self.company_id.id} .dashboard-section {{
            background-color: var(--partner-bg-color);
            color: var(--partner-text-color);
        }}
        """

        if self.custom_css:
            base_css += f"\n\n/* Custom CSS */\n{self.custom_css}"

        return base_css

    @api.model
    def get_partner_settings_by_company(self, company_id):
        """Get partner settings for a specific company."""
        return self.search([('company_id', '=', company_id)], limit=1)

    def update_company_branding(self):
        """Update the related company with branding information."""
        self.ensure_one()

        if self.company_id and self.logo:
            self.company_id.write({
                'logo': self.logo,
                'email': self.contact_email or self.company_id.email,
                'phone': self.contact_phone or self.company_id.phone,
            })

        return True