# Python Coding Style Guide

This document defines the coding style conventions for the Job-Stack / Karen Guard project. All Python modules must strictly adhere to these rules.

---

## 1. Fluent Interfaces & Method Chaining
All workflow, configuration, and pipeline methods must return `self` (using the class name as the type hint via `__future__.annotations`) to support fluent method chaining.

```python
class Process:
    def step_one(self) -> Process:
        # Lógica
        return self
```

## 2. Minimalist Constructors (`__init__`) with Static Typing
The class constructor `__init__` must perform no runtime logic or attribute assignments. It is reserved solely for type annotations under a `TYPE_CHECKING` block.

```python
from typing import TYPE_CHECKING

class Process:
    def __init__(self):
        if TYPE_CHECKING:
            self.attribute: type
```

## 3. Class-Level Factory Setup (`setup`)
Object initialization, attribute assignment, and directory setup are delegated to a class-level factory method `setup()` and a private companion method `_setup()`.

```python
class Process:
    def _setup(self) -> Process:
        self.attribute = "value"
        return self

    @classmethod
    def setup(cls) -> Process:
        _instance = cls()
        return _instance._setup()
```

When instantiating and running a pipeline, chain the classmethod directly:
```python
Process.setup()\
    .step_one()\
    .step_two()
```

## 4. Zero Comments and Docstrings
Code must be completely clean and free of inline comments (`#`) and docstrings (`"""`). The naming of methods, variables, and classes must be expressive enough to explain the code's intent.

## 5. Relative Package Imports
Always use relative imports for modules and packages inside the same directory tree.
* Correct: `from .core import Core`
* Incorrect: `from core import Core`

## 6. Typing and Annotations
* Always import `from __future__ import annotations` as the first line of every Python file.
* Use raw class type hints instead of string-based forward references.
* Keep types precise (e.g., `list[dict[str, str]]` instead of `list[str]` when lists contain dictionaries).
