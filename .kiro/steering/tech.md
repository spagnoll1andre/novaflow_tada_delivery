---
inclusion: fileMatch
fileMatchPattern: 'export/*'
---

# Technology Stack (Export Package)

## Language & Framework
- **Python 3.7+**: Primary development language
- **requests**: HTTP client library for API communication
- **typing**: Type hints for better code documentation
- **dataclasses**: Structured data representation
- **enum**: Enumerated constants for status and device types

## Architecture Pattern
- **Modular SDK Design**: Core SDK with optional encryption extensions
- **Single-class SDK**: `Chain2GateSDK` provides all functionality
- **Encryption Layer**: Hierarchical and Odoo-specific encryption modules
- **Dataclass Models**: Structured data objects for API responses
- **Enum-based Constants**: Type-safe status and device type definitions
- **Session Management**: Persistent HTTP sessions with authentication headers

## API Integration
- **Base URL**: `https://chain2-api.chain2gate.it`
- **Authentication**: API key via `x-api-key` header
- **Content Type**: `application/json`
- **Pagination**: Automatic handling with `nextToken` support
- **Error Handling**: Structured error responses with status codes

## Common Development Commands
The SDK supports multiple usage patterns from the export package:

```python
# Package-level imports (recommended)
from export import Chain2GateSDK, Chain2GateEncryptedSDK, Chain2GateOdooSDK

# Direct module imports
from export.chain2gate_sdk import Chain2GateSDK
from export.chain2gate_encrypted_sdk import Chain2GateEncryptedSDK
from export.chain2gate_odoo_sdk import Chain2GateOdooSDK

# Basic SDK usage
sdk = Chain2GateSDK(api_key="your-api-key")

# Encrypted SDK usage
encrypted_sdk = Chain2GateEncryptedSDK(api_key="your-api-key")

# Odoo SDK usage
odoo_sdk = Chain2GateOdooSDK(api_key="your-api-key")

# Encryption utilities
from export.odoo_secure_encryption import OdooSecureEncryption
from export.hierarchical_encryption import HierarchicalEncryption

# Testing (manual)
python -c "from export import Chain2GateSDK; print('Import successful')"
```

## Dependencies
- `requests`: HTTP client
- `typing`: Type annotations (Python 3.7+)
- `dataclasses`: Data structures (Python 3.7+)
- `datetime`: Date/time handling
- `enum`: Enumerated types
- `cryptography`: Encryption and security operations
- `base64`: Encoding/decoding for encrypted data
- `json`: Data serialization

## Code Style
- Follow PEP 8 conventions
- Use type hints for all public methods
- Dataclasses for structured data
- Enums for constants
- Comprehensive docstrings