"""Property-based roundtrip tests for the .mediapkg format.

Uses hypothesis to generate valid inputs, write them to a .mediapkg archive,
and verify that:
  1. validate_mediapkg() reports no errors (spec compliance)
  2. read_track() returns data matching what was written (roundtrip fidelity)

The oracle is validate_mediapkg() — the Python implementation of the MAVA format
spec. Any regression in writer.py or reader.py that violates the spec is caught
here without a human reading the diff.
"""
from __future__ import annotations

import pandas as pd
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mava_exchange import (
    AnnotationListSeries,
    AnnotationSeries,
    DimensionSpec,
    MediaPackageReader,
    MediaPackageWriter,
    ObservationSeries,
)
from mava_exchange.validate import validate_mediapkg

# ─────────────────────────────────────────────
# Reusable sub-strategies
# ─────────────────────────────────────────────

_track_name = st.from_regex(r"[a-z][a-z0-9_]{1,14}", fullmatch=True)
_dim_name = st.from_regex(r"[a-z][a-z0-9_]{1,12}", fullmatch=True)
_nonneg_float = st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
_value_float = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
_pos_duration = st.floats(min_value=0.001, max_value=50.0, allow_nan=False, allow_infinity=False)

_DEFAULT_SETTINGS = dict(
    max_examples=40,
    deadline=None,
    # tmp_path is function-scoped and shared across examples — safe here because
    # each example overwrites test.mediapkg before reading it back.
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)


# ─────────────────────────────────────────────
# Composite strategies
# ─────────────────────────────────────────────


@st.composite
def observation_series_with_data(draw: st.DrawFn) -> tuple[ObservationSeries, pd.DataFrame]:
    """Generate a valid ObservationSeries and a conforming DataFrame."""
    name = draw(_track_name)
    n_dims = draw(st.integers(min_value=1, max_value=4))
    dim_names = draw(st.lists(_dim_name, min_size=n_dims, max_size=n_dims, unique=True))
    dims = [DimensionSpec(name=d, description=f"Generated: {d}") for d in dim_names]

    n_rows = draw(st.integers(min_value=1, max_value=40))
    starts = sorted(draw(st.lists(_nonneg_float, min_size=n_rows, max_size=n_rows)))

    df_dict: dict[str, list] = {"start_seconds": starts}
    for d in dim_names:
        df_dict[d] = draw(st.lists(_value_float, min_size=n_rows, max_size=n_rows))

    track = ObservationSeries(name=name, description="Generated track", dimensions=dims)
    return track, pd.DataFrame(df_dict)


@st.composite
def annotation_series_with_data(draw: st.DrawFn) -> tuple[AnnotationSeries, pd.DataFrame]:
    """Generate a valid AnnotationSeries and a conforming DataFrame."""
    name = draw(_track_name)
    n_rows = draw(st.integers(min_value=1, max_value=30))

    starts = sorted(draw(st.lists(_nonneg_float, min_size=n_rows, max_size=n_rows)))
    durations = draw(st.lists(_pos_duration, min_size=n_rows, max_size=n_rows))
    ends = [s + d for s, d in zip(starts, durations)]
    labels = draw(st.lists(st.text(max_size=100), min_size=n_rows, max_size=n_rows))

    track = AnnotationSeries(name=name, description="Generated track")
    df = pd.DataFrame({"start_seconds": starts, "end_seconds": ends, "annotations": labels})
    return track, df


@st.composite
def annotation_list_series_with_data(draw: st.DrawFn) -> tuple[AnnotationListSeries, pd.DataFrame]:
    """Generate a valid AnnotationListSeries and a conforming DataFrame."""
    name = draw(_track_name)
    n_rows = draw(st.integers(min_value=1, max_value=20))

    starts = sorted(draw(st.lists(_nonneg_float, min_size=n_rows, max_size=n_rows)))
    durations = draw(st.lists(_pos_duration, min_size=n_rows, max_size=n_rows))
    ends = [s + d for s, d in zip(starts, durations)]
    tag_lists = draw(
        st.lists(
            st.lists(st.text(max_size=40), min_size=0, max_size=5),
            min_size=n_rows,
            max_size=n_rows,
        )
    )

    track = AnnotationListSeries(name=name, description="Generated track")
    df = pd.DataFrame({"start_seconds": starts, "end_seconds": ends, "annotations": tag_lists})
    return track, df


# ─────────────────────────────────────────────
# Properties: spec compliance (write → validate)
# ─────────────────────────────────────────────


@given(track_and_df=observation_series_with_data())
@settings(**_DEFAULT_SETTINGS)
def test_observation_series_roundtrip_clean(tmp_path, track_and_df):
    """Any valid ObservationSeries writes to a package that passes the validator."""
    track, df = track_and_df
    pkg = tmp_path / "test.mediapkg"
    with MediaPackageWriter(pkg, description="Roundtrip test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", track, df)
    result = validate_mediapkg(pkg)
    assert result.valid, result.summary()


@given(track_and_df=annotation_series_with_data())
@settings(**_DEFAULT_SETTINGS)
def test_annotation_series_roundtrip_clean(tmp_path, track_and_df):
    """Any valid AnnotationSeries writes to a package that passes the validator."""
    track, df = track_and_df
    pkg = tmp_path / "test.mediapkg"
    with MediaPackageWriter(pkg, description="Roundtrip test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", track, df)
    result = validate_mediapkg(pkg)
    assert result.valid, result.summary()


@given(track_and_df=annotation_list_series_with_data())
@settings(**_DEFAULT_SETTINGS)
def test_annotation_list_series_roundtrip_clean(tmp_path, track_and_df):
    """Any valid AnnotationListSeries writes to a package that passes the validator."""
    track, df = track_and_df
    pkg = tmp_path / "test.mediapkg"
    with MediaPackageWriter(pkg, description="Roundtrip test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", track, df)
    result = validate_mediapkg(pkg)
    assert result.valid, result.summary()


# ─────────────────────────────────────────────
# Properties: roundtrip fidelity (write → read)
# ─────────────────────────────────────────────


@given(track_and_df=observation_series_with_data())
@settings(**_DEFAULT_SETTINGS)
def test_observation_series_roundtrip_fidelity(tmp_path, track_and_df):
    """Data read back from .mediapkg matches what was written for ObservationSeries."""
    track, df = track_and_df
    pkg = tmp_path / "test.mediapkg"
    with MediaPackageWriter(pkg, description="Fidelity test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", track, df)
    with MediaPackageReader(pkg) as r:
        read_df = r.read_track("v001", track.name)
    pd.testing.assert_frame_equal(
        df[track.columns].reset_index(drop=True),
        read_df[track.columns].reset_index(drop=True),
    )


@given(track_and_df=annotation_series_with_data())
@settings(**_DEFAULT_SETTINGS)
def test_annotation_series_roundtrip_fidelity(tmp_path, track_and_df):
    """Data read back from .mediapkg matches what was written for AnnotationSeries."""
    track, df = track_and_df
    pkg = tmp_path / "test.mediapkg"
    with MediaPackageWriter(pkg, description="Fidelity test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", track, df)
    with MediaPackageReader(pkg) as r:
        read_df = r.read_track("v001", track.name)
    pd.testing.assert_frame_equal(
        df[track.columns].reset_index(drop=True),
        read_df[track.columns].reset_index(drop=True),
    )


# ─────────────────────────────────────────────
# Multi-video corpus
# ─────────────────────────────────────────────


@given(track_and_df=observation_series_with_data())
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_multi_video_corpus_roundtrip_clean(tmp_path, track_and_df):
    """Same track type across multiple videos produces a valid corpus package."""
    track, df = track_and_df
    pkg = tmp_path / "corpus.mediapkg"
    with MediaPackageWriter(pkg, description="Multi-video test") as w:
        w.add_video("v001", "https://example.org/v001.mp4")
        w.add_track("v001", track, df)
        w.add_video("v002", "https://example.org/v002.mp4")
        w.add_track("v002", track, df)
    result = validate_mediapkg(pkg)
    assert result.valid, result.summary()
