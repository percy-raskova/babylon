# Article IX: Governance

> Annex to [Babylon Constitution](../constitution.md). This file contains the full governance procedures, versioning policy, and compliance review details.

### Amendment Procedure

1. Propose amendment with rationale
1. Demonstrate consistency with existing principles or explicit supersession
1. Update dependent artifacts (templates, specs)
1. Increment version per semantic versioning

### Version Policy

| Change Type                       | Version Increment |
| --------------------------------- | ----------------- |
| Principle removal or redefinition | MAJOR             |
| New principle or section          | MINOR             |
| Clarification, wording fix        | PATCH             |

### Compliance Review

All features, formulas, and systems MUST be verifiable against this constitution.

**Review triggers**:

- New system implementation
- Formula modification
- Data source addition
- Scope expansion
- **UI component implementation** (must verify against Article VII)

Non-compliant code MUST be flagged and corrected before merge.
