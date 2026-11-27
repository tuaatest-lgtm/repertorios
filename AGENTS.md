# AGENTS.md — Palermo Music OMR

## Authority and scope
This repository contains the independent Palermo OMR engine. Work only on the active development branch `feature/omr-propio-palermo` unless the project owner explicitly authorizes another branch. Never modify `main`, the production `index.html`, or Sonoro as part of OMR work. Do not deploy or integrate with the player without explicit approval.

## Mandatory working rules
1. Before editing, read `omr-engine/WORK_HANDOFF.md`, inspect the current branch and HEAD, and compare the handoff base SHA with the actual HEAD. If they differ, stop and reconcile; never overwrite another contributor's work.
2. Create a dedicated branch for each work turn, based on the verified current development HEAD. Do not push or merge unless explicitly authorized.
3. Keep changes narrow, coherent, reviewable, and reversible. Do not rewrite working subsystems to pursue speculative improvements.
4. Preserve the musical distinction between **visual detection**, **candidate/hypothesis**, **human-confirmed interpretation**, and **validated musical event**. Never promote a candidate automatically just because a heuristic score is high.
5. Preserve real polyphony: simultaneous attacks may have independent durations and voices. Do not infer musical time from horizontal pixel distance. Use exact rational arithmetic for rhythmic values.
6. Never use an external OMR engine or cloud OMR service. This is Palermo's own engine.
7. Do not claim musical accuracy from synthetic tests, code coverage, candidate counts, or infrastructure. Report real-score measurements only against explicit human-reviewed ground truth, with the PDF hash, page/system scope, matching rules, and precision/recall/F1 or relevant event metrics.
8. Run the narrow tests first, then the complete test suite and CI where available. Report exact commands, outcomes, and run URLs. Never claim a test passed unless its result was observed.
9. Keep existing public contracts and backward compatibility unless the handoff explicitly authorizes a versioned change. Update docs and tests with behavior changes.
10. Do not change the project progress percentage unless a new, objective, goal-relevant capability is demonstrated on real annotated music. Explain the evidence and update `omr-engine/docs/project-progress.md` in the same change.

## Required end-of-turn handoff
Every contributor must update `omr-engine/WORK_HANDOFF.md` before finishing. The handoff must contain:
- verified branch, base SHA, and resulting commit SHA (or clearly state that no commit was created);
- completed work and exact changed files;
- tests run and observed results, including CI links;
- known defects, uncertainty, and what remains unverified;
- one next task with a bounded scope, acceptance criteria, and exact starting instructions for the next contributor;
- explicit protected areas and any dependencies or files needed.
Do not leave generic instructions such as "continue improving OMR". The next task must be executable by a fresh contributor without relying on chat history.

## Definition of done
A turn is complete only when its code, tests, documentation, evidence, and next-turn handoff agree. A commit alone is not completion. If the work cannot be validated, say so and leave the branch untouched or provide a clearly isolated draft patch.
