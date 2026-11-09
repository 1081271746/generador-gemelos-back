from app.rpc import negotiation_pb2 as pb


def test_proto_round_trip_preserves_contract():
    context = pb.NegotiationContext(user_id=1, negotiation_id=2, scenario_json='{"context":"Supply"}',
        messages=[pb.ConversationMessage(message_id=3, sender_type="user", content="Offer 100", kind="offer")])
    restored = pb.NegotiationContext.FromString(context.SerializeToString())
    assert restored.messages[0].message_id == 3
