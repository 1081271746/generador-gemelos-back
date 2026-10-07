def generate_twin_response(context: dict) -> str:
    negotiation = context["negotiation"]
    scenario = context["scenario"]
    messages = context["messages"]

    if negotiation["status"] != "active":
        raise ValueError("Negotiation is not active.")

    user_messages = [
        message
        for message in messages
        if message["sender_type"] == "user"
    ]

    if not user_messages:
        return (
            f"Estoy listo para negociar como "
            f"{scenario['counterpart_role']}."
        )

    last_user_message = user_messages[-1]["content"]

    return (
        f"He revisado tu propuesta: \"{last_user_message}\". "
        f"Como {scenario['counterpart_role']}, mi objetivo es "
        f"{scenario['counterpart_goal']} "
        f"y debo respetar los siguientes límites: "
        f"{scenario['counterpart_limits']} "
        f"Podemos continuar negociando si presentas una propuesta "
        f"que se acerque a mis condiciones."
    )