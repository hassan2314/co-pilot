# Engineering Practices

These are the defaults for ACME product engineering. Teams may tighten them, not loosen them, without a written exception in the architecture log. Platform questions go to #eng-help.

## Git and pull requests
Trunk-based development on `main`. Feature work happens on short-lived branches named `you/ticket-short-description`. Rebase on `main` before you open a pull request. Do not force-push to `main` or to anyone else's branch.

Every change lands through a pull request with CI green. A PR needs one approval from someone who did not author it. Prefer PRs under 400 lines; split migrations, refactors, and feature work. Description must include why, how to test, and any rollout risk. Do not merge your own PR unless you are the on-call owner unblocking an incident and you post in #eng afterward.

Draft PRs are welcome for early design. Mark them ready when you want review. Reviewers respond within one business day. If a PR sits idle for two days, the author pings the reviewer in Slack; after three days the author may reassign.

## Code review and testing
Review for correctness, readability, and operational risk before style. Ask for tests on new branches and failure modes. Do not approve if you do not understand the change. Nitpicks are suggestions, not blockers.

Unit tests run in CI on every PR. Coverage may not drop on the files you touch without an explanation. Integration tests cover the happy path and one failure path for new endpoints. Do not test implementation details of private helpers. Snapshot tests are allowed for generated output, not for business rules.

## Deploys
Staging auto-deploys from `main` after CI. Production deploys are the owner's responsibility during 10:00–16:00 in the team's primary timezone, Monday through Thursday. Friday production deploys need an explicit yes from the on-call engineer. Use the deploy bot in #deploys; never apply Kubernetes manifests from a laptop against prod.

Migrations run before application code that depends on them. Backward-compatible migrations only. If you need a multi-step migrate, ship expand → deploy → contract as separate PRs. Feature flags default off. Rollback is the first response to a bad deploy; forward-fixes wait until the service is stable.

## On-call
Each product squad has a primary and secondary on-call, rotating weekly in PagerDuty. Primary acknowledges pages within 15 minutes. Secondary is backup if primary does not ack. You are not expected to ship features while on-call; keep the calendar light.

Hand off with a written note in the squad channel: open incidents, risky deploys, and anything that paged overnight. Comp time is one day off for any night with a Sev-1 or two or more Sev-2 pages, taken within 30 days, scheduled with your manager.
