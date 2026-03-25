# prompttools — Project Memory

Last updated: 2026-03-24 (end of session)

## Project Status — FINAL

### ALL CODE COMPLETE AND TESTED

| Package | Version | Tests | E2E CLI | Status |
|---------|---------|-------|---------|--------|
| prompttools-core-ai | 1.0.0 | 108 pass | N/A (library) | ✅ Ready |
| promptlint-ai | 0.3.0 | 168 pass | ✅ `check`, `rules` verified | ✅ Ready |
| promptfmt-ai | 1.0.0 | 48 pass | ✅ `format`, `--check`, `--diff` verified | ✅ Ready |
| promptcost-ai | 1.0.0 | 47 pass | ✅ `estimate`, `--compare`, `budget`, `models` verified | ✅ Ready |
| prompttest-ai | 1.0.0 | 137 pass | ✅ `run` (text/json/junit), `init`, fail cases verified | ✅ Ready |
| Integration | — | 10 pass | — | ✅ Ready |
| **TOTAL** | — | **518 pass** | **All CLIs verified** | ✅ |

### Infrastructure
- .gitignore: ✅ Created
- LICENSE: ✅ MIT, Copyright 2026 Scott Converse
- GitHub Actions CI: ✅ `.github/workflows/ci.yml` (Python 3.9-3.12 matrix)
- CLAUDE.md: ✅ Project instructions
- Secret scan: ✅ CLEAN (no API keys, credentials, or secrets in any source file)
- Python 3.14.3 installed with venv at `.venv/`

### Documentation
- Root README.md: ✅ Created
- Per-package README.md: ✅ All 5 packages have README.md
- README-full.md: ❌ Not yet created
- README-full.txt: ❌ Not yet created
- PDF documentation: ❌ Not yet created
- Landing page: ❌ Not yet created

## NEXT SESSION — What's Left

1. **Create README-full.md** — extended docs combining all packages into one guide
2. **Create README-full.txt** — plain text version
3. **Generate PDF documentation**
4. **Build landing page** — static HTML
5. **Fix conftest namespace collision** — add `__init__.py` to each test dir so `pytest` can run all packages together
6. **Consider renaming prompttest models** — `TestCase`, `TestStatus`, `TestReport` trigger PytestCollectionWarnings. Rename to `PromptTestCase`, etc.
7. **promptcost table column width** — `gemini-2.0-flash` truncates in Rich table. Cosmetic fix.

## QA Review Summary

Full 4-pass review was completed. Background agents applied fixes for:
- Input validation (delimiter_style, variable_style enums in promptfmt)
- Budget limit > 0 validation in promptcost
- Error handling for file I/O in promptfmt CLI
- CLI help text additions
- Cache TTL implementation in core
- Role validation in format parsers

### Remaining QA Items (not yet fixed)
- Anthropic API key pattern (`sk-ant-`) missing from promptlint security rules (PL061)
- Duplicate `_significant_words()` code between system_prompt.py and smells.py
- O(n²) sentence comparison in CompetingInstructionsRule
- No parallelization for multi-file linting
- Watch mode doesn't respect .gitignore

## Architecture Notes

- All packages use Pydantic v2, Typer CLI, Rich terminal output
- prompttools-core-ai is the shared dependency for all packages
- promptlint-ai v0.3.0 depends on prompttools-core-ai>=1.0,<2.0
- Config discovery walks up directory tree (like .gitignore)
- 10+ built-in model profiles (GPT-4/4o/4o-mini, Claude-3/4, Gemini)
- Plugin system for custom lint rules
- Test files use YAML format with `assert:` field for assertion type

## User Preferences (Scott)

- Expects coder-ui-qa-test skill invocation before declaring done
- Expects full documentation suite: README.md, README-full.md, README-full.txt, PDF, landing page
- Gets frustrated when Claude re-reads things instead of executing
- Gets frustrated when Claude forgets promptlint is the base package
- Values honesty about what's not done over false "ready" claims
- MIT license, Author: Scott Converse
- Monorepo at: C:\Users\scott\OneDrive\Desktop\Claude\prompttools\
- Original promptlint (reference copy): C:\Users\scott\OneDrive\Desktop\Claude\promptlint\
