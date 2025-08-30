# Requirements Document

## Introduction

This feature involves creating a new Odoo module called "tada_erp" that duplicates the functionality of the existing "chain2gate_integration" module but removes all encryption-related features. The new module will maintain the same API integration capabilities, data models, and user interface while simplifying the architecture by eliminating the hierarchical encryption system and AWS Secrets Manager dependencies.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to install a tada_erp module that provides the same Chain2Gate API integration without encryption complexity, so that I can manage energy monitoring data in a simpler deployment environment.

#### Acceptance Criteria

1. WHEN the tada_erp module is installed THEN the system SHALL create all necessary models, views, and menu items identical to chain2gate_integration
2. WHEN the module is installed THEN the system SHALL NOT require AWS credentials or encryption key configuration
3. WHEN the module is installed THEN the system SHALL use the same Chain2Gate SDK without encryption wrappers
4. IF the installation is successful THEN the system SHALL display tada_erp menus and views in the Odoo interface

### Requirement 2

**User Story:** As a developer, I want the tada_erp module to use the base Chain2Gate SDK directly, so that API calls work identically but without encryption overhead.

#### Acceptance Criteria

1. WHEN API calls are made THEN the system SHALL use chain2gate_sdk.py directly without encryption layers
2. WHEN data is stored THEN the system SHALL store personal data in plain text format
3. WHEN data is retrieved THEN the system SHALL return data without decryption processing
4. IF encryption-related imports exist THEN the system SHALL remove all references to hierarchical_encryption and odoo_secure_encryption modules

### Requirement 3

**User Story:** As a user, I want to manage customers, devices, and requests through the tada_erp interface, so that I can perform the same operations as the encrypted version.

#### Acceptance Criteria

1. WHEN accessing customer records THEN the system SHALL display all customer information fields without encryption
2. WHEN creating association requests THEN the system SHALL store fiscal codes, names, and emails in plain text
3. WHEN viewing device information THEN the system SHALL show all device details without encryption processing
4. WHEN searching records THEN the system SHALL perform searches on plain text data

### Requirement 4

**User Story:** As a system administrator, I want the tada_erp module to have its own namespace and branding, so that it can coexist with the encrypted version if needed.

#### Acceptance Criteria

1. WHEN the module is installed THEN the system SHALL use "tada_erp" as the module name and directory
2. WHEN displaying menus THEN the system SHALL show "TADA ERP" branding instead of "Chain2Gate Integration"
3. WHEN accessing models THEN the system SHALL use "tada_erp" prefixes for model names
4. IF both modules are installed THEN the system SHALL allow them to coexist without conflicts

### Requirement 5

**User Story:** As a developer, I want the tada_erp module structure to mirror the original module, so that maintenance and updates are straightforward.

#### Acceptance Criteria

1. WHEN examining the module structure THEN the system SHALL maintain the same directory layout as chain2gate_integration
2. WHEN reviewing model files THEN the system SHALL keep the same model inheritance and field definitions
3. WHEN checking view files THEN the system SHALL preserve the same XML view structures with updated references
4. WHEN inspecting the manifest THEN the system SHALL maintain the same dependencies except encryption-related packages

### Requirement 6

**User Story:** As a user, I want to configure the tada_erp module through a setup wizard, so that I can easily connect to the Chain2Gate API without encryption setup.

#### Acceptance Criteria

1. WHEN running the configuration wizard THEN the system SHALL only request API key and base URL
2. WHEN testing the connection THEN the system SHALL verify API connectivity without encryption tests
3. WHEN saving configuration THEN the system SHALL store settings without encryption key generation
4. IF configuration is successful THEN the system SHALL enable all tada_erp functionality

### Requirement 7

**User Story:** As a system administrator, I want the tada_erp module to enforce strict multi-company data isolation, so that information never leaks between different companies in the system.

#### Acceptance Criteria

1. WHEN accessing customer records THEN the system SHALL only display records belonging to the current user's company
2. WHEN creating new records THEN the system SHALL automatically assign the current company_id to all new records
3. WHEN performing searches THEN the system SHALL filter results by company_id to prevent cross-company data access
4. WHEN API calls are made THEN the system SHALL use company-specific API keys and configurations
5. IF a user switches companies THEN the system SHALL only show data relevant to the newly selected company
6. WHEN viewing device associations THEN the system SHALL only display devices linked to the current company's customers

### Requirement 8

**User Story:** As a developer, I want the tada_erp module to have simplified dependencies, so that deployment is easier without AWS and encryption requirements.

#### Acceptance Criteria

1. WHEN installing the module THEN the system SHALL only require requests library for API calls
2. WHEN checking dependencies THEN the system SHALL NOT require cryptography or boto3 packages
3. WHEN reviewing imports THEN the system SHALL remove all AWS and encryption-related imports
4. IF the module loads successfully THEN the system SHALL function without any encryption infrastructure

### Requirement 9

**User Story:** As a security administrator, I want all tada_erp models to implement proper company-based record rules, so that data access is automatically restricted by company boundaries.

#### Acceptance Criteria

1. WHEN defining model security THEN the system SHALL implement record rules that filter by company_id
2. WHEN users access any tada_erp model THEN the system SHALL automatically apply company-based domain filters
3. WHEN performing CRUD operations THEN the system SHALL validate that users can only access their company's data
4. IF a user attempts to access another company's data THEN the system SHALL deny access and return empty results