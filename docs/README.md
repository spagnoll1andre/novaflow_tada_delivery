# Chain2Gate Integration for Odoo

This Odoo module provides seamless integration between Odoo and the Chain2Gate IoT energy monitoring platform, enabling you to use Chain2Gate SDK dataclasses as Odoo models with automatic hierarchical encryption for personal data.

## Features

- **SDK Dataclass Integration**: Use existing Chain2Gate SDK dataclasses directly as Odoo models
- **Automatic Encryption**: Personal data fields are automatically encrypted using hierarchical encryption
- **Company-Specific Security**: Each company gets its own encryption keys
- **API Synchronization**: Bidirectional sync with Chain2Gate API
- **Device Management**: Manage Chain2Gate energy monitoring devices
- **Request Handling**: Handle admissibility and association requests

## Models Included

- **Admissibility Requests** (`chain2gate.admissibility.request`)
- **Association Requests** (`chain2gate.association.request`)
- **Chain2Gate Devices** (`chain2gate.device`)

## Installation

1. **Install Python Dependencies**:
   ```bash
   pip install cryptography boto3 requests
   ```

2. **Configure AWS Credentials**:
   - Set up AWS credentials for Secrets Manager access
   - Ensure proper IAM permissions for Secrets Manager operations

3. **Install Module**:
   - Copy this folder to your Odoo addons directory
   - Update apps list in Odoo
   - Install "Chain2Gate Integration" module

4. **Configure Integration**:
   - Go to Settings → Chain2Gate
   - Click "Configuration Wizard"
   - Follow the setup steps

## Configuration

### Using the Configuration Wizard

1. Navigate to `Settings → Chain2Gate`
2. Click `Configuration Wizard`
3. Enter your Chain2Gate API key
4. Configure AWS settings:
   - AWS Region (default: us-east-1)
   - Master Secret Name (default: hibe/master-key)
5. Test connection and encryption
6. Initialize master key if needed
7. Save configuration

### Manual Configuration

Set the following system parameters in `Settings → Technical → Parameters → System Parameters`:

- `chain2gate.api_key`: Your Chain2Gate API key
- `chain2gate.base_url`: API base URL (default: https://chain2-api.chain2gate.it)
- `chain2gate.aws_region`: AWS region for Secrets Manager
- `chain2gate.master_secret_name`: Master key secret name in AWS

## Usage

### Creating Records from Dataclasses

```python
from odoo import api, SUPERUSER_ID

# In Odoo shell or custom code
env = api.Environment(cr, SUPERUSER_ID, {})

# Create from SDK dataclass
from addons.chain2gate_integration.models.chain2gate_sdk import AdmissibilityRequest, Status

request_data = AdmissibilityRequest(
    id="req_123",
    pod="IT001E12345678",
    status=Status.PENDING,
    fiscal_code="RSSMRA80A01H501U",  # Automatically encrypted
    # ... other fields
)

# Create Odoo record (encryption happens automatically)
odoo_record = env['chain2gate.admissibility.request'].from_dataclass(request_data)
```

### API Synchronization

```python
# Sync from Chain2Gate API
env['chain2gate.admissibility.request'].sync_from_api()
env['chain2gate.association.request'].sync_from_api()
env['chain2gate.device'].sync_from_api()
```

### Working with Encrypted Fields

```python
# Create record with personal data
record = env['chain2gate.association.request'].create({
    'pod': 'IT001E12345678',
    'serial': 'DEV123456',
    'first_name': 'Mario',  # Automatically encrypted
    'last_name': 'Rossi',   # Automatically encrypted
    'email': 'mario.rossi@example.com',  # Automatically encrypted
    'fiscal_code': 'RSSMRA80A01H501U',   # Automatically encrypted
    'pod_m_type': 'M1',
    'user_type': 'CONSUMER',
})

# Read decrypted values
print(record.first_name)  # Shows "Mario" (automatically decrypted)
print(record.first_name_encrypted)  # Shows encrypted data (for debugging)
```

## Security Features

### Hierarchical Encryption
- Master key stored in AWS Secrets Manager
- Company-specific keys derived using HKDF
- AES-256-GCM encryption for all personal data

### Field-Level Encryption
Only personal data fields are encrypted:
- `first_name`, `last_name`, `email`, `fiscal_code` in association requests
- `fiscal_code` in admissibility requests
- Technical fields (POD, serial, status, etc.) remain unencrypted for searching

### Session Management
- Automatic session lifecycle management
- Session timeout and cleanup
- Rate limiting protection
- Thread-safe operations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Odoo User Interface                          │
├─────────────────────────────────────────────────────────────────┤
│                    Odoo Models Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Admissibility   │  │ Association     │  │ Chain2Gate      │ │
│  │ Request Model   │  │ Request Model   │  │ Device Model    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│              Chain2Gate Dataclass Mixin                        │
│  • Automatic encryption/decryption                             │
│  • Dataclass ↔ Odoo record conversion                         │
│  • Company-specific encryption keys                            │
├─────────────────────────────────────────────────────────────────┤
│                Chain2Gate Odoo SDK                             │
│  • Session management                                          │
│  • API integration                                             │
│  • Error handling                                              │
├─────────────────────────────────────────────────────────────────┤
│              Hierarchical Encryption                           │
│  • AWS Secrets Manager                                         │
│  • Company-specific key derivation                             │
│  • AES-256-GCM encryption                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Common Issues

1. **"Master key not found"**
   - Run the configuration wizard
   - Initialize master key in AWS Secrets Manager

2. **"Session expired"**
   - Automatic recovery should handle this
   - Check AWS credentials and permissions

3. **"API connection failed"**
   - Check API key configuration
   - Verify network connectivity
   - Check Chain2Gate API status

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('odoo.addons.chain2gate_integration').setLevel(logging.DEBUG)
```

Check session info:
```python
sdk = record.get_sdk_instance()
session_info = sdk.get_session_info()
print(session_info)
```

## Requirements

- Odoo 14.0+ (compatible with 15.0, 16.0, 17.0)
- Python 3.7+
- AWS account with Secrets Manager access
- Chain2Gate API key

## Dependencies

- `cryptography` - Encryption operations
- `boto3` - AWS Secrets Manager integration
- `requests` - HTTP API communication

## License

LGPL-3 (compatible with Odoo)

## Support

For issues and questions:
- Check the troubleshooting section above
- Review Odoo logs for detailed error messages
- Verify AWS and Chain2Gate API connectivity
- Contact Chain2Gate support for API-related issues

## Version

1.0.0 - Initial release with full dataclass integration and hierarchical encryption