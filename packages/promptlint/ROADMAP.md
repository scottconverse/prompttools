# promptlint Roadmap

## v0.2.x (Current — Static Analysis)

### Done
- 33 built-in rules across 9 categories
- CLI with check/watch/rules/init/init-pipeline
- Plugin system for custom rules
- Auto-fix for formatting/structural issues (3 fixable rules)
- Model profiles with context window awareness
- Pipeline analysis for multi-prompt systems
- Caching, baseline mode, GitHub Actions output

### In Progress
- [ ] Approximate tokenizer warning (PL090) — surface when model profile uses a non-native tokenizer
- [ ] Docs: clarify auto-fix scope (formatting/structural only, never content)
- [ ] Docs: clarify static vs. dynamic analysis boundaries

## v0.3.0 (Planned — Hardening)

- [ ] Pre-commit hook integration (`promptlint` as a pre-commit hook)
- [ ] `--output` flag to write report to file
- [ ] Coverage reporting: track which rules fired across a project
- [ ] Rule documentation: `promptlint explain PL012` shows full description + examples
- [ ] Config validation: warn on unknown keys in `.promptlint.yaml`
- [ ] Parallel file linting for large directories

## v0.4.0 (Planned — Ecosystem)

- [ ] PyPI publishing
- [ ] VS Code extension (inline diagnostics)
- [ ] GitHub Action (marketplace)
- [ ] Plugin registry / community rules repository

## v1.0.0 (Future — Semantic Linting)

### Concept
Opt-in `--semantic` flag that uses a small, fast model (Claude Haiku, GPT-4o-mini) to perform dynamic prompt analysis that static rules cannot:

- **Intent-structure alignment**: Does the prompt's structure actually enforce its stated intent?
- **Persona consistency**: Does the system prompt's persona survive through multi-turn conversation?
- **Few-shot coherence**: Are examples consistent with the instructions?
- **Output format compliance**: Will the model actually produce the requested format?
- **Gate effectiveness**: Do conditional gates actually stop the model, or does it route around them?

### Design Constraints
- Must be opt-in (requires API key, costs money, non-deterministic)
- Must be clearly separated from static rules (different rule ID prefix: `PLS` for semantic)
- Must cache results aggressively (same prompt + same model = cached result)
- Must support multiple providers (Anthropic, OpenAI, Google)
- Must not be required for any CI workflow — static rules remain the default

### Architecture
- New `rules/semantic/` directory with `BaseSemanticRule` class
- Rules call a model API and evaluate the response
- Config: `semantic.provider`, `semantic.model`, `semantic.api_key_env`
- Plugin-compatible: third-party semantic rules via the existing plugin system

### Open Questions
- What's the right small model for this? (Cost vs. quality tradeoff)
- How to handle non-determinism in CI? (Run N times, majority vote?)
- Should semantic results be cached per-prompt or per-session?
- How to price-protect users? (Token budget per lint run)

## Not Planned

- **Content rewriting / auto-fix for wording**: promptlint will never auto-rewrite prompt content. Auto-fix is limited to formatting and structural changes. Content changes require human judgment.
- **Prompt generation**: promptlint analyzes prompts, it doesn't write them.
- **Model benchmarking**: Comparing model performance on prompts is a different tool.
