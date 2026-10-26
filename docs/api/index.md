---
icon: material/api
---
# API and CLI

!!! note "Designed, planned from 0.1"

Everything the web interface does can be done from a script, a LIMS such as LabID, a CI job or an AI agent.

- **REST API** under `/api/v1`, described by an OpenAPI file. Errors follow one format, and writes are safe to retry.
- **Events** as they happen: live in the browser, by webhooks, or to message systems (MQTT, AMQP, Kafka).
- **The `spectio` command line,** with the same models as depictio's CLI.
- **Tokens** for people, robots and services, each limited to what it needs.

```bash
# launch, wait, keep the IDs
spectio run launch nf-core/rnaseq@3.27.0 --env demo-hpc --project liver-tc \
  --params params.yaml --samplesheet samples.csv --wait --result-json run.json

# what is waiting for me, then decide
spectio gate list --assigned-to me
spectio gate decide gate_01JB… --approve --exclude S03 --comment "S03: 40 reads"
```

The commands above show the planned CLI; they do not exist yet.

Design details: [API and data model](../specs/api-and-data-model.md), [CLI and shared libraries](../specs/cli-and-shared-libraries.md).
