---
name: context-hygiene
description: >-
  Use this skill at the end of a feature, bugfix, or build milestone to keep
  docs/CONTEXT.md and docs/MEMORY.md concise, accurate, and token-efficient
  for future sessions.
---

# Context & Memory Hygiene Workflow

1. **Keep `docs/CONTEXT.md` under ~100 lines**:
   - Update only when files, public symbols, or data paths change.
   - Use compact `path -> purpose / key symbols` bullets; avoid prose paragraphs.
2. **Update `docs/MEMORY.md` incrementally**:
   - Record verified facts only (API quirks, build artifacts, test counts, signing thumbprints).
   - Move completed items out of `Pending` and remove stale notes.
3. **Protect `.geminiignore` / `.agentignore`**:
   - Ensure any newly generated heavy folders, cache dumps, or binary fixtures are listed so future sessions do not waste tokens indexing them.
4. **Verify**:
   - Confirm `GEMINI.md` + `AGENTS.md` + `.agents/rules/architecture.md` remain concise and non-redundant.
