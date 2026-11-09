from app.schemas.negotiation import NegotiationCreate
from app.services.negotiation_service import create_negotiation
from app.services.twin_service import build_twin_context
from app.rpc.transport import local_target, create_channel
import pytest


def test_context_uses_snapshot_and_transport_requires_tls(db, owner, scenario):
    negotiation = create_negotiation(db, owner.id, NegotiationCreate(scenario_id=scenario.id))
    context = build_twin_context(db, owner.id, negotiation.id)
    assert context.negotiation_id == negotiation.id
    assert "Supplier" in context.scenario_json
    assert local_target("127.0.0.1:50051")
    assert not local_target("0.0.0.0:50051")
    with pytest.raises(RuntimeError, match="TLS"):
        create_channel("remote.example.com:50051")
