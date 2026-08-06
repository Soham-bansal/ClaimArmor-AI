# Demonstration security and roles

ClaimArmor uses signed, expiring bearer tokens and PBKDF2 password hashes. The
API enforces permissions independently of the browser interface.

| Capability | Analyst | Reviewer | Auditor | Admin |
|---|:---:|:---:|:---:|:---:|
| View claims and metrics | Yes | Yes | Yes | Yes |
| Create/upload claims | Yes | No | No | Yes |
| Run investigation | Yes | Yes | No | Yes |
| Complete human review/writeback | No | Yes | No | Yes |
| View audit evidence | No | Yes | Yes | Yes |

## Production requirements

- replace seeded users with OIDC/enterprise SSO;
- set a secret through a managed secret store;
- use TLS and secure cookies or a hardened bearer-token flow;
- add account lockout, revocation, rotation, and security-event monitoring;
- run an independent security and privacy assessment;
- never enable real PHI until the complete compliance environment is approved.

