from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CaptureResult:
    tool: str
    output_path: str
    outputs: dict[str, str] = field(default_factory=dict)
    auxiliary_outputs: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComboResult:
    status: str
    files: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    auxiliary_outputs: dict[str, str] = field(default_factory=dict)

