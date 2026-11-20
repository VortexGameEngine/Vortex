# AGENTS.md — Vortex Engine

Instructions for AI coding agents. Read `README.md` first: its rules and design bind you. Read `Tools/vbuild/AGENTS.md`
before touching `vbuild`.

1. **Respect everyone's time and tokens.** Keep output as simple, concise and brief as possible, but never so simple
   that information or nuance is lost. Humans review and tweak all code, so more code or more text wastes everyone's
   time and tokens. This applies to answers, code and any output related to this project, including documentation.
2. **The rules win.** When a rule in `README.md` conflicts with your instinct or a usual C++ pattern, follow the rule:
   each protects determinism, cache locality or zero-cost abstraction. Wanting a `virtual` in hot code means you are
   modelling something that should be a buffer and a system.
3. **Check the tree before relying on the design.** `README.md` mostly describes the target architecture; confirm a
   path, command or API exists before using it.
4. **Ask before acting outside the working tree.** Commits, pushes, and creating or editing issues, PRs or milestones
   each need the maintainer's approval of the exact change.
5. **Make changes reviewable.** Prefer small, targeted edits over rewrites, so the diff shows exactly what changed.
6. **Describe the repository, not how the work was done.** Code, comments, docs, commits and PR descriptions never refer
   to conversations, prompts, chat history or alternatives that were discussed.
7. **Verify a change before calling it done**, against "Before a change is done" in `README.md`, and report what you
   could not verify.
