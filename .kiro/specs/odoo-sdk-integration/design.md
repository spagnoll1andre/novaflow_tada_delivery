# Design Document

## Overview

The Odoo SDK Integration creates a new Chain2Gate SDK variant (`Chain2GateOdooSDK`) that replaces the basic Fernet encryption with Odoo-compliant hierarchical encryption. This design maintains API compatibility with the existing encrypted SDK while providing enhanced security through company-specific encryption keys and thread-local session management.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Chain2GateOdooSDK                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   Encryption    │    │        SDK Methods              │ │
│  │   Layer         │    │  - get_*_requests()             │ │
│  │                 │    │  - create_*_request()           │ │
│  │ ┌─────────────┐ │    │  - get_customer_info()          │ │
│  │ │OdooSecure   │ │    │  - associate_customer_device()  │ │
│  │ │Encryption   │ │    └─────────────────────────────────┘ │
│  │ └─────────────┘ │                    │                   │
│  └─────────────────┘                    │                   │
├─────────────────────────────────────────┼───────────────────┤
│              Chain2GateSDK (Base)       │                   │
│  ┌─────────────────────────────────────┐ │                   │
│  │        HTTP Client & API Logic      │ │                   │
│  │  - _request()                       │ │                   │
│  │  - _paginate()                      │ │                   │
│  │  - Session management               │ │                   │
│  └─────────────────────────────────────┘ │                   │
└─────────────────────────────────────────┼───────────────────┘
                                          │
                                          ▼
                                ┌─────────────────┐
                                │   Chain2Gate    │
                                │      API        │
                                └─────────────────┘
```

### Component Integration

The design follows a layered approach where:
1. **Base SDK Layer**: Handles HTTP communication and API logic
2. **Encryption Layer**: Manages Odoo-compliant encryption/decryption
3. **SDK Interface Layer**: Provides the same interface as the encrypted SDK

## Components and Interfaces

### Core Components

#### 1. Chain2GateOdooSDK Class

```python
class Chain2GateOdooSDK(Chain2GateSDK):
    def __init__(self, api_key: str, company_id: str = "default", 
                 base_url: str = "https://chain2-api.chain2gate.it",
                 region_name: str = 'us-east-1',
                 master_secret_name: str = 'hibe/master-key')
```

**Responsibilities:**
- Initialize Odoo secure encryption with company-specific settings
- Manage encryption sessions automatically
- Override parent methods to add encryption/decryption logic
- Maintain API compatibility with Chain2GateEncryptedSDK

#### 2. Encryption Integration Layer

**Key Methods:**
- `_encrypt_field(value: str) -> str`: Encrypt personal data fields
- `_decrypt_field(encrypted_value: str) -> str`: Decrypt personal data fields
- `_ensure_session_active() -> None`: Ensure encryption session is active
- `_handle_encryption_error(error: Exception) -> Dict`: Handle encryption errors

#### 3. Data Model Reuse

The design reuses the encrypted dataclasses from `chain2gate_encrypted_sdk.py`:
- `EncryptedAdmissibilityRequest`
- `EncryptedAssociationRequest`
- `EncryptedDisassociationRequest`
- `EncryptedCustomer`

### Interface Design

#### Session Management Interface

```python
# Automatic session management
def _ensure_session_active(self) -> None:
    """Ensure encryption session is active, start if needed"""

def _cleanup_session(self) -> None:
    """Clean up encryption session on SDK destruction"""

def get_session_info(self) -> Dict[str, Any]:
    """Get current session information for debugging"""
```

#### Encryption Interface

```python
# Field-level encryption
def _encrypt_personal_field(self, value: str) -> str:
    """Encrypt a personal data field using company-specific key"""

def _decrypt_personal_field(self, encrypted_value: str) -> str:
    """Decrypt a personal data field using company-specific key"""

# Batch encryption for efficiency
def _encrypt_personal_fields(self, fields: Dict[str, str]) -> Dict[str, str]:
    """Encrypt multiple fields in a single operation"""
```

## Data Models

### Personal Information Fields

Based on analysis of `chain2gate_encrypted_sdk.py`, the following fields are considered personal information and require encryption:

**Always Encrypted:**
- `fiscal_code`: Personal tax identifier
- `first_name`: Personal name information
- `last_name`: Personal name information  
- `email`: Personal contact information

**Never Encrypted:**
- `pod`: Point of delivery identifier (location/device)
- `serial`: Device serial number
- `id`: Request/record identifiers
- `status`: Business status enums
- `user_type`: Business classification
- `group`: Business grouping
- `created_at`, `updated_at`: Timestamps
- `contract_signed`: Boolean flags

### Encryption Metadata

Each encrypted field will include metadata for proper decryption:

```python
@dataclass
class EncryptedFieldMetadata:
    company_id: str
    encrypted_at: float
    nonce: str  # Base64 encoded nonce for AES-GCM
```

## Error Handling

### Error Categories

1. **Encryption Errors**
   - Session not active
   - Rate limit exceeded
   - Key derivation failure
   - Encryption/decryption failure

2. **API Errors**
   - Network failures
   - Authentication errors
   - Invalid request data

3. **Session Management Errors**
   - Session expiration
   - Thread safety issues
   - Resource cleanup failures

### Error Response Format

All errors maintain compatibility with the base SDK format:

```python
{
    "error": True,
    "status_code": int,
    "message": str,
    "error_type": str,  # "encryption", "api", "session"
    "details": Dict[str, Any]  # Additional error context
}
```

### Error Handling Strategy

1. **Graceful Degradation**: If encryption fails, log the error and return a structured error response
2. **Session Recovery**: Attempt to restart sessions on certain failures
3. **Rate Limiting**: Respect Odoo's rate limiting and provide clear feedback
4. **Audit Logging**: Log all security-related events through Odoo's audit system

## Testing Strategy

### Unit Testing

1. **Encryption Layer Tests**
   - Test field encryption/decryption with various inputs
   - Test session management lifecycle
   - Test error handling for encryption failures
   - Test rate limiting behavior

2. **SDK Integration Tests**
   - Test all public methods return encrypted data
   - Test API compatibility with base SDK
   - Test error response format consistency
   - Test session cleanup on SDK destruction

3. **Data Model Tests**
   - Test encrypted dataclass creation and conversion
   - Test field validation and type safety
   - Test serialization/deserialization of encrypted data

### Integration Testing

1. **Odoo Environment Tests**
   - Test thread-local storage behavior
   - Test session management in multi-threaded environment
   - Test integration with Odoo's request lifecycle
   - Test audit logging integration

2. **API Compatibility Tests**
   - Test drop-in replacement for Chain2GateEncryptedSDK
   - Test method signature compatibility
   - Test return type compatibility
   - Test error handling compatibility

### Security Testing

1. **Encryption Validation**
   - Verify personal data is never stored in plaintext
   - Test key isolation between companies
   - Test session security and cleanup
   - Test rate limiting enforcement

2. **Audit Testing**
   - Verify all security events are logged
   - Test audit log format and content
   - Test security event correlation

## Implementation Considerations

### Performance Optimizations

1. **Key Caching**: Cache derived company keys in thread-local storage
2. **Batch Operations**: Encrypt/decrypt multiple fields in single operations
3. **Lazy Session Initialization**: Start sessions only when needed
4. **Connection Pooling**: Reuse HTTP sessions from base SDK

### Security Considerations

1. **Memory Management**: Ensure sensitive data is cleared from memory
2. **Thread Safety**: Use thread-local storage for all encryption state
3. **Key Rotation**: Support for key rotation through session restart
4. **Audit Compliance**: Comprehensive logging for security events

### Compatibility Requirements

1. **API Compatibility**: Maintain exact method signatures from Chain2GateEncryptedSDK
2. **Data Structure Compatibility**: Use same encrypted dataclasses
3. **Error Format Compatibility**: Return errors in same format as base SDK
4. **Import Compatibility**: Allow easy migration from existing encrypted SDK