from seed.load import load_seed
from app.models import User, Scenario, Negotiation, Analysis
from sqlalchemy import select, func


def test_seed_is_repeatable_and_does_not_fabricate_ai_results(session_factory):
    assert load_seed(session_factory, "test-demo-password-only")["created"]
    assert not load_seed(session_factory, "test-demo-password-only")["created"]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(Scenario)) == 2
        assert db.scalar(select(func.count()).select_from(Negotiation)) == 1
        assert db.scalar(select(func.count()).select_from(Analysis)) == 0
