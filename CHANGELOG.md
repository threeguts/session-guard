# Changelog

## v0.0.0

- Fixed the file watcher so it ignores `events.json` and does not re-trigger on its own log writes.
- Kept the watcher focused on the supported event types: `created`, `modified`, `deleted`, and `moved`.
