"""Validate product releases and record the exact Windows build evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import re


UPGRADE_CODE = "DD94B570-B5E2-4100-9D42-61930C611D8A"
TEST_TARGETS = (
    "//build_tools:mozc_version_test",
    "//build_tools:product_version_test",
    "//build_tools:gen_win32_resource_header_test",
    "//win32/installer:build_installer_test",
    "//win32/tip:build_tip_forwarder_dll_test",
    "//base:version_test",
    "//config:config_handler_test",
    "//rewriter:date_rewriter_test",
    "//rewriter:english_word_dictionary_rewriter_test",
    "//rewriter:rewriter_test",
)
FEATURES = {
    "date_conversion": [
        "//rewriter:date_rewriter_test", "//rewriter:rewriter_test"
    ],
    "english_completion_and_spelling": [
        "//rewriter:english_word_dictionary_rewriter_test"
    ],
    "settings": ["//config:config_handler_test"],
}
PE_TARGETS = (
    "//gui/tool:mozc_tool_win",
    "//renderer/win32:win32_renderer_main",
    "//server:mozc_server_win",
    "//win32/broker:mozc_broker_main",
    "//win32/cache_service:mozc_cache_service",
    "//win32/tip:mozc_tip32",
    "//win32/tip:mozc_tip64",
    "//win32/custom_action:custom_action",
)
INSTALLED_BINARIES = frozenset((
    "mozc_tool.exe", "mozc_renderer.exe", "mozc_server.exe", "mozc_broker.exe",
    "mozc_cache_service.exe", "mozc_tip32.dll", "mozc_tip64.dll",
))


def product_version(version):
    """Return canonical product and MSI versions, enforcing MSI field limits."""
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
        raise ValueError(f"Product version must have three numeric components: {version}")
    major, minor, patch = map(int, version.split("."))
    if major > 155 or minor > 255 or patch > 65535:
        raise ValueError(f"Product version exceeds Windows Installer limits: {version}")
    return {
        "product_version": version,
        "msi_version": f"{100 + major}.{minor}.{patch}",
        "release_tag": f"v{version}",
    }


def release_version(tag):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError(f"Release tags must use vMAJOR.MINOR.PATCH: {tag}")
    return product_version(tag[1:])


def version_tuple(version):
    return tuple(map(int, version.split(".")))


def previous_msi_version(tag):
    if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        return release_version(tag)["msi_version"]
    # Historic engine-based v3/v4 tags precede the independent product scheme.
    if re.fullmatch(r"v[34]\.[0-9]+\.[0-9]+\.[0-9]+", tag):
        return ".".join(tag[1:].split(".")[:3])
    raise ValueError(f"Unsupported published release tag: {tag}")


def check_release_order(tag, previous_tags):
    current = release_version(tag)
    for previous in previous_tags:
        old_msi = previous_msi_version(previous)
        if version_tuple(current["msi_version"]) <= version_tuple(old_msi):
            raise ValueError(
                f"MSI {current['msi_version']} must be newer than {previous} (MSI {old_msi})"
            )
        if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", previous):
            if version_tuple(current["product_version"]) <= version_tuple(previous[1:]):
                raise ValueError(f"Release {tag} must be newer than {previous}")
    return current


def check_generated_versions(expected, generated, header, msi):
    for key, value in expected.items():
        if generated.get(key) != value:
            raise ValueError(f"Generated {key} {generated.get(key)!r} does not match {value!r}")
    constants = {
        "kProductVersion": expected["product_version"],
        "kMsiProductVersion": expected["msi_version"],
        "kProductReleaseTag": expected["release_tag"],
    }
    for name, value in constants.items():
        match = re.search(rf'\b{name}\s*\[\s*\]\s*=\s*"([^"]+)"\s*;', header)
        if match is None or match[1] != value:
            raise ValueError(f"About/version header {name} does not match {value!r}")
    if msi.get("product_version") != expected["msi_version"]:
        raise ValueError("Built MSI ProductVersion does not match the product version mapping")
    if str(msi.get("upgrade_code", "")).strip("{}").upper() != UPGRADE_CODE:
        raise ValueError("Built MSI UpgradeCode changed; installed Mozkey compatibility is required")
    if msi.get("product_name") != "Mozc Date English":
        raise ValueError("Unexpected built MSI ProductName")
    if msi.get("manufacturer") != "Mozc Date English Project" or msi.get("publisher") != "Mozc Date English Project":
        raise ValueError("Unexpected built MSI publisher")
    expected_pe = expected["msi_version"] + ".0"
    for field in ("files", "pe_files"):
        records = msi.get(field, [])
        names = [item["name"].lower() for item in records]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate binary names in {field} version evidence")
    installed_files = {item["name"]: item["version"] for item in msi.get("files", [])}
    pe_files = {item["name"]: item for item in msi.get("pe_files", [])}
    if not INSTALLED_BINARIES.issubset(installed_files):
        raise ValueError("MSI File table is missing a required Mozc binary")
    if not (INSTALLED_BINARIES | {"mozc_installer_helper.dll"}).issubset(pe_files):
        raise ValueError("PE version evidence is missing a required Mozc binary")
    for name, file_version in installed_files.items():
        if file_version != expected_pe:
            raise ValueError(f"MSI File table version for {name} must be {expected_pe}, got {file_version}")
        if name not in pe_files:
            raise ValueError(f"MSI binary {name} has no matching PE version evidence")
    for name, binary in pe_files.items():
        if binary.get("file_version") != expected_pe or binary.get("product_version") != expected_pe:
            raise ValueError(f"PE FileVersion/ProductVersion for {name} must be {expected_pe}")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def configure(args):
    if args.tag:
        expected = check_release_order(args.tag, read_json(args.previous_tags))
    else:
        expected = product_version(Path(args.version_file).read_text(encoding="utf-8").strip())
    write_json(args.output, expected)
    write_json(args.test_targets, list(TEST_TARGETS))
    write_json(args.pe_targets, list(PE_TARGETS))
    # Never replace MOZC_VERSION: it remains the independent engine version.
    with Path(args.env_file).open("a", encoding="utf-8") as output:
        output.write(f"MOZKEY_PRODUCT_VERSION={expected['product_version']}\n")


def verify(args):
    expected = read_json(args.expected)
    canonical = product_version(expected["product_version"])
    if expected != canonical:
        raise ValueError("Configured product version metadata is inconsistent")
    check_generated_versions(
        expected, read_json(args.generated),
        Path(args.header).read_text(encoding="utf-8"), read_json(args.msi_metadata)
    )


def manifest(args):
    expected = read_json(args.expected)
    targets = read_json(args.test_targets)
    if targets != list(TEST_TARGETS):
        raise ValueError("Feature verification must include every required Windows test target")
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit) or args.commit != args.expected_commit:
        raise ValueError("Checked-out commit does not match the CI event commit")
    msi = Path(args.msi)
    value = {
        "schema_version": 1,
        "repository": args.repository,
        "commit": args.commit,
        "ci_run_url": args.run_url,
        "event": args.event,
        **expected,
        "about_version": expected["product_version"],
        "msi_metadata": read_json(args.msi_metadata),
        "installer": {"name": msi.name, "sha256": hashlib.sha256(msi.read_bytes()).hexdigest()},
        "passed_test_targets": targets,
        "passed_script_tests": [
            "build_tools.product_version_test", "win32.installer.build_installer_test",
            "build_tools.gen_win32_resource_header_test", "win32.tip.build_tip_forwarder_dll_test",
            "release_validation_test", "test-updater.ps1"
        ],
        "verified_features": FEATURES,
        "verification_scope": "Automated tests and built MSI metadata; Windows installation and UI checks are separate.",
    }
    write_json(args.output, value)
    if args.summary:
        with Path(args.summary).open("a", encoding="utf-8") as output:
            output.write(
                f"### Windows release verification\n\n"
                f"- Commit: `{args.commit}`\n"
                f"- Product/About version: `{expected['product_version']}`\n"
                f"- MSI ProductVersion: `{expected['msi_version']}`\n"
                f"- UpgradeCode: `{UPGRADE_CODE}`\n"
                f"- Passed targets: {', '.join(f'`{target}`' for target in targets)}\n"
                f"- Evidence: `release-manifest.json` in the MSI artifact.\n"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    configure_parser = commands.add_parser("configure")
    configure_parser.add_argument("--tag", default="")
    configure_parser.add_argument("--previous-tags")
    configure_parser.add_argument("--version-file", required=True)
    configure_parser.add_argument("--env-file", required=True)
    configure_parser.add_argument("--test-targets", required=True)
    configure_parser.add_argument("--pe-targets", required=True)
    configure_parser.add_argument("--output", required=True)
    configure_parser.set_defaults(func=configure)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--expected", required=True)
    verify_parser.add_argument("--generated", required=True)
    verify_parser.add_argument("--header", required=True)
    verify_parser.add_argument("--msi-metadata", required=True)
    verify_parser.set_defaults(func=verify)
    manifest_parser = commands.add_parser("manifest")
    for argument in ("expected", "test-targets", "commit", "expected-commit", "repository", "run-url", "event", "msi", "msi-metadata", "output"):
        manifest_parser.add_argument(f"--{argument}", required=True)
    manifest_parser.add_argument("--summary")
    manifest_parser.set_defaults(func=manifest)
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
