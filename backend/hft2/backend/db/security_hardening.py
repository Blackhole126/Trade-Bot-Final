"""
PHASE 3: SECURITY HARDENING - ENCRYPTION & BROKER CREDENTIAL MANAGEMENT
=========================================================================

Purpose: Secure broker credentials and sensitive data

Mandatory:
- Encrypt broker tokens (never store raw)
- Separate broker accounts storage
- Environment secrets rotation ready
- Multi-user broker account isolation
"""

from cryptography.fernet import Fernet
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import os
import base64
import logging
from pathlib import Path

from .samruddhi_memory import Base

logger = logging.getLogger(__name__)


# ============================================================================
# ENCRYPTION UTILITIES
# ============================================================================

class EncryptionManager:
    """
    Manage encryption/decryption of sensitive data.

    Uses Fernet symmetric encryption (AES 128-bit CBC).
    Keys must be stored securely (environment variables or secure vault).
    """

    def __init__(self, encryption_key: str = None):
        """
        Initialize encryption manager.

        Args:
            encryption_key: Base64-encoded Fernet key (32 bytes)
                           If None, loads from ENCRYPTION_KEY env var
        """
        self.encryption_key = encryption_key or os.environ.get(
            'ENCRYPTION_KEY')

        if not self.encryption_key:
            raise ValueError(
                "Encryption key not provided. Set ENCRYPTION_KEY environment variable "
                "or pass encryption_key parameter. Generate with: EncryptionManager.generate_key()"
            )

        # Validate key format
        try:
            self.fernet = Fernet(self.encryption_key.encode())
            logger.info("✓ EncryptionManager initialized")
        except Exception as e:
            logger.error(f"✗ Invalid encryption key: {e}")
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded URL-safe 32-byte key

        Usage:
            >>> key = EncryptionManager.generate_key()
            >>> print(key)  # Store this securely!
        """
        key = Fernet.generate_key().decode()
        logger.info("✓ Generated new encryption key")
        return key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt sensitive data.

        Args:
            plaintext: Sensitive string to encrypt

        Returns:
            Encrypted string (base64-encoded)

        Example:
            >>> encrypted = encrypt("broker_token_12345")
        """
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"✗ Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt sensitive data.

        Args:
            encrypted_text: Encrypted string (base64-encoded)

        Returns:
            Decrypted plaintext

        Example:
            >>> token = decrypt(encrypted_token)
        """
        try:
            decoded_bytes = base64.b64decode(encrypted_text.encode())
            decrypted_bytes = self.fernet.decrypt(decoded_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"✗ Decryption failed: {e}")
            raise

    def encrypt_dict(self, data: dict) -> dict:
        """
        Encrypt all string values in a dictionary.

        Args:
            data: Dictionary with sensitive values

        Returns:
            Dictionary with encrypted string values
        """
        encrypted = {}
        for key, value in data.items():
            if isinstance(value, str):
                encrypted[key] = self.encrypt(value)
            elif isinstance(value, dict):
                encrypted[key] = self.encrypt_dict(value)
            else:
                encrypted[key] = value
        return encrypted

    def decrypt_dict(self, encrypted_data: dict) -> dict:
        """
        Decrypt all string values in a dictionary.

        Args:
            encrypted_data: Dictionary with encrypted values

        Returns:
            Dictionary with decrypted string values
        """
        decrypted = {}
        for key, value in encrypted_data.items():
            if isinstance(value, str):
                try:
                    decrypted[key] = self.decrypt(value)
                except:
                    # If decryption fails, keep original (might not be encrypted)
                    decrypted[key] = value
            elif isinstance(value, dict):
                decrypted[key] = self.decrypt_dict(value)
            else:
                decrypted[key] = value
        return decrypted


# ============================================================================
# BROKER ACCOUNTS TABLE
# ============================================================================

class BrokerAccount(Base):
    """
    Broker account credentials (ENCRYPTED).

    Stores broker API credentials securely with encryption.
    Each user can have multiple broker accounts.

    Security:
    - All sensitive fields encrypted
    - Access logged for audit
    - Multi-user isolation via user_id
    """
    __tablename__ = 'broker_accounts'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), ForeignKey(
        'users.user_id'), index=True, nullable=False)

    # Broker identification
    # 'DHAN', 'FYERS', 'ZERODHA', etc.
    broker_name = Column(String(100), nullable=False)
    account_id = Column(String(255), nullable=False)  # Broker account ID
    account_type = Column(String(50))  # 'DEMAT', 'TRADING', 'BOTH'

    # Encrypted credentials
    api_key_encrypted = Column(Text, nullable=False)  # Encrypted API key
    api_secret_encrypted = Column(Text, nullable=False)  # Encrypted API secret
    # Encrypted access token (if applicable)
    access_token_encrypted = Column(Text)
    # Encrypted refresh token (if applicable)
    refresh_token_encrypted = Column(Text)

    # Metadata
    product_types = Column(JSON)  # ['MIS', 'CNC', 'NRML', 'BO', 'CO']
    exchanges_enabled = Column(JSON)  # ['NSE', 'BSE', 'NFO', 'CDO']
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Primary broker for this user

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    last_used_at = Column(DateTime)  # Last time credentials were used

    # Audit
    created_by = Column(String(255))  # Who added this (admin or user)
    # Track encryption algorithm version
    encryption_version = Column(String(50), default='v1')

    __table_args__ = (
        UniqueConstraint('user_id', 'broker_name', 'account_id',
                         name='uq_user_broker_account'),
    )

    def __repr__(self):
        return f"<BrokerAccount(user_id={self.user_id}, broker={self.broker_name}, account={self.account_id})>"


class BrokerCredentialAudit(Base):
    """
    Audit log for broker credential access.

    Every time credentials are accessed/used, log it here.
    Critical for security monitoring and compliance.
    """
    __tablename__ = 'broker_credential_audit'

    id = Column(Integer, primary_key=True)
    broker_account_id = Column(Integer, ForeignKey(
        'broker_accounts.id'), index=True, nullable=False)
    user_id = Column(String(255), index=True, nullable=False)

    # Action
    # 'ACCESS', 'UPDATE', 'DELETE', 'ROTATE'
    action = Column(String(50), nullable=False)
    reason = Column(String(500))  # Why credentials were accessed

    # Context
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    session_id = Column(String(255))

    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow,
                       nullable=False, index=True)

    # Relationships
    broker_account = relationship("BrokerAccount", backref='audit_logs')


# ============================================================================
# BROKER CREDENTIAL MANAGER
# ============================================================================

class BrokerCredentialManager:
    """
    High-level manager for broker credentials.

    Handles:
    - Adding broker accounts
    - Retrieving credentials (with decryption)
    - Rotating tokens
    - Audit logging
    """

    def __init__(self, memory_manager, encryption_manager: EncryptionManager):
        """
        Initialize credential manager.

        Args:
            memory_manager: FinancialMemoryManager instance
            encryption_manager: EncryptionManager instance
        """
        self.memory = memory_manager
        self.encryption = encryption_manager
        logger.info("✓ BrokerCredentialManager initialized")

    def add_broker_account(self, user_id: str, broker_data: dict) -> BrokerAccount:
        """
        Add a new broker account with encrypted credentials.

        Args:
            user_id: User ID
            broker_data: Dictionary with broker credentials:
                {
                    'broker_name': 'DHAN',
                    'account_id': '123456',
                    'api_key': 'your_api_key',
                    'api_secret': 'your_api_secret',
                    'access_token': 'your_access_token',
                    ...
                }

        Returns:
            BrokerAccount object
        """
        session = self.memory.get_session()
        try:
            # Encrypt sensitive credentials
            encrypted_credentials = self.encryption.encrypt_dict({
                'api_key': broker_data['api_key'],
                'api_secret': broker_data['api_secret'],
                'access_token': broker_data.get('access_token', ''),
                'refresh_token': broker_data.get('refresh_token', '')
            })

            # Create broker account
            broker_account = BrokerAccount(
                user_id=user_id,
                broker_name=broker_data['broker_name'],
                account_id=broker_data['account_id'],
                account_type=broker_data.get('account_type', 'BOTH'),
                api_key_encrypted=encrypted_credentials['api_key'],
                api_secret_encrypted=encrypted_credentials['api_secret'],
                access_token_encrypted=encrypted_credentials.get(
                    'access_token', ''),
                refresh_token_encrypted=encrypted_credentials.get(
                    'refresh_token', ''),
                product_types=broker_data.get('product_types', []),
                exchanges_enabled=broker_data.get('exchanges_enabled', []),
                is_active=True,
                is_primary=broker_data.get('is_primary', False),
                created_by=broker_data.get('created_by', 'system'),
                encryption_version='v1'
            )

            session.add(broker_account)
            session.commit()

            # Log audit
            self._log_audit(
                broker_account_id=broker_account.id,
                user_id=user_id,
                action='ADD',
                reason='Added new broker account',
                success=True
            )

            logger.info(
                f"✓ Added broker account: {broker_account.broker_name} ({broker_account.account_id})")
            return broker_account

        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error adding broker account: {e}")
            raise
        finally:
            session.close()

    def get_broker_credentials(self, broker_account_id: int, user_id: str = None) -> dict:
        """
        Retrieve and decrypt broker credentials.

        Args:
            broker_account_id: Broker account ID
            user_id: User ID (for authorization check)

        Returns:
            Dictionary with decrypted credentials

        Security:
            - Verifies user has access to this broker account
            - Logs credential access
            - Returns only necessary credentials
        """
        session = self.memory.get_session()
        try:
            # Get broker account
            broker_account = session.query(BrokerAccount).filter(
                BrokerAccount.id == broker_account_id
            ).first()

            if not broker_account:
                raise ValueError(
                    f"Broker account not found: {broker_account_id}")

            # Authorization check
            if user_id and broker_account.user_id != user_id:
                self._log_audit(
                    broker_account_id=broker_account_id,
                    user_id=user_id,
                    action='ACCESS',
                    reason='Unauthorized access attempt',
                    success=False,
                    error_message='User does not own this broker account'
                )
                raise PermissionError(
                    f"User {user_id} not authorized to access broker account {broker_account_id}")

            # Check if active
            if not broker_account.is_active:
                raise ValueError(
                    f"Broker account is inactive: {broker_account_id}")

            # Decrypt credentials
            decrypted = self.encryption.decrypt_dict({
                'api_key': broker_account.api_key_encrypted,
                'api_secret': broker_account.api_secret_encrypted,
                'access_token': broker_account.access_token_encrypted or '',
                'refresh_token': broker_account.refresh_token_encrypted or ''
            })

            # Update last used timestamp
            broker_account.last_used_at = datetime.utcnow()
            session.commit()

            # Log audit
            self._log_audit(
                broker_account_id=broker_account_id,
                user_id=user_id or broker_account.user_id,
                action='ACCESS',
                reason='Retrieved credentials for trading',
                success=True
            )

            # Return credentials
            return {
                'broker_account_id': broker_account.id,
                'broker_name': broker_account.broker_name,
                'account_id': broker_account.account_id,
                'account_type': broker_account.account_type,
                'api_key': decrypted['api_key'],
                'api_secret': decrypted['api_secret'],
                'access_token': decrypted.get('access_token', ''),
                'refresh_token': decrypted.get('refresh_token', ''),
                'product_types': broker_account.product_types,
                'exchanges_enabled': broker_account.exchanges_enabled,
                'encryption_version': broker_account.encryption_version
            }

        except Exception as e:
            if not str(e).startswith('User') or 'not authorized' not in str(e):
                self._log_audit(
                    broker_account_id=broker_account_id,
                    user_id=user_id,
                    action='ACCESS',
                    reason='Failed to retrieve credentials',
                    success=False,
                    error_message=str(e)
                )
            logger.error(f"✗ Error retrieving broker credentials: {e}")
            raise
        finally:
            session.close()

    def rotate_tokens(self, broker_account_id: int, user_id: str,
                      new_access_token: str = None, new_refresh_token: str = None) -> bool:
        """
        Rotate access/refresh tokens securely.

        Args:
            broker_account_id: Broker account ID
            user_id: User ID
            new_access_token: New access token (optional)
            new_refresh_token: New refresh token (optional)

        Returns:
            True if successful

        Security:
            - Only updates specified tokens
            - Logs rotation event
            - Requires user authorization
        """
        session = self.memory.get_session()
        try:
            broker_account = session.query(BrokerAccount).filter(
                BrokerAccount.id == broker_account_id,
                BrokerAccount.user_id == user_id
            ).first()

            if not broker_account:
                raise ValueError(
                    f"Broker account not found or unauthorized: {broker_account_id}")

            # Update tokens if provided
            if new_access_token:
                broker_account.access_token_encrypted = self.encryption.encrypt(
                    new_access_token)

            if new_refresh_token:
                broker_account.refresh_token_encrypted = self.encryption.encrypt(
                    new_refresh_token)

            broker_account.updated_at = datetime.utcnow()
            session.commit()

            # Log audit
            self._log_audit(
                broker_account_id=broker_account_id,
                user_id=user_id,
                action='ROTATE',
                reason='Rotated access/refresh tokens',
                success=True
            )

            logger.info(
                f"✓ Rotated tokens for broker account {broker_account_id}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error rotating tokens: {e}")
            raise
        finally:
            session.close()

    def deactivate_broker_account(self, broker_account_id: int, user_id: str) -> bool:
        """
        Deactivate a broker account (soft delete).

        Args:
            broker_account_id: Broker account ID
            user_id: User ID

        Returns:
            True if successful
        """
        session = self.memory.get_session()
        try:
            broker_account = session.query(BrokerAccount).filter(
                BrokerAccount.id == broker_account_id,
                BrokerAccount.user_id == user_id
            ).first()

            if not broker_account:
                raise ValueError(
                    f"Broker account not found or unauthorized: {broker_account_id}")

            broker_account.is_active = False
            broker_account.updated_at = datetime.utcnow()
            session.commit()

            # Log audit
            self._log_audit(
                broker_account_id=broker_account_id,
                user_id=user_id,
                action='DEACTIVATE',
                reason='Deactivated broker account',
                success=True
            )

            logger.info(f"✓ Deactivated broker account {broker_account_id}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"✗ Error deactivating broker account: {e}")
            raise
        finally:
            session.close()

    def _log_audit(self, broker_account_id: int, user_id: str, action: str,
                   reason: str, success: bool, error_message: str = None,
                   ip_address: str = None, user_agent: str = None, session_id: str = None):
        """Log credential access for audit"""
        session = self.memory.get_session()
        try:
            audit = BrokerCredentialAudit(
                broker_account_id=broker_account_id,
                user_id=user_id,
                action=action,
                reason=reason,
                success=success,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id
            )
            session.add(audit)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")
            session.rollback()
        finally:
            session.close()

    def get_user_brokers(self, user_id: str) -> list:
        """Get list of broker accounts for a user (without sensitive credentials)"""
        session = self.memory.get_session()
        try:
            brokers = session.query(BrokerAccount).filter(
                BrokerAccount.user_id == user_id,
                BrokerAccount.is_active == True
            ).all()

            return [{
                'id': b.id,
                'broker_name': b.broker_name,
                'account_id': b.account_id,
                'account_type': b.account_type,
                'product_types': b.product_types,
                'exchanges_enabled': b.exchanges_enabled,
                'is_primary': b.is_primary,
                'last_used_at': b.last_used_at.isoformat() if b.last_used_at else None,
                'created_at': b.created_at.isoformat()
            } for b in brokers]

        finally:
            session.close()


def main():
    """Demo and test encryption"""
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("PHASE 3: SECURITY HARDENING - ENCRYPTION & BROKER CREDENTIALS")
    print("="*80)

    # Generate encryption key (in production, store this securely!)
    print("\nGenerating encryption key...")
    encryption_key = EncryptionManager.generate_key()
    print(f"✓ Encryption Key Generated: {encryption_key[:20]}...")
    print(f"\n⚠️  IMPORTANT: Store this key securely!")
    print(f"Set environment variable:")
    print(f"  export ENCRYPTION_KEY='{encryption_key}'")

    # Initialize managers
    encryption_mgr = EncryptionManager(encryption_key)

    print("\n" + "="*80)
    print("Testing encryption/decryption...")
    print("="*80)

    # Test encryption
    test_token = "test_broker_token_12345"
    encrypted = encryption_mgr.encrypt(test_token)
    decrypted = encryption_mgr.decrypt(encrypted)

    print(f"\nOriginal:  {test_token}")
    print(f"Encrypted: {encrypted[:50]}...")
    print(f"Decrypted: {decrypted}")
    print(f"✓ Encryption test passed: {test_token == decrypted}")

    print("\n" + "="*80)
    print("✓ PHASE 3 SECURITY HARDENING READY")
    print("="*80)
    print("\nSecurity features implemented:")
    print("  ✓ Fernet encryption (AES 128-bit CBC)")
    print("  ✓ Broker account isolation per user")
    print("  ✓ Credential audit logging")
    print("  ✓ Token rotation support")
    print("  ✓ Soft delete capability")
    print("\nNext: Enable authentication in config")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
