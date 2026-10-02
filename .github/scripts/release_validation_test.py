"""Regression tests for release scheme transitions and built artifact checks."""

import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import release_validation as validation


class ReleaseValidationTest(unittest.TestCase):
    def setUp(self):
        self.expected = validation.product_version("0.2.1")
        self.header = '\n'.join((
            'inline constexpr char kProductVersion[] = "0.2.1";',
            'inline constexpr char kMsiProductVersion[] = "100.2.1";',
            'inline constexpr char kProductReleaseTag[] = "v0.2.1";',
        ))
        self.msi = {
            "product_version": "100.2.1",
            "upgrade_code": "{" + validation.UPGRADE_CODE + "}",
            "product_name": "mozc-date",
            "manufacturer": "mozc-date Project",
            "publisher": "mozc-date Project",
            "files": [{"name": name, "version": "100.2.1.0"} for name in sorted(validation.INSTALLED_BINARIES)],
            "pe_files": [{"name": name, "file_version": "100.2.1.0", "product_version": "100.2.1.0"}
                         for name in sorted(validation.INSTALLED_BINARIES | {"mozc_installer_helper.dll"})],
        }

    def test_migration_from_all_legacy_releases(self):
        self.assertEqual(validation.check_release_order("v0.2.1", [
            "v3.34.6239.100", "v3.34.6239.104", "v4.0.0.0"
        ]), self.expected)

    def test_msi_major_is_offset_from_product_major(self):
        self.assertEqual(validation.product_version("1.2.3")["msi_version"], "101.2.3")

    def test_new_release_must_advance_past_every_published_version(self):
        for previous in ("v0.2.1", "v0.2.2", "v0.3.0", "v1.0.0"):
            with self.subTest(previous=previous), self.assertRaises(ValueError):
                validation.check_release_order("v0.2.1", ["v4.0.0.0", previous])

    def test_new_release_order_after_transition(self):
        self.assertEqual(validation.check_release_order("v0.2.1", ["v0.2.0"]), self.expected)

    def test_tag_requires_three_canonical_components(self):
        for tag in ("v4.0.0.0", "0.2.1", "v0.2", "v0.2.1-rc1", "v0.02.1", "v0.2.1\n", "v0.٢.1", "v０.2.1"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                validation.release_version(tag)

    def test_unknown_published_tag_requires_explicit_migration_policy(self):
        with self.assertRaises(ValueError):
            validation.check_release_order("v0.2.1", ["v5.0.0.0"])

    def test_msi_field_bounds(self):
        self.assertEqual(validation.product_version("155.255.65535")["msi_version"], "255.255.65535")
        for version in ("156.0.0", "0.256.0", "0.0.65536"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validation.product_version(version)

    def test_built_artifacts_agree(self):
        validation.check_generated_versions(self.expected, self.expected, self.header, self.msi)

    def test_generated_json_cannot_use_engine_version_or_wrong_tag(self):
        for key, value in (("product_version", "3.34.6239.104"), ("msi_version", "0.2.1"), ("release_tag", "v4.0.0.0")):
            generated = dict(self.expected, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validation.check_generated_versions(self.expected, generated, self.header, self.msi)

    def test_about_header_cannot_retain_old_product_version(self):
        with self.assertRaises(ValueError):
            validation.check_generated_versions(self.expected, self.expected, self.header.replace('"0.2.1"', '"4.0.0.0"'), self.msi)

    def test_msi_properties_must_match_product_policy(self):
        for key, value in (("product_version", "0.2.1"), ("upgrade_code", "C1A818AF-6EC9-49EF-ADCF-35A40475D156"), ("product_name", "Mozc"), ("publisher", "Google LLC")):
            metadata = dict(self.msi, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validation.check_generated_versions(self.expected, self.expected, self.header, metadata)

    def test_old_engine_pe_versions_cannot_pass_upgrade_verification(self):
        for field in ("file_version", "product_version"):
            metadata = copy.deepcopy(self.msi)
            metadata["pe_files"][0][field] = "3.34.6239.104"
            with self.subTest(field=field), self.assertRaises(ValueError):
                validation.check_generated_versions(self.expected, self.expected, self.header, metadata)

    def test_msi_file_table_must_preserve_new_pe_version(self):
        metadata = copy.deepcopy(self.msi)
        metadata["files"][0]["version"] = "4.0.0.0"
        with self.assertRaises(ValueError):
            validation.check_generated_versions(self.expected, self.expected, self.header, metadata)

    def test_missing_binary_evidence_fails(self):
        for field in ("files", "pe_files"):
            metadata = copy.deepcopy(self.msi)
            metadata[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                validation.check_generated_versions(self.expected, self.expected, self.header, metadata)

    def test_duplicate_binary_evidence_cannot_hide_different_versions(self):
        for field in ("files", "pe_files"):
            metadata = copy.deepcopy(self.msi)
            duplicate = copy.deepcopy(metadata[field][0])
            duplicate["name"] = duplicate["name"].upper()
            metadata[field].append(duplicate)
            with self.subTest(field=field), self.assertRaises(ValueError):
                validation.check_generated_versions(self.expected, self.expected, self.header, metadata)

    def test_configuration_supplies_product_env_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "version.txt").write_text("0.0.0\n", encoding="utf-8")
            args = SimpleNamespace(tag="", previous_tags=None, version_file=root / "version.txt",
                                   env_file=root / "env", output=root / "version.json",
                                   test_targets=root / "targets.json", pe_targets=root / "pe.json")
            validation.configure(args)
            self.assertEqual((root / "env").read_text(), "MOZC_DATE_PRODUCT_VERSION=0.0.0\n")
            self.assertEqual(validation.read_json(root / "targets.json"), list(validation.TEST_TARGETS))

    def test_manifest_refuses_unverified_feature_target_or_wrong_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            validation.write_json(root / "expected.json", self.expected)
            validation.write_json(root / "targets.json", list(validation.TEST_TARGETS[:-1]))
            args = SimpleNamespace(expected=root / "expected.json", test_targets=root / "targets.json",
                                   commit="a" * 40, expected_commit="a" * 40)
            with self.assertRaises(ValueError):
                validation.manifest(args)
            validation.write_json(root / "targets.json", list(validation.TEST_TARGETS))
            args.expected_commit = "b" * 40
            with self.assertRaises(ValueError):
                validation.manifest(args)


if __name__ == "__main__":
    unittest.main()
