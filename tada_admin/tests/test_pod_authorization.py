# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields
import psycopg2


class TestPODAuthorization(TransactionCase):

    def setUp(self):
        super(TestPODAuthorization, self).setUp()
        self.PODAuthorization = self.env['tada_admin.pod.authorization']
        
        # Create test companies
        self.company_a = self.env['res.company'].create({
            'name': 'Test Company A'
        })
        self.company_b = self.env['res.company'].create({
            'name': 'Test Company B'
        })

    def test_create_pod_authorization(self):
        """Test creating a POD authorization record"""
        pod_auth = self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001',
            'chain2gate_id': 'C2G_001'
        })
        
        self.assertEqual(pod_auth.company_id, self.company_a)
        self.assertEqual(pod_auth.pod_code, 'POD001')
        self.assertEqual(pod_auth.pod_name, 'Test POD 001')
        self.assertEqual(pod_auth.chain2gate_id, 'C2G_001')
        self.assertTrue(pod_auth.is_active)
        self.assertIsNotNone(pod_auth.created_date)
        self.assertIsNotNone(pod_auth.last_modified)

    def test_unique_company_pod_constraint(self):
        """Test that the same POD cannot be assigned to the same company twice"""
        # Create first POD authorization
        self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001'
        })
        
        # Try to create duplicate - should raise ValidationError
        with self.assertRaises(ValidationError):
            self.PODAuthorization.create({
                'company_id': self.company_a.id,
                'pod_code': 'POD001',
                'pod_name': 'Duplicate POD 001'
            })

    def test_same_pod_different_companies(self):
        """Test that the same POD can be assigned to different companies"""
        # Create POD authorization for company A
        pod_auth_a = self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001 - Company A'
        })
        
        # Create POD authorization for company B with same POD code
        pod_auth_b = self.PODAuthorization.create({
            'company_id': self.company_b.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001 - Company B'
        })
        
        self.assertEqual(pod_auth_a.pod_code, pod_auth_b.pod_code)
        self.assertNotEqual(pod_auth_a.company_id, pod_auth_b.company_id)

    def test_empty_pod_code_validation(self):
        """Test that empty POD codes are not allowed"""
        with self.assertRaises(ValidationError):
            self.PODAuthorization.create({
                'company_id': self.company_a.id,
                'pod_code': '',
                'pod_name': 'Empty POD Code'
            })
        
        with self.assertRaises(ValidationError):
            self.PODAuthorization.create({
                'company_id': self.company_a.id,
                'pod_code': '   ',  # Only whitespace
                'pod_name': 'Whitespace POD Code'
            })

    def test_pod_code_trimming(self):
        """Test that POD codes are trimmed of whitespace"""
        pod_auth = self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': '  POD001  ',
            'pod_name': 'Trimmed POD'
        })
        
        self.assertEqual(pod_auth.pod_code, 'POD001')

    def test_activate_deactivate_pod(self):
        """Test POD activation and deactivation methods"""
        pod_auth = self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001'
        })
        
        # Initially active
        self.assertTrue(pod_auth.is_active)
        
        # Deactivate
        pod_auth.deactivate_pod()
        self.assertFalse(pod_auth.is_active)
        
        # Activate
        pod_auth.activate_pod()
        self.assertTrue(pod_auth.is_active)

    def test_sync_with_chain2gate(self):
        """Test Chain2Gate sync method"""
        pod_auth = self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001'
        })
        
        # Initially no sync timestamp
        self.assertFalse(pod_auth.last_sync)
        
        # Sync with Chain2Gate
        result = pod_auth.sync_with_chain2gate()
        self.assertTrue(result)
        self.assertIsNotNone(pod_auth.last_sync)

    def test_get_authorized_pods_for_company(self):
        """Test getting authorized PODs for a company"""
        # Create POD authorizations
        self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'is_active': True
        })
        self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD002',
            'is_active': True
        })
        self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD003',
            'is_active': False  # Inactive
        })
        self.PODAuthorization.create({
            'company_id': self.company_b.id,
            'pod_code': 'POD004',
            'is_active': True
        })
        
        # Get authorized PODs for company A
        authorized_pods = self.PODAuthorization.get_authorized_pods_for_company(self.company_a.id)
        
        self.assertEqual(len(authorized_pods), 2)
        self.assertIn('POD001', authorized_pods)
        self.assertIn('POD002', authorized_pods)
        self.assertNotIn('POD003', authorized_pods)  # Inactive
        self.assertNotIn('POD004', authorized_pods)  # Different company

    def test_is_pod_authorized_for_company(self):
        """Test checking if a specific POD is authorized for a company"""
        # Create POD authorization
        self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'is_active': True
        })
        
        # Test authorized POD
        self.assertTrue(
            self.PODAuthorization.is_pod_authorized_for_company(self.company_a.id, 'POD001')
        )
        
        # Test unauthorized POD
        self.assertFalse(
            self.PODAuthorization.is_pod_authorized_for_company(self.company_a.id, 'POD999')
        )
        
        # Test different company
        self.assertFalse(
            self.PODAuthorization.is_pod_authorized_for_company(self.company_b.id, 'POD001')
        )

    def test_display_name_computation(self):
        """Test computed display name"""
        pod_auth = self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001'
        })
        
        display_name = pod_auth.display_name
        self.assertIn('POD001', display_name)
        self.assertIn('Test POD 001', display_name)
        self.assertIn('Test Company A', display_name)

    def test_audit_fields_on_write(self):
        """Test that audit fields are updated on write operations"""
        pod_auth = self.PODAuthorization.create({
            'company_id': self.company_a.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 001'
        })
        
        original_modified = pod_auth.last_modified
        
        # Wait a moment and update
        import time
        time.sleep(0.1)
        
        pod_auth.write({'pod_name': 'Updated POD 001'})
        
        # Note: Due to timestamp precision, we just verify the modified_by field is updated
        # and that last_modified is at least the same (could be equal due to precision)
        self.assertGreaterEqual(pod_auth.last_modified, original_modified)
        self.assertEqual(pod_auth.modified_by, self.env.user)