# -*- coding: utf-8 -*-
"""Pytest configuration for unit tests.

Sets up import paths so that modules can import from
``ansible_collections.goodolclint.uptime_kuma.plugins.*``
even when running outside a real Ansible collection install.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys
from unittest.mock import MagicMock

# Create the ansible_collections namespace package structure
# so that "from ansible_collections.goodolclint.uptime_kuma.plugins..."
# resolves to our local plugins/ directory.

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up fake ansible_collections namespace
ansible_collections = MagicMock()
goodolclint = MagicMock()
uptime_kuma_ns = MagicMock()

# Point the plugins sub-packages to the real code
sys.path.insert(0, REPO_ROOT)

# Import real module_utils
import plugins.module_utils.uptime_kuma_api as real_api  # noqa: E402

# Create the namespace chain
sys.modules["ansible_collections"] = type(sys)("ansible_collections")
sys.modules["ansible_collections"].__path__ = []
sys.modules["ansible_collections.goodolclint"] = type(sys)("ansible_collections.goodolclint")
sys.modules["ansible_collections.goodolclint"].__path__ = []
sys.modules["ansible_collections.goodolclint.uptime_kuma"] = type(sys)("ansible_collections.goodolclint.uptime_kuma")
sys.modules["ansible_collections.goodolclint.uptime_kuma"].__path__ = []
sys.modules["ansible_collections.goodolclint.uptime_kuma.plugins"] = type(sys)("ansible_collections.goodolclint.uptime_kuma.plugins")
sys.modules["ansible_collections.goodolclint.uptime_kuma.plugins"].__path__ = []
sys.modules["ansible_collections.goodolclint.uptime_kuma.plugins.module_utils"] = type(sys)("ansible_collections.goodolclint.uptime_kuma.plugins.module_utils")
sys.modules["ansible_collections.goodolclint.uptime_kuma.plugins.module_utils"].__path__ = []
sys.modules["ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api"] = real_api
