set positional-arguments
set shell := ["bash", "-cue"]
root_dir := `git rev-parse --show-toplevel`
flake_dir := root_dir / "tools/nix"
output_dir := root_dir / ".output"
build_dir := output_dir / "build"

mod nix "./tools/just/nix.just"
mod changelog "./tools/just/changelog.just"

# Default target if you do not specify a target.
default:
    just --list --unsorted

# Enter the default Nix development shell and execute the command `"$@`.
develop *args:
    just nix::develop "default" "$@"

# Format the project.
format *args:
    "{{root_dir}}/tools/scripts/setup-config-files.sh"
    nix run --accept-flake-config {{flake_dir}}#treefmt -- "$@"

# Setup the project.
setup *args:
    cd "{{root_dir}}" && ./tools/scripts/setup.sh

# Run commands over the ci development shell.
ci *args:
    just nix::develop "ci" "$@"

# Lint the project.
[group('general')]
lint *args:
    uv run ruff check

# Build the project.
[group('general')]
build *args:
    uv build --out-dir "{{build_dir}}" "$@"

# Test the project (with coverage gate).
[group('general')]
test *args:
    uv run pytest --cov=mava_exchange --cov-report=term-missing --cov-fail-under=85 "$@"

# Type-check the project.
[group('general')]
typecheck *args:
    uv run mypy src/

# Audit dependencies for known vulnerabilities.
[group('general')]
audit *args:
    uv run pip-audit

# Run an executable.
[group('general')]
run *args:
    uv run cli "$@"

# Generate pyLODE documentation
[group('spec')]
pylode +args='':
    @echo "Generating pyLODE spec..."
    @uv run pylode {{args}} "{{root_dir}}/spec/mava.ttl" -o "{{root_dir}}/docs/_templates/mava.html" > /dev/null 2>&1
    @echo "✅ HTML successfully generated at: {{root_dir}}/docs/_templates/mava.html"

# Build the .mediapkg corpus from the committed example inputs.
[group('usage')]
example:
    uv run examples/scripts/build_mediapkg.py

# (maintainers) Regenerate examples/input/ from the raw exports in data/ (gitignored).
[group('data')]
extract-examples:
    uv run tools/scripts/extract_segment.py
    just format examples/input

# Serve the standalone .mediapkg viewer locally (needs internet for CDN libs).
[group('usage')]
viewer port="8000":
    @echo "Viewer → http://localhost:{{port}}/  (drop in examples/output/corpus.mediapkg)"
    python3 -m http.server -d docs/_static/viewer-app {{port}}

# Inspect a .mediapkg archive.
# Usage:
#   just inspect examples/output/corpus.mediapkg
#   just inspect path/to/corpus.mediapkg --track emotions --video video_001
[group('usage')]
inspect pkg *args:
    mediapkg-inspect "{{pkg}}" {{args}}

# Export manifest as Turtle RDF.
[group('usage')]
inspect-turtle pkg="examples/output/corpus.mediapkg":
    mediapkg-inspect "{{pkg}}" --format turtle

# Export manifest as JSON-LD.
[group('usage')]
inspect-jsonld pkg="examples/output/corpus.mediapkg":
    mediapkg-inspect "{{pkg}}" --format json-ld

# Validate a .mediapkg archive.
# Usage:
#   just validate examples/output/corpus.mediapkg
#   just validate path/to/corpus.mediapkg --strict
[group('usage')]
validate pkg *args:
    mediapkg-validate "{{pkg}}" {{args}}

# Build the HTML documentation
[group('docs')]
build-docs: pylode
    sphinx-build -b html docs .output/docs

# Remove the build directory for a fresh start
[group('docs')]
clean-docs:
    rm -rf .output/docs

# Watch for changes and rebuild (requires 'sphinx-autobuild' pip package)
[group('docs')]
watch:
    sphinx-autobuild docs/source docs/build/html
