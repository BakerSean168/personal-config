from __future__ import annotations

import unittest

import configctl


class PersonalConfigCompositionTests(unittest.TestCase):
    def test_catalog_and_profiles_validate(self) -> None:
        self.assertEqual(configctl.validate_all(), [])

    def test_composed_profiles_have_no_manual_install_steps(self) -> None:
        for profile_name, platform in (
            ("vps-minimal", "linux"),
            ("linux-dev", "linux"),
            ("wsl-dev", "wsl"),
            ("windows-main", "windows"),
        ):
            rows = configctl.plan_rows(profile_name, platform)
            self.assertTrue(rows)
            self.assertNotIn("manual", {row["install"] for row in rows})

    def test_windows_profile_delegates_rime_to_repository_owned_installer(self) -> None:
        rows = {row["id"]: row for row in configctl.plan_rows("windows-main", "windows")}
        self.assertEqual(rows["rime"]["install"], "& './install.ps1'")
        self.assertEqual(rows["ssh-client"]["install"], "& './install.ps1' -Profile windows-primary")
        self.assertEqual(rows["nvim"]["install"], "none")


if __name__ == "__main__":
    unittest.main()
