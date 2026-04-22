# FE Implementation Escalation Rules

Block when:
- selected design direction or component plan is missing
- API/data contract is missing for dynamic data
- required change touches protected/shared/locked path without approved CR
- implementation requires adding a new UI framework
- target platform is ambiguous

Retry when:
- visual issues are fixable inside scope
- spacing/hierarchy/token mismatch can be repaired
- build fails due to local implementation errors
