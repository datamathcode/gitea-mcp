# Make the repository public

`datamathcode/gitea-mcp` was made public to support the `git+https` install path decided in ADR-0001 — a private repo would have required SSH auth scoped to the org, which defeats the point of a simple, no-account install command for anyone who wants to try the tool.

## Considered options

Going public was not the default choice — the repo's git history had the maintainer's real self-hosted Gitea instance's hostname hardcoded as a literal example in `gitea_mcp.py`'s module docstring, present since the very first commit. Making the repo public without addressing this would have permanently exposed that hostname (not a credential, but real reconnaissance-surface information about internal infrastructure) in a way that isn't cleanly reversible — flipping back to private later doesn't un-expose what's already been crawled, cloned, or cached.

The alternatives considered:
- **Genericize, then go public** (chosen) — replace the hardcoded hostname with the same generic placeholder (`gitea.example.com`) the README already used, confirmed absent from the entire current working tree, *then* flip visibility.
- **Go public as-is** — rejected; treating the hostname as harmless wasn't a call to make silently.
- **Stay private, use SSH-based git install instead** — the fallback if the hostname couldn't be cleanly addressed. Not needed once genericization was confirmed complete.

## Consequences

Old commits in the git history still contain the real hostname — only the *current* file content was genericized, not history. This was an explicit, accepted trade-off (rewriting history was out of scope), not an oversight.
