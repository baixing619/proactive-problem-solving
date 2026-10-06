# Proactive Problem Solving

[中文](README.md) · [Original skill](skills/proactive-problem-solving/SKILL.md) · [MIT License](LICENSE)

A workflow skill I use in my own day-to-day work with AI agents. When implementation or troubleshooting hits an unknown, it asks the agent to investigate, run a small discriminating check, change routes based on evidence, and complete the work already authorized by the user.

I made it because tasks were too often marked “blocked” before investigation, leaving me to find information, choose another route, and take over. It aims to reduce premature stopping, repeated attempts without new evidence, and unnecessary handoffs to the user.

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

## Who might find it useful

Try it if an agent gives up after one tool error, repeatedly tweaks the same failing request, accepts success responses without checking the target, or stops after a prototype while the authorized integration remains unfinished.

Two attempts without new evidence is a cue to change the hypothesis or verification method, not a cap of two total attempts. Judge usefulness by new evidence, a verified route, an actual result, or an accurately identified blocker. The number of skill reads is not an effectiveness measure.

For a before/after comparison, track avoidable blockers, user corrections and takeover, verified completion, and elapsed time. Required authorization and scope changes belong in separate categories. Existing records do not establish fewer takeovers or improved efficiency. See the [measurement definitions and comparison method (Chinese)](docs/evaluation.md).

A [three-task reproducible incremental comparison (Chinese)](docs/comparison.md) also found correct authorized artifacts in 3/3 tasks for both conditions, zero avoidable handoff requests for both, and mixed elapsed times. Both inherited existing investigation rules, so this does not establish a stable efficiency or handoff benefit from additionally reading the skill text. Synthetic inputs, outputs and aggregates are public.

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

## Observations from actual work

![Evidence and result boundaries from actual records](docs/practical-observations.png)

Reviewed records include a file-backed pre-publication issue list, a test showing a background process actually stopped, and a data review that narrowed a conclusion after finding inconsistent comparison inputs. There are also incomplete tasks and overly broad judgments. These are limited, anonymized observations rather than evidence that the skill caused an improvement.

See the [case descriptions, sampling method, and limitations (Chinese)](docs/practical-observations.md). There was no no-skill control group, some delegated-task context was unavailable, and raw records remain private. No success-rate, time, or token improvement is claimed.

## Supplement: personal usage snapshot

![Seven-day observed skill-read coverage](docs/skill-usage.png)

In my local records for September 29–October 5, 2026 (UTC+08:00), the skill was confirmed read in **29 of 40 tool-active agent sessions (72.5%)**. It ranked first by distinct-session coverage among 25 observed skills. There were 128 confirmed reads; the main comparison deduplicates each session–skill pair.

Sessions can include subagents and forks, rather than 40 independent user conversations. My global working instructions also ask relevant tasks to use this skill, which influences its frequency. The figures describe personal observable file reads, **not an exact automatic invocation rate or an effectiveness benchmark**.

Only anonymous aggregates are public. See the [methodology and limitations (Chinese)](docs/usage-methodology.md), [skill counts](docs/skills.csv), [daily counts](docs/daily.csv), and [aggregate JSON](docs/safe_aggregate.json). The optional [standard-library analysis script](tools/analyze_skill_reads.py) takes source/output directories and dates as arguments. It also produces private audit files; inspect the methodology before sharing its outputs. The script is outside the installable skill and is not needed to use the skill.
