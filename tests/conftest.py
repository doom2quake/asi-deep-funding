"""Test environment for Ledgerkeep.

Two jobs, both done before ``ledgerkeep`` is imported anywhere:

1. Pin the configuration. ``ledgerkeep.config`` builds a frozen ``settings``
   singleton at import time and ``python-dotenv`` will happily read a developer's
   ``.env``, so every switch the suite depends on is set here explicitly. The
   suite runs offline, in memory, with no marketplace credential configured.

2. Cut the network. An autouse fixture replaces ``socket.socket``,
   ``urllib.request.urlopen`` and ``subprocess.run`` with objects that fail the
   test if anything reaches for them. A guardrailed agent whose test suite could
   touch the network is not a test suite.
"""

from __future__ import annotations

import os

# --- 1) pin the environment (must precede the first `import ledgerkeep`) ------

_TEST_ENV = {
    "LEDGERKEEP_OFFLINE": "1",
    "LEDGERKEEP_IN_MEMORY_STATE": "1",
    # every optional capability off, so a test opts in deliberately
    "LEDGERKEEP_DRY_RUN": "0",
    "LEDGERKEEP_ASI_AGENT_SEED": "",
    "LEDGERKEEP_ASI_NETWORK": "testnet",
    # limiter defaults the suite asserts against
    "LEDGERKEEP_MAX_ACTIONS_PER_CYCLE": "4",
    "LEDGERKEEP_MAX_ACTIONS_PER_HOUR": "20",
    # no integration is configured, and no credential may be discovered
    "AGENT_SLACK_WEBHOOK_URL": "",
    "AGENT_TICKET_ENDPOINT": "",
    "AGENT_GITHUB_REPO": "",
    "AGENT_GITHUB_TOKEN": "",
    "GITHUB_TOKEN": "",
    "LEDGERKEEP_PLAIN": "1",
}
os.environ.update(_TEST_ENV)

import socket  # noqa: E402
import subprocess  # noqa: E402
import urllib.request  # noqa: E402

import pytest  # noqa: E402

from ledgerkeep import ledger  # noqa: E402


# --- 2) cut the network ------------------------------------------------------

class _BlockedNetwork(AssertionError):
    """Raised when a test reaches for the network."""


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly on any outbound connection, credential probe or subprocess."""

    def _blocked(*args, **kwargs):
        raise _BlockedNetwork(
            "a test tried to open a network connection or spawn a process; "
            "inject a fake transport instead"
        )

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(urllib.request, "urlopen", _blocked)
    monkeypatch.setattr(subprocess, "run", _blocked)
    return _blocked


@pytest.fixture(autouse=True)
def clean_ledger():
    """Every test starts and ends with the fixture ledger un-remediated."""
    ledger.reset()
    yield
    ledger.reset()
