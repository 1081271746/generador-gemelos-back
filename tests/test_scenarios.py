import pytest
from app.core.errors import DomainError
from app.schemas.scenario import ScenarioCreate
from app.services.scenario_service import update_scenario, archive_scenario, get_user_scenarios


def test_update_archive_and_owner_boundaries(db, owner, scenario):
    data = ScenarioCreate.model_validate(scenario, from_attributes=True)
    updated = update_scenario(db, owner.id, scenario.id, data.model_copy(update={"title": "New contract"}))
    assert updated.title == "New contract"
    assert len(get_user_scenarios(db, owner.id, limit=1)) == 1
    with pytest.raises(DomainError):
        archive_scenario(db, owner.id + 1, scenario.id)
    archive_scenario(db, owner.id, scenario.id)
    assert not scenario.is_active
