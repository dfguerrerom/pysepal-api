# Connecting & TLS

## Host resolution

If you don't pass `base_url`, the client detects the SEPAL host from the sandbox
environment. You can inspect or override it:

```python
from pysepal_api import detect_base_url, normalize_base_url, SepalClient

print(detect_base_url())                 # e.g. https://sepal.io
SepalClient(base_url="https://sepal.io")
SepalClient(base_url=normalize_base_url("sepal.io"))  # adds scheme, strips trailing slash
```

## TLS verification

TLS is **verified by default**. Two escape hatches exist for local development
with self-signed certificates:

- `host.docker.internal` is auto-trusted (skipped) for local dev.
- Any other self-signed host: pass `verify=False`, or list it in the
  `PYSEPAL_INSECURE_TLS_HOSTS` env var (comma-separated, exact-host match).

```python
# local dev against a self-signed host
SepalClient(base_url="https://my-dev-host", verify=False)
```

```bash
export PYSEPAL_INSECURE_TLS_HOSTS="my-dev-host,another-host"
```

Verification is never skipped for arbitrary or production hosts.
