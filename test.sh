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
output_file="/tmp/try_repo_test_output"

current_branch="$(git branch --show-current)"

# Check that we are not currently on a test branch
if [ "$current_branch" == "$valid_branch" ] || [ "$current_branch" == "$invalid_branch" ]; then
    echo "Cannot run qualification tests on one of the test branches. Please select a different branch name."
    exit 1
fi

# Arguments:
# 1) Commit message
# 2) Branch name
# 3) "Passed" or "Failed"
try_repo () {
    echo
    echo "==============================================================================="
    echo "Testing with commit message '$1' on branch '$2'"
    echo "==============================================================================="
    if [ ! -z "$2" ] && [ "$2" != "main" ]; then
        # It is easier to run these two commands and suppress errors than it is to test for conditions and avoid errors
        git switch -d "$current_branch" > /dev/null 2>&1
        git branch -d "$2" > /dev/null 2>&1 || true
        git checkout -b "$2" > /dev/null 2>&1 || true
    fi
    echo "$1" > "$commit_msg_file"
    # It is preferrable to redirect the output to a file using tee instead of a subshell output to a variable because tee prints progress to terminal
    pre-commit try-repo . github-issue-number --verbose --hook-stage commit-msg --commit-msg-filename "$commit_msg_file" | tee "$output_file" || true
    grep "$hook_name.*$3" "$output_file"
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
