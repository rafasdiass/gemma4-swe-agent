---
name: repo_navigation
version: "1.0"
description: "Repository navigation patterns and code search strategies for SWE agent"
author: "Atena/Iris"
tags: [navigation, search, graph, codebase]
---

# Repo Navigation Skill

## Search Patterns

### Issue Keyword Search
```python
# Search for issue-related code
results = search_similar_code(
    query="memory leak QuerySet iterator",
    k=20
)
```

### Error Message Search
```python
# Search for exact error messages
results = search_similar_code(
    query="MemoryError: unable to allocate",
    k=15
)
```

### Function/Class Name Search
```python
# Search for specific identifiers
results = search_similar_code(
    query="def iterator QuerySet",
    k=10
)
```

## Graph Navigation Patterns

### Trace from Test to Implementation
```python
# 1. Find test file
test_results = search_similar_code(query="test_iterator", k=5)

# 2. Read test to understand expected behavior
test_content = read_file(test_results[0].file, start_line=1, end_line=100)

# 3. Trace call graph from test entry point
neighbors = get_code_neighbors(
    node="QuerySet.iterator",
    edge_type="calls",
    max_neighbors=50
)
```

### Find All Callers of a Function
```python
callers = get_code_neighbors(
    node="QuerySet._fetch_all",
    edge_type="called_by",
    max_neighbors=30
)
```

### Get Subgraph for Multi-File Understanding
```python
subgraph = get_code_subgraph(
    nodes=["QuerySet.iterator", "QuerySet._fetch_all", "QuerySet._fetch_chunk"]
)
```

## Navigation Strategies by Issue Type

### Memory Leak
1. Search for `iterator`, `chunk`, `batch`, `memory`
2. Trace `__iter__` and `__next__` implementations
3. Look for generator patterns, unclosed resources

### Bug Fix
1. Search for error message or exception type
2. Trace from test failure to source
3. Identify condition causing incorrect behavior

### Feature Request
1. Search for similar existing features
2. Find extension points, plugin systems
3. Trace configuration/registration patterns

## Resources
- `patterns.md` - Common search patterns per framework
- `scripts/navigate.py` - Automated navigation helpers

## Usage in Agent Workflow
```yaml
# Agent calls skill via AgentTool
skill: repo_navigation
action: trace_call_graph
params:
  entry_point: "QuerySet.iterator"
  depth: 3
```
