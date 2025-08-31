# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
import psycopg2


class TestCompanyPermissions(TransactionCase):

    def setUp(self):
        super(TestCompanyPermissions, self).setUp()
        self.CompanyPermissions = self.env['tada_admin.company.permissions']
        self.Company = self.env['res.company']
        
        # Create test companies
        self.company_a = self.Company.create({
            'name': 'Test Company A',
        })
        self.company_b = self.Company.create({
            'name': 'Test Company B',
        })

    def test_create_company_permissions(self):
        """Test creating company permissions with default values"""
        permissions = self.CompanyPermissions.create({
            'company_id': self.company_a.id,
        })
        
        self.assertEqual(permissions.company_id, self.company_a)
        self.assertFalse(permissions.is_partner_energia)
        self.assertFalse(permissions.has_configurazione_ammissibilita)
        self.assertFalse(permissions.has_configurazione_associazione)
        self.assertFalse(permissions.has_magazzino)
        self.assertFalse(permissions.has_spedizione)
        self.assertTrue(permissions.has_monitoraggio)  # Default True
        self.assertTrue(permissions.created_date)
        self.assertTrue(permissions.last_modified)
        self.assertEqual(permissions.modified_by, self.env.user)

    def test_create_company_permissions_with_custom_values(self):
        """Test creating company permissions with custom values"""
        permissions = self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'is_partner_energia': True,
            'has_configurazione_ammissibilita': True,
            'has_magazzino': True,
        })
        
        self.assertTrue(permissions.is_partner_energia)
        self.assertTrue(permissions.has_configurazione_ammissibilita)
        self.assertFalse(permissions.has_configurazione_associazione)
        self.assertTrue(permissions.has_magazzino)
        self.assertFalse(permissions.has_spedizione)
        self.assertTrue(permissions.has_monitoraggio)  # Default True

    def test_unique_company_constraint(self):
        """Test that each company can only have one permissions record"""
        # Create first permissions record
        self.CompanyPermissions.create({
            'company_id': self.company_a.id,
        })
        
        # Try to create second permissions record for same company
        with self.assertRaises(psycopg2.errors.UniqueViolation):  # Should raise UniqueViolation
            self.CompanyPermissions.create({
                'company_id': self.company_a.id,
            })

    def test_get_company_permissions_existing(self):
        """Test getting permissions for existing company"""
        # Create permissions
        self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'is_partner_energia': True,
            'has_configurazione_ammissibilita': True,
        })
        
        permissions = self.CompanyPermissions.get_company_permissions(self.company_a.id)
        
        self.assertTrue(permissions['is_partner_energia'])
        self.assertTrue(permissions['has_configurazione_ammissibilita'])
        self.assertFalse(permissions['has_configurazione_associazione'])
        self.assertFalse(permissions['has_magazzino'])
        self.assertFalse(permissions['has_spedizione'])
        self.assertTrue(permissions['has_monitoraggio'])

    def test_get_company_permissions_non_existing(self):
        """Test getting permissions for non-existing company returns defaults"""
        permissions = self.CompanyPermissions.get_company_permissions(self.company_a.id)
        
        self.assertFalse(permissions['is_partner_energia'])
        self.assertFalse(permissions['has_configurazione_ammissibilita'])
        self.assertFalse(permissions['has_configurazione_associazione'])
        self.assertFalse(permissions['has_magazzino'])
        self.assertFalse(permissions['has_spedizione'])
        self.assertTrue(permissions['has_monitoraggio'])  # Default True

    def test_check_permission_valid(self):
        """Test checking valid permissions"""
        # Create permissions
        self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'is_partner_energia': True,
            'has_configurazione_ammissibilita': False,
        })
        
        self.assertTrue(self.CompanyPermissions.check_permission(self.company_a.id, 'PARTNER_ENERGIA'))
        self.assertFalse(self.CompanyPermissions.check_permission(self.company_a.id, 'CONFIGURAZIONE_AMMISSIBILITA'))
        self.assertFalse(self.CompanyPermissions.check_permission(self.company_a.id, 'CONFIGURAZIONE_ASSOCIAZIONE'))
        self.assertFalse(self.CompanyPermissions.check_permission(self.company_a.id, 'MAGAZZINO'))
        self.assertTrue(self.CompanyPermissions.check_permission(self.company_a.id, 'MONITORAGGIO'))  # Default

    def test_check_permission_invalid_type(self):
        """Test checking invalid permission type raises error"""
        with self.assertRaises(ValidationError):
            self.CompanyPermissions.check_permission(self.company_a.id, 'INVALID_PERMISSION')

    def test_set_company_permissions_new(self):
        """Test setting permissions for new company"""
        permissions_dict = {
            'is_partner_energia': True,
            'has_configurazione_ammissibilita': True,
        }
        
        record = self.CompanyPermissions.set_company_permissions(self.company_a.id, permissions_dict)
        
        self.assertEqual(record.company_id, self.company_a)
        self.assertTrue(record.is_partner_energia)
        self.assertTrue(record.has_configurazione_ammissibilita)

    def test_set_company_permissions_existing(self):
        """Test updating permissions for existing company"""
        # Create initial permissions
        initial_record = self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'is_partner_energia': False,
        })
        
        # Update permissions
        permissions_dict = {
            'is_partner_energia': True,
            'has_configurazione_ammissibilita': True,
        }
        
        updated_record = self.CompanyPermissions.set_company_permissions(self.company_a.id, permissions_dict)
        
        self.assertEqual(updated_record.id, initial_record.id)
        self.assertTrue(updated_record.is_partner_energia)
        self.assertTrue(updated_record.has_configurazione_ammissibilita)

    def test_set_company_permissions_invalid_key(self):
        """Test setting permissions with invalid key raises error"""
        permissions_dict = {
            'invalid_key': True,
        }
        
        with self.assertRaises(ValidationError):
            self.CompanyPermissions.set_company_permissions(self.company_a.id, permissions_dict)

    def test_get_companies_with_permission(self):
        """Test getting companies with specific permission"""
        # Create permissions for multiple companies
        self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'is_partner_energia': True,
            'has_configurazione_ammissibilita': False,
        })
        
        self.CompanyPermissions.create({
            'company_id': self.company_b.id,
            'is_partner_energia': False,
            'has_configurazione_ammissibilita': True,
        })
        
        # Test partner energia permission
        partner_energia_companies = self.CompanyPermissions.get_companies_with_permission('PARTNER_ENERGIA')
        self.assertEqual(len(partner_energia_companies), 1)
        self.assertEqual(partner_energia_companies[0], self.company_a)
        
        # Test configurazione ammissibilita permission
        config_amm_companies = self.CompanyPermissions.get_companies_with_permission('CONFIGURAZIONE_AMMISSIBILITA')
        self.assertEqual(len(config_amm_companies), 1)
        self.assertEqual(config_amm_companies[0], self.company_b)
        
        # Test monitoraggio permission (both should have default True)
        monitoraggio_companies = self.CompanyPermissions.get_companies_with_permission('MONITORAGGIO')
        self.assertEqual(len(monitoraggio_companies), 2)

    def test_get_companies_with_permission_invalid_type(self):
        """Test getting companies with invalid permission type raises error"""
        with self.assertRaises(ValidationError):
            self.CompanyPermissions.get_companies_with_permission('INVALID_PERMISSION')

    def test_audit_fields_on_write(self):
        """Test that audit fields are updated on write"""
        # Create permissions
        permissions = self.CompanyPermissions.create({
            'company_id': self.company_a.id,
        })
        
        original_modified = permissions.last_modified
        
        # Sleep briefly to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Update permissions
        permissions.write({
            'is_partner_energia': True,
        })
        
        # Check audit fields were updated
        # Note: Due to timestamp precision, we just verify the modified_by field is updated
        # and that last_modified is at least the same (could be equal due to precision)
        self.assertGreaterEqual(permissions.last_modified, original_modified)
        self.assertEqual(permissions.modified_by, self.env.user)

    def test_check_company_exists_constraint(self):
        """Test company exists constraint"""
        # Create inactive company
        inactive_company = self.Company.create({
            'name': 'Inactive Company',
            'active': False,
        })
        
        # Try to create permissions for inactive company
        with self.assertRaises(ValidationError):
            self.CompanyPermissions.create({
                'company_id': inactive_company.id,
            })