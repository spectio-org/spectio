export const meta = {
  name: 'p3-task',
  description: 'Build one P3 task (one P1 plan task): TDD build, code review (security review when the diff touches a sensitive path), one fix round, short docs',
  whenToUse: 'The autopilot runs it once per P3 task (docs/playbooks/autopilot.md §10, §11). The orchestrator then pushes, opens the PR and merges; simplify, figure, doc review and promotion run once per batch (p3-batch).',
  phases: [
    { title: 'Build', detail: 'worker in its own git worktree, test-driven' },
    { title: 'Review', detail: 'code-reviewer, plus security-reviewer on sensitive paths, fix rounds' },
    { title: 'Docs', detail: 'doc-writer: review record, short Progress section, owning spec, PR body' },
  ],
}

// args: {step, task, base, title, extra, session}
//   step: "P3-t04"; task: "Task 4: Projector, run state and Nextflow mapping" (the P1 heading);
//   base: full sha of the integration tip; title: Conventional Commit PR title;
//   extra: deferred findings and follow-ups this task takes (text); session: the Claude-Session URL;
//   security: 'always' to force the security review (the dev-env §15.3 tasks); otherwise it runs
//   when a changed path matches SENSITIVE (autopilot.md §11, decision of 2026-11-04).
const A = args
const branch = `autopilot/${A.step}`
const wt = `.claude/worktrees/${A.step}`
const trailer = `End every commit message with these two lines:\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: ${A.session}`
const gate = 'uv run pytest -q; uv run ruff check .; uv run ruff format --check .; uv run mypy packages; uv run lint-imports; uv lock --check'

// Paths whose change always gets a security review (autopilot.md §11): the HTTP surface, file access,
// the runner and login shell, config, migrations, CI, dependencies, and anything named like a secret.
const SENSITIVE = [
  /^packages\/spectio-server\/src\/spectio_server\/(api|files|migrations)\//,
  /^packages\/spectio-server\/src\/spectio_server\/(app|serve|static|bootstrap)\.py$/,
  /^packages\/spectio\/src\/spectio\/(runner\/|loginshell\.py|config\.py)/,
  /^\.github\//, /^tools\/ci\//, /(^|\/)(pyproject\.toml|uv\.lock|package(-lock)?\.json)$/,
  /auth|token|secret|session|sandbox|plugin|permission/i,
]
const touched = new Set()
const needSecurity = () => A.security === 'always' || [...touched].some(p => SENSITIVE.some(r => r.test(p)))

const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'changes', 'block'] },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'simplify'] },
      summary: { type: 'string' }, where: { type: 'string' }, fix: { type: 'string' },
      defect: { type: 'boolean', description: 'true when it is a wrong result or regression in this step\'s own code, not style' },
    }, required: ['id', 'severity', 'summary', 'defect'] } },
    report: { type: 'string', description: 'the full review text, as it should be saved in the review record' },
  },
  required: ['verdict', 'findings', 'report'],
}
const BUILD = {
  type: 'object',
  properties: {
    head: { type: 'string' }, tests: { type: 'string' }, test_command: { type: 'string' },
    changed_paths: { type: 'array', items: { type: 'string' }, description: 'git diff --name-only BASE..HEAD, every line' },
    report: { type: 'string', description: 'what was built, commands run with results, assumptions, open questions' },
  },
  required: ['head', 'tests', 'test_command', 'changed_paths', 'report'],
}
phase('Build')
let build = await agent(
  `Build Spectio step ${A.step}: P1 plan "### ${A.task}" in docs/plans/P1-walking-skeleton.md (see P2-execution.md §0 for how P3 runs P1 tasks).
Create a git worktree: \`git worktree add ${wt} -b ${branch} ${A.base}\` (from the repository root), and work only there.
Also in scope: ${A.extra || 'nothing else'}.
Read the owning specs the task names and the earlier P3 review records in docs/reviews/code/ for the standard this code will meet.
Follow karpathy-guidelines, test-driven-development (show the failing run first) and verification-before-completion. Do not write docs pages.
Run the gate before finishing: ${gate}. Never push, never force-push, never bypass hooks, no model identifier in commits. ${trailer}`,
  { label: `build ${A.step}`, agentType: 'general-purpose', schema: BUILD })
build.changed_paths.forEach(p => touched.add(p))

const reviewPrompt = (kind, range) => `${kind} the Spectio build step ${A.step} ("${A.task}" in docs/plans/P1-walking-skeleton.md) in the worktree ${wt} (branch ${branch}).
Review the diff ${range}. Also in scope: ${A.extra || 'nothing else'}. Worker's report:\n${build.report}
Test command: ${build.test_command}. Number your findings ${kind === 'Review' ? 'CR' : 'SEC'}-${A.step.replace('-', '').toUpperCase()}-NN, continuing after any IDs already in docs/reviews/code/${A.step}.md.`
// verdicts[0] is the code review; verdicts[1], when present, the security review.
const review = (range) => parallel([
  () => agent(reviewPrompt('Review', range), { label: 'code-reviewer', phase: 'Review', agentType: 'code-reviewer', schema: FINDINGS }),
  ...(needSecurity() ? [() => agent(reviewPrompt('Security-review', range), { label: 'security-reviewer', phase: 'Review', agentType: 'security-reviewer', schema: FINDINGS })] : []),
])
const fix = async (items, why) => {
  const out = await agent(
    `In the worktree ${wt} (branch ${branch}), fix these review findings of step ${A.step} (${why}), test-first, then run the gate (${gate}) and commit:\n${items.map(f => `- ${f.id} (${f.severity}) ${f.summary} ${f.where || ''} Fix: ${f.fix || ''}`).join('\n')}
Keep each fix minimal. If a finding is wrong, say why instead of changing code. ${trailer}`,
    { label: `fix ${why}`, phase: 'Review', agentType: 'general-purpose', schema: BUILD })
  out.changed_paths.forEach(p => touched.add(p))
  return out
}

const rounds = []
let verdicts = await review(`${A.base}..HEAD`)
if (verdicts.some(v => !v)) throw new Error('a reviewer returned nothing')
rounds.push(verdicts)
// review-code step 4: one fix round, more while a security blocker or major is open (inbox #75; one round
// since 2026-11-04, autopilot.md §11), never more than 4. Unfixed minors go to the batch's follow-up list.
for (let r = 1; r <= 4; r++) {
  const open = verdicts.filter(Boolean).flatMap(v => v.findings).filter(f => f.severity === 'blocker' || f.severity === 'major')
  const secOpen = (verdicts[1]?.findings || []).some(f => f.severity === 'blocker' || f.severity === 'major')
  if (!open.length) break  // the fix loop is for blockers and majors only (review-code step 4)
  if (r > 1 && !secOpen) return { status: 'blocked', reason: 'one fix round without approval', rounds, build }
  if (r === 4) return { status: 'blocked', reason: 'four rounds and a security finding still open', rounds, build }
  build = await fix(open, `round ${r}`)
  verdicts = await review(`${A.base}..HEAD`)
  if (verdicts.some(v => !v)) throw new Error('a reviewer returned nothing')
  rounds.push(verdicts)
}

// After approval: defects among the minors are fixed (they are bugs in this step's own work), then one
// re-review of those fixes only (inbox #76, recommendation applied under the standing rule of 2026-10-30).
const defects = verdicts.flatMap(v => v.findings).filter(f => f.severity === 'minor' && f.defect)
if (defects.length) {
  const before = build.head
  build = await fix(defects, 'post-approval defects')
  // A post-approval fix can regress: its blockers and majors are fixed and that range re-reviewed, twice at most.
  for (let k = 0; ; k++) {
    const post = await review(`${before}..HEAD`)
    rounds.push(post)
    if (post.some(v => !v)) throw new Error('a reviewer returned nothing')
    const bad = post.flatMap(v => v.findings).filter(f => f.severity === 'blocker' || f.severity === 'major')
    if (!bad.length) break
    if (k === 2) return { status: 'blocked', reason: 'the post-approval fixes did not pass review', rounds, build }
    build = await fix(bad, `post-approval regression ${k + 1}`)
  }
}

// Simplify, the figure, doc-reviewer and the promotion run once per batch (p3-batch.js, autopilot.md §11).
phase('Docs')
const evidence = `Step ${A.step} (wave W5, kind build), worktree ${wt}, branch ${branch}, BASE ${A.base}. Use git log/diff BASE..HEAD for the code.
Worker report:\n${build.report}\nSecurity review: ${needSecurity() ? 'ran' : 'skipped, no sensitive path changed (autopilot.md §11)'}.
Review rounds (verdicts and findings, all saved to docs/reviews/code/${A.step}.md):\n${rounds.map((rv, i) => `Round ${i + 1}: ${rv.filter(Boolean).map(v => `${v.verdict}: ${v.findings.map(f => `${f.id} ${f.severity} ${f.summary}`).join(' | ')}`).join(' || ')}`).join('\n')}`
const docs = await agent(`Write the short per-task docs for ${evidence}
This is the per-task part of docs/specs/documentation-system.md §3.5; the figure, media, the full Progress page and doc-reviewer come later, once per batch. Write only:
- the review record docs/reviews/code/${A.step}.md with its CODE line (security=skipped when it did not run);
- a short section for this task in the milestone's Progress page under docs/progress/W5/ (What changed in a few bullets, the CODE line, links to the review record and the owning spec); no figure;
- the owning spec where behaviour was decided (new numbers marked assumed or [to be validated]; a question with no safe default goes to docs/reviews/inbox.md as a new entry with options, the recommendation assumed).
Run python3 tools/docs/check.py and uvx --with mkdocs-material mkdocs build --strict. Write the PR body (title "${A.title}") to docs-pr-body.md at the worktree root but do not commit that file; it carries no figure: say "Figure: in the batch docs PR" under Docs, and the PR gets the no-figure label. Check it with tools/docs/check.py --only pr-body --labels no-figure. ${trailer}`,
  { label: 'doc-writer', phase: 'Docs', agentType: 'doc-writer' })

return { status: 'done', step: A.step, branch, worktree: wt, prBody: `${wt}/docs-pr-body.md`, build, rounds: rounds.length, security: needSecurity() ? 'ran' : 'skipped', docs }
