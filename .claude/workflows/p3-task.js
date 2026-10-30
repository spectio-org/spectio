export const meta = {
  name: 'p3-task',
  description: 'Build one P3 task (one P1 plan task) end to end: TDD build, code and security review with fix rounds, simplify, docs, figure and doc review',
  whenToUse: 'The autopilot runs it once per P3 task (docs/playbooks/autopilot.md §10). The orchestrator then pushes, opens the PR, merges and promotes.',
  phases: [
    { title: 'Build', detail: 'worker in its own git worktree, test-driven' },
    { title: 'Review', detail: 'code-reviewer and security-reviewer in parallel, fix rounds' },
    { title: 'Simplify', detail: 'code-simplifier on the step diff' },
    { title: 'Docs', detail: 'doc-writer and diagram-artist, docs gate, doc-reviewer' },
  ],
}

// args: {step, task, base, title, extra, session}
//   step: "P3-t04"; task: "Task 4: Projector, run state and Nextflow mapping" (the P1 heading);
//   base: full sha of the integration tip; title: Conventional Commit PR title;
//   extra: deferred findings and follow-ups this task takes (text); session: the Claude-Session URL;
//   font: path of the sketch font (tools/diagrams/sketch.py, SPECTIO_SKETCH_TTF).
const A = args
const branch = `autopilot/${A.step}`
const wt = `.claude/worktrees/${A.step}`
const trailer = `End every commit message with these two lines:\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: ${A.session}`
const gate = 'uv run pytest -q; uv run ruff check .; uv run ruff format --check .; uv run mypy packages; uv run lint-imports; uv lock --check'

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
    report: { type: 'string', description: 'what was built, commands run with results, assumptions, open questions' },
  },
  required: ['head', 'tests', 'test_command', 'report'],
}
const DOCREVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'changes', 'block'] }, score: { type: 'integer' },
    required_changes: { type: 'array', items: { type: 'string' } }, report: { type: 'string' },
  },
  required: ['verdict', 'score', 'required_changes', 'report'],
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

const reviewPrompt = (kind, range) => `${kind} the Spectio build step ${A.step} ("${A.task}" in docs/plans/P1-walking-skeleton.md) in the worktree ${wt} (branch ${branch}).
Review the diff ${range}. Also in scope: ${A.extra || 'nothing else'}. Worker's report:\n${build.report}
Test command: ${build.test_command}. Number your findings ${kind === 'Review' ? 'CR' : 'SEC'}-${A.step.replace('-', '').toUpperCase()}-NN, continuing after any IDs already in docs/reviews/code/${A.step}.md.`
const review = (range) => parallel([
  () => agent(reviewPrompt('Review', range), { label: 'code-reviewer', phase: 'Review', agentType: 'code-reviewer', schema: FINDINGS }),
  () => agent(reviewPrompt('Security-review', range), { label: 'security-reviewer', phase: 'Review', agentType: 'security-reviewer', schema: FINDINGS }),
])
const fix = (items, why) => agent(
  `In the worktree ${wt} (branch ${branch}), fix these review findings of step ${A.step} (${why}), test-first, then run the gate (${gate}) and commit:\n${items.map(f => `- ${f.id} (${f.severity}) ${f.summary} ${f.where || ''} Fix: ${f.fix || ''}`).join('\n')}
Keep each fix minimal. If a finding is wrong, say why instead of changing code. ${trailer}`,
  { label: `fix ${why}`, phase: 'Review', agentType: 'general-purpose', schema: BUILD })

const rounds = []
let verdicts = await review(`${A.base}..HEAD`)
if (verdicts.some(v => !v)) throw new Error('a reviewer returned nothing')
rounds.push(verdicts)
// review-code step 4: two fix rounds, more while a security blocker or major is open (inbox #75), never more than 4.
for (let r = 1; r <= 4; r++) {
  const open = verdicts.filter(Boolean).flatMap(v => v.findings).filter(f => f.severity === 'blocker' || f.severity === 'major')
  const secOpen = (verdicts[1]?.findings || []).some(f => f.severity === 'blocker' || f.severity === 'major')
  if (!open.length) break  // the fix loop is for blockers and majors only (review-code step 4)
  if (r > 2 && !secOpen) return { status: 'blocked', reason: 'two fix rounds without approval', rounds, build }
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
  const post = await review(`${before}..HEAD`)
  rounds.push(post)
  const bad = post.filter(Boolean).flatMap(v => v.findings).filter(f => f.severity === 'blocker' || f.severity === 'major')
  if (bad.length || post.some(v => !v || v.verdict !== 'approve')) return { status: 'blocked', reason: 'the post-approval fixes did not pass review', rounds, build }
}

phase('Simplify')
const simplifyIn = rounds.flat().filter(Boolean).flatMap(v => v.findings).filter(f => f.severity === 'simplify')
const simplify = await agent(
  `Simplify step ${A.step} in the worktree ${wt} (branch ${branch}): only the diff ${A.base}..HEAD, never behaviour, public names or tests of kept code.
Findings to consider: ${simplifyIn.map(f => `${f.id}: ${f.summary} ${f.where || ''}`).join('; ') || 'none named'}. Test command: ${gate}. ${trailer}
Return the SIMPLIFY line (result=changed|reverted, -n/+n, tests=pass|fail) and the new HEAD.`,
  { label: 'code-simplifier', agentType: 'code-simplifier' })

phase('Docs')
const evidence = `Step ${A.step} (wave W5, kind build), worktree ${wt}, branch ${branch}, BASE ${A.base}. Use git log/diff BASE..HEAD for the code.
Worker report:\n${build.report}\nReview rounds (verdicts and findings, all saved to docs/reviews/code/${A.step}.md):\n${rounds.map((rv, i) => `Round ${i + 1}: ${rv.filter(Boolean).map(v => `${v.verdict}: ${v.findings.map(f => `${f.id} ${f.severity} ${f.summary}`).join(' | ')}`).join(' || ')}`).join('\n')}
Simplifier: ${simplify}`
const [docs] = await parallel([
  () => agent(`Write the docs for ${evidence}
Follow docs/specs/documentation-system.md and how Tasks 1-3 are documented: a section of docs/progress/W5/P3-M1.md, the review record docs/reviews/code/${A.step}.md with its CODE line, the owning spec updated where behaviour was decided (new numbers marked assumed or [to be validated]; a question with no safe default goes to docs/reviews/inbox.md as a new entry with options, the recommendation assumed). A diagram-artist draws docs/assets/diagrams/${A.step.toLowerCase()}-*_{light,dark}.png in parallel on the branch: embed it first under the !!! line when it exists.
Run python3 tools/docs/check.py and uvx --with mkdocs-material mkdocs build --strict. Write the PR body (title "${A.title}") to docs-pr-body.md at the worktree root but do not commit that file; it needs a Markdown image line to the figure on raw.githubusercontent.com/spectio-org/spectio/<sha>/... and preview links https://pr-PR_NUMBER.spectio.pages.dev/...; check it with tools/docs/check.py --only pr-body. ${trailer}`,
    { label: 'doc-writer', phase: 'Docs', agentType: 'doc-writer' }),
  () => agent(`Draw one figure for ${evidence}
Follow tools/diagrams/p3_t03_spool_reader.py: a script tools/diagrams/${A.step.toLowerCase().replace('-', '_')}_<name>.py producing docs/assets/diagrams/${A.step.toLowerCase()}-<name>_{light,dark}.{svg,png}, a docs/assets/media.yaml entry, pictograms not boxes, every label checked against the code. Render with SPECTIO_SKETCH_TTF=${A.font} uv run --no-project --with playwright python <script>; look at the PNGs. Commit on the branch. ${trailer}`,
    { label: 'diagram-artist', phase: 'Docs', agentType: 'diagram-artist' }),
])

let docReview
for (let r = 0; r <= 2; r++) {
  docReview = await agent(`Review the documentation of ${evidence}
Changed pages: see git diff --stat ${A.base}..HEAD -- docs tools/diagrams. PR body draft: ${wt}/docs-pr-body.md. Rubric: docs/specs/documentation-system.md §4.2. Re-run sampled commands, open every figure, check claims against the code, run tools/docs/check.py and mkdocs build --strict.`,
    { label: `doc-reviewer ${r + 1}`, phase: 'Docs', agentType: 'doc-reviewer', schema: DOCREVIEW })
  if (docReview.verdict === 'block') return { status: 'blocked', reason: 'doc-reviewer block', docReview, rounds, build }
  if (!docReview.required_changes.length) break
  if (r === 2) return { status: 'blocked', reason: 'two doc revisions without approval', docReview, rounds, build }
  await agent(`In the worktree ${wt} (branch ${branch}), make these required doc changes, rerun tools/docs/check.py and mkdocs build --strict, update docs-pr-body.md if affected, commit:\n${docReview.required_changes.join('\n')}\n${trailer}`,
    { label: `doc fix ${r + 1}`, phase: 'Docs', agentType: 'doc-writer' })
}

return { status: 'done', step: A.step, branch, worktree: wt, prBody: `${wt}/docs-pr-body.md`, build, rounds: rounds.length, simplify, docs, docReview }
