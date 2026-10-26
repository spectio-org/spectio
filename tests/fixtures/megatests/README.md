# Real nf-core megatest outputs

Small subsets of the outputs nf-core publishes for every release's full-size test (`s3://nf-core-awsmegatests`).
Made by `python3 tools/fixtures/megatests.py fetch … && … curate …`; each folder's `SOURCE.json` gives the release,
the commit and the bucket prefix. Owner: [`dev-environment-and-testing.md`](../../../docs/specs/dev-environment-and-testing.md) §10.3.

Used by the check bindings (real MultiQC column names), the UI boards and, later, the API mock mode.
Licence of the outputs: derived from nf-core/test-datasets [to be validated].
