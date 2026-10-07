Scrum master

**SM01. Sprint Flow Health Monitor**

**Purpose:** Analyse Jira workflow data and highlight where work is waiting.

**Checks:**

- Items with excessive status age.

- Work waiting for review.

- Work waiting for clarification or testing.

- Blockers without owners.

- Stories moving backward.

- Reopened items.

- Work approaching sprint end without completion evidence.

- “Almost done” clusters.

**Safe behavior:** Presents signals, not judgments about people or performance.

**SM02. Progress Evidence Correlator**

**Purpose:** Compare reported progress with workflow and engineering evidence.

**Possible evidence:**

- Jira status.

- labels and fix versions.

- linked pull requests.

- review state.

- build status.

- test state.

- applicable documentation.

**Output:**\
Consistent \| Inconsistent \| Insufficient evidence

This closely reflects the internal proposal to correlate Jira labels, code, completed items, and blockages to create an objective progress view

**SM03. Blocker and Impediment Detector**

**Purpose:** Identify potential blockers from work-item patterns, dependencies, comments, and workflow age.

**Categories:**

- Missing decision.

- Missing information.

- External dependency.

- Review bottleneck.

- Environment or access issue.

- Quality issue.

- Scope ambiguity.

- Capacity constraint.

**Safe rule:** Does not infer interpersonal problems, emotions, or individual capability.

**SM04. Dependency Radar**

**Purpose:** Identify cross-team dependencies and readiness mismatches.

**Output:**

- Providing team.

- Consuming team.

- Needed artifact.

- Required-by point.

- Current evidence.

- Risk signal.

- Named owner, if explicitly present.

- Recommended discussion, not an automatic escalation.

**SM05. Daily Scrum Preparation Assistant**

**Purpose:** Prepare factual prompts for the Daily Scrum.

**Produces:**

- Items that changed since the previous check.

- New blockers.

- Items with no movement.

- Dependencies requiring attention.

- Work at risk of remaining incomplete.

- Questions requiring team clarification.

**Avoid:** Automated status narration for every team member.

**SM06. Sprint Review Evidence Pack**

**Purpose:** Prepare a review of completed value and incomplete work.

**Contains:**

- Goals and observed outcomes.

- Completed items with evidence.

- Items not completed.

- Scope changes.

- Known deviations.

- Demos or artifacts available.

- Decisions required from stakeholders.

**SM07. Retrospective Pattern Finder**

**Purpose:** Analyse process signals across several iterations and propose neutral retrospective themes.

**Eligible themes:**

- Waiting time.

- Rework.

- Review delay.

- Dependency handling.

- Story readiness.

- Carry-over.

- Build and test instability.

- Documentation completion.

**Safe behavior:** Team-level system patterns only. No employee scoring or individual performance assessment.

**SM08. Flow Metrics Interpreter**

**Purpose:** Explain cycle time, lead time, age, throughput, carry-over, and work-in-progress in accessible language.

**Output must include:**

- Data source.

- Definition used.

- Period covered.

- Missing or inconsistent data.

- Context affecting interpretation.

- No unsupported causal claim.

This is important because Frequentis teams have reported inconsistent interpretation of sprint data and a need for comparable reports and shared ways of reading Jira information.

**SM09. PI Planning Readiness Checker**

**Purpose:** Assess team readiness before PI Planning.

**Checks:**

- Draft objectives.

- Prioritized features.

- Dependencies.

- capacity assumptions.

- architectural and compliance enablers.

- unresolved decisions.

- risks.

- confidence inputs.

- opening iteration readiness.

**SM10. Inspect and Adapt Evidence Organizer**

**Purpose:** Consolidate quantitative and qualitative evidence for Inspect and Adapt.

**Produces:**

- Observed outcomes.

- Flow and quality signals.

- recurring systemic issues.

- hypotheses.

- candidate improvement items.

- evidence quality and limitations.

**SM11. Risk and ROAM Preparation Assistant**

**Purpose:** Consolidate risks and prepare them for human ROAM discussion.

**Safe behavior:**\
May recommend a possible classification, but does not automatically mark a risk as Resolved, Owned, Accepted, or Mitigated.

**SM12. Ceremony Facilitator Builder**

**Purpose:** Generate agendas and facilitation structures for refinement, planning, retrospectives, problem-solving workshops, or cross-team alignment.

**Controls:**

- objective,

- participants,

- inputs,

- timeboxes,

- decision points,

- expected output,

- documented follow-up.
