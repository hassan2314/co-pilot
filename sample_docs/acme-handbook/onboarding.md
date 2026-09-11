# Onboarding

Welcome to ACME. This guide covers your first day, first week, and the accounts you should have before you write production code. Your manager and onboarding buddy own the schedule. HR owns paperwork. Ping #new-hires with anything stuck.

## Before day one
HR emails a Google Workspace invite, DocuSign packet, and laptop shipping notice at least three business days before start. Sign the employment agreement, I-9 (or local equivalent), and handbook acknowledgment in DocuSign. Complete 1Password enrollment and Okta MFA before Monday morning.

If your laptop has not arrived by 4pm the day before you start, message it@acme.example and your manager. Remote hires get a $250 home-office stipend in the first paycheck. Office hires receive a desk on the 4th floor; check the floor map in the wiki for your pod.

## First day
Start at 10:00 in your local timezone. The day is orientation, not delivery. You will meet your manager, buddy, and the people-ops partner. Expect a 45-minute security briefing, SSO walkthrough, and a tour of Slack, the wiki, and the HR portal.

By end of day you should have: Slack, Google Workspace, GitHub (read access), 1Password, and a calendar invite for the Friday new-hire AMA. Post a short intro in #new-hires: name, team, timezone, and one thing you want to learn this month. Do not request production AWS until week two.

## First week
Pair with your buddy on a starter ticket labeled `good-first-issue`. The goal is a merged pull request by Friday, even if it is a docs fix. Attend the Monday engineering standup and the Wednesday product demo. Shadow one customer support ticket if you are on a product team.

Your manager schedules 1:1s weekly for the first 90 days. Use the 30-60-90 template in the wiki: tools in month one, an owned project in month two, and independent delivery in month three. If accounts are still missing after 48 hours, escalate in #it-help rather than waiting.

## Accounts and access
Default access is email, Slack, GitHub org (team read), Notion wiki, and the HR portal. Engineering adds staging Kubernetes, the staging database viewer, and Sentry. Production AWS, PagerDuty, and customer PII tools require a separate request after you complete the security quiz in the LMS.

Contractors receive time-boxed Okta groups. Interns do not get production access. When you change teams, your old repos are reviewed within a week; unused production roles are removed automatically after 90 days of inactivity.
