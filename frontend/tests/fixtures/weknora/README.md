# WeKnora test fixtures

Source: https://github.com/Tencent/WeKnora at `cbdcebabf48c5ee2d6868b370326aa8341703f62`. Copyright and license: [UPSTREAM-LICENSE](../../../UPSTREAM-LICENSE).

These fixtures retain the upstream inputs needed by the inherited frontend tests without requiring the Go backend, website build, or sandbox deployment tree.

- `catalog-operations.json`: all unique `x-agent.id` values from `docs/swagger.json`; source SHA256 is recorded in the fixture. It checks inherited catalog translations; the running platform uses official ContextDB MCP schemas.
- `website-docs/`: exact Markdown files linked by `src/utils/docsUrl.ts` at this commit.
- `sandbox-pty-prompt.sh`: exact `docker/sandbox-pty-prompt.sh`, sourced only in the terminal regression test.

Refresh these files from the recorded upstream checkout when updating the inherited frontend.
