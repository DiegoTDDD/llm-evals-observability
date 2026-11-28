# Spec 003: Weekly dependency audit

## Requirements
- R1 `security-audit.yml` runs pip-audit over every requirements*.txt on dependency changes and
  every Monday, failing only when a fixed version exists.
- R2 First-party git pins (same GitHub owner) are skipped; those repositories audit themselves.

## Acceptance
- The audit passes locally and in CI.
