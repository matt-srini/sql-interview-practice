from questions import get_questions_by_difficulty
from unlock import compute_unlock_state, get_next_questions


def _ids(difficulty: str, count: int) -> set[int]:
    questions = get_questions_by_difficulty()[difficulty]
    return {int(question["id"]) for question in questions[:count]}


def test_free_plan_unlocks_only_easy_at_start() -> None:
    catalog = get_questions_by_difficulty()
    unlock_state = compute_unlock_state("free", set(), catalog)
    next_questions = get_next_questions(unlock_state, catalog)

    assert all(unlock_state[int(question["id"])] == "unlocked" for question in catalog["easy"])
    assert all(unlock_state[int(question["id"])] == "locked" for question in catalog["medium"])
    assert all(unlock_state[int(question["id"])] == "locked" for question in catalog["hard"])
    assert next_questions == {
        "easy": int(catalog["easy"][0]["id"]),
        "medium": None,
        "hard": None,
    }


def test_free_plan_unlocks_three_medium_after_ten_easy() -> None:
    catalog = get_questions_by_difficulty()
    unlock_state = compute_unlock_state("free", _ids("easy", 10), catalog)

    assert [unlock_state[int(question["id"])] for question in catalog["medium"][:3]] == ["unlocked"] * 3
    assert unlock_state[int(catalog["medium"][3]["id"])] == "locked"


def test_free_plan_unlocks_eight_medium_after_twenty_easy() -> None:
    catalog = get_questions_by_difficulty()
    unlock_state = compute_unlock_state("free", _ids("easy", 20), catalog)

    assert [unlock_state[int(question["id"])] for question in catalog["medium"][:8]] == ["unlocked"] * 8
    assert unlock_state[int(catalog["medium"][8]["id"])] == "locked"


def test_free_plan_unlocks_all_medium_after_thirty_easy() -> None:
    catalog = get_questions_by_difficulty()
    unlock_state = compute_unlock_state("free", _ids("easy", 30), catalog)

    assert all(unlock_state[int(question["id"])] == "unlocked" for question in catalog["medium"])


def test_free_plan_unlocks_three_hard_after_ten_medium() -> None:
    catalog = get_questions_by_difficulty()
    solved_ids = _ids("easy", 30) | _ids("medium", 10)
    unlock_state = compute_unlock_state("free", solved_ids, catalog)

    assert [unlock_state[int(question["id"])] for question in catalog["hard"][:3]] == ["unlocked"] * 3
    assert unlock_state[int(catalog["hard"][3]["id"])] == "locked"


def test_free_plan_caps_hard_unlocks_at_fifteen() -> None:
    catalog = get_questions_by_difficulty()
    solved_ids = _ids("easy", 30) | _ids("medium", 30)
    unlock_state = compute_unlock_state("free", solved_ids, catalog)

    assert [unlock_state[int(question["id"])] for question in catalog["hard"][:15]] == ["unlocked"] * 15
    assert unlock_state[int(catalog["hard"][15]["id"])] == "locked"


def test_pro_plan_unlocks_all_easy_medium_and_twenty_two_hard() -> None:
    catalog = get_questions_by_difficulty()
    unlock_state = compute_unlock_state("pro", set(), catalog)

    assert all(unlock_state[int(question["id"])] == "unlocked" for question in catalog["easy"])
    assert all(unlock_state[int(question["id"])] == "unlocked" for question in catalog["medium"])
    assert [unlock_state[int(question["id"])] for question in catalog["hard"][:22]] == ["unlocked"] * 22
    assert all(unlock_state[int(question["id"])] == "locked" for question in catalog["hard"][22:])


def test_elite_plan_unlocks_everything() -> None:
    catalog = get_questions_by_difficulty()
    unlock_state = compute_unlock_state("elite", set(), catalog)

    for difficulty in ("easy", "medium", "hard"):
        assert all(unlock_state[int(question["id"])] == "unlocked" for question in catalog[difficulty])


def test_solved_questions_always_show_as_solved() -> None:
    catalog = get_questions_by_difficulty()
    solved_ids = {int(catalog["hard"][24]["id"])}
    unlock_state = compute_unlock_state("free", solved_ids, catalog)

    assert unlock_state[int(catalog["hard"][24]["id"])] == "solved"


def test_solved_hard_question_survives_downgrade_to_free() -> None:
    catalog = get_questions_by_difficulty()
    solved_ids = {int(catalog["hard"][20]["id"])}
    unlock_state = compute_unlock_state("free", solved_ids, catalog)

    assert unlock_state[int(catalog["hard"][20]["id"])] == "solved"
