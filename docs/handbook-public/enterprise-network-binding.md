---


nav_title: Enterprise — network binding
public_publish: true
audience: public
product_area: lenses
tier: practitioner
handbook_area: lenses
learning_level: '201'
section: enterprise
status: shipped
description: Loopback default, binding to all interfaces, and TLS termination.
page_type: concept
---

# Enterprise — network binding

## What it is

Lenses defaults to **loopback** so **`POST`** surfaces are not reachable from LAN accidentally. Widening the listener is an explicit operator choice documented alongside **[Security and local-first](17-security-and-local-first.md)**.

## Modes

| Mode | Behavior |
|------|----------|
| **Default (`127.0.0.1`)** | Same-host browsers and tools reach Lenses; LAN hosts cannot open **`/api`** without tunnels. |
| **`--bind-all-interfaces`** | Listener on all interfaces — combine with firewall rules and OIDC/session gates before exposing broadly. |

Prefer terminating TLS on a reverse proxy you operate; avoid forwarding raw **`Authorization`** headers from untrusted clients.

## Verify

`ss -lptn` shows **loopback-only** binds unless you intentionally widened them.

## What to do next

- [Enterprise — OIDC sessions](enterprise-oidc-sessions.md)
