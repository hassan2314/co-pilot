# Security Policy

Everyone at ACME handles customer and company data. These rules apply to full-time staff, contractors, and vendors with system access. Report suspected incidents the same day to security@acme.example and #security. Do not wait for proof.

## Credentials and secrets
Never commit API keys, passwords, tokens, or private certificates to git, Slack, email, or tickets. Use 1Password Business for all work credentials. Production secrets live in the secrets manager, not in `.env` files on laptops. If a secret may have leaked, revoke it first, then file a report in #security with the repo, timestamp, and what was exposed.

Laptop disk encryption is required. Screen lock after 5 minutes of idle time. Do not share your SSO password or 1Password vault. ACME will never ask you for a password over Slack or email. MFA is mandatory on Google Workspace, GitHub, AWS, and 1Password. Hardware keys are preferred; SMS MFA is not allowed.

## Phishing and email
Treat unexpected payment requests, gift-card asks, and "urgent CEO" messages as phishing. Hover links before clicking. If a message looks suspicious, do not click, forward, or reply. Report it with the Gmail "Report phishing" button and ping security@acme.example the same day.

Finance will never request a wire over Slack. Vendor bank-detail changes require a video call with a known contact plus a ticket in the finance tracker. When in doubt, call the person on a number you already have.

## Devices and access
Work happens on ACME-managed laptops. Personal phones may use Google Workspace and Slack with a PIN and device encryption. Do not store customer data on USB drives or personal cloud accounts. Lost or stolen devices must be reported to IT within one hour so we can remote-wipe.

Access follows least privilege. Request production roles through the access portal; managers approve, security reviews. Access is reviewed every 90 days. Departing employees lose SSO the same day. Contractors expire on the contract end date unless explicitly renewed.

## Data classification
Public data may be posted on the website. Internal data (roadmap drafts, unreleased metrics) stays in ACME tools. Confidential data includes customer PII, credentials, and unpublished financials. Confidential data may not go in public Slack channels, personal email, or unsanctioned SaaS.

Customer PII is not copied into staging without masking. Production database dumps do not leave the VPC. If you need a production replica for debugging, open a ticket with the platform team; do not snapshot RDS from a laptop.
