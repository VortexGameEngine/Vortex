# Architecture Decision Records

An Architecture Decision Record (ADR) records one design decision: the problem, the decision, and what follows from it.
Read the relevant ADR before proposing a pattern that touches the same area.

**Never rewrite an accepted ADR.** To change a decision, add a new ADR that supersedes it and set the old one's status
to `Superseded by NNNN`. A `Proposed` ADR may still be edited until it is accepted.

**Name files `NNNN-short-title.md`**, numbered in order, and add each one to the table below.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-naming-convention.md) | Naming convention | Accepted |
| [0002](0002-module-linkage-and-export-macros.md) | Module linkage and export macros | Accepted |
| [0003](0003-dod-classes-and-references.md) | DOD classes, `VReference` and stores | Proposed |
