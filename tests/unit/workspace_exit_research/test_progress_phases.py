from app.workspace_exit_research.progress import (
    persistence_percent_complete,
    simulation_percent_complete,
)


def test_simulation_percent_never_reaches_100_before_completion():
    assert simulation_percent_complete(25757, 25757) == 90.0
    assert simulation_percent_complete(100, 25757) < 90.0
    assert simulation_percent_complete(0, 25757) == 0.0


def test_persistence_percent_starts_at_floor_and_reaches_100():
    assert persistence_percent_complete(0, 900) == 90.0
    assert persistence_percent_complete(450, 900) == 95.0
    assert persistence_percent_complete(900, 900) == 100.0
