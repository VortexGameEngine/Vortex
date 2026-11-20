---
name: github-issue-refinement
description: Refine this repository's GitHub issues one at a time so they follow the issue templates — fill missing sections, correct them against the repository, propose splits, and show an editable form per ticket. Use when asked to refine, triage, review, clean up or fill out GitHub issues or tasks.
---

# GitHub issue refinement

Bring open GitHub issues in line with the templates in `.github/ISSUE_TEMPLATE/`, one ticket at a time, with the user
approving every change.

## Rules

- **Never change GitHub without explicit approval for that exact change.** Editing, creating, closing, labelling,
  linking or moving an issue to a milestone, and creating or changing a milestone, each needs a yes from the user in
  chat after they have seen the final text.
- **Handle one ticket per turn.** Finish the feedback on one ticket and wait for the user before starting the next.
- **Open one editable form per ticket.** Every draft for that ticket appears prefilled in a text box the user can edit
  and send back.
- **Write issue text in the repository's terms.** No references to conversations, prompts or discussion history.

## Workflow

### 1. Gather context once

- Read every template in `.github/ISSUE_TEMPLATE/`; the section headings an issue must have come from each template's
  `label` fields (for a Task: `### Description` and `### Requirements`).
- Read `README.md`, `AGENTS.md` and any code the issues touch, so feedback reflects what exists and what was decided.
- List the open issues and read each one:

  ```bash
  gh issue list --state open --limit 200 --json number,title,issueType,milestone,labels
  ```

  ```bash
  gh issue view <N> --json title,body,comments,milestone,issueType
  ```

- Show an overview table: number, title, and how it differs from its template. Note issues that look like tests or
  duplicates, and milestones that are overdue or lack a description.

### 2. Review one ticket

For the ticket in hand, report:

- **What is missing** compared with its template.
- **What is wrong or outdated** compared with `README.md`, `AGENTS.md` or the code, quoting the file.
- **What already exists in the code**, so requirements cover only the remaining work.
- **Whether to split it**, by the rules below.
- **Questions only the user can answer**, such as scope or intent.

#### When to split

**Split a ticket when it cannot land as one good PR**, since one issue lands as one PR (`README.md`, Contributing). A
good PR:

1. **Is one kind of change:** a new feature, a behaviour change, a refactor, or a build or tooling change, never a mix.
2. **Is reviewable in one sitting:** about 400 changed lines at most, not counting tests and generated files.
3. **Merges on its own** and leaves `main` building and passing.

Split along the test the ticket fails, into as many issues as it takes; a ticket that is too large becomes steps that
each work, a mixed ticket becomes one issue per kind of change. When the size cannot be judged yet, leave the ticket
whole and split it when work starts.

#### Where each split-off goes

- **Sub-issue of the original** when the pieces together are the original ticket; the original becomes the parent and
  describes the finished state.
- **Separate issue** when a piece serves a different goal; the original ticket's scope shrinks.
- **Milestone:** propose for each split-off whether it stays in the original's milestone, moves to another existing
  milestone, or opens a new milestone, for example when the pieces form a deliverable of their own or some can wait.
  Pieces of one ticket may land in different milestones. A new milestone needs a title, a description of what done
  means, and a due date.

### 3. Open the form for that ticket

Load the form guidance with `mcp__visualize__read_me` (module `elicitation`), then call `mcp__visualize__show_widget`
with one form holding, for the rewritten ticket and for every split-off issue:

- a one-line text box for the title, prefilled;
- a text box for the body, prefilled with the template sections and the proposed text;
- for each split-off, a choice between sub-issue of the original and separate issue, and a choice of milestone (each
  existing milestone, none, or a new one), preselected with the proposal;
- for each proposed new milestone, prefilled text boxes for its title, description and due date.

Close every `<textarea>` and keep the footer with the submit button; a form cut off before its footer cannot be sent.
Without the widget tools, write the drafts to one Markdown file in the scratchpad and give its full path.

### 4. Apply only after confirmation

When the user sends the form back, list the exact GitHub changes (which issue is edited, which are created with which
type, parent and milestone, and which milestones are created or changed) and ask for a yes. Then write each body to a
file in the scratchpad and apply, creating new milestones first:

```bash
gh api repos/{owner}/{repo}/milestones -X POST -f title="<title>" -F description=@<desc.md> -f due_on=<YYYY-MM-DD>T00:00:00Z
```

```bash
gh issue edit <N> --title "<title>" --body-file <body.md>
```

```bash
gh api repos/{owner}/{repo}/issues -X POST -f title="<title>" -F body=@<body.md> -f type=Task -F milestone=<number>
```

Link a split-off issue under its parent with
`gh api repos/{owner}/{repo}/issues/<parent>/sub_issues -X POST -F sub_issue_id=<id>`, where `<id>` is the new issue's
numeric `id`, not its number.

### 5. Verify and move on

Re-read each changed issue with `gh issue view`, report its number and link, then offer the next ticket.
