## v0.2.0 (2026-07-07)

### BREAKING CHANGE

- files endpoint uses pathlib verbs (read_bytes/read_text/
read_json/write) instead of get/set; write() now raises Conflict instead of
silently no-op'ing; async create() is awaitable AND an async context manager;
errors SepalApiError/SepalTransportError renamed to ApiError/TransportError;
dropped sepal_host and create_base_dir kwargs (session_id/module_name are now
keyword-only); recipes attribute replaces processing_recipes; verify attribute
replaces verify_ssl; wait(poll=) renamed to wait(poll_interval=); global
PYSEPAL_INSECURE_TLS replaced by host-scoped PYSEPAL_INSECURE_TLS_HOSTS.
- removes pysepal_api.compat (pysepal-v3 shim); construct via SepalClient.create().

### Feat

- polish public client API before release
- redesign SepalClient API (factory, generic request, dedup core)

### Fix

- wrap non-array list responses in ResponseError instead of raw TypeError
- close client on context-enter failure, wrap response-parse errors
- root path errors under PysepalError and close client if create() fails

### Refactor

- rename processing_recipes module/classes to recipes

## v0.1.0 (2026-05-15)

### Feat

- **async**: AsyncSepalClient + async context manager
- **async**: async twins for user_files/tasks/processing_recipes
- **processing_recipes**: save (gzip) and delete endpoints
- **processing_recipes**: list and get endpoints
- **tasks**: wait helper with terminal-state handling
- **tasks**: cancel/remove/restart endpoints
- **tasks**: list with filters + get with optional details
- **tasks**: submit task endpoint
- **api**: public re-exports for SepalClient, auth, models, errors
- **compat**: pysepal v3 SepalClient compatibility surface
- **client**: sync SepalClient with auth/host/verify resolution
- **user_files**: createFolder + module_dir helper, idempotent
- **user_files**: setFile multipart upload with 409 idempotency
- **user_files**: download endpoint with optional JSON parsing
- **user_files**: listFiles endpoint with directory envelope
- **models**: pydantic v2 models for files, tasks, recipes
- **transport**: JSON parsing + error mapping for endpoint sends
- **auth**: ApiKeyAuth, CookieAuth, NoAuth + detect_auth
- **host**: detect and normalize SEPAL base URL
- **paths**: sanitize_write_path and normalize_list_folder
- **errors**: add SepalApiError hierarchy and status mapper

### Fix

- **compat**: cookies attribute is a dict, matching legacy SepalClient
