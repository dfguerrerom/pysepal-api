# pysepal-api

UI-free HTTP client for SEPAL platform services. Powers Jupyter notebooks, Voila apps, CLI scripts, and background jobs running inside a SEPAL sandbox.

```python
from pysepal_api import SepalClient

with SepalClient() as sepal:
    listing = sepal.user_files.list(".")
```

See `docs/` for the design spec.
