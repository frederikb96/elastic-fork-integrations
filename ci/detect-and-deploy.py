#!/usr/bin/env python3
"""Detect changed packages and deploy to EPR server."""

import sys

# Force unbuffered output for CI visibility
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import argparse
import subprocess
import yaml
import hashlib
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

from deploy_config import get_config, EPRConfig, ENVIRONMENTS


@dataclass
class PackageInfo:
    """Metadata for an integration package."""

    dir_path: Path
    name: str
    version: str

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class DeploymentError(Exception):
    """Raised when deployment fails."""

    pass


class DeploymentManager:
    """Manages detection and deployment of Elastic integration packages."""

    # SSH options for all commands
    SSH_OPTS = "-i ~/.ssh/epr_deploy_key -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

    def __init__(self, config: EPRConfig):
        self.config = config
        self.ssh_target = f"{config.user}@{config.host}"

        self.repo_root = Path(__file__).parent.parent
        self.packages_dir = self.repo_root / "packages"
        self.build_dir = self.repo_root / "build" / "packages"
        self.force_rebuild_file = self.repo_root / "ci" / "force-rebuild.yml"
        self.force_rebuild_hash = None

    def print_header(self, step: str, total: str, title: str):
        """Print formatted step header."""
        print(f"\n[{step}/{total}] {title}...")
        print()

    def run_ssh(
        self, command: str, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run SSH command on EPR server."""
        full_cmd = f"ssh {self.SSH_OPTS} -o ConnectTimeout=10 {self.ssh_target} '{command}'"
        result = subprocess.run(
            full_cmd, shell=True, capture_output=capture_output, text=True, check=False
        )
        return result

    def step0_test_connectivity(self):
        """Test SSH connectivity to EPR server."""
        self.print_header("0", "6", "Testing SSH connectivity to EPR server")

        result = self.run_ssh("echo 'SSH connection successful'")

        if result.returncode != 0:
            print("❌ ERROR: Cannot connect to EPR server via SSH")
            print()
            print("Troubleshooting checklist:")
            print("  1. Check CI/CD variables are set:")
            print("     - SSH_HOST_EPR (EPR server IP/hostname)")
            print("     - SSH_USER_EPR (SSH username)")
            print("     - SSH_KEY_EPR (private key content)")
            print("  2. Verify EPR server is reachable from GitLab runner")
            print("  3. Check firewall allows SSH from runner to EPR server")
            raise DeploymentError("SSH connectivity test failed")

        print("✓ SSH connectivity confirmed")

    def read_force_rebuild_packages(self) -> Dict[str, PackageInfo]:
        """Read packages from force-rebuild file and return as PackageInfo dict.

        Returns:
            Dict mapping package dir Path to PackageInfo for forced packages
        """
        if not self.force_rebuild_file.exists():
            return {}

        print(f"\n📋 Found {self.force_rebuild_file.name} - checking forced packages...")

        # Store file hash for later comparison
        content = self.force_rebuild_file.read_bytes()
        self.force_rebuild_hash = hashlib.sha256(content).hexdigest()

        # Parse YAML
        try:
            data = yaml.safe_load(content)
            if not data or "packages" not in data:
                print("  ⚠️  WARNING: force-rebuild.yml has no 'packages' field")
                print("     File will be ignored. Expected format:")
                print("     packages:")
                print("       - package_name")
                return {}

            package_names = data["packages"]

            # Validate packages is a list
            if not isinstance(package_names, list):
                print("  ⚠️  WARNING: force-rebuild.yml 'packages' field must be a list")
                print("     File will be ignored. Expected format:")
                print("     packages:")
                print("       - package_name")
                return {}

            if not package_names:
                print("  ⚠️  Warning: force-rebuild.yml packages list is empty")
                return {}

            print(f"  Found {len(package_names)} packages to force rebuild:")
            for name in package_names:
                print(f"    - {name}")

            # Load manifest data for these packages
            forced_packages = {}
            for pkg_name in package_names:
                pkg_dir = self.packages_dir / pkg_name
                manifest_path = pkg_dir / "manifest.yml"

                if not manifest_path.exists():
                    print(
                        f"  ⚠️  Warning: Package {pkg_name} not found, skipping"
                    )
                    continue

                try:
                    with open(manifest_path, "r") as f:
                        manifest_data = yaml.safe_load(f)

                    name = manifest_data.get("name")
                    version = str(manifest_data.get("version", ""))

                    if name and version:
                        forced_packages[pkg_dir] = PackageInfo(
                            dir_path=pkg_dir, name=name, version=version
                        )
                except Exception as e:
                    print(
                        f"  ⚠️  Warning: Failed to parse {manifest_path}: {e}"
                    )
                    continue

            print(f"\n✓ Loaded {len(forced_packages)} packages from force-rebuild.yml")
            return forced_packages

        except yaml.YAMLError as e:
            print(f"  ❌ ERROR: Failed to parse force-rebuild.yml (invalid YAML syntax)")
            print(f"     {e}")
            print("     File will be ignored. Fix syntax and re-run deployment.")
            return {}
        except Exception as e:
            print(f"  ❌ ERROR: Unexpected error reading force-rebuild.yml: {e}")
            print("     File will be ignored. Check file permissions and format.")
            return {}

    def step1_validate_local_packages(self) -> Dict[Path, PackageInfo]:
        """Validate all local package manifests and extract metadata."""
        self.print_header(
            "1", "6", "Validating main branch packages and extracting metadata"
        )

        manifests = list(self.packages_dir.glob("*/manifest.yml"))

        if not manifests:
            raise DeploymentError(f"No manifest.yml files found in {self.packages_dir}")

        packages = {}
        processed = 0

        for manifest_path in manifests:
            pkg_dir = manifest_path.parent

            # Parse manifest with PyYAML
            try:
                with open(manifest_path, "r") as f:
                    manifest_data = yaml.safe_load(f)
            except Exception as e:
                raise DeploymentError(f"Failed to parse {manifest_path}: {e}")

            # Validate required fields
            pkg_name = manifest_data.get("name")
            pkg_version = manifest_data.get("version")

            if not pkg_name:
                raise DeploymentError(
                    f"Package in {pkg_dir} has no 'name' field in manifest.yml"
                )

            if not pkg_version:
                raise DeploymentError(
                    f"Package '{pkg_name}' in {pkg_dir} has no 'version' field in manifest.yml"
                )

            # Handle version as string (YAML may parse as int/float)
            pkg_version = str(pkg_version)

            packages[pkg_dir] = PackageInfo(
                dir_path=pkg_dir, name=pkg_name, version=pkg_version
            )

            processed += 1
            if processed % 50 == 0:
                print(f"  ... validated {processed} packages so far")

        print(f"\n✓ Validated {len(packages)} packages from main branch")
        return packages

    def step2_check_deployment_status(
        self, packages: Dict[Path, PackageInfo], forced_packages: Dict[Path, PackageInfo]
    ) -> List[PackageInfo]:
        """Check deployment status on EPR server and find changed packages.

        Args:
            packages: All local packages
            forced_packages: Packages from force-rebuild.yml to rebuild regardless of version

        Returns:
            List of packages to build and deploy
        """
        self.print_header("2", "6", "Checking deployment status on EPR server")

        # Fetch all manifest files from server (raw YAML content)
        # Use delimiters to separate multiple files in single SSH call
        fetch_script = f"""
cd {self.config.deploy_path} || exit 1

# Output all manifests with delimiters
for manifest in */*/manifest.yml; do
    if [[ -f "$manifest" ]]; then
        echo "===MANIFEST_START=== $manifest"
        cat "$manifest"
        echo "===MANIFEST_END==="
    fi
done

# List all zip files
echo "===ZIPS_START==="
ls -1 *.zip 2>/dev/null || true
echo "===ZIPS_END==="
"""

        result = self.run_ssh(fetch_script)

        if result.returncode != 0:
            raise DeploymentError(f"Failed to fetch deployment data: {result.stderr}")

        print("✓ Fetched deployment data from EPR server")
        print()

        # Parse fetched data
        deployed_manifests = {}  # (name, version) -> manifest_path
        deployed_zips = set()

        output = result.stdout

        # Extract manifest section
        if "===MANIFEST_START===" in output:
            manifest_blocks = output.split("===MANIFEST_START===")[1:]

            for block in manifest_blocks:
                if "===MANIFEST_END===" not in block:
                    continue

                # Split header and content
                parts = block.split("\n", 1)
                if len(parts) < 2:
                    continue

                manifest_path = parts[0].strip()
                yaml_content = parts[1].split("===MANIFEST_END===")[0]

                # Parse YAML with PyYAML (handles all quote types automatically)
                try:
                    manifest_data = yaml.safe_load(yaml_content)
                    if manifest_data:
                        name = manifest_data.get("name")
                        version = str(manifest_data.get("version", ""))

                        if name and version:
                            deployed_manifests[(name, version)] = manifest_path
                except yaml.YAMLError as e:
                    print(f"  ⚠ Warning: Failed to parse {manifest_path}: {e}")
                    continue

        # Extract zip list
        if "===ZIPS_START===" in output:
            zips_section = output.split("===ZIPS_START===")[1].split("===ZIPS_END===")[
                0
            ]
            deployed_zips = set(
                line.strip()
                for line in zips_section.strip().split("\n")
                if line.strip()
            )

        print("Deployed packages found:")
        print(f"  Manifests: {len(deployed_manifests)}")
        print(f"  Zip files: {len(deployed_zips)}")
        print()

        # Compare and find changed packages (version-based)
        changed = []

        for pkg_dir, pkg_info in packages.items():
            manifest_key = (pkg_info.name, pkg_info.version)
            zip_name = f"{pkg_info.name}-{pkg_info.version}.zip"

            # Check if deployed with correct version
            if manifest_key not in deployed_manifests:
                print(f"  + {pkg_info}: NEW or UPDATED")
                changed.append(pkg_info)
            elif zip_name not in deployed_zips:
                print(f"  + {pkg_info}: INCOMPLETE (missing zip)")
                changed.append(pkg_info)

        # Add forced packages (deduplicate by package name)
        changed_names = {pkg.name for pkg in changed}
        forced_added = []

        for pkg_dir, pkg_info in forced_packages.items():
            if pkg_info.name not in changed_names:
                print(f"  + {pkg_info}: FORCED REBUILD")
                changed.append(pkg_info)
                forced_added.append(pkg_info)

        print()
        print("Summary:")
        print(f"  Total packages in repo: {len(packages)}")
        print(f"  Changed/new packages (version): {len(changed) - len(forced_added)}")
        if forced_added:
            print(f"  Forced rebuild packages: {len(forced_added)}")
        print(f"  Total to build: {len(changed)}")

        if not changed:
            print()
            print("✅ No packages changed - nothing to build or deploy!")
            sys.exit(0)

        print()
        print("Packages to build:")
        for pkg in changed:
            print(f"  - {pkg} from {pkg.dir_path.name}")

        return changed

    def step3_build_packages(self, changed: List[PackageInfo]) -> List[PackageInfo]:
        """Build changed packages using elastic-package."""
        self.print_header("3", "6", "Building changed packages")

        built = []
        failed = []

        for idx, pkg_info in enumerate(changed, 1):
            print(f"[{idx}/{len(changed)}] Building {pkg_info.name}...")

            result = subprocess.run(
                ["elastic-package", "build", "-C", str(pkg_info.dir_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"  ✓ {pkg_info.name} built successfully")
                built.append(pkg_info)
            else:
                print(f"  ✗ {pkg_info.name} FAILED")
                failed.append(pkg_info.name)
                print()
                print("  Error output:")
                # Show last 20 lines of stderr
                error_lines = result.stderr.strip().split("\n")
                for line in error_lines[-20:]:
                    print(f"    {line}")
                print()

            print()

        print("Build summary:")
        print(f"  Successfully built: {len(built)}")
        print(f"  Failed: {len(failed)}")

        if failed:
            print()
            print("❌ Failed packages:")
            for pkg in failed:
                print(f"  - {pkg}")
            raise DeploymentError("Package builds failed")

        return built

    def step4_deploy(self):
        """Deploy built packages to EPR server via rsync."""
        self.print_header("4", "6", "Deploying packages to EPR server")

        print(f"Syncing packages to {self.ssh_target}:{self.config.deploy_path}...")

        rsync_ssh = f"ssh {self.SSH_OPTS}"
        result = subprocess.run(
            [
                "rsync",
                "-rh",
                "--stats",
                "--chmod=D777,F666",
                "--no-perms",
                "--no-times",
                "--no-owner",
                "--no-group",
                "-e", rsync_ssh,
                f"{self.build_dir}/",
                f"{self.ssh_target}:{self.config.deploy_path}/",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print()
            print("❌ ERROR: Failed to deploy packages to EPR server")
            print(result.stderr)
            raise DeploymentError("Rsync failed")

        print()
        print("✓ Rsync completed successfully")
        # Print stats summary
        print(result.stdout)

    def step5_validate_deployment(self, built: List[PackageInfo]):
        """Validate deployed packages on EPR server."""
        self.print_header("5", "6", "Validating deployed packages on EPR server")

        # Fetch raw manifest content for all built packages in ONE SSH call
        # Build package list for validation
        pkg_paths = " ".join(f"{p.name}:{p.version}" for p in built)

        validate_script = f"""
cd {self.config.deploy_path} || exit 1

# Check each package
for pkg in {pkg_paths}; do
    IFS=':' read -r name version <<< "$pkg"

    # Check manifest
    manifest_path="${{name}}/${{version}}/manifest.yml"
    if [[ -f "$manifest_path" ]]; then
        echo "===MANIFEST_START=== $name|$version"
        cat "$manifest_path"
        echo "===MANIFEST_END==="
    else
        echo "===MANIFEST_MISSING=== $name|$version"
    fi

    # Check zip
    zip_file="${{name}}-${{version}}.zip"
    if [[ -f "$zip_file" ]]; then
        echo "===ZIP_OK=== $name|$version"
    else
        echo "===ZIP_MISSING=== $name|$version"
    fi
done
"""

        result = self.run_ssh(validate_script)

        if result.returncode != 0:
            raise DeploymentError(f"Validation command failed: {result.stderr}")

        # Parse output with PyYAML (no text processing!)
        output = result.stdout
        validation_failed = []

        # Track which packages have valid manifests and zips
        manifest_validated = {}  # pkg.name -> True/False
        zip_validated = {}

        # Process each built package
        for pkg_info in built:
            key = f"{pkg_info.name}|{pkg_info.version}"
            print(f"  Validating {pkg_info}...")

            # Check for manifest
            if f"===MANIFEST_MISSING=== {key}" in output:
                print("    ✗ Manifest missing")
                validation_failed.append(f"{pkg_info.name}: manifest missing")
                manifest_validated[pkg_info.name] = False
            elif f"===MANIFEST_START=== {key}" in output:
                # Extract and parse YAML content
                start_marker = f"===MANIFEST_START=== {key}"
                if start_marker in output:
                    yaml_block = output.split(start_marker)[1].split(
                        "===MANIFEST_END==="
                    )[0]

                    try:
                        manifest_data = yaml.safe_load(yaml_block)
                        if manifest_data:
                            deployed_name = manifest_data.get("name")
                            deployed_version = str(manifest_data.get("version", ""))

                            if (
                                deployed_name == pkg_info.name
                                and deployed_version == pkg_info.version
                            ):
                                manifest_validated[pkg_info.name] = True
                            else:
                                print(
                                    f"    ✗ Manifest mismatch: name={deployed_name}, version={deployed_version}"
                                )
                                validation_failed.append(
                                    f"{pkg_info.name}: manifest mismatch"
                                )
                                manifest_validated[pkg_info.name] = False
                        else:
                            print("    ✗ Manifest empty")
                            validation_failed.append(f"{pkg_info.name}: manifest empty")
                            manifest_validated[pkg_info.name] = False
                    except yaml.YAMLError as e:
                        print(f"    ✗ Manifest parse error: {e}")
                        validation_failed.append(
                            f"{pkg_info.name}: manifest parse error"
                        )
                        manifest_validated[pkg_info.name] = False
            else:
                print("    ✗ Manifest check failed (unknown status)")
                validation_failed.append(f"{pkg_info.name}: manifest unknown")
                manifest_validated[pkg_info.name] = False

            # Check for zip
            if f"===ZIP_OK=== {key}" in output:
                zip_validated[pkg_info.name] = True
            elif f"===ZIP_MISSING=== {key}" in output:
                print("    ✗ Zip file missing")
                validation_failed.append(f"{pkg_info.name}: zip missing")
                zip_validated[pkg_info.name] = False
            else:
                print("    ✗ Zip check failed (unknown status)")
                validation_failed.append(f"{pkg_info.name}: zip unknown")
                zip_validated[pkg_info.name] = False

            # Print result
            if manifest_validated.get(pkg_info.name) and zip_validated.get(
                pkg_info.name
            ):
                print("    ✓ Validated successfully")

        print()

        if validation_failed:
            print(
                f"❌ Post-deployment validation FAILED for {len(validation_failed)} packages:"
            )
            for failure in validation_failed:
                print(f"  - {failure}")
            print()
            raise DeploymentError("Deployment validation failed")

        print(f"✅ All {len(built)} packages validated successfully on EPR server")

    def step6_restart_epr(self):
        """Restart EPR container to load new packages."""
        self.print_header("6", "6", "Restarting EPR container to load new packages")

        # Go to parent directory of packages (where docker-compose.yml lives)
        epr_dir = str(Path(self.config.deploy_path).parent)
        result = self.run_ssh(
            f"cd {epr_dir} && sudo docker restart epr", capture_output=True
        )

        if result.returncode != 0:
            print("❌ ERROR: Failed to restart EPR container")
            print(result.stderr)
            raise DeploymentError("EPR restart failed")

        print("✅ EPR container restarted successfully")

    def cleanup_force_rebuild_file(self):
        """Delete force-rebuild file if unchanged since read.

        Only deletes if file hash matches the stored hash from initial read.
        This ensures we don't delete a file that was modified during deployment.
        """
        if not self.force_rebuild_file.exists():
            return

        if self.force_rebuild_hash is None:
            # File wasn't read initially (didn't exist at start)
            return

        print("\n🧹 Cleaning up force-rebuild file...")

        current_hash = hashlib.sha256(self.force_rebuild_file.read_bytes()).hexdigest()

        if current_hash == self.force_rebuild_hash:
            self.force_rebuild_file.unlink()
            print("✅ Deleted force-rebuild.yml (deployment successful)")
        else:
            print(
                "⚠️  force-rebuild.yml was modified during deployment - keeping file"
            )
            print("   File will be processed on next deployment run")

    def run(self):
        """Run complete deployment pipeline."""
        print("=" * 64)
        print("Elastic Integration Packages - Selective Build and Deploy")
        print("=" * 64)

        try:
            # Step 0: Test connectivity
            self.step0_test_connectivity()

            # Read force-rebuild file (if exists)
            forced_packages = self.read_force_rebuild_packages()

            # Step 1: Validate local packages
            packages = self.step1_validate_local_packages()

            # Step 2: Check deployment status
            changed = self.step2_check_deployment_status(packages, forced_packages)

            # Step 3: Build changed packages
            built = self.step3_build_packages(changed)

            # Step 4: Deploy to server
            self.step4_deploy()

            # Step 5: Validate deployment
            self.step5_validate_deployment(built)

            # Step 6: Restart EPR
            self.step6_restart_epr()

            # Cleanup force-rebuild file if deployment successful
            self.cleanup_force_rebuild_file()

            # Success summary
            print()
            print("=" * 64)
            print("DEPLOYMENT COMPLETE")
            print("=" * 64)
            print(f"Built and deployed {len(built)} integration packages:")
            for pkg in built:
                print(f"  ✓ {pkg}")
            print()

            return 0

        except DeploymentError as e:
            print(f"\n❌ Deployment failed: {e}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\n\n⚠ Deployment interrupted by user", file=sys.stderr)
            return 130
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            return 1


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Deploy Elastic packages to EPR server")
    parser.add_argument(
        "--env",
        required=True,
        choices=list(ENVIRONMENTS.keys()),
        help="Target environment",
    )
    args = parser.parse_args()

    config = get_config(args.env)
    print(f"Target: {args.env} ({config.host})")

    manager = DeploymentManager(config)
    sys.exit(manager.run())


if __name__ == "__main__":
    main()
