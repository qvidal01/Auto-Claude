"""
Command Registry for Dynamic Security Profiles
==============================================

FACADE MODULE: This module re-exports all functionality from the
auto-claude/project/command_registry/ package for backward compatibility.

The implementation has been refactored into focused modules:
- command_registry/base.py - Core commands and validated commands
- command_registry/languages.py - Language-specific commands
- command_registry/package_managers.py - Package manager commands
- command_registry/frameworks.py - Framework-specific commands
- command_registry/databases.py - Database commands
- command_registry/infrastructure.py - Infrastructure/DevOps commands
- command_registry/cloud.py - Cloud provider commands
- command_registry/code_quality.py - Code quality tools
- command_registry/version_managers.py - Version management tools

This file maintains the original API so existing imports continue to work.

Maps technologies to their associated commands for building
tailored security profiles.
"""

# Re-export all command registries from the package
from .command_registry.base import (
    BASE_COMMANDS,
    VALIDATED_COMMANDS,
)
from .command_registry.cloud import CLOUD_COMMANDS
from .command_registry.code_quality import CODE_QUALITY_COMMANDS
from .command_registry.databases import DATABASE_COMMANDS
from .command_registry.frameworks import FRAMEWORK_COMMANDS
from .command_registry.infrastructure import INFRASTRUCTURE_COMMANDS
from .command_registry.languages import LANGUAGE_COMMANDS
from .command_registry.package_managers import PACKAGE_MANAGER_COMMANDS
from .command_registry.version_managers import VERSION_MANAGER_COMMANDS

__all__ = [
    "BASE_COMMANDS",
    "VALIDATED_COMMANDS",
    "LANGUAGE_COMMANDS",
    "PACKAGE_MANAGER_COMMANDS",
    "FRAMEWORK_COMMANDS",
    "DATABASE_COMMANDS",
    "INFRASTRUCTURE_COMMANDS",
    "CLOUD_COMMANDS",
    "CODE_QUALITY_COMMANDS",
    "VERSION_MANAGER_COMMANDS",
]
