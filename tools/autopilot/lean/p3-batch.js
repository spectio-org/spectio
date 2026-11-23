export const meta = {
  name: 'p3-batch',
  description: 'Close a batch of merged P3 tasks: one simplify pass on the batch diff and the Progress page; at a milestone end also one figure and doc-reviewer',
  whenToUse: 'The autopilot runs it after 3 to 5 P3 tasks have merged into autopilot/integration, or when a milestone ends (milestone: true) (docs/playbooks/autopilot.md §11, §14). The orchestrator then pushes, opens the PR and merges it; promotion to main runs once at the end of the session run.',
  phases: [
    { title: 'Simplify', detail: 'code-simplifier on the batch diff, re-review when more than trivial' },
    { title: 'Docs', detail: 'doc-writer; at a milestone end also diagram-artist and doc-reviewer' },
  ],
}

// args: {batch, steps, base, head, title, session, font, milestone}
//   milestone: true when this batch closes a milestone: only then the figure and doc-reviewer run (autopilot.md §14).
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
let simplify = await agent(
  `Create a git worktree: \`git worktree add ${wt} -b ${branch} ${A.head}\` (from the repository root), and work only there.
Simplify the code of batch ${A.batch} (steps ${steps}): only the diff ${A.base}..${A.head} under packages/ and web/src/, never behaviour, public names or tests of kept code.
Consider the simplify: findings in ${simplifyIn}. Test command: ${gate}. Commit on the branch. ${trailer}
Return result=none when nothing is worth changing, and the new HEAD.`,
  { label: 'code-simplifier', agentType: 'code-simplifier', schema: SIMPLIFY })

// review-code step 5: a failed simplification is reverted and never blocks the batch; one that is more
// than trivial is re-reviewed once on its own range, and reverted on a blocker or major.
const REVERT = { type: 'object', properties: { head: { type: 'string' }, tests: { type: 'string', enum: ['pass', 'fail'] } }, required: ['head', 'tests'] }
const revert = async (why) => {
  const out = await agent(`In the worktree ${wt} (branch ${branch}), revert every commit after ${A.head} with git revert (never reset or force-push), because ${why}. Run the gate (${gate}) and return the new HEAD. ${trailer}`,
    { label: 'revert simplify', phase: 'Simplify', agentType: 'general-purpose', schema: REVERT })
  if (!out || out.tests !== 'pass') throw new Error(`the simplify revert did not leave the gate green (${why})`)
  return { result: 'reverted', head: out.head, removed: 0, added: 0, tests: 'pass', report: `reverted: ${why}` }
}
if (!simplify) simplify = await revert('the simplifier returned nothing')
else if (simplify.result === 'changed' && simplify.tests === 'fail') simplify = await revert('the tests failed after it')

let rereview = null
if (simplify.result === 'changed' && simplify.removed + simplify.added > 20) {
  const prompt = (kind) => `${kind} the code-simplifier commits of batch ${A.batch} in the worktree ${wt}: the diff ${A.head}..HEAD only. They must not change behaviour, public names or tests. Test command: ${gate}. Number findings ${kind === 'Review' ? 'CR' : 'SEC'}-${A.batch.replace('-', '').toUpperCase()}-NN.`
  rereview = await parallel([
    () => agent(prompt('Review'), { label: 'code-reviewer', phase: 'Simplify', agentType: 'code-reviewer', schema: FINDINGS }),
    () => agent(prompt('Security-review'), { label: 'security-reviewer', phase: 'Simplify', agentType: 'security-reviewer', schema: FINDINGS }),
  ])
  if (rereview.some(v => !v)) throw new Error('a reviewer of the simplification returned nothing')
  const bad = rereview.flatMap(v => v.findings).filter(f => f.severity === 'blocker' || f.severity === 'major')
  if (bad.length) simplify = await revert(`its review found ${bad.map(f => `${f.id} ${f.summary}`).join('; ')}`)
}

phase('Docs')
const evidence = `Batch ${A.batch} (wave W5): steps ${steps}, merged into autopilot/integration between ${A.base} and ${A.head}. Worktree ${wt}, branch ${branch}.
Per step: its review record docs/reviews/code/<step>.md (CODE line, findings, assumptions) and its PR on GitHub. Use git log/diff ${A.base}..HEAD for the code.
Simplifier: ${simplify.result} -${simplify.removed}/+${simplify.added} tests=${simplify.tests}. ${simplify.report}
Re-review of the simplification: ${rereview ? rereview.map(v => `${v.verdict}: ${v.findings.map(f => `${f.id} ${f.severity} ${f.summary}`).join(' | ') || 'no findings'}`).join(' || ') : 'not needed'}.`
const [docs] = await parallel([
  () => agent(`Write the batch docs for ${evidence}
Follow docs/specs/documentation-system.md §3.5: save the re-review of the simplification, if any, to docs/reviews/code/${A.batch}.md with its CODE line; add one short section per step to the milestone Progress page under docs/progress/W5/ (3 to 5 bullets, the CODE line, links${A.milestone ? '' : '; keep status: running'}), its Findings and open questions and the follow-up list of minors left open, the guide or reference pages the batch needs, and the screenshots for new screens only (media-capture, docs/assets/media.yaml). ${A.milestone ? `This batch closes the milestone: complete the page (Evidence, Figures and media); a diagram-artist draws docs/assets/diagrams/${A.batch.toLowerCase()}-*_{light,dark}.png in parallel on the branch: embed it first under the !!! line.` : 'No figure: it comes at the milestone end.'}
Run python3 tools/docs/check.py (CI's docs-gate builds the site). Write the PR body (title "${A.title}") to docs-pr-body.md at the worktree root but do not commit that file; ${A.milestone ? 'it needs a Markdown image line to the figure on raw.githubusercontent.com/spectio-org/spectio/<sha>/... and' : 'the PR carries the no-figure label; it needs'} preview links https://pr-PR_NUMBER.spectio.pages.dev/...; check it with \`python3 tools/docs/check.py --only pr-body --pr-title "${A.title}" --pr-body docs-pr-body.md --changed <(git diff --name-only ${A.base}..HEAD)${A.milestone ? '' : ' --labels no-figure'}\`. ${trailer}`,
    { label: 'doc-writer', phase: 'Docs', agentType: 'doc-writer' }),
  ...(A.milestone ? [() => agent(`Draw one figure for ${evidence}
It shows the mechanisms the batch added, together. Follow tools/diagrams/p3_t03_spool_reader.py: a script tools/diagrams/${A.batch.toLowerCase().replace('-', '_')}_<name>.py producing docs/assets/diagrams/${A.batch.toLowerCase()}-<name>_{light,dark}.{svg,png}, a docs/assets/media.yaml entry, pictograms not boxes, every label checked against the code. Render with SPECTIO_SKETCH_TTF=${A.font} uv run --no-project --with playwright python <script>; look at the PNGs. Commit on the branch. ${trailer}`,
    { label: 'diagram-artist', phase: 'Docs', agentType: 'diagram-artist' })] : []),
])

// doc-reviewer once per milestone, not per batch (autopilot.md §14).
let docReview = null
for (let r = 0; A.milestone && r <= 2; r++) {
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
