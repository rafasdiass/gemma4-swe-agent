#!/usr/bin/env python3
"""
Repository Navigation Helpers for SWE Agent
Automated navigation patterns for common issue types.
"""

import json
from typing import Any


def search_code(query: str, k: int = 20) -> dict[str, Any]:
    """Wrapper for search_similar_code tool."""
    return {"tool": "search_similar_code", "query": query, "k": k}


def get_neighbors(node: str, edge_type: str = None, max_neighbors: int = 50) -> dict[str, Any]:
    """Wrapper for get_code_neighbors tool."""
    return {
        "tool": "get_code_neighbors",
        "node": node,
        "edge_type": edge_type,
        "max_neighbors": max_neighbors,
    }


def get_subgraph(nodes: list[str]) -> dict[str, Any]:
    """Wrapper for get_code_subgraph tool."""
    return {"tool": "get_code_subgraph", "nodes": nodes}


def read_file(filepath: str, start_line: int = None, end_line: int = None) -> dict[str, Any]:
    """Wrapper for read_file tool."""
    params = {"filepath": filepath}
    if start_line:
        params["start_line"] = start_line
    if end_line:
        params["end_line"] = end_line
    return {"tool": "read_file", **params}


def run_command(command: str) -> dict[str, Any]:
    """Wrapper for run_command tool."""
    return {"tool": "run_command", "command": command}


def trace_memory_leak() -> list[dict]:
    """Navigation pattern for memory leak issues."""
    return [
        search_code("iterator chunk batch memory", k=20),
        search_code("__iter__ __next__ generator", k=15),
        get_neighbors("QuerySet.iterator", "calls", 30),
        get_neighbors("QuerySet._fetch_all", "called_by", 20),
    ]


def trace_bug_fix(error_message: str) -> list[dict]:
    """Navigation pattern for bug fixes."""
    return [
        search_code(error_message, k=15),
        get_neighbors("error_function_name", "called_by", 25),
    ]


def trace_feature_request(feature_keywords: str) -> list[dict]:
    """Navigation pattern for feature requests."""
    return [
        search_code(feature_keywords, k=20),
        search_code("plugin extension hook register", k=15),
    ]


if __name__ == "__main__":
    print(json.dumps(trace_memory_leak(), indent=2))
