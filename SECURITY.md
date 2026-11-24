# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x | Yes |
| 0.x | No |

## Reporting a vulnerability

Do not post vulnerability details in a public issue. Open an issue that only asks for a private
contact channel, and share the details once one is agreed. This is a personal project maintained
on a best-effort basis, so no response time is guaranteed.

## Security model

battery-lab runs as an unprivileged user, reads from sysfs, writes only its own log and opens no
network connections. It treats firmware strings and log contents as untrusted input.

Logs can contain battery serial numbers and a machine identifier. They are created with mode `0600`.
Review or strip those columns before sharing a log.

The findings of the latest review are in [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md).
