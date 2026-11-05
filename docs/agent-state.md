# Agent checkpoint / sanitized memory schema

State is an external record, not guaranteed model memory. Save one JSON checkpoint per task under .shards/state/<task-id>.json (ignored by Git). Validate it again on resume; it does not grant permissions.

Recommended JSON keys: goal (string), repo (string), branch (string), commit (string), completed (string array), decisions (string array), evidence (string array), blockers (string array), pending (string array).

Checkpoint rules: use concise factual entries; distinguish observation from inference; include command outputs by reference, not secrets; never include private keys, credentials, environment dumps or personal data. Do not treat stale approval or stale repository state as current authorization. Delete local checkpoints after they are no longer needed.

Use the curated shards-agent-handoff skill for a validating writer. The command rejects recognizable secret formats but cannot prove redaction completeness; human review remains required.
