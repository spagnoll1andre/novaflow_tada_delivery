---
inclusion: fileMatch
fileMatchPattern: 'export/*'
---

# Product Overview (Export Package)

Chain2Gate SDK is a Python SDK for managing IoT energy monitoring devices through the Chain2Gate API. The SDK provides a modular interface for handling device associations, admissibility requests, and energy meter management, with optional encryption and Odoo integration capabilities.

## Core Functionality (export/ package)
- **Device Association Management**: Handle association/disassociation requests for energy meters
- **Admissibility Verification**: Check POD (Point of Delivery) eligibility for Chain2Gate services  
- **Device Management**: Query and manage various types of energy monitoring devices
- **Customer Management**: Comprehensive customer information aggregation
- **Security & Encryption**: Hierarchical encryption and secure data handling
- **Odoo Integration**: Specialized SDK and encryption for Odoo ERP systems

## SDK Variants Available
- **Chain2GateSDK**: Core functionality without encryption
- **Chain2GateEncryptedSDK**: Enhanced security with encryption layer
- **Chain2GateOdooSDK**: Specialized implementation for Odoo integration

## Device Types Supported
- Energy meters (monophase/triphase)
- Smart plugs
- DIN rail devices
- Modbus devices
- Engine monitoring devices

## Key Concepts
- **POD**: Point of Delivery identifier for energy connections
- **M1/M2 Meters**: M1 for consumption, M2/M2_2/M2_3/M2_4 for production
- **User Types**: PROSUMER (produces energy) vs CONSUMER (consumes only)
- **Request Lifecycle**: PENDING → AWAITING → ADMISSIBLE/ASSOCIATED → TAKEN_IN_CHARGE