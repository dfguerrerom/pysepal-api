# Usage

All examples use the sync client; the async twin mirrors them with `await`.

## Files — `sepal.files`

File verbs follow `pathlib`:

```python
listing = sepal.files.list("/", extensions=[".tif"], include_hidden=False)
print(listing.count, len(listing))
for entry in listing:                 # DirectoryListing iterates its entries
    print(entry.name, entry.is_dir)

data = sepal.files.read_json("results/summary.json")
text = sepal.files.read_text("notes.txt")
raw = sepal.files.read_bytes("image.tif")

result = sepal.files.write("out/report.txt", "hello", overwrite=True)
sepal.files.mkdir("out/nested")       # idempotent
module_path = sepal.files.module_dir("my_module")
```

## Tasks — `sepal.tasks`

```python
task = sepal.tasks.submit("image.download", params={"recipeId": "abc"})
final = sepal.tasks.wait(task.id, poll_interval=5.0, timeout=600)
print(final.state)                    # a TaskState enum member

running = sepal.tasks.list(status="ACTIVE")
sepal.tasks.cancel(task.id)
sepal.tasks.restart(task.id)          # maps to SEPAL's execute route
sepal.tasks.remove(task.id)
```

## Recipes — `sepal.recipes`

```python
summaries = sepal.recipes.list()      # list[RecipeSummary]
recipe = sepal.recipes.get("recipe-id")          # parsed JSON
raw = sepal.recipes.get_raw("recipe-id")         # exact stored bytes

sepal.recipes.save(
    "recipe-id",
    project_id="proj-1",
    type="CLASSIFICATION",
    name="My recipe",
    contents={"key": "value"},        # JSON-serializable or bytes/str
)
sepal.recipes.delete("recipe-id")
```

## Escape hatch — any other route

The typed endpoints cover the common cases; for anything else use the generic
primitives. They return the raw `httpx.Response` with the same typed-error
mapping.

```python
image = sepal.get("/api/gee/image/json", params={"recipeId": "foo"}).json()
sepal.post("/api/some/route", json={"a": 1})
```
