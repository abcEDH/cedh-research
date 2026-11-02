"""Load trusted repository model artifacts from their training runtime."""

import pickle
from pathlib import Path
from typing import Any


class _ArtifactUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        # sklearn 1.7.2's training build serialized its Cython loss module
        # without the package prefix. Official wheels expose this exact module
        # under sklearn._loss._loss. Do not install a process-wide module alias.
        if module == "_loss":
            module = "sklearn._loss._loss"
        return super().find_class(module, name)


def load_model_artifact(path: Path | str) -> dict[str, Any]:
    """Unpickle a trusted artifact; this does not make untrusted pickles safe."""
    with Path(path).open("rb") as handle:
        return _ArtifactUnpickler(handle).load()
