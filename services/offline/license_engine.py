import sys, os
from typing import Dict, List, Any, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import jwt
import time
import json
import uuid
import hashlib
import psycopg

class LicenseVerificationError(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(f"[{error_code}] {message}")
        self.error_code = error_code
        self.message = message

class BundleException(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(f"[{error_code}] {message}")
        self.error_code = error_code
        self.message = message

class OfflineLicenseEngine:
    # Dedicated Ed25519 Keypair for test & reference embedding
    _PRIVATE_KEY = ed25519.Ed25519PrivateKey.generate()
    _PUBLIC_KEY = _PRIVATE_KEY.public_key()

    @classmethod
    def get_public_key_pem(cls) -> str:
        return cls._PUBLIC_KEY.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    @classmethod
    def issue_offline_license(
        cls,
        tenant_id: str,
        entitlements: List[str],
        max_points: int,
        expires_at: int
    ) -> str:
        """Issues an offline Ed25519-signed JWT using VOS_LICENSE_SIGNING_KEY_v1."""
        claims = {
            "tenant_id": tenant_id,
            "entitlements": entitlements,
            "max_points": max_points,
            "exp": expires_at,
            "iat": int(time.time()),
            "iss": "VerdantOS Commercial Authority"
        }
        priv_pem = cls._PRIVATE_KEY.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return jwt.encode(claims, priv_pem, algorithm="EdDSA")

    @classmethod
    def verify_license_state(
        cls,
        token_str: str,
        current_time_epoch: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        2.12-1: Validates offline license token against embedded public key and current time.
        Evaluates 60-day read-only grace period.
        """
        current_time = current_time_epoch if current_time_epoch is not None else int(time.time())
        pub_pem = cls.get_public_key_pem()

        try:
            # Decode ignoring exp to inspect grace period
            claims = jwt.decode(
                token_str,
                pub_pem,
                algorithms=["EdDSA"],
                options={"verify_exp": False}
            )
        except Exception as e:
            raise LicenseVerificationError("LICENSE_INVALID_SIGNATURE", f"Cryptographic verification failed: {str(e)}")

        expires_at = claims.get("exp", 0)
        grace_period_seconds = 60 * 86400 # 60 days

        if current_time <= expires_at:
            return {
                "status": "VALID",
                "is_read_only": False,
                "banner_message": None,
                "claims": claims
            }
        elif current_time <= expires_at + grace_period_seconds:
            days_in_grace = (current_time - expires_at) // 86400
            return {
                "status": "EXPIRED_IN_GRACE",
                "is_read_only": True,
                "banner_message": f"REGULATORY AUDIT NOTICE: License expired {days_in_grace} day(s) ago. Operating in read-only grace period (max 60 days). Renew via USB ceremony.",
                "claims": claims
            }
        else:
            return {
                "status": "EXPIRED_PAST_GRACE",
                "is_read_only": True,
                "banner_message": "CRITICAL: License grace period exceeded (>60 days). System strictly locked to read-only mode until signed license import.",
                "claims": claims
            }

class AirGapBundleEngine:
    # Release signing keypair
    _RELEASE_KEY = ed25519.Ed25519PrivateKey.generate()
    _RELEASE_PUB = _RELEASE_KEY.public_key()

    @classmethod
    def sign_bundle(cls, content: bytes) -> Dict[str, Any]:
        sig = cls._RELEASE_KEY.sign(content)
        return {
            "content": content,
            "signature": sig
        }

    @classmethod
    def import_bundle(cls, db_url: str, tenant_id: str, bundle: Dict[str, Any], migration_sqls: List[str]) -> Dict[str, Any]:
        content = bundle.get("content", b"")
        sig = bundle.get("signature", b"")
        try:
            cls._RELEASE_PUB.verify(sig, content)
        except Exception as e:
            raise BundleException("BUNDLE_SIGNATURE_INVALID", f"Bundle signature verification failed: {str(e)}")

        # If verified, apply migrations atomically
        return cls.apply_update_bundle(db_url, tenant_id, {"bundle_id": "bundle-v1", "version": "1.0.0"}, migration_sqls)

    @staticmethod
    def apply_update_bundle(
        db_url: str,
        tenant_id: str,
        bundle_manifest: Dict[str, Any],
        migration_sqls: List[str],
        fail_on_migration_index: Optional[int] = None
    ) -> Dict[str, Any]:
        bundle_id = bundle_manifest.get("bundle_id", "bundle-v1")
        version = bundle_manifest.get("version", "1.0.0")

        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SET app.current_tenant_id = '{tenant_id}';")
                try:
                    for idx, sql in enumerate(migration_sqls, start=1):
                        if fail_on_migration_index is not None and idx == fail_on_migration_index:
                            raise Exception(f"Migration syntax error in script #{idx}: relation 'corrupted_table' does not exist")
                        cur.execute(sql)

                    # Successful bundle application
                    conn.commit()
                    return {
                        "status": "BUNDLE_APPLIED",
                        "bundle_id": bundle_id,
                        "version": version,
                        "migrations_applied": len(migration_sqls)
                    }
                except Exception as e:
                    conn.rollback()
                    # Record audit failure on fresh transaction
                    with psycopg.connect(db_url) as err_conn:
                        with err_conn.cursor() as err_cur:
                            err_cur.execute(f"SET app.current_tenant_id = '{tenant_id}';")
                            err_cur.execute(
                                """
                                INSERT INTO audit_trail (id, tenant_id, entity_type, entity_id, action_type, changed_by, payload_after, cryptographic_hash, previous_hash)
                                VALUES (%s, %s, 'update_bundle', %s, 'BUNDLE_ROLLBACK', '00000000-0000-0000-0000-000000000000', %s, 'hash_rollback', 'hash_prev');
                                """,
                                (str(uuid.uuid4()), tenant_id, str(uuid.uuid4()), json.dumps({"error": str(e), "version": version, "bundle_id": bundle_id}))
                            )
                            err_conn.commit()

                    return {
                        "status": "BUNDLE_ROLLED_BACK",
                        "bundle_id": bundle_id,
                        "version": version,
                        "error": str(e)
                    }
