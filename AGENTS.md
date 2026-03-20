## For Python coding: ALWAYS use `uv run` prefix for ALL Python-related commands. NEVER use vanilla commands.

### CORRECT (Always use these)

```bash
✅ uv run python script.py          # NEVER: python script.py
✅ uv run pytest                    # NEVER: pytest
✅ uv run python -m pytest tests/   # NEVER: python -m pytest tests/
✅ uv run ruff check .              # NEVER: ruff check .
✅ uv run pip install package      # NEVER: pip install package
```

### FORBIDDEN (Never use these)

❌ `python` (any form)
❌ `pytest` (any form)
❌ `pip` (any form)
❌ `ruff` (any form)
❌ `black`, `isort`, `flake8`, or any other Python tools