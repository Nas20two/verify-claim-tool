# verify-claim-tool

Agent claim-verification gate for the nasyhub Buzz fleet (pain #1).

Verifies completion claims **before** an agent reports "done":
- `verify-claim commit --sha <sha> --branch <branch> --repo <path>` — SHA must exist on origin
- `verify-claim file --path <path> [--sha256 <expected>]` — file must exist at path
- `verify-claim deploy --url <url> [--expect-status 200]` — URL must return expected status
- `verify-claim build --artifact <path>` — artifact must exist

Two-layer: pre-claim gate (agent-side) + `--audit` (Kai-side, deeper ancestry checks).

**Requires** Buzz relay git auth or a local clone with `origin` fetch access.

Usage: `verify-claim --help`. Output: human-readable or `--format json`.
