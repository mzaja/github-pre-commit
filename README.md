# github-pre-commit
A pre-commit hook for checking commits against GitHub conventions. Ensures that branches and commits are linked against the corresponding GitHub issues.

- Branch name must being with a GitHub issue number, followed by a dash. Example: `123-my-branch-name`.
- A commit message must include a GitHub issue number preceeded by `#`. Example: `#123 my commit message`.

This hook does not check whether the issue number actually exists in the repository, only that the branch name and the commit message satisfy the conventions.

## Installation
To use this hook in your project, add the following entry to `repos` section inside `.pre-commit.config.yaml` file:
```yml
  - repo: https://github.com/mzaja/github-pre-commit
    rev: v1.0.0
    hooks:
      - id: github-issue-number
        args: []  # Optional arguments to provide to the hook
```

## Usage
By default, this hook will abort the commit if:
1. The branch name does not begin with a number followed by a dash.
2. The commit message does not include a hash sign followed by a number.
3. The commit message contains more than one hash sign followed by a number.
4. The issue number in the commit message does not match the issue number in the branch name. 

### Optional arguments
The hook's behaviour can be further customised using the following optional arguments:

- `-x PATTERN`, `--exclude-branches PATTERN`: A regex pattern of branch names to exclude from the branch name check. This is useful when committing directly to the main branch, as is often the case on single-developer projects. Can be provided more than once.
- `--multi-issue-commits`: Allows referencing more than one issue number in a single commit message. One of the issue numbers must correspond to the branch issue number, unless that branch is excluded by the regex pattern.
- `--auto-prepend`: Automatically inserts the GitHub issue number, taken from the branch name, at the beginning of the commit message.
- `--auto-append`: Automatically inserts the GitHub issue number, taken from the branch name, at the end of the commit message.
