# Lenses Studio and Forge Fleet

Studio **Settings → Forge Fleet** configures one or more Fleet base URLs (ports **18765** / **18766** are common). The workspace server exposes JSON APIs under `/api/fleet/*` (loopback-only unless `LENSES_ALLOW_ACTIONS`).

**LAN discovery** builds the address list from each non-loopback interface’s **IPv4 address + prefix length** via `ip -json addr show up` (same view as local routing). *Quick* mode probes a capped host set per derived range (for prefixes shorter than /24 it uses the /24 slice that contains that address); *Subnet* mode walks hosts in the real prefix up to a safety cap. If `ip` is missing, a single guessed `/24` from the UDP outbound trick is used instead.

Default TCP ports probed per host are **18765**, **18766** (direct `fleet_server`), and **18767** (typical **Caddy** public port in forge-fleet layouts where Fleet stays on loopback). A browser may work on `:18767` while `:18765` on the LAN IP refuses connections — that is expected; use discovery after this change or pass a custom `ports` array in `POST /api/fleet/discover`.

## Multi-gateway (OpenAI-compatible) follow-up

Today, Lenses stores a **single** `openai_compatible_base_url` plus one optional bearer key. **Connect forge-llm to LLM settings** updates that primary endpoint when you point Studio at a Fleet-hosted forge-gateway.

If you need **several simultaneous** custom OpenAI-compatible origins (different hosts or keys in parallel), a future change would add something like `gateway_endpoints[]` to `llm-settings.json`, extend `merge_save` / `merged_openai_compat_base_url`, and teach routing (`llm_resolve`, agent runtime endpoint registry) to pick among them.
