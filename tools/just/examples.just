set positional-arguments
set shell := ["bash", "-cue"]

root_dir := `git rev-parse --show-toplevel`

default:
    just --list --unsorted -f "{{source_file()}}"

# (maintainers) Regenerate examples/input/ from the raw exports in data/ (gitignored).
extract:
    cd "{{root_dir}}" && uv run tools/scripts/extract_segment.py
    cd "{{root_dir}}" && just format examples/input

# (maintainers) Cut the short demo clips (examples/videos/) from raw sources in data/.
cut-clips:
    cd "{{root_dir}}" && uv run tools/scripts/cut_clips.py

# (maintainers) Regenerate the committed inspect RDF snapshots from the corpus.
snapshots pkg="examples/output/corpus.mediapkg":
    cd "{{root_dir}}" && uv run mediapkg-inspect "{{pkg}}" --format turtle  > examples/output/inspect/corpus.mediapkg.ttl
    cd "{{root_dir}}" && uv run mediapkg-inspect "{{pkg}}" --format json-ld > examples/output/inspect/corpus.mediapkg.jsonld

# Safe only when data/ holds the raw sources to rebuild them (it does).
# (maintainers) Remove generated example OUTPUTS (corpus, inspect RDF, clips).
clean:
    cd "{{root_dir}}" && rm -f examples/output/corpus.mediapkg examples/output/inspect/corpus.mediapkg.ttl examples/output/inspect/corpus.mediapkg.jsonld examples/videos/*.mp4

# Idempotent: each step overwrites in place, so re-running is the safe "retry".
# (maintainers) Full rebuild: input -> clips -> corpus -> inspect RDF.
regenerate:
    cd "{{root_dir}}" && just examples::extract
    cd "{{root_dir}}" && just examples::cut-clips
    cd "{{root_dir}}" && just example
    cd "{{root_dir}}" && just examples::snapshots
