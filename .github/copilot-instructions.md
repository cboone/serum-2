# GitHub Copilot Instructions for serum-2

For full project conventions, see AGENTS.md in the repository root.

## PR Review

- **Done plans are historical records**: Files in `docs/plans/done/` are completed plan documents preserved for reference. They may not match the final implementation. Do not flag discrepancies between done plan content and the actual codebase.
- **Tools are standalone scripts, not a package**: Every Python tool under `tools/` is a single executable script with a `uv run --script` shebang and a PEP 723 inline dependency block. Do not suggest adding a `pyproject.toml` or converting the repository into an installable package.
