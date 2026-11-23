export const meta = {
  name: 'p3-lean',
  description: 'Build one P3 feature slice cheaply: scoped TDD build, one review, one fix round for blockers and majors, review record and PR body',
  whenToUse: 'Default per-task workflow since 2026-11-09, feature-sized since 2026-11-10 (autopilot.md §14). Simplify and the Progress page run once per batch (p3-batch); figure and doc review once per milestone.',
  phases: [
    { title: 'Build', detail: 'worker in its own worktree, tests in scope only' },
    { title: 'Review', detail: 'one review (security only on sensitive paths), one fix round, verify-only after a blocker' },
    { title: 'Docs', detail: 'review record, owning spec, PR body' },
  ],
}

// args: {step, task, base, title, extra, session, security: 'always'|'never'|undefined}
// task is the full task text (not a P1 heading). Boards-only tasks set no gate: render and look instead.
const A = args
const branch = `autopilot/${A.step}`
const wt = `.claude/worktrees/${A.step}`
const trailer = `End every commit message with exactly these two lines:\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: ${A.session}`
const gate = 'Run only the tests in scope (the test files of what you changed, plus ruff check, ruff format --check and mypy on the changed Python files; tsc --noEmit when web/ changed). The full suite runs in CI: do not run it. A boards-only change runs no test: render each board and look at the PNG.'
const SENSITIVE = [
  /^packages\/spectio-server\/src\/spectio_server\/(api|files|migrations|stages)\//,
  /^packages\/spectio-server\/src\/spectio_server\/(app|serve|static|bootstrap|resume|rebuild)\.py$/,
  /^packages\/spectio-server\/src\/spectio_server\/projector\/ingest\.py$/,
  /^packages\/spectio\/src\/spectio\/(runner\/|loginshell\.py|config\.py|open_remote\.py|cli\/(serve|open)\.py)/,
  /^web\/src\/(runs\/(ReportViewer|LogViewer|ResultsBrowser)|api)\./,
  /^engine-bridges\//, /^\.github\//, /^tools\/ci\//, /(^|\/)(pyproject\.toml|uv\.lock|package(-lock)?\.json)$/,
  /auth|token|secret|session|sandbox|plugin|permission/i,
]
const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'changes', 'block'] },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
      summary: { type: 'string' }, where: { type: 'string' }, fix: { type: 'string' },
      defect: { type: 'boolean', description: "true for a wrong result in this step's own work, not style" },
    }, required: ['id', 'severity', 'summary', 'defect'] } },
    report: { type: 'string', description: 'the review text for the review record, short' },
  },
  required: ['verdict', 'findings', 'report'],
}
const BUILD = {
  type: 'object',
  properties: {
    head: { type: 'string' }, tests: { type: 'string' },
    changed_paths: { type: 'array', items: { type: 'string' } },
    report: { type: 'string', description: 'what was built, commands and results, assumptions; at most 20 lines' },
  },
  required: ['head', 'tests', 'changed_paths', 'report'],
}
const VERIFY = {
  type: 'object',
  properties: {
    resolved: { type: 'array', items: { type: 'string' } },
    unresolved: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } },
  },
  required: ['resolved', 'unresolved'],
}

phase('Build')
let build = await agent(
  `Build Spectio step ${A.step}: ${A.task}
Create a git worktree: \`git worktree add ${wt} -b ${branch} ${A.base}\` (from the repository root) and work only there.
Also in scope: ${A.extra || 'nothing else'}.
Keep it small and surgical (karpathy-guidelines); test-first for code (show the failing run). Do not write docs pages.
${gate} If you add, rename or remove a file under packages/*/src/, update tests/packaging/contents/<package>.wheel.txt.
Never push, never bypass hooks, no model identifier in commits. ${trailer}`,
  { label: `build ${A.step}`, agentType: 'general-purpose', schema: BUILD })

const sec = A.security === 'always' || (A.security !== 'never' && build.changed_paths.some(p => SENSITIVE.some(r => r.test(p))))
const prompt = (kind) => `${kind} step ${A.step} in the worktree ${wt} (branch ${branch}), diff ${A.base}..HEAD. Task: ${A.task}
Worker's report:\n${build.report}
One pass only: report every blocker and major you find now; there is no second full review. Minors are listed, not chased.
Number findings ${kind === 'Review' ? 'CR' : 'SEC'}-${A.step.replace('-', '').toUpperCase()}-NN. Keep the report short.`
phase('Review')
const verdicts = (await parallel([
  () => agent(prompt('Review'), { label: 'code-reviewer', phase: 'Review', agentType: 'code-reviewer', schema: FINDINGS }),
  ...(sec ? [() => agent(prompt('Security-review'), { label: 'security-reviewer', phase: 'Review', agentType: 'security-reviewer', schema: FINDINGS })] : []),
])).filter(Boolean)
if (!verdicts.length) throw new Error('no reviewer returned')

// One fix round, only when a blocker or major was found; defect minors ride along in it, otherwise they go
// to the batch's follow-up list (autopilot.md §14). A verify-only check runs after a blocker or any security
// finding (inbox #75);
// the tests and CI check the rest. It never opens new findings.
const all = verdicts.flatMap(v => v.findings)
const toFix = all.some(f => f.severity !== 'minor') ? all.filter(f => f.severity !== 'minor' || f.defect) : []
let check = null
if (toFix.length) {
  const before = build.head
  build = await agent(
    `In the worktree ${wt} (branch ${branch}), fix these findings of step ${A.step}, minimally, test-first for code, then commit:\n${toFix.map(f => `- ${f.id} (${f.severity}) ${f.summary} ${f.where || ''} Fix: ${f.fix || ''}`).join('\n')}
If a finding is wrong, say why instead of changing anything. ${gate} ${trailer}`,
    { label: 'fix', phase: 'Review', agentType: 'general-purpose', schema: BUILD })
  if (toFix.some(f => f.severity === 'blocker' || f.id.startsWith('SEC-'))) check = await agent(
    `In ${wt}, check ONLY whether each of these findings is resolved by the diff ${before}..HEAD (or rightly rejected by the worker: ${build.report.slice(0, 1500)}). Do not review anything else and do not report new findings.\n${toFix.map(f => `- ${f.id}: ${f.summary}`).join('\n')}`,
    { label: 'verify fixes', phase: 'Review', agentType: 'code-reviewer', schema: VERIFY, effort: 'low' })
  const openBad = (check?.unresolved || []).filter(u => toFix.find(f => f.id === u.id && f.severity !== 'minor'))
  if (openBad.length) return { status: 'blocked', reason: 'blockers or majors unresolved after one fix round', open: openBad, verdicts, build }
}

phase('Docs')
const rec = `Round 1: ${verdicts.map(v => `${v.verdict}: ${v.findings.map(f => `${f.id} ${f.severity}${f.defect ? ' defect' : ''} ${f.summary}`).join(' | ')}`).join(' || ')}${check ? `\nFix check: resolved ${check.resolved.join(', ') || 'none'}; unresolved ${check.unresolved.map(u => `${u.id} (${u.why})`).join(', ') || 'none'}` : ''}`
const docs = await agent(`Write the short per-task docs for step ${A.step}, worktree ${wt}, branch ${branch}, BASE ${A.base} (git log/diff BASE..HEAD).
Worker report:\n${build.report}\nSecurity review: ${sec ? 'ran' : 'skipped (no sensitive path)'}. Reviews:\n${rec}
Write only, briefly (documentation-system §3.5, per-task part):
- docs/reviews/code/${A.step}.md with its CODE line (rounds=${toFix.length ? 2 : 1}; security=skipped when it did not run) and the assumptions the task made;
- the owning spec only where behaviour was decided; an inbox entry only for a question with no safe default or a reserved item (triage-policy.md); no Progress section (the batch writes it), no figure.
Do not build the site: CI's docs-gate does. Write the PR body (title "${A.title}") to docs-pr-body.md at the worktree root, uncommitted, with sections ## Summary (with one "**Type:** <type of the title>" line), ## Docs ("Figure: in the batch docs PR"), ## Evidence (the CODE line in a \`\`\`text block), ## Checks, then the footer "🤖 Generated with [Claude Code](https://claude.com/claude-code)", a blank line, and ${A.session}. Check it with \`python3 tools/docs/check.py --only pr-body --pr-title "${A.title}" --pr-body docs-pr-body.md --changed <(git diff --name-only ${A.base}..HEAD) --labels no-figure\`. Return at most 10 lines. ${trailer}`,
  { label: 'doc-writer', phase: 'Docs', agentType: 'doc-writer', effort: 'low' })

return { status: 'done', step: A.step, branch, worktree: wt, head: build.head, tests: build.tests, security: sec ? 'ran' : 'skipped', fixed: check ? check.resolved : toFix.map(f => f.id), verified: !!check, check, minors: all.filter(f => f.severity === 'minor' && !toFix.includes(f)).map(f => ({ id: f.id, defect: !!f.defect })), docs }
