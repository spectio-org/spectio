export const meta = {
  name: 'p3-batch',
  description: 'Close a batch of merged P3 tasks: one simplify pass on the batch diff, the full Progress page, one figure, the docs gate and doc-reviewer',
  whenToUse: 'The autopilot runs it after 3 to 5 P3 tasks have merged into autopilot/integration, or when a milestone ends (docs/playbooks/autopilot.md §11). The orchestrator then pushes, opens the PR, merges it and promotes to main once.',
  phases: [
    { title: 'Simplify', detail: 'code-simplifier on the batch diff, re-review when more than trivial' },
    { title: 'Docs', detail: 'doc-writer and diagram-artist, docs gate, doc-reviewer' },
  ],
}

// args: {batch, steps, base, head, title, session, font}
//   batch: "P3-B01"; steps: ["P3-t12", "P3-t13", ...] (the merged tasks of the batch);
//   base: full sha of autopilot/integration before the first task of the batch merged;
//   head: full sha of the integration tip, after the last one; title: Conventional Commit PR title;
//   session: the Claude-Session URL; font: path of the sketch font (SPECTIO_SKETCH_TTF).
const A = args
const branch = `autopilot/${A.batch}`
const wt = `.claude/worktrees/${A.batch}`
const trailer = `End every commit message with these two lines:\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: ${A.session}`
const gate = 'uv run pytest -q; uv run ruff check .; uv run ruff format --check .; uv run mypy packages; uv run lint-imports; uv lock --check; (cd web && npx vitest run && npx tsc --noEmit)'
const steps = A.steps.join(', ')

const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'changes', 'block'] },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'simplify'] },
      summary: { type: 'string' }, where: { type: 'string' },
    }, required: ['id', 'severity', 'summary'] } },
    report: { type: 'string' },
  },
  required: ['verdict', 'findings', 'report'],
}
const SIMPLIFY = {
  type: 'object',
  properties: {
    result: { type: 'string', enum: ['changed', 'reverted', 'none'] }, head: { type: 'string' },
    removed: { type: 'integer' }, added: { type: 'integer' }, tests: { type: 'string', enum: ['pass', 'fail'] },
    report: { type: 'string' },
  },
  required: ['result', 'head', 'removed', 'added', 'tests', 'report'],
}
const DOCREVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'changes', 'block'] }, score: { type: 'integer' },
    required_changes: { type: 'array', items: { type: 'string' } }, report: { type: 'string' },
  },
  required: ['verdict', 'score', 'required_changes', 'report'],
}

phase('Simplify')
const simplifyIn = A.steps.map(s => `docs/reviews/code/${s}.md`).join(', ')
const simplify = await agent(
  `Create a git worktree: \`git worktree add ${wt} -b ${branch} ${A.head}\` (from the repository root), and work only there.
Simplify the code of batch ${A.batch} (steps ${steps}): only the diff ${A.base}..${A.head} under packages/ and web/src/, never behaviour, public names or tests of kept code.
Consider the simplify: findings in ${simplifyIn}. Test command: ${gate}. Commit on the branch. ${trailer}
Return result=none when nothing is worth changing, and the new HEAD.`,
  { label: 'code-simplifier', agentType: 'code-simplifier', schema: SIMPLIFY })

// review-code step 5: a simplification that is more than trivial is re-reviewed once on its own range.
let rereview = null
if (simplify.result === 'changed' && simplify.removed + simplify.added > 20) {
  const prompt = (kind) => `${kind} the code-simplifier commits of batch ${A.batch} in the worktree ${wt}: the diff ${A.head}..HEAD only. They must not change behaviour, public names or tests. Test command: ${gate}.`
  rereview = await parallel([
    () => agent(prompt('Review'), { label: 'code-reviewer', phase: 'Simplify', agentType: 'code-reviewer', schema: FINDINGS }),
    () => agent(prompt('Security-review'), { label: 'security-reviewer', phase: 'Simplify', agentType: 'security-reviewer', schema: FINDINGS }),
  ])
  const bad = rereview.filter(Boolean).flatMap(v => v.findings).filter(f => f.severity === 'blocker' || f.severity === 'major')
  if (bad.length) {
    await agent(`In the worktree ${wt} (branch ${branch}), revert the code-simplifier commits after ${A.head} (git revert, never reset or force-push): their review found ${bad.map(f => `${f.id} ${f.summary}`).join('; ')}. Run the gate (${gate}). ${trailer}`,
      { label: 'revert simplify', phase: 'Simplify', agentType: 'general-purpose' })
  }
}

phase('Docs')
const evidence = `Batch ${A.batch} (wave W5): steps ${steps}, merged into autopilot/integration between ${A.base} and ${A.head}. Worktree ${wt}, branch ${branch}.
Per step: its review record docs/reviews/code/<step>.md (CODE line, findings), its short section in the milestone Progress page under docs/progress/W5/, its PR on GitHub. Use git log/diff ${A.base}..HEAD for the code.
Simplifier: ${simplify.result} -${simplify.removed}/+${simplify.added} tests=${simplify.tests}${rereview ? `; re-review: ${rereview.filter(Boolean).map(v => v.verdict).join(', ')}` : ''}.`
const [docs] = await parallel([
  () => agent(`Write the batch docs for ${evidence}
Follow docs/specs/documentation-system.md §3.5: complete the milestone Progress page from the per-task sections (Evidence, Figures and media, Findings and open questions, the follow-up list of minors left open), the guide or reference pages the batch needs, and the screenshots or casts for new screens and CLI flows (media-capture, docs/assets/media.yaml). A diagram-artist draws docs/assets/diagrams/${A.batch.toLowerCase()}-*_{light,dark}.png in parallel on the branch: embed it first under the !!! line.
Run python3 tools/docs/check.py and uvx --with mkdocs-material mkdocs build --strict. Write the PR body (title "${A.title}") to docs-pr-body.md at the worktree root but do not commit that file; it needs a Markdown image line to the figure on raw.githubusercontent.com/spectio-org/spectio/<sha>/... and preview links https://pr-PR_NUMBER.spectio.pages.dev/...; check it with tools/docs/check.py --only pr-body. ${trailer}`,
    { label: 'doc-writer', phase: 'Docs', agentType: 'doc-writer' }),
  () => agent(`Draw one figure for ${evidence}
It shows the mechanisms the batch added, together. Follow tools/diagrams/p3_t03_spool_reader.py: a script tools/diagrams/${A.batch.toLowerCase().replace('-', '_')}_<name>.py producing docs/assets/diagrams/${A.batch.toLowerCase()}-<name>_{light,dark}.{svg,png}, a docs/assets/media.yaml entry, pictograms not boxes, every label checked against the code. Render with SPECTIO_SKETCH_TTF=${A.font} uv run --no-project --with playwright python <script>; look at the PNGs. Commit on the branch. ${trailer}`,
    { label: 'diagram-artist', phase: 'Docs', agentType: 'diagram-artist' }),
])

let docReview
for (let r = 0; r <= 2; r++) {
  docReview = await agent(`Review the documentation of ${evidence}
Changed pages: see git diff --stat ${A.base}..HEAD -- docs tools/diagrams. PR body draft: ${wt}/docs-pr-body.md. Rubric: docs/specs/documentation-system.md §4.2. Re-run sampled commands, open every figure, check claims against the code, run tools/docs/check.py and mkdocs build --strict.`,
    { label: `doc-reviewer ${r + 1}`, phase: 'Docs', agentType: 'doc-reviewer', schema: DOCREVIEW })
  if (docReview.verdict === 'block') return { status: 'blocked', reason: 'doc-reviewer block', docReview, simplify }
  if (!docReview.required_changes.length) break
  if (r === 2 && docReview.verdict !== 'approve') return { status: 'blocked', reason: 'two doc revisions without approval', docReview, simplify }
  await agent(`In the worktree ${wt} (branch ${branch}), make these required doc changes, rerun tools/docs/check.py and mkdocs build --strict, update docs-pr-body.md if affected, commit:\n${docReview.required_changes.join('\n')}\n${trailer}`,
    { label: `doc fix ${r + 1}`, phase: 'Docs', agentType: 'doc-writer' })
  if (r === 2) break
}

return { status: 'done', batch: A.batch, steps: A.steps, branch, worktree: wt, prBody: `${wt}/docs-pr-body.md`, simplify, rereview, docs, docReview }
