# Open Review Items for https://github.com/elastic/integrations/pull/14161
Date: 2025-09-25T09:58:00Z
Reviewed with:
- `gh api graphql` (see AGENTS.md for exact command)
- `jq` to filter `isResolved == false` threads

## Action Items

### packages/bitsight/data_stream/vulnerability/elasticsearch/ingest_pipeline/default.yml
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328876588>
- **Reviewer ask**: Apply the full suggested block so the shared error processors remain and the templated error message uses conditional tag expansion.
- **Current status**: Updated to the reviewer’s snippet (conditional tag expansion and post-on_failure processors restored).
- **Next steps**: None beyond reiterating in the PR comment.

### packages/bitsight/_dev/deploy/docker/docker-compose.yml
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2157811223>
- **Reviewer ask**: Pin mock stream image to `docker.elastic.co/observability/stream:v0.18.0`.
- **Current status**: File already updated, awaiting reviewer confirmation.
- **Next steps**: None (just mention in GH reply).

### packages/bitsight/data_stream/vulnerability/agent/stream/cel.yml.hbs — retry guard
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328866403>
- **Reviewer ask**: Only set `want_more`/retry when additional jobs remain (`size(tail(state.jobs)) != 0`).
- **Current status**: Added queue-size checks to `want_more` branches across the CEL program.
- **Next steps**: none.

### packages/bitsight/data_stream/vulnerability/agent/stream/cel.yml.hbs — evidence encoding
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328867304>
- **Reviewer ask**: Use `msg.encode_json()` directly (function already returns string).
- **Current status**: Switched to `encode_json()` directly.
- **Next steps**: none.

### packages/bitsight/data_stream/vulnerability/agent/stream/cel.yml.hbs — empty company branch
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328868524>
- **Reviewer ask**: Emit a single event with `{ "threat": job.threat }.encode_json()` and skip new jobs.
- **Current status**: Branch now matches reviewer snippet and emits encoded threat JSON.
- **Next steps**: none.

### packages/bitsight/data_stream/vulnerability/agent/stream/cel.yml.hbs — error prefix
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328869105>
- **Reviewer ask**: Build message with `job.url` directly (no `string(...)`).
- **Current status**: `job.url` concatenation applied.
- **Next steps**: none.

### packages/bitsight/manifest.yml — request tracer location
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328871452>
- **Reviewer ask**: Move `enable_request_tracer` var into the data stream manifest per integration guidelines.
- **Current status**: Var removed from package manifest and added to data stream manifest.
- **Next steps**: none.

### packages/bitsight/_dev/build/docs/README.md
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328872132>
- **Reviewer ask**: Align README structure with official documentation guidelines.
- **Current status**: README rewritten following the guideline section order.
- **Next steps**: none.

### packages/bitsight/data_stream/vulnerability/_dev/test/pipeline/test-vulnerability.json
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328873110>
- **Reviewer ask**: Rename fixture to `test-vulnerability.log` and keep JSON sample on a single line as provided (update expected filename accordingly).
- **Current status**: Fixture renamed to `.log` with reviewer-provided payload; expected filename updated.
- **Next steps**: none.

### packages/bitsight/data_stream/vulnerability/agent/stream/cel.yml.hbs — acknowledgement
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328873372>
- **Reviewer ask**: Informational response from reviewer (“Thank you for this comment.”).
- **Current status**: No change required; keep note for completeness until reviewer resolves thread.
- **Next steps**: None.

### packages/bitsight/data_stream/vulnerability/agent/stream/cel.yml.hbs — polling event
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328874773>
- **Reviewer ask**: Emit polling events as a list of objects with encoded JSON string per suggestion.
- **Current status**: Polling events now emit encoded JSON objects matching the suggestion.
- **Next steps**: none.

### packages/bitsight/data_stream/vulnerability/agent/stream/cel.yml.hbs — evidence mapping
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328875927>
- **Reviewer ask**: Restructure success branch to map results, encode JSON once, and keep queue updates identical to snippet.
- **Current status**: Success branch now mirrors reviewer snippet (map + encode + queue guard).
- **Next steps**: none.

### packages/bitsight/manifest.yml — owner type
- **Comment**: <https://github.com/elastic/integrations/pull/14161#discussion_r2328894801>
- **Reviewer ask**: Set owner type to `partner` or `community`.
- **Current status**: Updated to `partner` in repo, awaiting reviewer confirmation.
- **Next steps**: None beyond highlighting in PR response.

---
