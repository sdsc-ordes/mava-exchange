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

# Safe only when data/ holds the raw sources to rebuild them (it does).
# (maintainers) Remove generated example OUTPUTS (corpus, clips).
clean:
    cd "{{root_dir}}" && rm -f examples/output/corpus.mediapkg examples/videos/*.mp4

# Idempotent: each step overwrites in place, so re-running is the safe "retry".
# (maintainers) Full rebuild: input -> clips -> corpus.
regenerate:
    cd "{{root_dir}}" && just examples::extract
    cd "{{root_dir}}" && just examples::cut-clips
    cd "{{root_dir}}" && just example
