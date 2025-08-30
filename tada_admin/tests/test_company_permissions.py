# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


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
        self.assertFalse(permissions.has_monitoring)
        self.assertTrue(permissions.has_reporting)  # Default True
        self.assertFalse(permissions.has_analytics)
        self.assertFalse(permissions.has_advanced_config)
        self.assertTrue(permissions.created_date)
        self.assertTrue(permissions.last_modified)
        self.assertEqual(permissions.modified_by, self.env.user)

    def test_create_company_permissions_with_custom_values(self):
        """Test creating company permissions with custom values"""
        permissions = self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'has_monitoring': True,
            'has_analytics': True,
            'has_advanced_config': True,
        })
        
        self.assertTrue(permissions.has_monitoring)
        self.assertTrue(permissions.has_reporting)  # Default True
        self.assertTrue(permissions.has_analytics)
        self.assertTrue(permissions.has_advanced_config)

    def test_unique_company_constraint(self):
        """Test that each company can only have one permissions record"""
        # Create first permissions record
        self.CompanyPermissions.create({
            'company_id': self.company_a.id,
        })
        
        # Try to create second permissions record for same company
        with self.assertRaises(Exception):  # Should raise IntegrityError
            self.CompanyPermissions.create({
                'company_id': self.company_a.id,
            })

    def test_get_company_permissions_existing(self):
        """Test getting permissions for existing company"""
        # Create permissions
        self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'has_monitoring': True,
            'has_analytics': True,
        })
        
        permissions = self.CompanyPermissions.get_company_permissions(self.company_a.id)
        
        self.assertTrue(permissions['has_monitoring'])
        self.assertTrue(permissions['has_reporting'])
        self.assertTrue(permissions['has_analytics'])
        self.assertFalse(permissions['has_advanced_config'])

    def test_get_company_permissions_non_existing(self):
        """Test getting permissions for non-existing company returns defaults"""
        permissions = self.CompanyPermissions.get_company_permissions(self.company_a.id)
        
        self.assertFalse(permissions['has_monitoring'])
        self.assertTrue(permissions['has_reporting'])  # Default True
        self.assertFalse(permissions['has_analytics'])
        self.assertFalse(permissions['has_advanced_config'])

    def test_check_permission_valid(self):
        """Test checking valid permissions"""
        # Create permissions
        self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'has_monitoring': True,
            'has_analytics': False,
        })
        
        self.assertTrue(self.CompanyPermissions.check_permission(self.company_a.id, 'monitoring'))
        self.assertTrue(self.CompanyPermissions.check_permission(self.company_a.id, 'reporting'))  # Default
        self.assertFalse(self.CompanyPermissions.check_permission(self.company_a.id, 'analytics'))
        self.assertFalse(self.CompanyPermissions.check_permission(self.company_a.id, 'advanced_config'))

    def test_check_permission_invalid_type(self):
        """Test checking invalid permission type raises error"""
        with self.assertRaises(ValidationError):
            self.CompanyPermissions.check_permission(self.company_a.id, 'invalid_permission')

    def test_set_company_permissions_new(self):
        """Test setting permissions for new company"""
        permissions_dict = {
            'has_monitoring': True,
            'has_analytics': True,
        }
        
        record = self.CompanyPermissions.set_company_permissions(self.company_a.id, permissions_dict)
        
        self.assertEqual(record.company_id, self.company_a)
        self.assertTrue(record.has_monitoring)
        self.assertTrue(record.has_analytics)

    def test_set_company_permissions_existing(self):
        """Test updating permissions for existing company"""
        # Create initial permissions
        initial_record = self.CompanyPermissions.create({
            'company_id': self.company_a.id,
            'has_monitoring': False,
        })
        
        # Update permissions
        permissions_dict = {
            'has_monitoring': True,
            'has_analytics': True,
        }
        
        updated_record = self.CompanyPermissions.set_company_permissions(self.company_a.id, permissions_dict)
        
        self.assertEqual(updated_record.id, initial_record.id)
        self.assertTrue(updated_record.has_monitoring)
        self.assertTrue(updated_record.has_analytics)

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
            'has_monitoring': True,
            'has_analytics': False,
        })
        
        self.CompanyPermissions.create({
            'company_id': self.company_b.id,
            'has_monitoring': False,
            'has_analytics': True,
        })
        
        # Test monitoring permission
        monitoring_companies = self.CompanyPermissions.get_companies_with_permission('monitoring')
        self.assertEqual(len(monitoring_companies), 1)
        self.assertEqual(monitoring_companies[0], self.company_a)
        
        # Test analytics permission
        analytics_companies = self.CompanyPermissions.get_companies_with_permission('analytics')
        self.assertEqual(len(analytics_companies), 1)
        self.assertEqual(analytics_companies[0], self.company_b)
        
        # Test reporting permission (both should have default True)
        reporting_companies = self.CompanyPermissions.get_companies_with_permission('reporting')
        self.assertEqual(len(reporting_companies), 2)

    def test_get_companies_with_permission_invalid_type(self):
        """Test getting companies with invalid permission type raises error"""
        with self.assertRaises(ValidationError):
            self.CompanyPermissions.get_companies_with_permission('invalid_permission')

    def test_audit_fields_on_write(self):
        """Test that audit fields are updated on write"""
        # Create permissions
        permissions = self.CompanyPermissions.create({
            'company_id': self.company_a.id,
        })
        
        original_modified = permissions.last_modified
        
        # Update permissions
        permissions.write({
            'has_monitoring': True,
        })
        
        # Check audit fields were updated
        self.assertGreater(permissions.last_modified, original_modified)
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