# Chain2Gate SDK Dataclass to Odoo Model Mapping

## Complete Mapping Overview

This document shows the complete mapping between Chain2Gate SDK dataclasses and their corresponding Odoo models with automatic encryption.

## ✅ All SDK Dataclasses Mapped

### 1. **AdmissibilityRequest** → `chain2gate.admissibility.request`
```python
@dataclass
class AdmissibilityRequest:
    id: str                    # → request_id
    pod: str                   # → pod
    status: Status             # → status (selection)
    message: str               # → message (encrypted)
    fiscal_code: str           # → fiscal_code (encrypted)
    closed_at: Optional[str]   # → closed_at
    created_at: str           # → created_at
    updated_at: str           # → updated_at
    group: str                # → group
```
**Encrypted Fields**: `fiscal_code`, `message`
**File**: `models/odoo_models/admissibility_request.py`

### 2. **AssociationRequest** → `chain2gate.association.request`
```python
@dataclass
class AssociationRequest:
    id: str                    # → request_id
    pod: str                   # → pod
    serial: str                # → serial
    request_type: str          # → request_type
    pod_m_type: PodMType       # → pod_m_type (selection)
    user_type: UserType        # → user_type (selection)
    first_name: str            # → first_name (encrypted)
    last_name: str             # → last_name (encrypted)
    email: str                 # → email (encrypted)
    contract_signed: bool      # → contract_signed
    product: str               # → product
    status: Status             # → status (selection)
    message: str               # → message
    fiscal_code: str           # → fiscal_code (encrypted)
    closed_at: Optional[str]   # → closed_at
    created_at: str           # → created_at
    updated_at: str           # → updated_at
    group: str                # → group
```
**Encrypted Fields**: `first_name`, `last_name`, `email`, `fiscal_code`, `message`
**File**: `models/odoo_models/association_request.py`

### 3. **DisassociationRequest** → `chain2gate.disassociation.request`
```python
@dataclass
class DisassociationRequest:
    id: str                    # → request_id
    pod: str                   # → pod
    serial: str                # → serial
    request_type: str          # → request_type
    pod_m_type: PodMType       # → pod_m_type (selection)
    user_type: UserType        # → user_type (selection)
    first_name: str            # → first_name (encrypted)
    last_name: str             # → last_name (encrypted)
    email: str                 # → email (encrypted)
    fiscal_code: str           # → fiscal_code (encrypted)
    contract_signed: bool      # → contract_signed
    product: str               # → product
    status: Status             # → status (selection)
    created_at: str           # → created_at
    updated_at: str           # → updated_at
    group: str                # → group
```
**Encrypted Fields**: `first_name`, `last_name`, `email`, `fiscal_code`
**File**: `models/odoo_models/disassociation_request.py`

### 4. **Chain2GateDevice** → `chain2gate.device`
```python
@dataclass
class Chain2GateDevice:
    id: str                    # → device_id
    m1: Optional[str]          # → m1
    m2: Optional[str]          # → m2
    m2_2: Optional[str]        # → m2_2
    m2_3: Optional[str]        # → m2_3
    m2_4: Optional[str]        # → m2_4
    login_key: str             # → login_key
    du_name: str               # → du_name
    hw_version: str            # → hw_version
    sw_version: str            # → sw_version
    fw_version: str            # → fw_version
    mac: str                   # → mac
    k1: str                    # → k1
    k2: str                    # → k2
    system_title: str          # → system_title
    created_at: str           # → created_at
    updated_at: str           # → updated_at
    group: str                # → group
    type_name: str            # → type_name
```
**Encrypted Fields**: None (technical data only)
**File**: `models/odoo_models/device.py`

### 5. **Customer** → `chain2gate.customer`
```python
@dataclass
class Customer:
    fiscal_code: str                              # → fiscal_code (encrypted)
    first_name: Optional[str] = None              # → first_name (encrypted)
    last_name: Optional[str] = None               # → last_name (encrypted)
    email: Optional[str] = None                   # → email (encrypted)
    user_type: Optional[UserType] = None          # → user_type (selection)
    group: Optional[str] = None                   # → group
    admissibility_requests: List[AdmissibilityRequest] = None  # → admissibility_request_ids (One2many)
    association_requests: List[AssociationRequest] = None      # → association_request_ids (One2many)
    disassociation_requests: List[DisassociationRequest] = None # → disassociation_request_ids (One2many)
    devices: List[Chain2GateDevice] = None        # → device_ids (Many2many)
```
**Encrypted Fields**: `first_name`, `last_name`, `email`, `fiscal_code`
**File**: `models/odoo_models/customer.py`

## Encryption Strategy by Model

### Personal Data Encryption
| Model | Encrypted Fields | Reason |
|-------|------------------|---------|
| Admissibility Request | `fiscal_code`, `message` | Personal identification |
| Association Request | `first_name`, `last_name`, `email`, `fiscal_code`, `message` | Full personal data |
| Disassociation Request | `first_name`, `last_name`, `email`, `fiscal_code` | Full personal data |
| Device | None | Technical data only |
| Customer | `first_name`, `last_name`, `email`, `fiscal_code` | Full personal data |

### Storage Format
- **Database**: `"ciphertext:nonce"` (encrypted)
- **Interface**: Decrypted values for user interaction
- **API**: Automatic conversion between formats

## Model Relationships

### Customer as Central Hub
```
Customer (fiscal_code)
├── Admissibility Requests (fiscal_code match)
├── Association Requests (fiscal_code match)
├── Disassociation Requests (fiscal_code match)
└── Devices (via association requests)
```

### Request Lifecycle
```
1. Admissibility Request (POD eligibility check)
2. Association Request (link customer to device)
3. [Device Usage Period]
4. Disassociation Request (unlink customer from device)
```

## Usage Examples

### 1. Complete Dataclass Coverage
```python
# All SDK dataclasses can be used as Odoo models
from chain2gate_sdk import (
    AdmissibilityRequest, AssociationRequest, DisassociationRequest,
    Chain2GateDevice, Customer
)

# Convert any dataclass to Odoo record
for dataclass_type in [AdmissibilityRequest, AssociationRequest, 
                      DisassociationRequest, Chain2GateDevice, Customer]:
    instance = dataclass_type(...)  # Create instance
    model_name = f'chain2gate.{dataclass_type.__name__.lower()}'
    odoo_record = env[model_name].from_dataclass(instance)
```

### 2. Customer Aggregation
```python
# Customer automatically aggregates all related data
customer = env['chain2gate.customer'].search([('fiscal_code', '=', 'RSSMRA80A01H501U')])
print(f"Admissibility requests: {customer.admissibility_count}")
print(f"Association requests: {customer.association_count}")
print(f"Disassociation requests: {customer.disassociation_count}")
print(f"Associated devices: {customer.device_count}")
```

### 3. API Synchronization
```python
# Sync all model types from API
env['chain2gate.admissibility.request'].sync_from_api()
env['chain2gate.association.request'].sync_from_api()
env['chain2gate.disassociation.request'].sync_from_api()
env['chain2gate.device'].sync_from_api()

# Sync specific customer (aggregates all related data)
env['chain2gate.customer'].sync_customer_from_api('RSSMRA80A01H501U')
```

### 4. Cross-Model Navigation
```python
# From association to disassociation
association = env['chain2gate.association.request'].browse(1)
disassociation = env['chain2gate.disassociation.request'].search([
    ('pod', '=', association.pod),
    ('serial', '=', association.serial),
    ('fiscal_code', '=', association.fiscal_code)
])

# From device to all requests
device = env['chain2gate.device'].browse(1)
device.action_view_associated_requests()  # Shows all association requests
```

## Enhanced Features

### Model-Specific Features
- **Admissibility**: POD eligibility checking
- **Association**: Customer-device linking with contract management
- **Disassociation**: Device unlinking with reference to original association
- **Device**: Technical device management with POD connections
- **Customer**: Complete customer lifecycle and relationship management

### Security Features
- **Company Isolation**: Each company gets unique encryption keys
- **Field-Level Encryption**: Only personal data is encrypted
- **Transparent Operations**: Encryption/decryption is automatic
- **Audit Trail**: All operations are logged for security

### Performance Features
- **Computed Fields**: Display names, counts, status indicators
- **Efficient Queries**: Proper indexing on key fields
- **Bulk Operations**: API sync handles large datasets
- **Caching**: Encryption sessions are cached per company

## Validation

### ✅ Complete Coverage Checklist
- [x] **AdmissibilityRequest** → `chain2gate.admissibility.request`
- [x] **AssociationRequest** → `chain2gate.association.request`
- [x] **DisassociationRequest** → `chain2gate.disassociation.request`
- [x] **Chain2GateDevice** → `chain2gate.device`
- [x] **Customer** → `chain2gate.customer`

### ✅ All Features Implemented
- [x] Automatic encryption/decryption
- [x] Dataclass ↔ Odoo record conversion
- [x] API synchronization
- [x] Company-specific encryption keys
- [x] Cross-model relationships
- [x] Enhanced UI views
- [x] Security access controls
- [x] Comprehensive error handling

## Conclusion

**All Chain2Gate SDK dataclasses are now fully mapped to Odoo models** with:
- Complete feature parity
- Automatic hierarchical encryption for personal data
- Seamless dataclass integration
- Enhanced Odoo-specific functionality
- Comprehensive relationship management

The integration provides a complete bridge between the Chain2Gate SDK and Odoo, maintaining all the power and flexibility of the original dataclasses while adding enterprise-grade security and Odoo's rich UI capabilities.