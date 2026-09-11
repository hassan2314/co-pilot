# Incident Response

An incident is any unplanned event that degrades customer-facing service, risks data, or will do so if ignored. We optimize for fast mitigation, then for learning. Status and decisions belong in #incidents, not in DMs.

## Severity levels
Sev-1 is a total outage of a revenue path, confirmed data loss or exposure, or a security breach in progress. Examples: checkout down for all customers, production database unreachable, leaked credentials in a public gist. Page the incident commander immediately.

Sev-2 is a major degradation with a workaround, or an outage limited to one region or one plan tier. Examples: 5xx on 20% of API traffic, search latency above 2 seconds, webhooks delayed over 15 minutes. Page the owning squad's on-call.

Sev-3 is a limited impact or a defect with a clear workaround. Examples: a single enterprise tenant failing SSO, a non-critical job lagging, a cosmetic billing-PDF bug. Ticket it, post in the squad channel, do not page unless it is trending toward Sev-2.

When in doubt, start one severity higher. The incident commander can downgrade after the first assessment. Severity is about customer impact, not how embarrassed we are.

## During an incident
Sev-1 requires a Slack post in #incidents within 15 minutes of detection, including severity, customer impact, and the commander. The commander is the on-call for the owning service unless they hand off. One person drives; others take notes, comms, or investigation.

Mitigate before you root-cause. Roll back, fail over, or disable the flag. Do not ship an unreviewed forward-fix during a Sev-1 unless rollback is impossible. Customer-facing status updates go out at least every 30 minutes for Sev-1 and every 60 minutes for Sev-2, even if the update is "still investigating."

Keep a running timeline in the incident thread: detection time, actions, and who did them. Do not debate process in the incident channel until the service is stable. If the incident lasts more than two hours, rotate the commander and the scribe.

## Communication
Internal: #incidents is the source of truth. #eng gets a one-line pointer, not a second war room. External: the commander or a designated comms lead updates status.acme.example. Support uses the approved customer blurb; they do not invent technical detail.

Legal and security join immediately on any suspected data exposure. Do not notify individual customers of a breach until legal and security agree on the wording. Executives get a written summary for Sev-1 within one hour of start, then at resolution.

## Postmortems
A written postmortem is due within 48 hours of Sev-1 resolution and within five business days of Sev-2. There is no blame section. Required headings: summary, impact (duration and customers), timeline, contributing factors, what went well, action items with owners and dates.

Action items that reduce repeat risk are scheduled in the next two sprints or explicitly declined in writing. The incident commander schedules a 30-minute review with the squad and anyone who paged in. Postmortems live in the wiki under `/incidents/YYYY-MM-DD-short-name` and are linked from the Slack thread.
