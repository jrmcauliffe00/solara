"""Regression tests for anyio import-time compatibility."""

import importlib
import sys
from unittest import mock


def test_starlette_import_does_not_touch_anyio_from_thread_attribute():
    sys.modules.pop("solara.server.starlette", None)

    original_import = importlib.import_module

    def guarded_import(name, package=None):
        module = original_import(name, package)
        if name == "anyio":
            module = mock.Mock(wraps=module)
            delattr(module, "from_thread")
        return module

    with mock.patch("importlib.import_module", side_effect=guarded_import):
        module = importlib.import_module("solara.server.starlette")

    assert module is not None
