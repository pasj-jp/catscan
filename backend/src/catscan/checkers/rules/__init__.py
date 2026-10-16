"""
YAML rule loading for the paper checkers.

Every checker reads its configuration from one YAML file in this directory:

    jacow_word.yaml   jacow_latex.yaml   pasj_word.yaml   pasj_latex.yaml

The directory can be overridden with the ``CATSCAN_RULES_DIR`` environment
variable (e.g. to mount editor-maintained rule files into a container).

Files are re-read automatically when their modification time changes, so
conference editors can tweak rules without restarting the server.  If an edited
file fails validation, the error is logged and the last valid version keeps
being used; at first load the error is raised.
"""
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Tuple, Type, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("catscan.rules")

T = TypeVar("T", bound=BaseModel)

_DEFAULT_DIR = Path(__file__).resolve().parent
_cache: Dict[str, Tuple[float, Any]] = {}
_lock = threading.Lock()


class RulesError(Exception):
    """Raised when a rules YAML file cannot be read or does not match its schema."""


def rules_dir() -> Path:
    env = os.environ.get("CATSCAN_RULES_DIR")
    return Path(env) if env else _DEFAULT_DIR


def rules_path(name: str) -> Path:
    return rules_dir() / f"{name}.yaml"


def _parse(path: Path, model: Type[T]) -> T:
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        raise RulesError(f"Cannot read rules file {path}: {e}") from e
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise RulesError(f"Invalid rules file {path}:\n{e}") from e


def load_rules(name: str, model: Type[T]) -> T:
    """Load ``<name>.yaml`` validated against ``model`` (cached, reloaded on change)."""
    path = rules_path(name)
    try:
        mtime = path.stat().st_mtime
    except OSError as e:
        raise RulesError(f"Rules file not found: {path}") from e

    key = f"{path}:{model.__module__}.{model.__qualname__}"
    with _lock:
        cached = _cache.get(key)
        if cached and cached[0] == mtime:
            return cached[1]
        try:
            parsed = _parse(path, model)
        except RulesError:
            if cached:
                logger.exception("Keeping previous version of %s because the edited file is invalid", path)
                return cached[1]
            raise
        _cache[key] = (mtime, parsed)
        return parsed
