set positional-arguments
set shell := ["bash", "-cue"]
root_dir := `git rev-parse --show-toplevel`
flake_dir := root_dir / "tools/nix"
output_dir := root_dir / ".output"
build_dir := output_dir / "build"

mod nix "./tools/just/nix.just"
mod changelog "./tools/just/changelog.just"
mod examples "./tools/just/examples.just"

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

# Serve the standalone .mediapkg viewer locally (needs internet for CDN libs).
[group('usage')]
viewer port="8000":
    @echo "Viewer → http://localhost:{{port}}/  (drop in examples/output/corpus.mediapkg)"
    python3 -m http.server -d docs/_static/viewer-app {{port}}

# Unpack a .mediapkg (ZIP) into a dir; optional 3rd arg (turtle|json-ld) also renders the manifest as RDF.
[group('usage')]
unpack pkg dir format="":
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p "{{dir}}"
    unzip -o -q "{{pkg}}" -d "{{dir}}"
    echo "Unpacked {{pkg}} → {{dir}}/"
    if [ -n "{{format}}" ]; then
        ext="ttl"; [ "{{format}}" = "json-ld" ] && ext="jsonld"
        uv run mediapkg-inspect "{{pkg}}" --format "{{format}}" > "{{dir}}/manifest.$ext"
        echo "Rendered {{dir}}/manifest.$ext"
    fi

# Pack a directory (manifest.json at its root) into a .mediapkg and validate it.
[group('usage')]
pack dir pkg:
    #!/usr/bin/env bash
    set -euo pipefail
    test -f "{{dir}}/manifest.json" || { echo "✗ {{dir}}/manifest.json not found (it must sit at the archive root)"; exit 1; }
    out="$(cd "$(dirname "{{pkg}}")" && pwd)/$(basename "{{pkg}}")"
    rm -f "$out"
    ( cd "{{dir}}" && zip -q -r -X "$out" . -x '*.ttl' '*.jsonld' '*.DS_Store' )
    echo "Packed {{dir}}/ → {{pkg}}"
    uv run mediapkg-validate "{{pkg}}"

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

# Build the docs (in the dev shell) and serve them locally at the given port.
[group('docs')]
serve-docs port="8000":
    #!/usr/bin/env bash
    set -euo pipefail
    if python3 -c "import socket,sys; s=socket.socket(); r=s.connect_ex(('127.0.0.1',{{port}})); s.close(); sys.exit(0 if r==0 else 1)"; then
        echo "⚠  Port {{port}} is already in use — a server may already be running there."
        echo "   Use another port, e.g.:  just serve-docs $(({{port}}+1))"
        exit 1
    fi
    just develop just build-docs
    echo "Docs → http://localhost:{{port}}/"
    python3 -m http.server -d .output/docs "{{port}}"
