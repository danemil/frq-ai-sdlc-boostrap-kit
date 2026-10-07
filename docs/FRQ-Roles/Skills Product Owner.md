Product Owner

**PO01. Story Readiness Reviewer**

**Purpose:** Assess whether a Jira story is ready for refinement, estimation, development, or testing.

**Checks:**

- Business purpose is clear.

- User or operational value is defined.

- Scope and boundaries are understandable.

- Acceptance criteria are testable.

- Dependencies are recorded.

- Non-functional considerations are addressed.

- Relevant safety, security, and regulatory tags are present.

- Source requirement and related documentation are linked.

- Open questions are explicit.

**Output:**\
Ready \| Ready with conditions \| Not ready, with evidence and missing elements.

**Safe behavior:** It does not rewrite or approve the story automatically.

**PO02. Acceptance Criteria Quality Reviewer**

**Purpose:** Evaluate acceptance criteria for clarity, testability, completeness, and operational relevance.

**Checks:**

- Observable outcome.

- Positive, negative, boundary, and failure conditions.

- Role and permission implications.

- Error handling.

- Security and privacy considerations.

- Traceability to the source requirement.

- Ambiguous language such as “fast,” “appropriate,” or “user-friendly.”

The Frequentis engineering material already positions the PO as responsible for acceptance criteria aligned with operational value, with safety and quality validation remaining with the designated human roles.

**PO03. Requirement Ambiguity Detector**

**Purpose:** Identify contradictions, undefined terms, hidden assumptions, and missing decision points.

**Output categories:**

- Ambiguous statement.

- Conflicting requirement.

- Missing actor.

- Missing trigger.

- Missing expected result.

- Missing exception.

- Missing source.

- Required SME clarification.

**PO04. Requirement-to-Test Traceability Checker**

**Purpose:** Verify that a requirement or story has corresponding acceptance criteria and test evidence.

**What it compares:**

- Business or system requirement.

- Jira story.

- Acceptance criteria.

- Test case.

- Test result.

- Defect or deviation.

- Documentation update.

**Safe behavior:** Reports gaps. It does not claim compliance or completion.

This directly responds to the Frequentis finding that requirements can become disconnected from integration testing or fall out of sync with delivered code.

**PO05. Backlog Refinement Preparation Assistant**

**Purpose:** Prepare a structured refinement pack before the meeting.

**Produces:**

- Summary of business intent.

- Unresolved questions.

- Dependency overview.

- Traceability gaps.

- Acceptance-criteria concerns.

- Suggested discussion order.

- Required participants.

- Decisions needed during refinement.

**PO06. Story Split Advisor**

**Purpose:** Suggest safe ways to split oversized work without losing traceability or testability.

**Splitting lenses:**

- Operational scenario.

- User journey step.

- Business rule.

- Interface or integration.

- happy path versus exceptions.

- risk and learning.

- configuration versus implementation.

**Safe rule:** Suggestions only. The PO approves the split.

**PO07. Definition of Ready Compliance Check**

**Purpose:** Apply the approved team or organizational Definition of Ready consistently.

**Special value:**\
The Skill should load the relevant team template, not use a generic DoR invented by the model.

**PO08. Definition of Done Evidence Checker**

**Purpose:** Verify whether evidence exists for the applicable Definition of Done elements.

**Possible evidence:**

- acceptance criteria results,

- review status,

- tests,

- integration evidence,

- documentation,

- traceability,

- required approvals,

- unresolved defects,

- release artifacts.

**Safe behavior:** Says “evidence found” or “evidence not found,” not “the story is compliant.”

**PO09. Functional Change Impact Analyzer**

**Purpose:** Identify potentially affected capabilities, requirements, interfaces, teams, tests, and documentation when a story changes.

**Output:** A candidate impact map requiring technical and product validation.

**PO10. Requirement Change Diff Summarizer**

**Purpose:** Compare requirement versions and explain what changed in business language.

**Highlights:**

- Added or removed behavior.

- Modified acceptance conditions.

- Changed constraints.

- New dependencies.

- New test obligations.

- Potentially obsolete Jira items.
