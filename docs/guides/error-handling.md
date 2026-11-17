# Error handling

Every exception this library raises descends from `PysepalError`, so one
`except PysepalError` is enough to catch anything it throws.

```
PysepalError
├── ApiError                (HTTP status → typed)
│   ├── BadRequest          (400)
│   ├── Unauthorized        (401)
│   ├── Forbidden           (403)
│   ├── NotFound            (404)
│   ├── Conflict            (409)
│   ├── TooManyRequests     (429)
│   └── ServerError         (5xx)
├── TransportError          (connection / timeout at the socket level)
├── ResponseError          (unexpected/unparseable response body)
├── NoCredentialsError     (no auth could be resolved)
├── MissingHostError       (no base URL could be resolved)
├── InvalidPathError       (also a ValueError)
└── TaskError
    ├── TaskFailed          (task reached FAILED)
    ├── TaskCanceled        (task reached CANCELED)
    └── TaskTimeout         (also a TimeoutError; wait() exceeded its timeout)
```

## Why a request failed

When a SEPAL service says why it refused a request, `ApiError.reason` holds
that message and the error text ends with it. The full response body stays
available as `ApiError.body`.

```python
from pysepal_api import BadRequest

try:
    sepal.ee_exports.submit_table(collection=fc, destination="SEPAL", name="plots", file_format="TIFF")
except BadRequest as exc:
    print(exc.reason)   # Unsupported table export fileFormat: TIFF; expected CSV, GeoJSON, KML, KMZ or SHP
```

## Catch specific cases

```python
from pysepal_api import Conflict, NotFound, PysepalError, TaskFailed, TaskTimeout

try:
    sepal.files.write("out/report.txt", "hi")     # may raise Conflict if it exists
except Conflict:
    sepal.files.write("out/report.txt", "hi", overwrite=True)

try:
    final = sepal.tasks.wait(task.id, timeout=600)
except TaskTimeout:
    ...        # still running after 600s
except TaskFailed as exc:
    print(exc.task.state)                          # the terminal Task is attached

try:
    sepal.files.read_json("missing.json")
except NotFound:
    ...
except PysepalError as exc:
    ...        # anything else from the library
```
