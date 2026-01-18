#!/usr/bin/env python3
"""
Tests for Client Creation and Token Validation
===============================================

Tests the client.py and simple_client.py module functionality including:
- Token validation before SDK initialization
- Encrypted token rejection
- Client creation with valid tokens
"""

import pytest


class TestClientTokenValidation:
    """Tests for client token validation."""

    def test_create_client_rejects_encrypted_tokens(self, tmp_path, monkeypatch):
        """Verify create_client() rejects encrypted tokens."""
        from core.client import create_client

        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "enc:test123456789012")
        # Mock keychain to ensure encrypted token is the only source
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        with pytest.raises(ValueError, match="encrypted format"):
            create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")

    def test_create_simple_client_rejects_encrypted_tokens(self, monkeypatch):
        """Verify create_simple_client() rejects encrypted tokens."""
        from core.simple_client import create_simple_client

        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "enc:test123456789012")
        # Mock keychain to ensure encrypted token is the only source
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        with pytest.raises(ValueError, match="encrypted format"):
            create_simple_client(agent_type="merge_resolver")
