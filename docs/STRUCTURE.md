# Chain2Gate Integration - Module Structure

## Overview

This document describes the organized structure of the Chain2Gate Integration Odoo module, with models properly separated into logical folders and individual files.

## Directory Structure

```
chain2gate_integration/
├── __manifest__.py                 # Odoo module manifest
├── __init__.py                     # Module initialization with hooks
├── README.md                       # Module documentation
├── requirements.txt                # Python dependencies
├── STRUCTURE.md                    # This file
├── 
├── models/                         # All model-related code
│   ├── __init__.py                 # Models package init
│   ├── 
│   ├── sdk/                        # Chain2Gate SDK components
│   │   ├── __init__.py
│   │   ├── chain2gate_sdk.py       # Core Chain2Gate SDK
│   │   ├── hierarchical_encryption.py  # Encryption implementation
│   │   ├── odoo_secure_encryption.py   # Odoo-specific encryption
│   │   ├── chain2gate_encrypted_sdk.py # Encrypted SDK variant
│   │   └── chain2gate_odoo_sdk.py      # Odoo-integrated SDK
│   │
│   ├── mixins/                     # Reusable model mixins
│   │   ├── __init__.py
│   │   └── dataclass_mixin.py      # Dataclass integration mixin
│   │
│   └── odoo_models/                # Concrete Odoo models
│       ├── __init__.py
│       ├── admissibility_request.py    # Admissibility request model
│       ├── association_request.py      # Association request model
│       ├── disassociation_request.py   # Disassociation request model
│       ├── device.py                   # Device model
│       └── customer.py                 # Customer aggregation model
│
├── wizards/                        # Configuration wizards
│   ├── __init__.py
│   └── chain2gate_config_wizard.py
│
├── views/                          # Odoo UI views
│   ├── chain2gate_views.xml        # Main model views
│   └── chain2gate_wizard_views.xml # Wizard views
│
├── security/                       # Access control
│   └── ir.model.access.csv
│
├── data/                          # Default data
│   └── chain2gate_data.xml
│
└── static/description/            # Module metadata
    ├── index.html                 # Module description page
    └── icon.svg                   # Module icon
```

## Model Organization

### 1. SDK Components (`models/sdk/`)

Contains all Chain2Gate SDK related code:

- **`chain2gate_sdk.py`** - Original Chain2Gate SDK with dataclasses
- **`hierarchical_encryption.py`** - Hierarchical encryption implementation
- **`odoo_secure_encryption.py`** - Odoo-specific secure encryption
- **`chain2gate_encrypted_sdk.py`** - SDK with encryption capabilities
- **`chain2gate_odoo_sdk.py`** - Odoo-integrated SDK with session management

### 2. Mixins (`models/mixins/`)

Reusable model components:

- **`dataclass_mixin.py`** - Abstract mixin providing:
  - Automatic encryption/decryption of personal fields
  - Conversion between Odoo records and SDK dataclasses
  - Company-specific encryption context
  - SDK instance management

### 3. Odoo Models (`models/odoo_models/`)

Concrete Odoo models, each in its own file:

#### `admissibility_request.py`
- **Model**: `chain2gate.admissibility.request`
- **Dataclass**: `AdmissibilityRequest`
- **Encrypted Fields**: `fiscal_code`, `message`
- **Features**:
  - API synchronization
  - Create requests via API
  - Refresh from API
  - Unique constraints on request_id and pod

#### `association_request.py`
- **Model**: `chain2gate.association.request`
- **Dataclass**: `AssociationRequest`
- **Encrypted Fields**: `first_name`, `last_name`, `email`, `fiscal_code`, `message`
- **Features**:
  - API synchronization
  - Create requests via API
  - Refresh from API
  - Display name computation
  - POD M Type suggestions
  - Unique constraints on request_id and pod+serial

#### `disassociation_request.py`
- **Model**: `chain2gate.disassociation.request`
- **Dataclass**: `DisassociationRequest`
- **Encrypted Fields**: `first_name`, `last_name`, `email`, `fiscal_code`
- **Features**:
  - API synchronization
  - Create requests via API
  - Refresh from API
  - View original association request
  - Display name computation
  - Unique constraints on request_id and pod+serial

#### `device.py`
- **Model**: `chain2gate.device`
- **Dataclass**: `Chain2GateDevice`
- **Encrypted Fields**: None (device data is not personal)
- **Features**:
  - API synchronization by device type
  - POD count computation
  - Meter type detection
  - View associated requests
  - View connected PODs
  - Last sync tracking

#### `customer.py`
- **Model**: `chain2gate.customer`
- **Dataclass**: `Customer`
- **Encrypted Fields**: `first_name`, `last_name`, `email`, `fiscal_code`
- **Features**:
  - Aggregates all customer data from API
  - Links to all related requests and devices
  - Customer statistics and status tracking
  - Sync specific customer from API
  - View all related records

## Key Features by Model

### Common Features (via Mixin)
All models inherit from `chain2gate.dataclass.mixin` and get:
- Automatic encryption/decryption
- Dataclass conversion (`to_dataclass()`, `from_dataclass()`)
- SDK instance management (`get_sdk_instance()`)
- Company-specific encryption keys
- Created/updated timestamps

### Model-Specific Features

#### Admissibility Request
```python
# Create from dataclass
request = AdmissibilityRequest(fiscal_code="RSSMRA80A01H501U", ...)
odoo_record = env['chain2gate.admissibility.request'].from_dataclass(request)

# Sync from API
env['chain2gate.admissibility.request'].sync_from_api()

# Create via API
record.create_api_request()
```

#### Association Request
```python
# Create with encrypted personal data
record = env['chain2gate.association.request'].create({
    'first_name': 'Mario',  # Automatically encrypted
    'last_name': 'Rossi',   # Automatically encrypted
    'email': 'mario@example.com',  # Automatically encrypted
    'fiscal_code': 'RSSMRA80A01H501U',  # Automatically encrypted
    'pod': 'IT001E12345678',
    'serial': 'DEV123456',
})

# Access decrypted data
print(record.first_name)  # Shows "Mario"
print(record.display_name)  # Shows "Mario Rossi (IT001E12345678)"
```

#### Device
```python
# Sync devices by type
env['chain2gate.device'].sync_from_api(device_type='METER_TRIFASE')

# View device capabilities
device = env['chain2gate.device'].browse(device_id)
print(f"PODs: {device.pod_count}")
print(f"Has consumption: {device.has_consumption}")
print(f"Has production: {device.has_production}")

# View associated requests
device.action_view_associated_requests()
```

## Security Architecture

### Encryption Strategy
- **Company Isolation**: Each company gets unique encryption keys
- **Field-Level**: Only personal data fields are encrypted
- **Hierarchical**: Master key → Company keys → Field encryption
- **Storage Format**: `"ciphertext:nonce"` in database, decrypted in interface

### Personal Data Fields
- **Admissibility**: `fiscal_code`, `message`
- **Association**: `first_name`, `last_name`, `email`, `fiscal_code`, `message`
- **Device**: None (technical data only)

### Access Control
- **Users**: Read/write access to requests, read-only to devices
- **Managers**: Full access including delete
- **Technical**: Access to encrypted field debugging

## Usage Patterns

### 1. Direct Dataclass Usage
```python
# SDK dataclass → Odoo record
request = AdmissibilityRequest(...)
odoo_record = env['chain2gate.admissibility.request'].from_dataclass(request)

# Odoo record → SDK dataclass
dataclass_instance = odoo_record.to_dataclass()
```

### 2. API Integration
```python
# Bulk sync from API
env['chain2gate.admissibility.request'].sync_from_api()
env['chain2gate.association.request'].sync_from_api()
env['chain2gate.device'].sync_from_api()

# Individual refresh
record.action_refresh_from_api()
```

### 3. Encrypted Field Access
```python
# Transparent encryption/decryption
record.first_name = "Mario"  # Encrypted on save
print(record.first_name)     # Decrypted on read

# Debug encrypted data
print(record.first_name_encrypted)  # Shows encrypted value
```

## Benefits of This Structure

### 1. **Maintainability**
- Each model in its own file
- Clear separation of concerns
- Logical folder organization

### 2. **Reusability**
- Mixin provides common functionality
- SDK components are modular
- Easy to extend with new models

### 3. **Security**
- Centralized encryption logic
- Company-specific isolation
- Field-level encryption control

### 4. **Developer Experience**
- Type-safe dataclass integration
- Familiar Odoo patterns
- Comprehensive error handling

### 5. **Scalability**
- Easy to add new models
- Modular architecture
- Performance optimizations

This structure provides a clean, maintainable, and scalable foundation for the Chain2Gate Odoo integration while preserving all the powerful features of dataclass integration and hierarchical encryption.