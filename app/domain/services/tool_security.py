"""Tool argument validation for adversarial defense."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from typing import Any

import sqlglot

MAX_NESTING_DEPTH = 10
MAX_STRING_LENGTH = 10000
MAX_CONTAINER_ENTRIES = 1000
ALLOWED_URL_SCHEMES = {"http", "https"}


class ToolSecurityError(Exception):
    """Raised when a tool argument fails security validation."""


class ToolArgumentValidator:
    """Validates tool arguments against adversarial threat patterns.

    Enforces:
    - Maximum nesting depth
    - Maximum string length
    - Maximum container size
    - No binary data in strings
    - No null bytes
    - Path traversal prevention
    - SSRF and unsafe URL scheme prevention
    - SQL injection prevention
    """

    def validate_schema(self, arguments: dict[str, Any]) -> None:
        self._validate_depth(arguments, depth=0)
        self._validate_strings(arguments)
        self._validate_heuristics(arguments)

    def validate_path(self, path_value: str, allow_absolute: bool = False) -> None:
        if ".." in path_value:
            raise ToolSecurityError("Path traversal detected.")
        if not allow_absolute and os.path.isabs(path_value):
            raise ToolSecurityError("Absolute paths are not allowed.")
        os.path.normpath(path_value)

    def validate_url(self, url_value: str, allowed_hosts: list[str] | None = None) -> None:
        has_slashes = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url_value))
        has_colon = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url_value))
        if not has_slashes and not has_colon:
            raise ToolSecurityError("Invalid URL format.")
        scheme_match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://", url_value) or re.match(
            r"^([a-zA-Z][a-zA-Z0-9+.-]*):", url_value
        )
        scheme = scheme_match.group(1).lower()  # type: ignore[union-attr]
        if scheme not in ALLOWED_URL_SCHEMES:
            raise ToolSecurityError(f"Unsafe URL scheme: {scheme}")
        host_match = re.search(r"://([^/:]+)", url_value) or re.search(r":([^/]+)", url_value)
        if host_match is None:
            raise ToolSecurityError("Invalid URL host.")
        host = host_match.group(1)
        self._validate_host(host, allowed_hosts)
        port_match = re.search(r":(\d+)(?:/|$)", url_value)
        if port_match:
            port = int(port_match.group(1))
            if port not in {80, 443}:
                raise ToolSecurityError(f"Non-standard port blocked: {port}")

    def validate_sql(self, query: str) -> None:
        normalized = query.strip()
        upper = normalized.upper()
        dml_ddl = {"DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"}
        first_word = upper.split()[0] if upper.split() else ""
        if first_word in dml_ddl:
            raise ToolSecurityError(f"DML/DDL statement blocked: {first_word}")
        try:
            parsed = sqlglot.parse_one(normalized)
        except Exception:  # nosec B110 - SQL parser failure means not destructive SQL  # noqa: S110
            return
        if parsed is not None:
            sql_type = str(parsed.key).upper()
            if sql_type in dml_ddl:
                raise ToolSecurityError(f"Destructive SQL blocked by parser: {sql_type}")

    def _validate_depth(self, value: Any, depth: int) -> None:
        if depth > MAX_NESTING_DEPTH:
            raise ToolSecurityError(f"Maximum nesting depth exceeded: {depth}")
        if isinstance(value, dict):
            if len(value) > MAX_CONTAINER_ENTRIES:
                raise ToolSecurityError("Dictionary exceeds maximum entry count.")
            for item in value.values():
                self._validate_depth(item, depth + 1)
        elif isinstance(value, list):
            if len(value) > MAX_CONTAINER_ENTRIES:
                raise ToolSecurityError("List exceeds maximum entry count.")
            for item in value:
                self._validate_depth(item, depth + 1)

    def _validate_strings(self, value: Any) -> None:
        if isinstance(value, str):
            if len(value) > MAX_STRING_LENGTH:
                raise ToolSecurityError(f"String exceeds maximum length: {len(value)}")
            if "\x00" in value:
                raise ToolSecurityError("Null bytes are not allowed in strings.")
            if any(ord(ch) > 0x10FFFF or (0xD800 <= ord(ch) <= 0xDFFF) for ch in value):
                raise ToolSecurityError("Invalid binary data in string field.")
        elif isinstance(value, dict):
            for item in value.values():
                self._validate_strings(item)
        elif isinstance(value, list):
            for item in value:
                self._validate_strings(item)

    def _validate_heuristics(self, value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str):
                    lowered_key = key.lower()
                    lowered_value = item.lower()
                    if "path" in lowered_key or "file" in lowered_key:
                        self.validate_path(item)
                    url_prefixes = ("http://", "https://", "file://", "ftp://", "javascript:")
                    if ("url" in lowered_key or "link" in lowered_key
                            or lowered_value.startswith(url_prefixes)):
                        self.validate_url(item)
                    if lowered_key == "query" and self._looks_like_sql(item):
                        self.validate_sql(item)
                    if lowered_key == "cmd" and self._looks_like_shell(item):
                        raise ToolSecurityError(
                            "Shell metacharacters detected in command argument."
                        )
                    sensitive_keys = "secret" in lowered_key or "password" in lowered_key
                    sensitive_keys = sensitive_keys or "key" in lowered_key
                    sensitive_keys = sensitive_keys or "token" in lowered_key
                    if sensitive_keys and self._looks_like_sensitive_name(item):
                        raise ToolSecurityError("Sensitive parameter name detected.")
                    if lowered_key == "path" and self._looks_like_sensitive_path(item):
                        raise ToolSecurityError("Sensitive file path detected.")
                else:
                    self._validate_heuristics(item)
        elif isinstance(value, list):
            for item in value:
                self._validate_heuristics(item)

    def _looks_like_sql(self, value: str) -> bool:
        sql_keywords = re.findall(
            r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b",
            value,
            flags=re.IGNORECASE,
        )
        return bool(sql_keywords)

    def _looks_like_shell(self, value: str) -> bool:
        return any(char in value for char in {";", "|", "&&", "||", "$(", "`", "\n"})

    def _looks_like_sensitive_name(self, value: str) -> bool:
        sensitive = re.findall(
            r"(?:^|[^a-zA-Z0-9])(jwt|secret|password|private_key|api_key|token|credential)(?:[^a-zA-Z0-9]|$)",
            value,
            flags=re.IGNORECASE,
        )
        return bool(sensitive)

    def _looks_like_sensitive_path(self, value: str) -> bool:
        sensitive = re.findall(
            r"(?:^|[^a-zA-Z0-9])(private\.pem|\.env|secret|id_rsa|\.p12|\.pfx)(?:[^a-zA-Z0-9]|$)",
            value,
            flags=re.IGNORECASE,
        )
        return bool(sensitive)

    def _validate_host(self, host: str, allowed_hosts: list[str] | None) -> None:
        if allowed_hosts is not None:
            if host not in allowed_hosts:
                raise ToolSecurityError(f"Host not in allowlist: {host}")
            return
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_private or addr.is_loopback or addr.is_reserved:
                raise ToolSecurityError(f"Internal IP blocked: {host}")
        except ValueError:  # nosec B110 - invalid host string means not an IP to block  # noqa: S110
            pass
        try:
            resolved = socket.getaddrinfo(host, None)
            for _family, _, _, _, sockaddr in resolved:
                addr = ipaddress.ip_address(sockaddr[0])
                if addr.is_private or addr.is_loopback or addr.is_reserved:
                    raise ToolSecurityError(f"Host resolves to internal IP: {host}")
        except socket.gaierror as err:
            raise ToolSecurityError(f"Unable to resolve host: {host}") from err
