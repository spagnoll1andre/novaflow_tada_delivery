# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError
from ..exceptions import AuthorizationError, DataAccessError


class TestAuthorizationService(TransactionCase):
    """Test cases for TADA Admin Authorization Service"""

    def setUp(self):
        super(TestAuthorizationService, self).setUp()
        
        # Get the authorization service
        self.auth_service = self.env['tada_admin.authorization.service']
        
        # Create test company
        self.test_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.env.ref('base.USD').id,
        })
        
        # Create company permissions
        self.permissions = self.env['tada_admin.company.permissions'].create({
            'company_id': self.test_company.id,
            'is_partner_energia': True,
            'has_configurazione_ammissibilita': False,
            'has_configurazione_associazione': False,
            'has_magazzino': True,
            'has_spedizione': False,
            'has_monitoraggio': True,
        })
        
        # Create POD authorizations
        self.pod_auth1 = self.env['tada_admin.pod.authorization'].create({
            'company_id': self.test_company.id,
            'pod_code': 'POD001',
            'pod_name': 'Test POD 1',
            'is_active': True,
        })
        
        self.pod_auth2 = self.env['tada_admin.pod.authorization'].create({
            'company_id': self.test_company.id,
            'pod_code': 'POD002',
            'pod_name': 'Test POD 2',
            'is_active': True,
        })

    def test_check_company_permission_success(self):
        """Test successful permission check"""
        # Test PARTNER_ENERGIA permission (should pass)
        result = self.auth_service.check_company_permission(
            self.test_company.id, 'PARTNER_ENERGIA'
        )
        self.assertTrue(result)
        
        # Test MONITORAGGIO permission (should pass)
        result = self.auth_service.check_company_permission(
            self.test_company.id, 'MONITORAGGIO'
        )
        self.assertTrue(result)

    def test_check_company_permission_denied(self):
        """Test permission check denial"""
        # Test CONFIGURAZIONE_AMMISSIBILITA permission (should fail)
        with self.assertRaises(AuthorizationError) as context:
            self.auth_service.check_company_permission(
                self.test_company.id, 'CONFIGURAZIONE_AMMISSIBILITA'
            )
        
        self.assertEqual(context.exception.company_id, self.test_company.id)
        self.assertEqual(context.exception.permission_type, 'CONFIGURAZIONE_AMMISSIBILITA')

    def test_check_company_permission_invalid_type(self):
        """Test permission check with invalid permission type"""
        with self.assertRaises(ValidationError):
            self.auth_service.check_company_permission(
                self.test_company.id, 'invalid_permission'
            )

    def test_get_authorized_pods(self):
        """Test getting authorized PODs for company"""
        pods = self.auth_service.get_authorized_pods(self.test_company.id)
        
        self.assertEqual(len(pods), 2)
        self.assertIn('POD001', pods)
        self.assertIn('POD002', pods)

    def test_get_authorized_pods_invalid_company(self):
        """Test getting PODs for invalid company"""
        with self.assertRaises(ValidationError):
            self.auth_service.get_authorized_pods(99999)

    def test_validate_pod_access_success(self):
        """Test successful POD access validation"""
        # Test single POD
        result = self.auth_service.validate_pod_access(
            self.test_company.id, 'POD001'
        )
        self.assertEqual(result, ['POD001'])
        
        # Test multiple PODs
        result = self.auth_service.validate_pod_access(
            self.test_company.id, ['POD001', 'POD002']
        )
        self.assertEqual(set(result), {'POD001', 'POD002'})

    def test_validate_pod_access_denied(self):
        """Test POD access validation denial"""
        with self.assertRaises(DataAccessError) as context:
            self.auth_service.validate_pod_access(
                self.test_company.id, 'POD999'
            )
        
        self.assertEqual(context.exception.company_id, self.test_company.id)
        self.assertIn('POD999', context.exception.pod_ids)

    def test_validate_company_and_permission(self):
        """Test combined validation method"""
        result = self.auth_service.validate_company_and_permission(
            self.test_company.id, 'MONITORAGGIO', ['POD001']
        )
        
        self.assertTrue(result['authorized'])
        self.assertEqual(result['company_id'], self.test_company.id)
        self.assertEqual(result['permission_type'], 'MONITORAGGIO')
        self.assertEqual(result['authorized_pods'], ['POD001'])

    def test_get_companies_with_permission(self):
        """Test getting companies with specific permission"""
        companies = self.auth_service.get_companies_with_permission('MONITORAGGIO')
        
        self.assertIn(self.test_company, companies)
        
        # Test permission that company doesn't have
        companies = self.auth_service.get_companies_with_permission('CONFIGURAZIONE_AMMISSIBILITA')
        self.assertNotIn(self.test_company, companies)