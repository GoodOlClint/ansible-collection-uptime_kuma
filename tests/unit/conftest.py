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
_ns = type(sys)

_PKG = "ansible_collections"
_GCOL = f"{_PKG}.goodolclint"
_UK = f"{_GCOL}.uptime_kuma"
_PLUG = f"{_UK}.plugins"
_MU = f"{_PLUG}.module_utils"

for _name in (_PKG, _GCOL, _UK, _PLUG, _MU):
    sys.modules[_name] = _ns(_name)
    sys.modules[_name].__path__ = []

sys.modules[f"{_MU}.uptime_kuma_api"] = real_api
