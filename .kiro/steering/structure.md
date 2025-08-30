---
inclusion: fileMatch
fileMatchPattern: 'export/*'
---

# Export Directory Structure

## File Organization (export/ directory focus)
```
export/
├── __init__.py                     # Package initialization and exports
├── chain2gate_sdk.py               # Core SDK implementation
├── chain2gate_encrypted_sdk.py     # Encrypted version of SDK
├── chain2gate_odoo_sdk.py          # Odoo-specific SDK implementation
├── hierarchical_encryption.py      # Hierarchical encryption utilities
├── odoo_secure_encryption.py       # Odoo-specific secure encryption
├── MAC_API_doc.md                  # API documentation
└── README_ODOO_INTEGRATION.md      # Odoo integration guide
```

## Code Architecture

### Main SDK Files
The SDK is organized across multiple files in the `export/` directory:

#### Core SDK (`export/chain2gate_sdk.py`)
The main SDK implementation with the following structure:

1. **Imports & Dependencies** - Standard library and requests
2. **Enums** - Status, PodMType, UserType, DeviceType constants
3. **Dataclasses** - Structured models for API responses
4. **Main SDK Class** - `Chain2GateSDK` with all functionality

### Class Organization within SDK
```python
# Enums (constants)
Status, PodMType, UserType, DeviceType

# Data Models
AdmissibilityRequest, AssociationRequest, DisassociationRequest
Chain2GateDevice, Customer

# Main SDK Class
Chain2GateSDK:
  ├── __init__()              # Initialize with API key
  ├── _request()              # Internal HTTP handler
  ├── _paginate()             # Pagination helper
  ├── Admissibility Methods   # get/create admissibility requests
  ├── Association Methods     # get/create association requests  
  ├── Disassociation Methods  # get/create disassociation requests
  ├── Device Methods          # query Chain2Gate devices
  └── Helper Methods          # customer info, debug utilities
```

## Method Grouping Conventions
- **Private methods**: Prefixed with `_` (e.g., `_request`, `_paginate`)
- **CRUD operations**: `get_*`, `create_*` patterns
- **Bulk operations**: `get_*_requests` for lists
- **Single item**: `get_*_request` for individual items
- **Helper methods**: Utility functions like `get_customer_info`

## Data Flow Pattern
1. **Input validation** via type hints and enums
2. **API request** through `_request()` method
3. **Response parsing** into dataclass objects
4. **Error handling** with structured error dictionaries
5. **Return typed objects** or error dictionaries

## Export Module Organization
- **Package Init**: `export/__init__.py` - Exports Chain2GateSDK, Chain2GateEncryptedSDK, Chain2GateOdooSDK
- **Core SDK**: `export/chain2gate_sdk.py` - Main API client functionality
- **Encrypted SDK**: `export/chain2gate_encrypted_sdk.py` - Enhanced security version
- **Odoo SDK**: `export/chain2gate_odoo_sdk.py` - Odoo-specific implementation
- **Encryption Utilities**: `export/hierarchical_encryption.py` - Hierarchical encryption tools
- **Odoo Encryption**: `export/odoo_secure_encryption.py` - Odoo-specific secure encryption

## Documentation Location (within export/)
- **API Reference**: `export/MAC_API_doc.md`
- **Integration Guide**: `export/README_ODOO_INTEGRATION.md`
- **Code Documentation**: Inline docstrings in SDK methods
- **Usage Examples**: Within method docstrings