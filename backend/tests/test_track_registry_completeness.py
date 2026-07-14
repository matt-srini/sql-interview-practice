"""Track-registry completeness — the CI backstop for the single-SoT model.

The mechanical per-track maps (module / count / label / db-topic / sample-file /
reasoning-class / interaction-mode) all DERIVE from the ``TRACKS`` registry, so they
cannot drift when a track is added. These tests guard the *remaining* hand-authored
per-track content — the single-track mock benchmark shape and the practice-page SEO
copy — so a new track that forgets one fails CI instead of silently degrading in prod.

See docs/track-onboarding.md § New-track integration surfaces.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tracks import TRACKS

ALL_SLUGS = {t.slug for t in TRACKS}


def test_every_track_has_a_single_track_benchmark_config():
    """Benchmark mode looks up BENCHMARK_CONFIGS[track]; a missing track 404s silently."""
    from routers.mock import BENCHMARK_CONFIGS

    missing = sorted(ALL_SLUGS - set(BENCHMARK_CONFIGS))
    assert not missing, (
        f"Tracks missing a single-track benchmark config in routers/mock.py "
        f"BENCHMARK_CONFIGS: {missing}. Add {{'num_questions': N, 'time_limit_s': N}} "
        f"per track (this is a per-track content map — it does not derive)."
    )


def test_every_track_has_a_practice_seo_description():
    """/practice/<slug> SEO meta comes from spa.py _PRACTICE_DESC; a missing track gets
    generic meta instead of its own description."""
    from routers.spa import _build_seo_meta

    meta = _build_seo_meta()
    missing = sorted(s for s in ALL_SLUGS if f"/practice/{s}" not in meta)
    assert not missing, (
        f"Tracks missing a /practice SEO description in routers/spa.py _PRACTICE_DESC: "
        f"{missing}. Add one, or the practice page falls back to generic meta."
    )
