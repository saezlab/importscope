from __future__ import annotations

from typing import Any
from pathlib import Path
from dataclasses import field, asdict, dataclass


@dataclass(frozen=True)
class ImportEdge:
    """One resolved internal import edge between two modules."""

    source: str
    target: str
    imported: tuple[str, ...] = ()
    import_type: str = 'import'
    lazy_kind: str = 'eager'
    line: int = 0
    source_file: str = ''

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the edge."""
        data = asdict(self)
        data['imported'] = list(self.imported)
        return data


@dataclass
class ModuleInfo:
    """Metadata collected for one discovered Python module."""

    module: str
    path: Path
    is_package: bool
    definitions: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the module."""
        return {
            'module': self.module,
            'path': str(self.path),
            'is_package': self.is_package,
            'definitions': sorted(self.definitions),
        }


@dataclass
class PolicyFinding:
    """One policy-level classification or warning derived from an import edge."""

    finding_type: str
    severity: str
    source: str
    target: str
    line: int
    source_file: str
    imported: tuple[str, ...] = ()
    message: str = ''

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the finding."""
        data = asdict(self)
        data['imported'] = list(self.imported)
        return data


@dataclass
class AnalysisResult:
    """Normalized analysis output for one repository scan."""

    repo: Path
    module_roots: list[Path]
    modules: dict[str, ModuleInfo]
    edges: list[ImportEdge]
    cycles: list[list[str]]
    coverage_gaps: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the analysis result."""
        return {
            'repo': str(self.repo),
            'module_roots': [str(root) for root in self.module_roots],
            'modules': {
                name: info.to_dict()
                for name, info in sorted(self.modules.items())
            },
            'edges': [edge.to_dict() for edge in self.edges],
            'cycles': self.cycles,
            'coverage_gaps': self.coverage_gaps,
        }
