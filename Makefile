# serum-2
#
# The tools here are standalone PEP 723 scripts, so there is no build step and
# no dependency install: `uv run` resolves each script's dependencies from its
# own inline metadata.

RUFF_VERSION := 0.16.5

.PHONY: node-tools lint fmt fmt-fix text-lint text-fix check help git-setup test-scrut

lint: ## Run ruff lint
	uvx ruff@$(RUFF_VERSION) check .

fmt: ## Check Python formatting
	uvx ruff@$(RUFF_VERSION) format --check .

fmt-fix: ## Apply ruff formatting and safe lint fixes
	uvx ruff@$(RUFF_VERSION) format .
	uvx ruff@$(RUFF_VERSION) check --fix .

node-tools: node_modules ## Install the pinned text linters

node_modules: package-lock.json
	npm ci --ignore-scripts --include=dev --no-audit --no-fund
	@touch node_modules

# The text linters run from node_modules rather than whatever is on PATH, so
# these match CI. CI installs the same package-lock.json.
text-lint: node-tools ## Run markdownlint, Prettier and cspell checks
	npm run --silent lint:md
	npm run --silent format:check
	npm run --silent spell

text-fix: node-tools ## Apply Prettier formatting and markdownlint fixes
	npm run --silent format:write
	npm run --silent lint:md:fix
	npm run --silent format:write

check: lint fmt text-lint test-scrut ## Run every check

test-scrut: ## Run scrut CLI tests
	@command -v scrut >/dev/null 2>&1 || { echo "scrut not installed. See https://github.com/facebookincubator/scrut"; exit 1; }
	REPO_ROOT="$(CURDIR)" scrut test tests/scrut/

git-setup: ## Decode Serum presets and curves in git diff (run once per clone)
	git config diff.serum.textconv "tools/serumfile.py dump"
	git config diff.serum.cachetextconv true

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
