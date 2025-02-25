"""
This pre-commit hook checks that the branch name and commit messages
satisfy GitHub conventions which link the branches and commits to 
tickets on GitHub Issues.

Flags:
    --exclude-branches [patterns]: Regex patterns to exclude branches from branch name validations.
    --multi-issue-commits: Allows specifying more than one GitHub issue number per commit.
    --auto-prepend: Automatically prepend the issue number from the branch name to the commit message.
    --auto-append: Automatically append the issue number from the branch name to the commit message.
"""

import re
from argparse import ArgumentParser
from pathlib import Path
from subprocess import check_output
from typing import List, Optional


# ---------------------------------------------------------------------------
# EXCEPTIONS
# ---------------------------------------------------------------------------
class GitHookError(Exception):
    """Base exception for the package."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BranchNameError(GitHookError):
    """Raised when there is a problem with the branch name."""

    exit_code = 1

    def __init__(self, message: str):
        super().__init__(message)


class CommitMessageError(GitHookError):
    """Raised when there is a problem with the commit message."""

    exit_code = 2

    def __init__(self, message: str):
        super().__init__(message)


# ---------------------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------------------
def get_branch_name() -> str:
    """Returns the name of the current git branch."""
    # From: https://stackoverflow.com/a/6245587
    return check_output("git rev-parse --abbrev-ref HEAD", shell=True).decode().strip()


def get_issue_number_from_branch_name(branch_name: str) -> Optional[str]:
    """
    Returns the GitHub issue number extracted from the branch name. If the
    number cannot be extracted, returns None.

    The branch name is expected to start with a number, followed by a dash.
    """
    result = re.match(r"^(\d+)-", branch_name)
    return result.group(1) if result else None


def get_issue_numbers_from_commit_message(commit_msg: str) -> List[str]:
    """
    Returns all issue numbers extracted from the commit message.
    Numbers must be preceded by a hash symbol.
    """
    return re.findall(r"#(\d+)", commit_msg)


def create_parser() -> ArgumentParser:
    """Creates and returns the argument parser."""
    parser = ArgumentParser(
        description="Validates GitHub's branch naming and commit message conventions"
    )
    parser.add_argument(
        "commit_msg_file",
        type=Path,
        help="Path to the file containing the git commit message.",
    )
    parser.add_argument(
        "--exclude-branches",
        dest="exclude_branches_regexes",
        action="extend",
        nargs="+",
        default=[],
        help="A list of regex patterns identifying which branches to exclude from the branch name checks.",
    )
    parser.add_argument(
        "--multi-issue-commits",
        action="store_true",
        help="Commit message can reference more than one GitHub issue.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--auto-prepend",
        action="store_true",
        help="Prepends the GitHub issue number to the commit message if one is not provided.",
    )
    group.add_argument(
        "--auto-append",
        action="store_true",
        help="Appends the GitHub issue number to the commit message if one is not provided.",
    )
    return parser


def main():
    """Main function. Entry point for the script."""
    parser = create_parser()
    args = parser.parse_args()
    branch_name = get_branch_name()
    branch_issue_number = None
    branch_name_excluded_from_checks = any(
        re.match(pattern, branch_name) for pattern in args.exclude_branches_regexes
    )
    try:
        # Check that the branch starts with the GitHub issue number, unless listed as excluded
        if not branch_name_excluded_from_checks:
            branch_issue_number = get_issue_number_from_branch_name(branch_name)
            if branch_issue_number is None:
                raise BranchNameError(
                    "Branch name must start with a GitHub issue number followed by a dash."
                )

        commit_msg = args.commit_msg_file.read_text()
        message_issue_numbers = get_issue_numbers_from_commit_message(commit_msg)

        # Check that only one issue is referenced in the commit message unless permitted otherwise
        if (not args.multi_issue_commits) and (len(message_issue_numbers) > 1):
            raise CommitMessageError(
                "Commit message contains more than one issue number. "
                "Use '--multi-issue-commits' option if you wish to permit this behaviour."
            )

        # Check whether the branch issue number is provided in the commit message
        if branch_issue_number not in message_issue_numbers:
            if args.auto_prepend or args.auto_append:
                # Issue number is missing from the commit message, so we shall add it
                if not branch_issue_number:
                    # No issue number to insert
                    prepend_option = "prepend" if args.auto_prepend else "append"
                    raise BranchNameError(
                        f"Auto-{prepend_option}ing the GitHub issue number to the commit message is enabled,"
                        " but the current branch does not begin with a number."
                    )
                elif message_issue_numbers and not args.multi_issue_commits:
                    # Branch contains the issue number, but we already have a different number
                    # in the commit message.
                    # Adding the branch number to the message would break the one-issue-per-commit rule.
                    raise CommitMessageError(
                        "Cannot add a GitHub issue number to the commit message because "
                        "the message already contains another issue number."
                    )
                else:
                    # If this point is reached, branch contains the issue number while the commit
                    # message does not. It is safe to insert the issue number into the message.
                    if args.auto_prepend:
                        Path(args.commit_msg_file).write_text(
                            f"#{branch_issue_number} {commit_msg}"
                        )
                    elif args.auto_append:
                        args.commit_msg_file.write_text(
                            f"{commit_msg} #{branch_issue_number}"
                        )
            else:
                # Auto-inserting the issue number into the commit messafe is off
                if message_issue_numbers:
                    if not branch_name_excluded_from_checks:
                        # Issue numbers are provided in the commit message, but for the wrong branch
                        raise CommitMessageError(
                            "Commit message's issue number(s) do not match the branch's issue number."
                        )
                else:
                    # No
                    raise CommitMessageError(
                        "Commit message does not contain the GitHub issue number. "
                        "Did you prepend it with '#'?"
                    )

    except GitHookError as ex:
        print(ex.message)
        exit(ex.exit_code)

    return exit(0)  # All validations have passed if this point is reached


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
