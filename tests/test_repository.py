import pytest

from app.core.errors import DomainError
from app.repositories.negotiation_repository import NegotiationRepository


def test_private_scenario_is_invisible(db, owner, scenario):
    assert NegotiationRepository(db, owner.id).scenario(scenario.id).id == scenario.id
    with pytest.raises(DomainError) as error:
        NegotiationRepository(db, owner.id + 100).scenario(scenario.id)
    assert error.value.status_code == 404
