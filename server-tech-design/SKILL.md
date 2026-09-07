---
name: server-tech-design
description: >-
  Write high-quality, review-ready server-side technical design documents (技术方案 / TDD / RFC).
  Use this skill whenever the user is drafting, reviewing, structuring, or improving a backend
  technical design — including phrases like "写技术方案", "服务端技术方案", "technical design doc",
  "system design", "RFC", "设计评审", "架构方案", "接口设计", "存储设计", "上线方案",
  or when they share a design template and ask to fill it in or make it more readable. Also use it
  to critique an existing design draft for completeness (interfaces, storage, security, MG, capacity,
  monitoring, rollout, risk control) and for readability. Prefer this skill over generic doc writing
  whenever the topic is a backend/server-side engineering design that will go through review.
---

# Server-Side Technical Design (服务端技术方案)

A good server-side technical design document has one job: **let a reviewer who was not in your head
understand the problem, agree the solution is sound, and spot the risks — in one read.** This skill
helps produce exactly that: complete on the dimensions that matter for backend systems, and readable
enough that people actually finish it.

## When to use this skill

- Drafting a new server-side technical design from a PRD, a problem statement, or a rough idea.
- Filling in a design template (including the internal 技术方案 template) with real content.
- Reviewing / critiquing an existing design for **completeness** and **readability**.
- Turning scattered notes, chat threads, or a meeting into a structured design doc.

If the user is designing frontend/client UI, writing a PRD, or doing pure coding, this skill is not the
right fit — say so and redirect.

## Core principles (the "why" behind everything below)

1. **Reader-first, not author-first.** The author already knows the context; the reader does not.
   Every section should reduce the reader's uncertainty. If a paragraph doesn't help a reviewer decide
   or catch a risk, cut it.
2. **Decisions over descriptions.** A design doc is a record of *decisions and their trade-offs*, not a
   restatement of the code. For any non-trivial choice, show the alternatives you rejected and *why* —
   that is what reviewers actually scrutinize.
3. **Make risk visible.** The most valuable thing a design surfaces is what could go wrong: failure
   modes, compatibility breaks, capacity limits, security exposure. Hiding these wastes the review;
   surfacing them is the point.
4. **Quantify whenever possible.** "Improves performance" is unreviewable; "P99 from 800ms → 300ms,
   +200 QPS on lark.facade.chat" is. Goals, capacity, and performance impact should carry numbers.
5. **Right-size the doc.** Not every section applies to every change. Delete sections that don't apply
   (and say you deleted them) rather than padding them with "N/A" boilerplate. A tight doc gets read.

## Workflow

Follow these steps. Skip or compress steps that clearly don't apply, but be explicit when you do.

### Step 1 — Understand the change and gather inputs

Before writing, establish: What problem does this solve? Who is the reviewer? What is the blast radius
(link level L0–L3, is it on the security/critical path)? Is it a new feature, a refactor, or a fix?
If the user already has a PRD or the change spans known systems, pull those in. Ask only the questions
you genuinely cannot infer — reviewers hate a doc that asks *them* for context.

### Step 2 — Choose the section set

Read `references/section-guide.md` for the full catalog of sections, what each is for, the
completeness checks reviewers apply, and common traps. Then select the sections this specific change
needs. The backbone is almost always:

**Background & Goals → Detailed Design (options + chosen design) → Interfaces → Storage & Cache →
Exception Handling → Security → Monitoring → Capacity → Risk Control (FG kill-switch) →
Compatibility → Performance Impact → Testing → Milestones → Rollout → Review Records**

Mandatory-by-default for any server change that touches real traffic: **Interfaces, Storage, Exception
Handling, Security, Monitoring, Risk Control (kill-switch), Rollout.** Drop MG / 私有互通 / 容量 only
when you can justify they don't apply.

### Step 3 — Draft with the readability rules

Write the content following `references/writing-style.md`. The short version:

- **Lead with the answer.** Start each section with the conclusion, then support it. Reviewers scan.
- **One idea per paragraph; short paragraphs.** Break walls of text.
- **Use tables for anything comparative** — option comparisons, interface fields, capacity estimates,
  traffic/rate-limit configs. Tables are scannable; prose is not.
- **Use a diagram for any non-trivial flow or architecture.** A sequence/flow/architecture diagram
  replaces three confusing paragraphs. See the diagram guidance below.
- **Number your options and state the decision explicitly.** "We chose Option 2 because …" — never
  make the reader guess which one won.
- **Bold the load-bearing sentences** — the decision, the risk, the kill-switch. Reviewers should be
  able to catch the critical points from the bold text alone.
- **Quantify goals and impact.** Attach metrics, QPS, latency, storage/day, blast radius.

### Step 4 — Self-review against the checklist

Before handing off, run `references/review-checklist.md` against the draft. This is the same lens a
reviewer uses. Fix gaps, or explicitly note "not applicable because …". Flag anything that needs a
human decision (e.g., a real FG name, a capacity sign-off, a security conclusion) as a clearly marked
**【待填写】 / TODO** so it isn't silently forgotten.

### Step 5 — Produce the output

Default to a **Feishu doc** (via the `lark-doc` skill) unless the user asks otherwise, because these
designs live and get reviewed in Feishu. When creating the Feishu doc:

- Use real headings (H1/H2/H3) so the outline/TOC is navigable — this is a big readability win.
- Render flows/architecture as **Mermaid/PlantUML code blocks** (Feishu turns them into editable
  whiteboards); use the `lark-whiteboard` skill for complex architecture diagrams. Never paste a
  screenshot or generated image in place of a diagram.
- Use native tables for comparisons and field definitions.
- Put callouts around the decision and the kill-switch so they stand out.

If the user wants a local file (Markdown), produce clean GitHub-flavored Markdown with the same
structure. Match the output language to the user's language.

## Diagrams — when and which

A design without a picture of its main flow is usually harder to review than it needs to be. Reach for:

- **Sequence diagram** — for request/response flows, multi-service calls, MG cross-region paths.
- **Flowchart** — for decision logic, state handling, exception branches.
- **Architecture / component diagram** — for how services, storage, and queues fit together (complex
  ones → `lark-whiteboard`).
- **ER-style table** — for data model relationships.

Keep each diagram focused on one thing. A diagram that tries to show everything shows nothing.

## References

- `references/section-guide.md` — Every section, its purpose, completeness checks, and traps. **Read
  this before choosing the section set.**
- `references/writing-style.md` — Concrete readability techniques with before/after examples.
- `references/review-checklist.md` — The pre-handoff checklist; also usable standalone to critique an
  existing draft.
- `references/template.md` — A ready-to-fill skeleton with section prompts, aligned to the internal
  技术方案 template. Copy it as a starting point.
