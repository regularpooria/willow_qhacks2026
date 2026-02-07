#!/usr/bin/env python3
"""Simple runner script for the tools module.

Usage:
  python run_tools.py
"""

if __name__ == "__main__":
	from public.tools import execute_tool, get_tool_specs
	import json

	print("=== Available Tools ===\n")
	print(json.dumps(get_tool_specs(), indent=2))
	print("\n=== Demo Execution ===\n")

	# Example: start a headed browser
	seq = [
		("start_browser", {"headless": False}),
		# ("search_youtube", {"query": "Bob Ross"}),
		# ("close_browser", {}),
	]

	for name, args in seq:
		print(f"Executing: {name}")
		result = execute_tool(name, args)
		print(f"Result: {json.dumps(result, indent=2)}\n")
