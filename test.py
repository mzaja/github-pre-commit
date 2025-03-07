import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Tuple
from unittest import TestCase, mock

import hook
from hook import (
    BranchNameError,
    CommitMessageError,
    get_issue_number_from_branch_name,
    get_issue_numbers_from_commit_message,
)


class HookUnitTest(TestCase):
    """Unit tests for the hook."""

    def test_get_issue_number_from_branch_name(self):
        """Tests retrieving the GitHub issue number from the branch name."""
        # Invalid branch names
        for branch_name in [
            "branch-name",  # No number
            "-branch-name",  # No number
            "3x-branch-name",  # Contains a non-digit
            " 31-branch name",  # Begins with whitespace
            "branch-name-31",  # Number in the wrong place
        ]:
            with self.subTest(branch_name=branch_name):
                self.assertIsNone(get_issue_number_from_branch_name(branch_name))

        # Valid branch name
        self.assertEqual(get_issue_number_from_branch_name("31-branch-name"), "31")

    def test_get_issue_numbers_from_commit_message(self):
        """Tests extracting GitHub issue numbers from the commit message."""
        for commit_msg, issue_numbers in [
            ("#31 msg", ["31"]),
            ("  #31 msg  ", ["31"]),
            ("#31, #24 msg", ["31", "24"]),
            ("#31 msg", ["31"]),
            ("msg #31", ["31"]),
            ("msg", []),
            ("", []),
        ]:
            with self.subTest(commit_msg=commit_msg):
                self.assertEqual(
                    get_issue_numbers_from_commit_message(commit_msg), issue_numbers
                )


class HookIntegrationTests(TestCase):
    """Integration tests for the hook."""

    def setUp(self) -> None:
        self._original_sys_argv = sys.argv

    def tearDown(self) -> None:
        sys.argv = self._original_sys_argv

    def call_hook(
        self, branch_name: str, commit_msg: str, *args: str
    ) -> Tuple[int, str]:
        """
        Calls the hook with a custom commit message stored in a file
        and optional arguments.

        Returns the original or modified commit message.
        """
        tmpfile = NamedTemporaryFile("w", delete=False)
        try:
            tmpfile.write(commit_msg)
            tmpfile.close()
            with mock.patch("hook.main.get_branch_name") as mock_get_branch_name:
                mock_get_branch_name.return_value = branch_name
                # pre-commit inserts all the args hooks before the commit file name
                # This is a very important distinction when using options accepting
                # multiple arguments. If this is provided as the last option,
                sys.argv = [hook.__name__] + list(args) + [str(tmpfile.name)]
                stderr_buffer = StringIO()
                with (
                    self.assertRaises(SystemExit) as ctx,
                    redirect_stderr(stderr_buffer),
                ):
                    hook.main()
                self.error_code = ctx.exception.code
                self.commit_msg = Path(tmpfile.name).read_text()
                self.stderr = stderr_buffer.getvalue()
        finally:
            tmpfile.close()
            Path(tmpfile.name).unlink()

    def test_basic_successful_case(self):
        """Basic case of successful validation - branch and commit numbers match."""
        commit_msg = "#31 msg"
        self.call_hook("31-brunch", commit_msg)
        self.assertEqual(self.error_code, 0)
        self.assertEqual(self.commit_msg, commit_msg)

    def test_branch_name_validation(self):
        """Tests validating the branch name."""
        commit_msg = "#31 msg"  # valid commit message

        # Missing the issue number
        self.call_hook("main", commit_msg)
        self.assertEqual(self.error_code, BranchNameError.exit_code)

        # Number in the wrong position
        self.call_hook("brunch-31", commit_msg)
        self.assertEqual(self.error_code, BranchNameError.exit_code)

        # Branch excluded by exact name
        self.call_hook("main", commit_msg, "--exclude-branches", "main")
        self.assertEqual(self.error_code, 0)

        # Branch excluded by one of the regexes
        self.call_hook("master", commit_msg, "-x", "main", "-x", ".*ter$")
        self.assertEqual(self.error_code, 0)

        # Branch not excluded by regex
        self.call_hook("main", commit_msg, "--exclude-branches", "master")
        self.assertEqual(self.error_code, BranchNameError.exit_code)

    def test_branch_and_message_issue_numbers_mismatch(self):
        """Tests the mismatch between branch and commit message issue numbers."""
        self.call_hook("29-brunch", "#31 msg")
        self.assertEqual(self.error_code, CommitMessageError.exit_code)

    def test_multi_issue_commit_messages(self):
        """Tests the multi-issue commit message feature."""
        branch_name = "29-brunch"
        commit_msg = "#31 msg #29"

        # Multi-issue commit messages are not allowed by default
        self.call_hook(branch_name, commit_msg)
        self.assertEqual(self.error_code, CommitMessageError.exit_code)

        # However, the feature can be enabled with a switch
        self.call_hook(branch_name, commit_msg, "--multi-issue-commits")
        self.assertEqual(self.error_code, 0)

    def test_auto_prepend_or_append(self):
        """
        Tests automatically adding the issue number
        to the commit message if it is missing.
        """
        FLAGS = ("--auto-prepend", "--auto-append")
        branch_name = "29-brunch"

        # Message with the correct issue number - no change
        for flag in FLAGS:
            for commit_msg in ["#29 msg", "msg #29"]:
                self.call_hook(branch_name, commit_msg, flag)
                self.assertEqual(self.error_code, 0)
                self.assertEqual(self.commit_msg, commit_msg)  # No change

        # Message without the issue number - take from the branch and add
        commit_msg = "msg"
        self.call_hook(branch_name, commit_msg, "--auto-prepend")
        self.assertEqual(self.error_code, 0)
        self.assertEqual(self.commit_msg, "#29 " + commit_msg)
        self.call_hook(branch_name, commit_msg, "--auto-append")
        self.assertEqual(self.error_code, 0)
        self.assertEqual(self.commit_msg, commit_msg + " #29")

        # Branch does not contain the issue number
        for flag in FLAGS:
            self.call_hook("main", "msg", flag)
            self.assertEqual(self.error_code, BranchNameError.exit_code)

        # Commit message already contains another issue number
        for flag in FLAGS:
            self.call_hook(branch_name, "#31 msg", flag)
            self.assertEqual(self.error_code, CommitMessageError.exit_code)

        # Commit message already contains another issue number and allows multi-issue commits
        for flag in FLAGS:
            self.call_hook(branch_name, "#31 msg", flag, "--multi-issue-commits")
            self.assertEqual(self.error_code, 0)


if __name__ == "__main__":
    unittest.main(buffer=True)
