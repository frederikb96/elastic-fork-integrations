# Dynamic Dataset Modifications Tracking

This file tracks all Elastic integrations that have been modified by SVA to remove `dynamic_dataset` and `dynamic_namespace` flags for multi-tenant namespace isolation.

**What this is:** Upstream Elastic integrations sometimes use dynamic_dataset/dynamic_namespace flags that grant wildcard API key permissions (logs-*-*), breaking tenant isolation. This automated system removes those flags and marks affected integrations with warnings in Kibana Fleet UI.

**How it works:** Daily merge pipeline from upstream Elastic integrations triggers automatic detection and removal of dynamic flags. Python script modifies integration manifests, updates this tracking file, and commits changes. If any flags remain after cleanup, pipeline fails for manual SE investigation.

**Pipeline trigger:**
- Scheduled daily merge from upstream Elastic integrations repository
- Scans packages/ directory for dynamic_dataset and dynamic_namespace flags
- Invokes auto-fix script if flags detected
- Commits changes and triggers deploy pipeline
- Generates this YAML tracking data automatically

**Using restricted integrations:** If you need to use an integration marked as "SVA RESTRICTED" in Fleet UI, be aware it has been modified for namespace isolation. For production use with routing or special requirements, manual package cloning and testing is required. Contact SE team for assistance.

**Data stream status indicators:**
- ✅ (green checkmark) = Namespace-scoped, no dynamic flags. **Note:** This doesn't guarantee the data stream will work correctly - some depend on specific configurations or other data streams. Always test integrations before production use.
- ⚠️ (warning) = Had dynamic flags, now removed for namespace isolation. Review before use.

---

<!-- AUTO-GENERATED SECTION BELOW - DO NOT MODIFY YAML STRUCTURE -->
<!-- Only edit 'comment' fields - all other fields are auto-managed by ci/remove-dynamic-flags.py -->

```yaml
integrations: {}
```
