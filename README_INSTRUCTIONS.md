# AI Engineer Technical Assignment (Open-Ended)

Build a practical prototype that uses GitHub data to produce useful engineering insights.

This assignment is intentionally open-ended. We care most about how you scope, prioritize, and explain trade-offs.

## Time Box

- Duration: 2 hours
- Commit cadence: every 10-15 minutes with short, descriptive messages

## Task

Design and implement a small end-to-end solution on top of GitHub data.

You can choose the data scope that best fits your approach, for example:
- One repository
- A set of repositories
- A topic-based selection
- A broader slice of public GitHub

Do not feel constrained to a single public repo or to an organization-level scope.

You may build an agent, an assistant workflow, a retrieval + analysis pipeline, or another practical interface.
Natural-language interaction is encouraged, but the exact UX is up to you.

You may use any stack. Databricks Free Edition is allowed.

## Functional Expectations (Flexible)

At minimum, your submission should demonstrate:

- Real GitHub data ingestion (issues, PRs, comments, metadata, or another justified subset)
- A usable way to explore or query insights (chat, CLI, notebook flow, dashboard, report generation, etc.)
- Evidence-backed outputs (links, IDs, snippets, or query traces)
- Basic resilience for API limits/failures

Examples of what your solution can do:

- Answer natural-language questions about issue/PR patterns
- Generate a short triage or risk summary
- Highlight bottlenecks, ownership gaps, stale work, or recurring themes
- Compare activity across multiple repositories

These are examples, not mandatory checkboxes.

## README Must Include

- Architecture diagram (simple Mermaid is enough)
- Scope and tool choices, with short rationale
- How data is retrieved and prepared
- How users interact with the system
- How you assess output quality (lightweight approach is fine)
- Known limitations and next improvements
- Exact run instructions

## Deliverables

- All code and configuration
- README
- Sample outputs from your chosen workflow
- Commit history showing progress during the 2-hour window
- Claude session trasncripts

## Evaluation Criteria

1. Decision quality under time constraints
1. End-to-end usefulness of the solution
1. Grounded outputs (evidence-backed, low hallucination)
1. Clarity of implementation and README
1. Quality of trade-offs and improvement plan

## Ground Rules

- AI-assisted coding is allowed
- Local-only setup is fully acceptable
- If incomplete, document what works, what is missing, and what you would do next


Good luck. We care more about your reasoning and judgment than perfect polish.
Cauchy team
