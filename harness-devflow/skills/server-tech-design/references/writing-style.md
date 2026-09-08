# Writing Style — Make the Main Design Easy to Explain

## 1. Start with the answer and the flow

Open with the problem, the proposed change, and its main effect. Give the reader a path through the
solution before describing its internals. Within a section, state the behavior or decision first.
For a significant trade-off, give the reason and the relevant alternative; routine choices need no
ceremonial option table.

A reader should be able to follow one real example and identify where the important decisions act.
Use specific verbs and actors: who loads, validates, selects, calls, switches, or rejects what.

## 2. Decide what belongs in the main text

Keep information that helps a reviewer understand the mechanism, judge a decision, or identify a
consequential correctness, security, compatibility, or rollout constraint. Put exhaustive field details,
implementation mechanics, and long verification inventories in a linked reference or appendix when useful.
Omit material that serves neither purpose; moving everything into an appendix is not required.

Example of lowering detail while preserving behavior:

**Too much for the opening explanation**
> 加载任务核对订阅代次和 desiredRevision，编译候选对象并原子替换 active 引用，
> 旧对象等待引用释放后回收；失败进入 REJECTED 状态。

**Main text**
> **新配置检查通过后，再替换运行中的配置。** 新请求使用新配置，正在执行的请求继续
> 用旧配置完成；更新失败时继续使用旧配置。

Keep race-prevention and lifecycle details where implementation review needs them. If one is itself a
central correctness decision, summarize it in the main text as well. Shortening should preserve the
conditions and exceptions that change the behavior.

## 3. Explain concepts, sources, and contracts once

Introduce terms at first use. When two names look interchangeable, explain their different jobs and
relationship together. A small example often works better than a growing glossary.

For a configuration or interface, establish structure before examples. Use an annotated schema or a
field table as its main reference; avoid repeating every field in both. State what comes from the key,
environment, caller, or configuration. Distinguish comments and illustrative values from a publishable
payload, and distinguish a proposed contract from an implemented or tested one.

## 4. Choose a representation that reduces work for the reader

- Use short connected paragraphs for explanations and trade-offs; use a list for actual steps or parallel items.
- Use tables for concise mappings and comparisons. A paragraph copied into every cell is still a wall of text.
- Use a focused diagram when it makes a flow or relationship clearer. A compact overview can precede a
  detailed sequence when both earn their space. Separate preparation from execution, or independent
  control and request flows, when combining them would imply the wrong timing.
- Put constraints alongside the steps they govern. A limit that applies throughout a request should not
  appear as a final step after all processing has finished.
- Bold the conclusion or consequential rule selectively. Headings and bold sentences should convey the
  main decisions, but the complete text must still be understandable without formatting.

Keep labels and vocabulary consistent between diagrams, schemas, examples, and prose. Do not add a
second diagram that merely repeats an existing one. Follow current document and whiteboard tools for
rendering, preserve unrelated user annotations, and inspect the actual rendered result.

## 5. Show evidence without manufacturing certainty

Quantify when the number helps a decision. Identify measured results, estimates with assumptions, and
proposed targets or limits. An unsourced precise number is not stronger evidence than an honest unknown.
Keep current behavior, planned behavior, and verified behavior distinct at the relevant statement.

Open items should state what decision or evidence is missing and its consequence. A design draft can
contain a planned test without a result link. Do not fill a TODO list with unrelated checks or claim that
an example has passed validation because it looks complete.

## 6. Revise toward a smaller, consistent explanation

Replace the affected explanation when a decision changes. Then follow dependent terms, field names,
examples, diagrams, and references. Remove stale details and merge repeated rules. Prefer placing a
clarification in its owning section over adding another chapter.

Do a deletion pass after drafting or a substantial revision: if removing a paragraph does not weaken
understanding, a decision, or a consequential constraint, shorten it, relocate it, or remove it. Do not
confuse shorter paragraphs with less information overload. Respect the user's edit scope; update related
material as needed for consistency without rewriting unaffected sections for style alone.
