import importlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name: str, relative_path: str):
    import importlib.util

    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path
    )
    module = importlib.util.module_from_spec(spec)

    assert spec is not None
    assert spec.loader is not None

    spec.loader.exec_module(module)

    return module


def import_service_module(
    service_relative_path: str,
    module_name: str = "app.main",
    env_overrides: dict[str, str] | None = None
):
    if env_overrides:
        for key, value in env_overrides.items():
            os.environ[key] = value

    for imported_name in list(sys.modules):
        if imported_name == "app" or imported_name.startswith("app."):
            sys.modules.pop(imported_name)

    service_root = ROOT / service_relative_path
    service_root_str = str(service_root)

    if service_root_str in sys.path:
        sys.path.remove(service_root_str)

    sys.path.insert(0, service_root_str)

    return importlib.import_module(module_name)
