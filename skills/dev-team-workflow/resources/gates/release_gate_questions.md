# Release Gate Questions

Purpose:
Ensure the current story is safe to deliver as the next baseline.

Required artifacts:
- story_manifest.json
- delivery_index.json
- release notes or summary

Questions:
- Is the delivered story usable now?
- Have the acceptance criteria passed?
- Are any blockers still open?
- Is this output safe to become the baseline for the next story?
- Does the story manifest contain enough traceability?
- Was delivery_index updated correctly?
- In existing_project mode, is the new baseline safe for future brownfield work?

Pass when:
- DELIVER_STORY is justified
- the baseline is usable
- manifest and delivery index are correct
- no blocker remains

Fail when:
- the output is not yet safe to reuse
- manifest is incomplete
- acceptance is not fully passed
- blocker issues still remain
