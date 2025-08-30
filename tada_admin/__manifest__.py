# -*- coding: utf-8 -*-
{
    'name': 'TADA Admin',
    'version': '1.0.0',
    'category': 'IoT/Energy',
    'summary': 'TADA Admin - Centralized Chain2Gate Data Management and Authorization',
    'description': """
TADA Admin for Odoo
===================

This module provides centralized data management and authorization services for the TADA ecosystem.
It serves as the single point of access to Chain2Gate API and manages multi-company data isolation.

Key Features:
* **Centralized Chain2Gate Access**: Single module with direct SDK integration
* **Authorization Service**: Company-based permission management and POD filtering
* **Data Service Layer**: Centralized data operations with caching and validation
* **Multi-Company Security**: Strict company-based data isolation and access control
* **Audit Logging**: Comprehensive tracking of all operations and access attempts
* **Cache Management**: Performance optimization with intelligent cache invalidation

Service Components:
* Authorization Service - Company permission validation and POD access control
* Data Service - Centralized Chain2Gate data operations and synchronization
* Cache Service - Performance optimization with TTL-based caching
* Audit Service - Complete operation tracking and security logging

Models Included:
* Company Permissions - Feature access control per company
* POD Authorization - Company-to-POD mapping and access rights
* Chain2Gate Cache - Persistent cache storage with TTL support
* Audit Logs - Comprehensive operation and access tracking
* Existing TADA models (Customer, Device, Requests) - Maintained for compatibility

Security Features:
* Centralized authorization with company-based filtering
* API authentication and service-to-service communication
* Comprehensive audit logging for security analysis
* Input validation and sanitization for all service methods

Technical Architecture:
* Service-oriented architecture with clean separation of concerns
* Built on Chain2Gate SDK with centralized access patterns
* Thread-safe session management and connection pooling
* Comprehensive error handling with custom exception types

Installation Requirements:
* Chain2Gate API key
* Python packages: requests

Configuration:
Use the included configuration wizard to set up API keys, company permissions,
and POD authorizations. The wizard will guide you through the setup process.
    """,
    'author': 'TADA Admin Team',
    'website': 'https://tada-admin.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
    ],
    'external_dependencies': {
        'python': [
            'requests',
        ],
    },
    'data': [
        'security/tada_security_groups.xml',
        'security/tada_record_rules.xml',
        'security/ir.model.access.csv',
        'views/search_views.xml',
        'views/customer_views.xml',
        'views/device_views.xml',
        'views/admissibility_request_views.xml',
        'views/association_request_views.xml',
        'views/disassociation_request_views.xml',
        'views/wizard_views.xml',
        'views/company_views.xml',
        'views/menu_views.xml',
        'views/company_permissions_views.xml',
        'views/pod_authorization_views.xml',
        'views/pod_summary_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
    'images': ['static/description/icon.png'],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}