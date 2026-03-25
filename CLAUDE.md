# prompttools — Project Instructions for Claude

## WHAT THIS PROJECT IS

A monorepo containing a suite of developer tools for managing LLM prompt files. Think eslint/prettier/jest but for prompts.

**promptlint is the base package.** Everything in this suite was extracted from or built on top of the original promptlint tool at `C:\Users\scott\OneDrive\Desktop\Claude\promptlint\`. That project is the reference implementation. Do NOT forget this.

## THE SUITE (v1 scope)

| Package | What it does | Location |
|---------|-------------|----------|
| **prompttools-core** | Shared foundation: parsing, models, tokenization, profiles, config, cache, plugins | `packages/prompttools-core/` |
| **promptlint** | Static analysis / linter for prompt files (34 rules, 9 categories) | CURRENTLY at `C:\Users\scott\OneDrive\Desktop\Claude\promptlint\` — NEEDS TO MOVE into `packages/promptlint/` |
| **promptfmt** | Auto-formatter (whitespace, delimiters, variables, wrapping, structure) | `packages/promptfmt/` |
| **promptcost** | Token cost estimator, model comparison, budget enforcement | `packages/promptcost/` |
| **prompttest** | Test framework — YAML test files with assertions about prompts | `packages/prompttest/` |
| **promptdiff** | Semantic diff for prompt changes — message-level diffs, variable impact, token deltas, breaking change detection | `packages/promptdiff/` |
| **promptvault** | Version control and registry for prompt assets — semantic versioning, dependency resolution, lockfiles, searchable catalog | `packages/promptvault/` |

## BUILD & TEST COMMANDS

```bash
# Install all packages in dev mode
pip install -e packages/prompttools-core[dev]
pip install -e packages/promptcost[dev]
pip install -e packages/promptfmt[dev]
pip install -e packages/prompttest[dev]
pip install -e packages/promptdiff[dev]
pip install -e packages/promptvault[dev]

# Run all tests
pytest

# Run tests for a single package
pytest packages/prompttools-core/tests/
pytest packages/promptcost/tests/
pytest packages/promptfmt/tests/
pytest packages/prompttest/tests/
pytest packages/promptdiff/tests/
pytest packages/promptvault/tests/

# Lint
ruff check .

# Type check
mypy packages/
```

## MANDATORY WORKFLOW — DO NOT SKIP

### Before declaring ANY work "done":

1. **Run all tests** — `pytest` must pass with zero failures
2. **Invoke the QA skill** — Run the `coder-ui-qa-test` skill for Principal Engineer / QA Engineer / UI Designer review. This is NOT optional.
3. **Fix all CRITICAL and HIGH findings** before moving on
4. **E2E test every CLI command** — actually invoke `promptfmt format`, `promptcost estimate`, `prompttest run`, `promptlint check` with real files and verify output
5. **Verify documentation matches code** — every feature claim in READMEs must be real

### Before publishing:

6. **Full deliverables required:**
   - README.md (per package + monorepo root)
   - README-full.md (extended docs)
   - README-full.txt (plain text version)
   - PDF documentation
   - Landing page (static HTML)
7. **Security scan** — grep staged changes for API key patterns: `AIza`, `sk-`, `gsk_`, `ghp_`, `xoxb-`, `sk-ant-`
8. **Never fabricate information** — no fake URLs, emails, test results, or feature claims

## MANDATORY SECURITY RULES — NO EXCEPTIONS

- **NEVER** publish, commit, or include ANY API key, secret, token, or credential
- **NEVER** hardcode real API keys in test code, spike code, or any source file
- **ALWAYS** use `.gitignore` to exclude `.env`, `secrets/`, `*.key`
- Before every commit, grep for key patterns. If found, STOP and remove them.

## PRD DOCUMENTS

The original specs are at:
```
C:\Users\scott\AppData\Roaming\Claude\local-agent-mode-sessions\2bfe04f5-3c2c-4e75-9d4d-55809b12cb12\4015a7de-50b1-430f-a1ba-f1b4cfda94f1\local_0178b53e-22a9-4516-8a7b-56020128c3e1\outputs\
```
- PRD-0-prompttools-core.docx
- PRD-1-promptfmt.docx
- PRD-2-prompttest.docx
- PRD-3-promptdiff.docx (v2)
- PRD-4-promptvault.docx (v2)
- PRD-5-promptcost.docx

## ANTI-PATTERNS — THINGS THAT WENT WRONG

- Do NOT spend time re-reading code you already wrote. The code is there. Read it if you need a specific detail, not to "understand the project."
- Do NOT declare things "ready to publish" without running the full QA workflow above.
- Do NOT forget that promptlint exists and is part of this suite.
- Do NOT launch dozens of research agents when you should be executing.
- When the user says "start over and do it right," they mean follow the workflow — not re-read everything from scratch.
