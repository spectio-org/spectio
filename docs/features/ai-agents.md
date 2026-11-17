# AI agents

!!! note "Later: not in 0.0.1"

    AI agents are planned and not built. The date is not set; see the [roadmap](../roadmap/index.md).

AI agents are optional. Spectio treats them like any other participant, with their own access and a full record of what they do.

- **They suggest at QC gates.** An agent reads a gate's checks and suggests a decision; a person decides. A gate can also let an agent approve on its own, or keep agents out: each workflow chooses (`agents: propose`, `approve` or `none`).
- **They get the evidence, not the raw reports.** An agent sees the metrics, small thumbnails and the text taken from reports, never their raw HTML, so a report cannot slip instructions to it.
- **They have their own token.** An agent signs in with its own token and scopes, such as suggesting at gates without deciding.
- **Every action is recorded.** Each decision keeps who made it: a person, a service or an agent, with the agent's model. The run's RO-Crate keeps that record too.
- **They can drive Spectio.** Besides the API, Spectio offers an MCP server, so an assistant can list runs, follow them or look at a gate.

Spectio itself is designed and built with AI coding agents, each step checked by independent reviewers; the record is in the repository.
