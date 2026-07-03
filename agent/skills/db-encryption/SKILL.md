---
name: django-field-encryption
description: Enforces the use of django-cryptography or specialized EncryptedFields for incident data. Use this whenever generating models for incidents, biodata, or fingerprints.
---
# Security Mandate: Field Encryption
When writing or updating Django models, you MUST use `django-cryptography` or `django-encrypted-model-fields`.
1. Sensitive fields like `incident_details`, `fingerprint_minutiae`, and `phone_number` must be wrapped in `EncryptedCharField` or `EncryptedTextField`.
2. Ensure encryption keys are loaded exclusively from server environment variables, never hardcoded.


# django-field-encryption

## Name: django-field-encryption

## Description
Enforces the use of `django-cryptography` or specialized `EncryptedFields` for incident data. Use this whenever generating models for incidents, biodata, or fingerprints.

## Use Case
Use this skill when:
- Creating new Django models that will store sensitive PII.
- Modifying existing models to add encrypted fields.
- Updating serializers or viewsets to handle encrypted data correctly.

## Workflow
1.  **Identify Sensitive Fields**: Determine which fields require encryption (e.g., names, addresses, biometrics, case details).
2.  **Implement Encryption**: Use `EncryptedCharField`, `EncryptedTextField`, or `FernetField`.
3.  **Configure Settings**: Ensure `ENCRYPTION_KEY` is loaded from environment variables.
4.  **Validate Data Flow**: Verify that encryption/decryption happens automatically in the ORM.

## Output Format
When implementing this skill, provide the updated model code with:
```python
from django.db import models
from django_cryptography.fields import EncryptedTextField

class SensitiveRecord(models.Model):
    # Encrypted field - automatic encryption/decryption
    data = EncryptedTextField()
    
    # Standard field - no encryption
    metadata = models.JSONField()
```
