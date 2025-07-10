"""
Encryption utilities for protecting sensitive data like credentials
"""

import os
import base64
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import getpass
import keyring

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, key_file: Optional[Path] = None):
        self.key_file = key_file or Path("data/.encryption_key")
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = None
        self._key = None
        
        # Service name for keyring storage
        self.service_name = "ai_test_automation_tool"
        
    def _get_or_create_key(self, password: Optional[str] = None) -> bytes:
        """Get existing encryption key or create a new one"""
        
        # Try to load existing key
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    encrypted_key = f.read()
                
                if password:
                    # Decrypt the key using password
                    return self._decrypt_key_with_password(encrypted_key, password)
                else:
                    # Try to get password from keyring
                    stored_password = keyring.get_password(self.service_name, "encryption_key")
                    if stored_password:
                        return self._decrypt_key_with_password(encrypted_key, stored_password)
                    else:
                        # Key exists but no password available
                        raise ValueError("Encryption key exists but password not available")
            
            except Exception as e:
                logging.warning(f"Failed to load existing encryption key: {e}")
        
        # Create new key
        return self._create_new_key(password)
    
    def _create_new_key(self, password: Optional[str] = None) -> bytes:
        """Create a new encryption key"""
        
        # Generate a new Fernet key
        key = Fernet.generate_key()
        
        if password is None:
            # Prompt for password if not provided
            password = getpass.getpass("Enter password for encryption key: ")
            confirm_password = getpass.getpass("Confirm password: ")
            
            if password != confirm_password:
                raise ValueError("Passwords do not match")
        
        # Encrypt the key with password
        encrypted_key = self._encrypt_key_with_password(key, password)
        
        # Save encrypted key to file
        with open(self.key_file, 'wb') as f:
            f.write(encrypted_key)
        
        # Store password in keyring
        try:
            keyring.set_password(self.service_name, "encryption_key", password)
        except Exception as e:
            logging.warning(f"Failed to store password in keyring: {e}")
        
        logging.info("Created new encryption key")
        return key
    
    def _encrypt_key_with_password(self, key: bytes, password: str) -> bytes:
        """Encrypt the Fernet key with a password"""
        
        # Generate salt
        salt = os.urandom(16)
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        password_key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Encrypt the Fernet key
        f = Fernet(password_key)
        encrypted_key = f.encrypt(key)
        
        # Combine salt and encrypted key
        return salt + encrypted_key
    
    def _decrypt_key_with_password(self, encrypted_data: bytes, password: str) -> bytes:
        """Decrypt the Fernet key with a password"""
        
        # Extract salt and encrypted key
        salt = encrypted_data[:16]
        encrypted_key = encrypted_data[16:]
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        password_key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Decrypt the Fernet key
        f = Fernet(password_key)
        return f.decrypt(encrypted_key)
    
    def initialize(self, password: Optional[str] = None) -> bool:
        """Initialize the encryption manager"""
        try:
            self._key = self._get_or_create_key(password)
            self._fernet = Fernet(self._key)
            return True
        except Exception as e:
            logging.error(f"Failed to initialize encryption: {e}")
            return False
    
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string and return base64 encoded result"""
        if not self._fernet:
            raise ValueError("Encryption not initialized")
        
        encrypted_data = self._fernet.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt a base64 encoded encrypted string"""
        if not self._fernet:
            raise ValueError("Encryption not initialized")
        
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}")
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary and return base64 encoded result"""
        json_string = json.dumps(data)
        return self.encrypt_string(json_string)
    
    def decrypt_dict(self, encrypted_text: str) -> Dict[str, Any]:
        """Decrypt and return a dictionary"""
        json_string = self.decrypt_string(encrypted_text)
        return json.loads(json_string)
    
    def encrypt_file(self, file_path: Path, encrypted_file_path: Optional[Path] = None) -> Path:
        """Encrypt a file"""
        if not self._fernet:
            raise ValueError("Encryption not initialized")
        
        if encrypted_file_path is None:
            encrypted_file_path = file_path.with_suffix(file_path.suffix + '.encrypted')
        
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        encrypted_data = self._fernet.encrypt(file_data)
        
        with open(encrypted_file_path, 'wb') as f:
            f.write(encrypted_data)
        
        logging.info(f"Encrypted file: {file_path} -> {encrypted_file_path}")
        return encrypted_file_path
    
    def decrypt_file(self, encrypted_file_path: Path, decrypted_file_path: Optional[Path] = None) -> Path:
        """Decrypt a file"""
        if not self._fernet:
            raise ValueError("Encryption not initialized")
        
        if decrypted_file_path is None:
            # Remove .encrypted extension
            if encrypted_file_path.suffix == '.encrypted':
                decrypted_file_path = encrypted_file_path.with_suffix('')
            else:
                decrypted_file_path = encrypted_file_path.with_suffix('.decrypted')
        
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = self._fernet.decrypt(encrypted_data)
        
        with open(decrypted_file_path, 'wb') as f:
            f.write(decrypted_data)
        
        logging.info(f"Decrypted file: {encrypted_file_path} -> {decrypted_file_path}")
        return decrypted_file_path
    
    def is_encrypted(self, text: str) -> bool:
        """Check if a string appears to be encrypted by this manager"""
        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(text.encode('utf-8'))
            # If successful, it might be our encrypted format
            return True
        except:
            return False

class CredentialManager:
    """Manages encrypted storage of credentials and sensitive configuration"""
    
    def __init__(self, credentials_file: Optional[Path] = None):
        self.credentials_file = credentials_file or Path("data/credentials.json.encrypted")
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.encryption_manager = EncryptionManager()
        self._credentials = {}
        self._initialized = False
    
    def initialize(self, password: Optional[str] = None) -> bool:
        """Initialize the credential manager"""
        try:
            # Initialize encryption
            if not self.encryption_manager.initialize(password):
                return False
            
            # Load existing credentials
            self._load_credentials()
            self._initialized = True
            
            logging.info("Credential manager initialized")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize credential manager: {e}")
            return False
    
    def _load_credentials(self):
        """Load credentials from encrypted file"""
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r') as f:
                    encrypted_data = f.read()
                
                self._credentials = self.encryption_manager.decrypt_dict(encrypted_data)
                logging.info("Loaded existing credentials")
                
            except Exception as e:
                logging.warning(f"Failed to load credentials: {e}")
                self._credentials = {}
        else:
            self._credentials = {}
    
    def _save_credentials(self):
        """Save credentials to encrypted file"""
        if not self._initialized:
            raise ValueError("Credential manager not initialized")
        
        try:
            encrypted_data = self.encryption_manager.encrypt_dict(self._credentials)
            
            with open(self.credentials_file, 'w') as f:
                f.write(encrypted_data)
            
            logging.info("Saved credentials")
            
        except Exception as e:
            logging.error(f"Failed to save credentials: {e}")
            raise
    
    def store_credential(self, key: str, value: str, category: str = "general"):
        """Store a credential"""
        if not self._initialized:
            raise ValueError("Credential manager not initialized")
        
        if category not in self._credentials:
            self._credentials[category] = {}
        
        self._credentials[category][key] = value
        self._save_credentials()
        
        logging.info(f"Stored credential: {category}.{key}")
    
    def get_credential(self, key: str, category: str = "general", default: Optional[str] = None) -> Optional[str]:
        """Get a credential"""
        if not self._initialized:
            raise ValueError("Credential manager not initialized")
        
        return self._credentials.get(category, {}).get(key, default)
    
    def remove_credential(self, key: str, category: str = "general") -> bool:
        """Remove a credential"""
        if not self._initialized:
            raise ValueError("Credential manager not initialized")
        
        if category in self._credentials and key in self._credentials[category]:
            del self._credentials[category][key]
            
            # Remove empty categories
            if not self._credentials[category]:
                del self._credentials[category]
            
            self._save_credentials()
            logging.info(f"Removed credential: {category}.{key}")
            return True
        
        return False
    
    def list_credentials(self, category: Optional[str] = None) -> Dict[str, Any]:
        """List stored credentials (keys only, not values)"""
        if not self._initialized:
            raise ValueError("Credential manager not initialized")
        
        if category:
            return {category: list(self._credentials.get(category, {}).keys())}
        else:
            return {cat: list(creds.keys()) for cat, creds in self._credentials.items()}
    
    def store_salesforce_credentials(self, username: str, password: str, 
                                   security_token: str = "", login_url: str = ""):
        """Store Salesforce credentials"""
        self.store_credential("username", username, "salesforce")
        self.store_credential("password", password, "salesforce")
        if security_token:
            self.store_credential("security_token", security_token, "salesforce")
        if login_url:
            self.store_credential("login_url", login_url, "salesforce")
    
    def get_salesforce_credentials(self) -> Dict[str, str]:
        """Get Salesforce credentials"""
        return {
            "username": self.get_credential("username", "salesforce", ""),
            "password": self.get_credential("password", "salesforce", ""),
            "security_token": self.get_credential("security_token", "salesforce", ""),
            "login_url": self.get_credential("login_url", "salesforce", "https://login.salesforce.com")
        }
    
    def store_openai_credentials(self, api_key: str, organization: str = ""):
        """Store OpenAI credentials"""
        self.store_credential("api_key", api_key, "openai")
        if organization:
            self.store_credential("organization", organization, "openai")
    
    def get_openai_credentials(self) -> Dict[str, str]:
        """Get OpenAI credentials"""
        return {
            "api_key": self.get_credential("api_key", "openai", ""),
            "organization": self.get_credential("organization", "openai", "")
        }
    
    def export_credentials(self, export_file: Path, include_values: bool = False):
        """Export credentials to a file (optionally encrypted)"""
        if not self._initialized:
            raise ValueError("Credential manager not initialized")
        
        if include_values:
            # Export encrypted credentials
            export_data = self._credentials.copy()
            encrypted_data = self.encryption_manager.encrypt_dict(export_data)
            
            with open(export_file, 'w') as f:
                f.write(encrypted_data)
        else:
            # Export only credential structure (keys, not values)
            structure = self.list_credentials()
            
            with open(export_file, 'w') as f:
                json.dump(structure, f, indent=2)
        
        logging.info(f"Exported credentials to: {export_file}")
    
    def import_credentials(self, import_file: Path, merge: bool = True):
        """Import credentials from a file"""
        if not self._initialized:
            raise ValueError("Credential manager not initialized")
        
        try:
            with open(import_file, 'r') as f:
                data = f.read()
            
            # Try to decrypt (assumes encrypted format)
            try:
                imported_credentials = self.encryption_manager.decrypt_dict(data)
            except:
                # Assume plain JSON format
                imported_credentials = json.loads(data)
            
            if merge:
                # Merge with existing credentials
                for category, creds in imported_credentials.items():
                    if category not in self._credentials:
                        self._credentials[category] = {}
                    self._credentials[category].update(creds)
            else:
                # Replace all credentials
                self._credentials = imported_credentials
            
            self._save_credentials()
            logging.info(f"Imported credentials from: {import_file}")
            
        except Exception as e:
            logging.error(f"Failed to import credentials: {e}")
            raise

def create_encryption_manager(key_file: Optional[Path] = None, 
                            password: Optional[str] = None) -> EncryptionManager:
    """Create and initialize an encryption manager"""
    manager = EncryptionManager(key_file)
    
    if not manager.initialize(password):
        raise RuntimeError("Failed to initialize encryption manager")
    
    return manager

def create_credential_manager(credentials_file: Optional[Path] = None,
                            password: Optional[str] = None) -> CredentialManager:
    """Create and initialize a credential manager"""
    manager = CredentialManager(credentials_file)
    
    if not manager.initialize(password):
        raise RuntimeError("Failed to initialize credential manager")
    
    return manager

# Utility functions for common encryption tasks
def encrypt_sensitive_config(config: Dict[str, Any], 
                           sensitive_keys: list,
                           password: Optional[str] = None) -> Dict[str, Any]:
    """Encrypt sensitive values in a configuration dictionary"""
    
    manager = create_encryption_manager(password=password)
    encrypted_config = config.copy()
    
    for key in sensitive_keys:
        if key in encrypted_config and encrypted_config[key]:
            encrypted_config[key] = manager.encrypt_string(str(encrypted_config[key]))
    
    return encrypted_config

def decrypt_sensitive_config(config: Dict[str, Any],
                           sensitive_keys: list,
                           password: Optional[str] = None) -> Dict[str, Any]:
    """Decrypt sensitive values in a configuration dictionary"""
    
    manager = create_encryption_manager(password=password)
    decrypted_config = config.copy()
    
    for key in sensitive_keys:
        if key in decrypted_config and decrypted_config[key]:
            try:
                decrypted_config[key] = manager.decrypt_string(decrypted_config[key])
            except ValueError:
                # Value might not be encrypted
                pass
    
    return decrypted_config
