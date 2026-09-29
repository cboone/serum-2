# Align serum-2 with its Tier 1 role

## Context

On 2026-09-28 the original `cboone/serum-2` was renamed and made private, and this repository was created fresh from one commit (`5ce9d8d`) holding the public share of the split: `serumfile.py`, `make_sweep.py`, the file-format reference, the Dirichlet Sweep tables and synthetic CC0 fixtures. Catamount Audio's internal label guidelines define this repository as public, Tier 1, MIT with CC0 examples, and as the future Serum adapter once a host-agnostic core is split out.

The content is already in good shape. History is a single commit with no private material, `make check` passes (15/15 scrut cases, ruff, markdownlint, Prettier), the regenerated tables are byte-identical to the committed ones, and `make_fixtures.py` reproduces the fixtures exactly. The README already carries the output-ownership statement, the Catamount names statement, and the Xfer Records disclaimer.

What remains is scrubbing a few preset-repository leftovers, meeting the label guidelines' host disclaimer and core/adapter boundary rules, bringing scaffolding up to the level of the sibling Tier 1 repository `audio-tools`, and configuring GitHub settings, which are all at defaults.

## Work

### 1. Scrub preset-repository leftovers

- `tools/serumfile.py`: `rowcurves` defaults `CURVE_DIR` to `serum/Curves`, a directory that does not exist here. Make the argument required (existing callers already pass it explicitly). Update the docstring, `docs/SERUM-FILE-FORMAT.md`, the README usage block, and the scrut test if its output changes.
- `docs/SERUM-FILE-FORMAT.md`:
  - Rewrite the opening, whose second sentence has no verb ("Generated curves, wavetables, and a modified preset copy loaded in Serum.").
  - Replace "the preset's macro names in capitals" with a neutral description of the `name` field.
  - "The generated tables matched the reference tables sample for sample" refers to tables not in this repository. Restate it as a confirmed-against-earlier-copies claim, or drop it in favor of the scrut test that now enforces reproduction.
  - Reword "the mysterious kParamCurveIn" and the "(CurveIn test)" example so they describe the format (the key's meaning is not established) rather than a measurement in progress.
  - Audit every claim for a confirmed, documented or inferred label, per `AGENTS.md`.

### 2. Host disclaimer in documentation

The label guidelines require the not-affiliated disclaimer in every piece of documentation that names a third-party host, not only the README. Add a short disclaimer to `docs/SERUM-FILE-FORMAT.md`, and to any new community files that name Serum.

### 3. Record the core/adapter boundary

The label guidelines say host-independent code must stay free of Serum imports so it can move to a core repository when Vital work begins, and forbids splitting before then. The boundary already holds: `make_sweep.py` (wavetable generation and the `clm` WAV writer) does not import `serumfile`. Add a rule to `AGENTS.md` naming which scripts are host-independent and forbidding `serumfile` imports in them. No code moves now.

### 4. Community and security scaffolding

Match `audio-tools`, the closest sibling (Python tools, public, MIT):

- Add `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/SECURITY.md` and `.github/PULL_REQUEST_TEMPLATE.md` with the `add-community-files` skill. `CONTRIBUTING.md` must restate the CC0 rule for new example files and the ban on factory or third-party content, and must not link to any private repository.
- Add gitleaks and TruffleHog workflows with the `set-up-secret-scanning` skill, SHA-pinned.
- Add `.github/dependabot.yml` for `github-actions` and `npm`. Dependabot cannot update PEP 723 script lockfiles, so those stay manual (`uv lock --script`).
- Add a `cspell` spelling check matching `audio-tools` (`cspell.jsonc`, `cspell-words.txt`, pinned in `package.json`, run by `make text-lint` and the text-lint workflow).

### 5. README and changelog

- Add a Contributing section linking `CONTRIBUTING.md`, and document `make git-setup` for users who keep their own presets in Git.
- Note the tested Serum version near the top (2.1.5), since format changes are the main compatibility risk.
- Add changelog entries for user-visible changes (the required `rowcurves` argument above all).

### 6. GitHub repository settings

These are writes to `cboone/serum-2`. Apply them as part of this work once Chris confirms the details. `audio-tools` and the other public Catamount repositories share identical settings, so the values follow them, plus topics:

- General: disable the wiki and projects, enable discussions, enable auto-merge, and enable delete-branch-on-merge.
- Merging: allow merge commits only (turn off squash and rebase merging).
- Topics: `serum`, `serum-2`, `wavetable`, `synthesizer`, `preset`, `cli`, `sound-design`.
- Rulesets: the `Main` ruleset on the default branch (block deletion and force pushes, require a pull request with no required approvals and merge method `merge`, Copilot review on push and on drafts) and the `PRs` ruleset on all branches (Copilot review).
- Unchanged: Dependabot security updates, secret scanning and push protection (already on), Actions read-only default token.

### 7. First release

Approved. After this work merges, cut `v0.1.0` with the `release` skill, so downstream pins have a readable name and the adapter's own release schedule starts.

### Out of scope

- Updating downstream pins of this repository. Consumers update their own pins after verifying against the new release; nothing here refers to them.
- Changes to the label guidelines, which already describe this repository correctly.
- Extracting a core package or repository (deferred until a second host, per the label guidelines).

## Verification

- `make check` passes, and scrut tests cover the `rowcurves` change.
- No names of private repositories or unreleased products appear anywhere in the repository.
- Every Markdown file naming Serum carries the disclaimer.
- Tables and fixtures still regenerate identically (checksums).
- `gh api repos/cboone/serum-2` and its rulesets match the intended settings.

## Outcome

Steps 1 to 6 are done in PR #1. `make check`, `actionlint`, and local gitleaks and TruffleHog scans of the full history pass, and tables and fixtures regenerate identically. The repository settings, topics and both rulesets were applied on 2026-09-29 and match `audio-tools` field for field; the rulesets also carry that repository's bypass for the admin role.

- The disclaimer appears in the user-facing documentation: the README, `CONTRIBUTING.md` and the format reference. Agent config, the changelog and the PR template name Serum only in passing and do not carry it.
- The code of conduct contact is `conduct@snappy.sh`, matching `audio-tools`.
- The first draft of this plan named private repositories. The branch was rebuilt before its first push so that text never reached public history.
- Step 7, the `v0.1.0` release, follows the merge.
