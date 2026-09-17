"""Shared fixtures for the KoBALT-700 harness tests.

Offline by design: no network, no GPU. Live-dataset tests live in
test_dataset.py and are skipped unless KOBALT_TEST_LIVE=1.
"""

from __future__ import annotations

import pytest

from helpers import StubBackend, make_items, make_raw_items

__all__ = ["StubBackend"]


def pytest_configure(config):
    # pyproject.toml is off-limits, so the gpu marker is registered here.
    config.addinivalue_line(
        "markers",
        "gpu: marks tests needing a GPU / heavy local engines (deselected in CI)",
    )


@pytest.fixture
def items():
    return make_items()


@pytest.fixture
def raw_items():
    return make_raw_items()


@pytest.fixture
def stub_outputs():
    from helpers import (
        STUB_OUTPUT_CORRECT_H,
        STUB_OUTPUT_MULTI,
        STUB_OUTPUT_NO_PHRASE,
    )

    return [STUB_OUTPUT_CORRECT_H, STUB_OUTPUT_NO_PHRASE, STUB_OUTPUT_MULTI]


@pytest.fixture
def stub_backend(stub_outputs):
    return StubBackend(stub_outputs)
