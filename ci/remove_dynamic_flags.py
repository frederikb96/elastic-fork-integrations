#!/usr/bin/env python3
"""
Remove dynamic_dataset and dynamic_namespace flags from Elastic integrations.

This script:
1. Scans all integration packages for dynamic_dataset/dynamic_namespace flags
2. Removes flags from data stream manifests
3. Marks affected integrations with (⚠️ SVA RESTRICTED) prefix in titles
4. Updates DYNAMIC_DATASET_MODIFICATIONS.md tracking file

Usage: python3 ci/remove-dynamic-flags.py
Exit codes: 0 (success), 1 (failure)
"""

from pathlib import Path
from ruamel.yaml import YAML
import re
import sys
from typing import Dict, Optional


# Constants
REPO_ROOT = Path(__file__).parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"
OVERVIEW_FILE = REPO_ROOT / "DYNAMIC_DATASET_MODIFICATIONS.md"
PREFIX = "(⚠️ SVA RESTRICTED) "


class IntegrationProcessor:
    """Processes a single integration package for dynamic flags."""

    def __init__(self, package_dir: Path, yaml: YAML):
        self.package_dir = package_dir
        self.package_name = package_dir.name
        self.yaml = yaml
        self.affected_data_streams: Dict[str, bool] = {}
        self.integration_title: Optional[str] = None

    def has_dynamic_flags(self) -> bool:
        """Scan data streams for dynamic flags."""
        ds_dir = self.package_dir / "data_stream"
        if not ds_dir.exists():
            return False

        for ds_path in ds_dir.iterdir():
            if not ds_path.is_dir():
                continue

            manifest_path = ds_path / "manifest.yml"
            if not manifest_path.exists():
                continue

            try:
                with open(manifest_path, "r") as f:
                    data = self.yaml.load(f)

                # Handle empty YAML files
                if data is None:
                    self.affected_data_streams[ds_path.name] = False
                    continue

                # Check for elasticsearch section with dynamic flags
                if "elasticsearch" in data:
                    es_section = data["elasticsearch"]
                    # Handle elasticsearch: null or elasticsearch: {}
                    if es_section is None or not isinstance(es_section, dict):
                        self.affected_data_streams[ds_path.name] = False
                    else:
                        has_flags = (
                            es_section.get("dynamic_dataset") is True
                            or es_section.get("dynamic_namespace") is True
                        )
                        self.affected_data_streams[ds_path.name] = has_flags
                else:
                    self.affected_data_streams[ds_path.name] = False

            except Exception as e:
                print(
                    f"❌ ERROR: Failed to parse {manifest_path}: {e}", file=sys.stderr
                )
                sys.exit(1)

        return any(self.affected_data_streams.values())

    def process(self) -> None:
        """Remove flags and update titles for affected integration."""
        print(f"  Processing: {self.package_name}")

        # Update package-level title
        self._update_package_title()

        # Process each affected data stream
        for ds_name, is_affected in self.affected_data_streams.items():
            if is_affected:
                self._remove_flags_from_datastream(ds_name)
                self._update_datastream_title(ds_name)

    def _update_package_title(self) -> None:
        """Add prefix to package manifest title using text-based editing."""
        pkg_manifest = self.package_dir / "manifest.yml"

        try:
            # Read file as lines
            with open(pkg_manifest, "r") as f:
                lines = f.readlines()

            # Find and parse title for integration_title
            for line in lines:
                match = re.match(r"^(\s*)title:\s*(.*)$", line)
                if match:
                    value = match.group(2).strip()
                    # Parse value (handle quotes)
                    if value.startswith('"'):
                        self.integration_title = value[1:-1]
                    elif value.startswith("'"):
                        self.integration_title = value[1:-1]
                    else:
                        self.integration_title = value
                    break

            if not self.integration_title:
                print(f"❌ ERROR: No 'title' field in {pkg_manifest}", file=sys.stderr)
                sys.exit(1)

            # Check if already has prefix
            if self.integration_title.startswith(PREFIX):
                print("    ✓ Package title already marked")
                return

            # Find title line and modify it
            modified = False
            for i, line in enumerate(lines):
                match = re.match(r"^(\s*)title:\s*(.*)$", line)
                if match:
                    indent = match.group(1)
                    value = match.group(2).strip()

                    # Determine quote style and modify
                    if value.startswith('"'):
                        inner = value[1:-1]
                        lines[i] = f'{indent}title: "{PREFIX}{inner}"\n'
                    elif value.startswith("'"):
                        inner = value[1:-1]
                        lines[i] = f"{indent}title: '{PREFIX}{inner}'\n"
                    else:
                        # Need quotes if prefix contains special chars
                        lines[i] = f'{indent}title: "{PREFIX}{value}"\n'

                    modified = True
                    break

            if modified:
                with open(pkg_manifest, "w") as f:
                    f.writelines(lines)
                print("    ✓ Updated package title")

        except Exception as e:
            print(
                f"❌ ERROR: Failed to update package title in {pkg_manifest}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    def _remove_flags_from_datastream(self, ds_name: str) -> None:
        """Remove dynamic flags from data stream manifest using text-based editing."""
        ds_manifest = self.package_dir / "data_stream" / ds_name / "manifest.yml"

        try:
            # Read file as lines
            with open(ds_manifest, "r") as f:
                lines = f.readlines()

            # Find elasticsearch section
            es_line_idx = None
            es_indent = None
            for i, line in enumerate(lines):
                match = re.match(r"^(\s*)elasticsearch:\s*$", line)
                if match:
                    es_line_idx = i
                    es_indent = len(match.group(1))
                    break

            if es_line_idx is None:
                return  # No elasticsearch section

            # Parse section to check if it has only dynamic flags
            # We'll remove specific lines instead of whole section
            end_idx = es_line_idx + 1
            lines_to_remove = []
            has_other_settings = False

            while end_idx < len(lines):
                line = lines[end_idx]
                if line.strip() == "":
                    end_idx += 1
                    continue

                # Check indentation
                stripped = line.lstrip()
                current_indent = len(line) - len(stripped)

                if current_indent <= es_indent:
                    break  # End of elasticsearch section

                # Check if this is a dynamic flag line
                if stripped.startswith("dynamic_dataset:") or stripped.startswith(
                    "dynamic_namespace:"
                ):
                    lines_to_remove.append(end_idx)
                else:
                    has_other_settings = True

                end_idx += 1

            # Remove flagged lines
            if lines_to_remove:
                # Remove in reverse to preserve indices
                for idx in reversed(lines_to_remove):
                    del lines[idx]

                # If no other settings, remove elasticsearch section entirely
                if not has_other_settings:
                    del lines[es_line_idx]

                with open(ds_manifest, "w") as f:
                    f.writelines(lines)

                print(f"    ✓ Removed flags from {ds_name}")

        except Exception as e:
            print(
                f"❌ ERROR: Failed to remove flags from {ds_manifest}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    def _update_datastream_title(self, ds_name: str) -> None:
        """Add prefix to data stream manifest title using text-based editing."""
        ds_manifest = self.package_dir / "data_stream" / ds_name / "manifest.yml"

        try:
            # Read file as lines
            with open(ds_manifest, "r") as f:
                lines = f.readlines()

            # Find title line
            title_found = False
            for i, line in enumerate(lines):
                match = re.match(r"^(\s*)title:\s*(.*)$", line)
                if match:
                    title_found = True
                    indent = match.group(1)
                    value = match.group(2).strip()

                    # Check if already has prefix
                    if PREFIX in value:
                        print(f"    ✓ {ds_name} title already marked")
                        return

                    # Modify based on quote style
                    if value.startswith('"'):
                        inner = value[1:-1]
                        lines[i] = f'{indent}title: "{PREFIX}{inner}"\n'
                    elif value.startswith("'"):
                        inner = value[1:-1]
                        lines[i] = f"{indent}title: '{PREFIX}{inner}'\n"
                    else:
                        lines[i] = f'{indent}title: "{PREFIX}{value}"\n'

                    with open(ds_manifest, "w") as f:
                        f.writelines(lines)
                    print(f"    ✓ Updated {ds_name} title")
                    return

            if not title_found:
                print(
                    f"⚠️  WARNING: No 'title' field in {ds_manifest}, skipping title update"
                )

        except Exception as e:
            print(
                f"❌ ERROR: Failed to update data stream title in {ds_manifest}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    def get_data(self) -> Dict:
        """Return data for overview file with emoji indicators."""
        return {
            "title": self.integration_title.replace(PREFIX, "")
            if self.integration_title
            else "",
            "comment": "",
            "data_streams": {
                ds_name: {"namespaced": "✅" if not is_affected else "⚠️", "comment": ""}
                for ds_name, is_affected in self.affected_data_streams.items()
            },
        }


class OverviewManager:
    """Manages DYNAMIC_DATASET_MODIFICATIONS.md file."""

    def __init__(self, overview_file: Path, yaml: YAML):
        self.overview_file = overview_file
        self.yaml = yaml
        self.data: Dict = {}

    def load(self) -> None:
        """Load existing overview file."""
        if not self.overview_file.exists():
            print(
                f"❌ ERROR: Overview file does not exist: {self.overview_file}",
                file=sys.stderr,
            )
            print("   Create it manually first with proper structure.", file=sys.stderr)
            sys.exit(1)

        content = self.overview_file.read_text()

        # Extract YAML section between markers
        # Looking for: <!-- AUTO-GENERATED... --> ... ```yaml\n <content> \n```
        pattern = r"```yaml\n(.*?)\n```"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            print(
                f"❌ ERROR: Could not find YAML section in {self.overview_file}",
                file=sys.stderr,
            )
            print("   Expected format: ```yaml\\n<content>\\n```", file=sys.stderr)
            sys.exit(1)

        yaml_content = match.group(1)

        try:
            self.data = self.yaml.load(yaml_content)
            if not self.data:
                self.data = {"integrations": {}}
            if "integrations" not in self.data:
                self.data["integrations"] = {}
        except Exception as e:
            print(
                f"❌ ERROR: Failed to parse YAML in {self.overview_file}: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    def merge(self, new_integrations: Dict) -> None:
        """Merge new integration data, preserving existing comments."""
        for pkg_name, new_data in new_integrations.items():
            if pkg_name in self.data["integrations"]:
                # Update existing entry, preserve comments
                existing = self.data["integrations"][pkg_name]

                # Update title
                existing["title"] = new_data["title"]

                # Preserve integration-level comment
                if "comment" in existing:
                    new_data["comment"] = existing["comment"]

                # Merge data streams, preserving DS-level comments
                for ds_name, ds_data in new_data["data_streams"].items():
                    if (
                        "data_streams" in existing
                        and ds_name in existing["data_streams"]
                    ):
                        # Preserve DS comment
                        if "comment" in existing["data_streams"][ds_name]:
                            ds_data["comment"] = existing["data_streams"][ds_name][
                                "comment"
                            ]

                    # Update/add DS entry
                    if "data_streams" not in existing:
                        existing["data_streams"] = {}
                    existing["data_streams"][ds_name] = ds_data
            else:
                # New integration entry
                self.data["integrations"][pkg_name] = new_data

    def save(self) -> None:
        """Write updated YAML back to overview file."""
        content = self.overview_file.read_text()

        # Dump YAML to string
        from io import StringIO

        stream = StringIO()
        self.yaml.dump(self.data, stream)
        yaml_str = stream.getvalue()

        # Replace YAML section between ```yaml and ```
        pattern = r"(```yaml\n).*?(\n```)"
        replacement = r"\1" + yaml_str.rstrip() + r"\2"

        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        try:
            self.overview_file.write_text(new_content)
            print(f"  ✓ Updated {self.overview_file.name}")
        except Exception as e:
            print(
                f"❌ ERROR: Failed to write {self.overview_file}: {e}", file=sys.stderr
            )
            sys.exit(1)


def write_force_rebuild_file(package_names: list) -> None:
    """Write packages to force-rebuild file for deploy pipeline.

    Args:
        package_names: List of package names to force rebuild
    """
    force_rebuild_file = REPO_ROOT / "ci" / "force-rebuild.yml"

    # Create simple YAML structure
    content = "# Packages to force rebuild on next deploy\n"
    content += "# Auto-generated by merge pipeline, can be manually edited\n"
    content += "# This file is automatically deleted after successful deployment\n"
    content += "packages:\n"

    for pkg_name in sorted(package_names):
        content += f"  - {pkg_name}\n"

    try:
        force_rebuild_file.write_text(content)
        print(f"  ✓ Created {force_rebuild_file.name} with {len(package_names)} packages")
    except Exception as e:
        print(f"❌ ERROR: Failed to write {force_rebuild_file}: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    """Main entry point.

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 70)
    print("Dynamic Dataset Flag Removal Script")
    print("=" * 70)

    # Initialize YAML handler
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    # Check packages directory exists
    if not PACKAGES_DIR.exists():
        print(
            f"❌ ERROR: Packages directory not found: {PACKAGES_DIR}", file=sys.stderr
        )
        return 1

    # Scan all integrations
    affected_integrations: Dict[str, Dict] = {}

    for pkg_dir in sorted(PACKAGES_DIR.iterdir()):
        if not pkg_dir.is_dir():
            continue

        processor = IntegrationProcessor(pkg_dir, yaml)

        if processor.has_dynamic_flags():
            processor.process()
            affected_integrations[pkg_dir.name] = processor.get_data()

    # Update overview file
    if affected_integrations:
        print("\n📝 Updating overview file...")
        overview = OverviewManager(OVERVIEW_FILE, yaml)
        overview.load()
        overview.merge(affected_integrations)
        overview.save()

        # Write force-rebuild file for deploy pipeline
        print("\n📝 Creating force-rebuild marker...")
        write_force_rebuild_file(list(affected_integrations.keys()))

        print(f"\n✅ Successfully processed {len(affected_integrations)} integrations")
        print(
            f"   Modified packages: {', '.join(sorted(affected_integrations.keys()))}"
        )
    else:
        print("\n✓ No integrations with dynamic flags found")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
