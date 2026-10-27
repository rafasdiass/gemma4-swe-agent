# Navigation Patterns Reference

## Django Patterns

### Common Search Queries
- `QuerySet iterator memory` - Iterator implementation
- `Model.save override` - Custom save logic
- `Manager.get_queryset` - Custom managers
- `select_related prefetch_related` - Query optimization

### Key Classes/Methods
- `django.db.models.query.QuerySet` - Core queryset
- `django.db.models.manager.Manager` - Model managers
- `django.db.models.Model` - Base model

## Requests Patterns

### Common Search Queries
- `Session.request hook` - Request/response hooks
- `PreparedRequest prepare` - Request preparation
- `HTTPAdapter send` - Connection handling

### Key Classes/Methods
- `requests.sessions.Session` - Main session
- `requests.adapters.HTTPAdapter` - Transport adapter

## NumPy/Pandas Patterns

### Common Search Queries
- `ndarray memory view` - Memory management
- `DataFrame apply vectorize` - Performance patterns
- `ufunc reduce accumulate` - Universal functions

## General SWE Patterns

### Bug Fix Patterns
1. **Null/None checks** - Search for `if not x:` `if x is None:`
2. **Boundary conditions** - Search for `len(` `range(` `index`
3. **Exception handling** - Search for `try:` `except:` `raise`
4. **Resource cleanup** - Search for `close()` `__exit__` `with`

### Feature Patterns
1. **Plugin systems** - Search for `register` `hook` `signal`
2. **Configuration** - Search for `settings` `config` `options`
3. **Extension points** - Search for `abstract` `interface` `protocol`

## Graph Navigation Tips

### High-Value Nodes to Explore
- Test files (show expected behavior)
- Entry points (`__main__`, CLI commands, API endpoints)
- Core abstractions (base classes, interfaces)
- Configuration/registry modules

### Edge Types to Use
- `calls` - Forward tracing (what does this call?)
- `called_by` - Backward tracing (who calls this?)
- `imports` - Module dependencies
- `inherits` - Class hierarchies

## Search Query Templates

### By Issue Type
```
Memory leak: "iterator chunk batch memory generator __iter__ __next__"
Performance: "cache memoize lazy prefetch select_related"
Bug fix: "error_message OR exception_type OR function_name"
Feature: "feature_keyword plugin hook register extension"
```

### By Framework
```
Django: "QuerySet Manager Model Field Meta"
Requests: "Session Adapter PreparedRequest Response"
FastAPI: "Depends router endpoint dependency"
SQLAlchemy: "Session Query Model relationship"
```

## Budget-Aware Navigation

### Priority Order (high to low)
1. Test files for the issue (exact expected behavior)
2. Direct error location (stack trace, error message)
3. Call graph from entry point (2-3 hops)
4. Related modules (same package, similar names)
5. Configuration/registration points

### When to Stop
- Found root cause with high confidence
- Budget < 20% remaining
- Multiple independent paths converge on same location
