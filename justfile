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

# Test the project.
[group('general')]
test *args:
   uv run pytest "$@"

# Run an executable.
[group('general')]
run *args:
    uv run cli "$@"

# Run the Jupyter notebook.
[group('general')]
notebook *args:
    uv run python -m notebook "$@"

# Generate pyLODE documentation
[group('spec')]
pylode +args='':
    @echo "Generating pyLODE spec..."
    @uv run pylode {{args}} "{{root_dir}}/spec/mava.ttl" -o "{{root_dir}}/spec/html/mava.html" > /dev/null 2>&1
    @echo "✅ HTML successfully generated at: {{root_dir}}/spec/html/mava.html"

# Build and then serve the documentation locally
[group('spec')]
preview: pylode
    @echo "Starting private server at http://localhost:8000/mava.html"
    @echo "Press Ctrl+C to stop."
    @# Automatically open the browser (works on macOS)
    @open "http://localhost:8000/mava.html"
    @python3 -m http.server 8000 --directory "{{root_dir}}/spec/html"

# Build a .mediapkg from the example TSV files.
[group('usage')]
example:
    uv run examples/tsv_to_mediapkg.py

# Inspect a .mediapkg archive.
# Usage: (default example corpus)
#   just inspect
#   just inspect path/to/corpus.mediapkg
#   just inspect path/to/corpus.mediapkg --track emotions --video video_001
[group('usage')]
inspect pkg="examples/output/corpus.mediapkg" *args:
    mediapkg-inspect "{{pkg}}" {{args}}

# Validate a .mediapkg archive.
# Usage: (default example corpus)
#   just validate
#   just validate path/to/corpus.mediapkg
#   just validate path/to/corpus.mediapkg --strict
[group('usage')]
validate pkg="examples/output/corpus.mediapkg" *args:
    mediapkg-validate "{{pkg}}" {{args}}
