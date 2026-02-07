"""Shared utility classes for tool definitions and results."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


def _result_ok(value: Any) -> Dict[str, Any]:
	"""Wrap a successful result."""
	return {"ok": True, "result": value}


def _result_error(message: str) -> Dict[str, Any]:
	"""Wrap an error result."""
	return {"ok": False, "error": str(message)}


@dataclass
class ToolSpec:
	"""Metadata for a single tool."""
	name: str
	description: str
	parameters: Dict[str, Any]


@dataclass
class ToolDefinition:
	"""Pairs a tool function with its spec for easy registration."""
	name: str
	func: Callable
	spec: ToolSpec