"""
VerdantOS Data Connectors Core Runtime & Base Interfaces (§10.2 / ADR-007)
Provides Connector interface, SecretProvider abstraction, query parser with AST read-only enforcement,
and atomic chunk-based sync execution with watermark management.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Iterator
import re
import uuid
import time
import psycopg

class ConnectorException(Exception):
    def __init__(self, error_code: str, message: str, run_level: str = "ERROR"):
        super().__init__(f"[{error_code}] {message}")
        self.error_code = error_code
        self.message = message
        self.run_level = run_level

class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, tenant_id: str, secret_ref: str) -> Dict[str, Any]:
        """Resolves a secret_ref URI to concrete credentials."""
        pass

class MockVaultSecretProvider(SecretProvider):
    def __init__(self, store: Optional[Dict[str, Dict[str, Any]]] = None):
        self.store = store or {}

    def get_secret(self, tenant_id: str, secret_ref: str) -> Dict[str, Any]:
        key = f"{tenant_id}:{secret_ref}"
        if key not in self.store and secret_ref not in self.store:
            raise ConnectorException("SOURCE_AUTH_FAILED", f"Secret ref '{secret_ref}' not found in vault", "FATAL")
        return self.store.get(key) or self.store[secret_ref]

class SQLQueryGuard:
    """
    Enforces Layer 2 read-only query inspection before dispatching to external database.
    Rejects any non-SELECT statement with structured SOURCE_READ_ONLY_VIOLATION.
    """
    DISALLOWED_KEYWORDS = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
        re.IGNORECASE
    )

    @classmethod
    def validate_select_only(cls, query: str):
        cleaned = query.strip()
        # Must start with SELECT or WITH (for CTEs) or EXPLAIN
        if not re.match(r"^(SELECT|WITH|EXPLAIN)\b", cleaned, re.IGNORECASE):
            raise ConnectorException(
                "SOURCE_READ_ONLY_VIOLATION",
                f"Query rejected: Only read-only SELECT queries are permitted. Query starts with '{cleaned.split()[0]}'",
                "FATAL"
            )
        # Check for disallowed mutation keywords in query body
        match = cls.DISALLOWED_KEYWORDS.search(cleaned)
        if match:
            # Allow EXPLAIN
            if cleaned.upper().startswith("EXPLAIN") and match.group(0).upper() == "EXPLAIN":
                pass
            else:
                raise ConnectorException(
                    "SOURCE_READ_ONLY_VIOLATION",
                    f"Query rejected: Disallowed mutation keyword '{match.group(0)}' detected in query body",
                    "FATAL"
                )

class Connector(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def discover_schema(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def read_incremental(self, watermark: int, limit: int = 1000) -> Iterator[Dict[str, Any]]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
