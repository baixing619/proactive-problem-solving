# Proactive Problem Solving

[中文](README.md) · [Original skill](skills/proactive-problem-solving/SKILL.md) · [MIT License](LICENSE)

A workflow skill I use in my own day-to-day work with AI agents. When implementation or troubleshooting hits an unknown, it asks the agent to investigate, run a small discriminating check, change routes based on evidence, and complete the work already authorized by the user.

The skill addresses early surrender after one failed tool call, repeated attempts that test the same hypothesis, unverified “success” responses, and unnecessary requests for information the agent can find itself.

## Workflow

1. Define the objective, hard constraints, and observable evidence of success.
2. Turn the unknown into a testable question and run the smallest useful check.
3. After two attempts on the same hypothesis without new evidence or meaningful progress, change the observation, test object, or underlying mechanism.
4. Read back the actual result. HTTP 200, a successful tool response, or passing tests does not establish that the user's requested outcome was achieved.
5. Complete the authorized implementation, integration, and verification. Ask only when a material decision or unavailable information really requires the user.

Use it for implementation, troubleshooting, and technical feasibility work with unresolved steps. Simple Q&A, translation, and copywriting do not need this extra workflow.

## Boundaries

Changing routes must respect existing constraints and permissions. This skill does not authorize bypassing security controls, expanding access, spending money, or taking unapproved external actions. If essential access or a decision is missing, preserve completed work and report the specific limitation.

It is instruction-only guidance, not a new tool or background service. Results depend on the model, tools, task, and user constraints. No fixed improvement in task success rate has been established.

## Install in Codex

Ask Codex:

```text
$skill-installer Install skills/proactive-problem-solving from https://github.com/baixing619/proactive-problem-solving
```

Or download the repository ZIP and copy the complete `skills/proactive-problem-solving` folder into either:

- `~/.agents/skills/proactive-problem-solving` for personal use.
- `<repository-root>/.agents/skills/proactive-problem-solving` for a project.

On Windows, `~` is your user directory. Preserve both `SKILL.md` and `agents/openai.yaml`. Back up an existing version and avoid installing the same skill in multiple locations.

See [OpenAI's skill documentation](https://learn.chatgpt.com/docs/build-skills) for installation and selection behavior. The folder uses the [Agent Skills format](https://agentskills.io/specification). Installation, selection, and support for `agents/openai.yaml` in other hosts have not been individually tested.

## Invoke

```text
Use $proactive-problem-solving to investigate the current obstacle, run the smallest discriminating check, and continue within existing constraints and authorization until the result is verifiable.
```

The existing `allow_implicit_invocation: true` metadata is preserved. Codex may select the skill when its description matches a task; this is not a guarantee of automatic activation.

For a project that wants this as a default, optionally add this instruction to its `AGENTS.md`:

```text
Read and apply proactive-problem-solving for implementation, troubleshooting, or feasibility work with unknown steps. Revisit its decision checks after a material obstacle, two attempts without new evidence, a user correction, or before asking the user for help or declaring the task infeasible. This does not expand authorization or bypass security controls. Simple Q&A, translation, and copywriting do not need the extra workflow.
```

## Contents and license

The installable skill contains only `SKILL.md` and `agents/openai.yaml`. It contains no conversation logs, private paths, account configuration, or credentials. The Chinese instructions are an unchanged copy of the author's daily-use version at publication. This English README explains the original rather than defining a separate skill.

Released under the [MIT License](LICENSE). Keep the copyright and license notice when redistributing.
