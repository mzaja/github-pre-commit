#!/bin/bash
set -e  # Exit on failure

# =====================================================================
# Run unit and integration tests
# =====================================================================
python -m unittest -b test.py

# =====================================================================
# Run qualification tests
# =====================================================================
hook_name="check GitHub issue number"
commit_msg_file=/tmp/COMMIT_MSG
valid_commit_msg="#2325 some msg"
valid_branch="2325-test-branch"
invalid_commit_msg="#123 msg"
invalid_branch="test-branch"

current_branch="$(git branch --show-current)"

# Check that we are not currently on a test branch
if [ "$current_branch" == "$valid_branch" ] || [ "$current_branch" == "$invalid_branch" ]; then
    echo "Cannot run qualification tests on one of the test branches. Please change the branch."
    exit 1
fi

# Runs the pre-commit hook using try-repo command and inspects the output for the expected result.
# Arguments:
# 1) Commit message
# 2) Branch name
# 3) "Passed" or "Failed"
try_repo () {
    # Safety mechanism to prevent deleting non-test branches
    if [ "$2" != "$valid_branch" ] && [ "$2" != "$invalid_branch" ]; then
        echo "Test branch must use one of the approved test branch names."
        exit 1
    fi
    echo
    echo "==============================================================================="
    echo "Testing with commit message '$1' on branch '$2'"
    echo "==============================================================================="
    git switch "$current_branch" > /dev/null 2>&1
    # It is easier to run these two commands and suppress errors than
    # it is to test for conditions and avoid errors
    git branch -d "$2" > /dev/null 2>&1 || true
    git switch -c "$2" > /dev/null 2>&1 || true
    echo "$1" > "$commit_msg_file"
    output="$(pre-commit try-repo . github-issue-number --verbose --color never \
            --hook-stage commit-msg --commit-msg-filename "$commit_msg_file" | tee /dev/tty || true)"
    echo "$output" | grep "$hook_name\.\+$3"
}

# Restore the original branch on script's exit and delete temp branches
cleanup () {
    git switch "$current_branch" > /dev/null 2>&1
    git branch -d "$valid_branch" > /dev/null 2>&1 || true
    git branch -d "$invalid_branch" > /dev/null 2>&1 || true
}
trap cleanup EXIT

try_repo "$valid_commit_msg" "$invalid_branch" "Failed"

try_repo "$invalid_commit_msg" "$valid_branch" "Failed"

try_repo "$valid_commit_msg" "$valid_branch" "Passed"
