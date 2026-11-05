import pytest

from conftest import csrf_token
from modules.exercises import EXERCISES


@pytest.mark.parametrize("scenario", list(EXERCISES))
def test_exercises_branch_and_score(signed_in, scenario):
    token = csrf_token(signed_in.get("/exercises/"))
    paths = [signed_in.post("/exercises/start", data={
        "scenario": scenario, "csrf_token": token,
    }).location for _ in range(2)]
    for path, first in zip(paths, (0, 1), strict=True):
        first_answer = {"csrf_token": token, "step_number": "0", "choice": str(first),
                        "evidence": "Documented source event"}
        assert signed_in.post(path, data=first_answer).status_code == 302
        assert signed_in.post(path, data=first_answer).status_code == 302
        evidence = EXERCISES[scenario][1].evidence if first == 0 else EXERCISES[scenario][1].changed_evidence
        assert evidence.encode() in signed_in.get(path).data
        for step, choice in [(1, 1), (2, 0)]:
            assert signed_in.post(path, data={
                "csrf_token": token, "step_number": str(step), "choice": str(choice),
            }).status_code == 302
        result = signed_in.get(path)
        score = 6 if first == 0 else 4
        assert f"{score} / 6".encode() in result.data
        assert b"Evidence documented in 1 of 3" in result.data
