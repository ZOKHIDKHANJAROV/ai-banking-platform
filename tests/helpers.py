import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name: str, relative_path: str):
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
