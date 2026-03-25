---
name: harness
description: "Build harness orchestrator. Runs the full Planner → Builder → Evaluator loop. Takes a PRD or feature request, produces a sprint contract, builds the code, evaluates it, and loops until the Evaluator passes or max loops (3) are reached. Writes a session handoff artifact when complete."
---

# Build Harness Orchestrator

You orchestrate the three-agent build harness: Planner → Builder → Evaluator. You manage the loop, enforce the process, and write the session handoff artifact when complete.

## How It Works

```
Input (PRD / feature request / task)
    │
    ▼
┌──────────┐
│  PLANNER  │ → Sprint Contract (.claude/sprints/sprint-NNN.yaml)
└──────────┘
    │
    ▼
┌──────────┐
│  BUILDER  │ → Code + Tests + Build Summary
└──────────┘
    │
    ▼
┌────────────┐
│  EVALUATOR  │ → Evaluation Report (.claude/evaluations/eval-NNN.yaml)
└────────────┘
    │
    ├── PASS → Write handoff artifact. Done.
    │
    ├── NEEDS_WORK → Send findings back to Builder (max 3 loops)
    │
    └── FAIL → Escalate to user. Something fundamental is wrong.
```

## Process

### Phase 1: Planning

1. Determine the next sprint number by checking `.claude/sprints/` for existing files
2. Launch a **Planner agent** (use the Agent tool with subagent_type or a detailed prompt that includes the harness-plan skill instructions)
3. The Planner reads the input (PRD, feature request, or task description) and produces a sprint contract
4. Present the sprint contract summary to the user for approval
5. If approved, proceed. If not, revise.

**Planner agent prompt template:**
```
You are the Planner in a build harness. Read the following input and produce a sprint contract.

[Include the full harness-plan SKILL.md instructions]

Input: <the PRD or feature request>
Codebase root: C:\Users\scott\OneDrive\Desktop\Claude\prompttools
Output: Write sprint contract to .claude/sprints/sprint-<N>.yaml

Explore the existing codebase first to understand patterns and conventions before writing the contract.
```

### Phase 2: Building

1. Launch a **Builder agent** with the sprint contract
2. The Builder implements all deliverables, writes tests, runs them
3. The Builder outputs a build summary with status "READY FOR REVIEW"

**Builder agent prompt template:**
```
You are the Builder in a build harness. Implement the sprint contract.

[Include the full harness-build SKILL.md instructions]

Sprint contract: <path to sprint-NNN.yaml>
Codebase root: C:\Users\scott\OneDrive\Desktop\Claude\prompttools

Read the sprint contract, then implement every deliverable. Follow all constraints. Run tests before declaring ready for review.
```

### Phase 3: Evaluation

1. Launch an **Evaluator agent** with the sprint contract and access to the built code
2. The Evaluator reads every file, runs tests, checks acceptance criteria, tries to break things
3. The Evaluator writes an evaluation report to `.claude/evaluations/eval-NNN.yaml`

**Evaluator agent prompt template:**
```
You are the Evaluator in a build harness. Review the Builder's work.

[Include the full harness-eval SKILL.md instructions]

Sprint contract: <path to sprint-NNN.yaml>
Codebase root: C:\Users\scott\OneDrive\Desktop\Claude\prompttools

Read the sprint contract. Read every file the Builder created or modified. Run the full test suite. Verify every acceptance criterion. Try to break things. Write your evaluation report.
```

### Phase 4: Loop or Complete

**If PASS:**
1. Report the result to the user
2. Write the session handoff artifact (see below)
3. Commit the new code (if user approves)

**If NEEDS_WORK (and loop < 3):**
1. Send the evaluation report to a new Builder agent
2. The Builder reads the findings and fixes only what was flagged
3. Send the fixed code back to a new Evaluator agent
4. Repeat until PASS or loop reaches 3

**If FAIL or loop >= 3 without PASS:**
1. Report to the user with the evaluation report
2. Explain what's wrong and recommend: re-plan (different approach) or manual intervention
3. Write a handoff artifact noting the failure

### Phase 5: Session Handoff

After completion (PASS or escalation), write a handoff artifact to `.claude/handoffs/handoff-YYYY-MM-DD.yaml`:

```yaml
date: "<YYYY-MM-DD>"
sprint: <N>
verdict: PASS | NEEDS_WORK | FAIL | ESCALATED
loops_used: <1-3>
total_loops_allowed: 3

session_summary: "<what was built and the outcome>"

packages_modified:
  - package: "<package name>"
    files_created: <N>
    files_modified: <N>
    tests_passing: <N>
    tests_total: <N>

pending_work:
  - title: "<what's next>"
    priority: high | medium | low
    reason: "<why this is pending>"

known_issues:
  - "<any issues discovered but not fixed in this sprint>"

evaluator_patterns:
  - "<things the Builder tends to miss — carry forward to future sprints>"
  - "<e.g., 'Builder skips help text on CLI options'>"
  - "<e.g., 'Builder declares ready before running tests'>"

builder_strengths:
  - "<things the Builder does well — don't over-scaffold these>"
```

## Rules for the Orchestrator

1. **Never skip the Planner.** Even for "simple" tasks. The sprint contract is what makes the loop work.
2. **Never skip the Evaluator.** The Builder cannot self-evaluate. This is the core principle.
3. **Use separate agents for each role.** Don't let the Builder also evaluate. Don't let the Evaluator also fix. Separation is the point.
4. **Present the sprint contract to the user before building.** Don't burn compute on the wrong plan.
5. **Maximum 3 loops.** If 3 rounds of build-eval don't produce a PASS, the problem is in the plan, not the implementation. Escalate.
6. **Write the handoff artifact every time.** Even on failure. The next session needs to know what happened.
7. **Record evaluator patterns.** If the Evaluator keeps finding the same type of issue, record it in the handoff. Future Planner agents can add it as a constraint.

## Quick Start

When the user says `/harness` followed by a task:

1. "Let me plan this first." → Launch Planner
2. Show sprint contract → "Does this look right?"
3. User approves → "Building now." → Launch Builder
4. Builder finishes → "Evaluating." → Launch Evaluator
5. Report result → Loop or complete
6. Write handoff → "Done. Here's what was built and what's next."
