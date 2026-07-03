import base64
import hashlib
from django.conf import settings
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes

class FieldEncryptor:
    """Helper class to encrypt and decrypt database field values using AES-256-GCM."""
    def __init__(self):
        # Derive a 256-bit key from Django's SECRET_KEY or a specific FIELD_ENCRYPTION_KEY
        key_source = getattr(settings, 'FIELD_ENCRYPTION_KEY', settings.SECRET_KEY)
        if isinstance(key_source, str):
            key_source = key_source.encode('utf-8')
        self.key = hashlib.sha256(key_source).digest()

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            return None
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)
        if plaintext == "":
            return ""
        
        iv = get_random_bytes(12) # Standard IV size for GCM
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=iv)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        
        # Combine iv (12 bytes), tag (16 bytes), and ciphertext
        combined = iv + tag + ciphertext
        return base64.b64encode(combined).decode('utf-8')

    def decrypt(self, ciphertext_b64: str) -> str:
        if ciphertext_b64 is None:
            return None
        if ciphertext_b64 == "":
            return ""
        
        try:
            combined = base64.b64decode(ciphertext_b64.encode('utf-8'))
            if len(combined) < 28:
                return ciphertext_b64 # Fallback if not actually encrypted
            
            iv = combined[:12]
            tag = combined[12:28]
            ciphertext = combined[28:]
            
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=iv)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)
            return decrypted.decode('utf-8')
        except Exception:
            # If decryption fails (e.g. data not encrypted, or wrong key), return original
            return ciphertext_b64

# Global instance for easy reuse
encryptor = FieldEncryptor()
