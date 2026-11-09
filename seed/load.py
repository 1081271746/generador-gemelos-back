import os

from sqlalchemy import select

from app.database.database import SessionLocal
from app.models import User, Scenario, Message
from app.schemas.user import UserCreate
from app.schemas.scenario import ScenarioCreate
from app.schemas.negotiation import NegotiationCreate, NegotiationFinish
from app.services.auth_service import create_user
from app.services.scenario_service import create_scenario
from app.services.negotiation_service import create_negotiation, finish_negotiation


SCENARIOS = [
    {"title": "Renovación de suministro", "description": "Contrato anual de insumos",
        "context": "Una empresa ficticia necesita renovar el suministro para el próximo año.",
        "objective": "Reducir el costo un 10% sin perder calidad", "counterpart_role": "Proveedor",
        "counterpart_goal": "Mantener el margen y asegurar volumen", "counterpart_limits": "No reducir más del 5% sin mayor volumen"},
    {"title": "Distribución de tareas", "description": "Acuerdo de trabajo de un equipo ficticio",
        "context": "Un equipo debe distribuir tareas para entregar un proyecto universitario.",
        "objective": "Lograr una carga equilibrada", "counterpart_role": "Coordinador del equipo",
        "counterpart_goal": "Entregar antes del viernes", "counterpart_limits": "No ampliar el plazo del proyecto"},
]

EXERCISES = [
    {"title": "Justificar una propuesta", "instructions": "Presenta una oferta y dos razones verificables."},
    {"title": "Responder a una objeción", "instructions": "Reconoce un interés de la contraparte antes de proponer una alternativa."},
]


def load_seed(session_factory=SessionLocal, password: str | None = None) -> dict:
    supplied = password or os.getenv("SEED_PASSWORD", "")
    data = UserCreate(username="demo_student", email="demo@example.com", password=supplied)
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == data.email))
        if user is not None:
            return {"created": False, "user_id": user.id}
        user = create_user(db, data)
        scenarios = [create_scenario(db, user.id, ScenarioCreate(**item)) for item in SCENARIOS]
        negotiation = create_negotiation(db, user.id, NegotiationCreate(scenario_id=scenarios[0].id))
        db.add(Message(negotiation_id=negotiation.id, sender_type="user",
            content="Propongo aumentar el volumen si acordamos un descuento del 5%.", kind="offer"))
        db.commit()
        finish_negotiation(db, user.id, negotiation.id, NegotiationFinish(status="completed",
            result="Ejemplo ficticio sin respuesta de IA: propuesta pendiente de aceptación"))
        return {"created": True, "user_id": user.id, "negotiation_id": negotiation.id}


if __name__ == "__main__":
    result = load_seed()
    print("Datos ficticios cargados." if result["created"] else "Los datos ficticios ya existen.")
