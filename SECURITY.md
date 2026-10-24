# Security Policy

## Supported versions

Decime UY is an MVP. Security fixes are applied on a best-effort basis to the
default branch. There is no long-term support schedule for older revisions.

## Reporting a vulnerability

If you discover a security issue in this repository or in the public demo at
[decime.online](https://decime.online):

1. Prefer a **private** report (GitHub Security Advisories if enabled, or email
   the repository owner via the address listed on their GitHub profile).
2. Do **not** open a public issue that includes secrets, tokens, private keys,
   personal data, or working exploit details.
3. Include enough information to reproduce the problem (affected path, version /
   commit, and a minimal description).

Please allow reasonable time for a response before any public disclosure.

## Secrets and local configuration

- Never commit `.env`, keystores, private keys, or production credentials.
- Use `.env.example` and `deploy/.env.production.example` as templates only.
- Rotating credentials is required if a secret was ever committed or shared.

## Scope notes

- Production speech may run on a private edge host; do not publish private mesh
  addresses or tunnel tokens.
- Paid LLM smoke workflows are manual and must not run on untrusted pull
  requests from forks.
