"""Project-authored synthetic curriculum. CC0. NOT an expert training corpus."""
import argparse
import json
from pathlib import Path

from app.schemas.analysis import DIMENSION_NAMES
from training.data import Example

# Different interests and reciprocal concessions, not copied conversations.
CASES = [
    ("comercial", "Proveedor de café", "Contrato anual de 200 cajas", "Reducir el costo total",
     "Mantener margen y asegurar volumen", "No vender por debajo de 90 por caja",
     "Ofrezco 80 por caja con un pedido de 200 cajas.",
     "No puedo aceptar 80. Puedo ofrecer 95 por caja si confirmamos las 200 cajas con pago anticipado.",
     "contraoferta condicionada", "Defiende el margen y vincula el descuento a un beneficio verificable."),
    ("salarial", "Responsable de contratación", "Oferta de empleo de ingeniería", "Obtener salario de 5000",
     "Contratar dentro del presupuesto", "Salario máximo 4500; revisión a seis meses",
     "Solicito 5000 por mi experiencia. ¿Qué margen tienen?",
     "El salario disponible es 4500. Podemos acordar una revisión a seis meses con objetivos medibles. ¿Qué metas propondrías?",
     "ampliación de variables", "No excede el presupuesto e incorpora una revisión sin prometer un aumento."),
    ("vehiculos", "Vendedor de vehículo usado", "Venta de un vehículo con mantenimiento documentado",
     "Comprar por 9000", "Vender con pago seguro", "Precio mínimo 10000; no ocultar defectos",
     "Puedo pagar 9000 hoy si hacemos una inspección independiente.",
     "Acepto la inspección independiente, pero 9000 no me permite cerrar. Propongo 10200, condicionado al informe y a un pago seguro.",
     "concesión parcial", "Acepta una condición no económica sin aceptar un precio fuera del límite."),
    ("precios", "Comerciante de equipos", "Compra de diez portátiles", "Conseguir descuento y garantía",
     "Vender inventario sin perder margen", "Precio mínimo unitario 600; garantía de doce meses",
     "Si compro diez equipos, ¿aceptan 550 por unidad con garantía?",
     "Por diez equipos puedo proponer 620 por unidad con la garantía de doce meses. No puedo aceptar 550.",
     "anclaje y justificación", "Ofrece una cifra viable sin reducir derechos de garantía."),
    ("empresarial", "Directora de alianzas", "Distribución regional con riesgos compartidos",
     "Exclusividad regional sin compras mínimas", "Asegurar inversión recuperable",
     "Exclusividad solo con compra mínima trimestral de 100 unidades",
     "Queremos exclusividad, pero no podemos comprometernos a un mínimo todavía.",
     "Sin un mínimo no puedo ofrecer exclusividad. Propongo iniciar una distribución no exclusiva y revisarla tras alcanzar 100 unidades trimestrales.",
     "acuerdo escalonado", "Plantea una alternativa al desacuerdo sin regalar la exclusividad."),
    ("contratos", "Consultor independiente", "Contrato de implementación de software",
     "Entrega en dos semanas por 3000", "Acotar alcance y asegurar calidad",
     "Alcance completo requiere cuatro semanas; no prometer fechas imposibles",
     "Necesitamos todo en dos semanas y el presupuesto no puede aumentar.",
     "No puedo comprometer el alcance completo en dos semanas. Podemos priorizar un módulo para esa fecha y negociar el resto en una segunda fase.",
     "redefinición del alcance", "Explicita la restricción temporal y pide priorización en vez de aceptar lo imposible."),
    ("conflictos", "Coordinador de equipo", "Desacuerdo sobre horarios de reuniones",
     "Evitar reuniones fuera de jornada", "Coordinar sin sobrecargar al equipo",
     "No imponer horas extra ni reuniones después de las 18",
     "Tus reuniones siempre nos perjudican. Quiero que todas sean a las 19.",
     "Entiendo la molestia por los horarios. Las 19 quedan fuera de la jornada. Revisemos dos franjas antes de las 18 y elijamos una que permita participar.",
     "desescalada", "Reconoce la objeción sin personalizar ni trasladar el conflicto a horas extra."),
    ("colaborativa", "Representante de asociación", "Uso compartido de un salón",
     "Reservar todos los sábados", "Mantener acceso equitativo",
     "Cada asociación puede reservar máximo dos sábados por mes",
     "Necesitamos todos los sábados; podemos ayudar con la limpieza.",
     "Agradezco la propuesta de limpieza. Puedo reservar dos sábados al mes y explorar contigo franjas entre semana para el resto de actividades.",
     "búsqueda de intereses", "Reconoce un interés compartido y mantiene la regla de acceso equitativo."),
    ("competitiva", "Agente de compras", "Licitación de un lote con varios oferentes",
     "Vender el lote por 25000", "Adquirir dentro del techo autorizado",
     "Gasto máximo 22000; no inventar ofertas rivales",
     "Por menos de 25000 me retiro. Es mi última oferta.",
     "No puedo comprometer 25000. Mi propuesta es 22000 por el lote descrito; si no te resulta viable, respetaré tu decisión de no continuar.",
     "defensa del límite y alternativa de no acuerdo", "No cede a la presión ni inventa competidores para justificar su posición."),
    ("objeciones", "Responsable de servicio", "Renovación de soporte anual",
     "Reducir precio por retrasos anteriores", "Retener al cliente con un compromiso sostenible",
     "Descuento máximo 10%; no prometer disponibilidad absoluta",
     "Con los retrasos del mes pasado, solo renuevo con un descuento del 30%.",
     "Los retrasos justifican revisar el servicio. Puedo proponer un 10% de descuento y métricas de atención acordadas; no puedo ofrecer el 30%. ¿Qué tiempos de respuesta priorizas?",
     "manejo de objeciones", "Reconoce el problema y propone un compromiso medible sin exceder el descuento permitido."),
]


def examples():
    for index, (domain, role, scenario, objective, goal, limits, offer, reply, strategy, rationale) in enumerate(CASES, 1):
        context = {"negotiation_id": index,
                   "scenario": {"context": scenario, "objective": objective, "counterpart_role": role,
                                "counterpart_goal": goal, "counterpart_limits": limits},
                   "profile": {}, "result": "",
                   "messages": [{"message_id": 1, "sender_type": "user", "content": offer, "kind": "offer"}]}
        common = {"family": domain, "domain": domain, "source": "project-authored:training/seed.py",
                  "license": "CC0-1.0", "authorized": True, "synthetic": True, "reviewed": False}
        yield Example(**common, id=f"{domain}-twin", task="twin", context=context,
                      expected={"content": reply, "kind": "counteroffer"}, rationale=rationale)
        dimension = {"score": 50, "explanation": "Un único turno no permite inferir un patrón estable; indicador pedagógico provisional.",
                     "evidence": [{"message_id": 1, "quote": offer}]}
        analysis_context = {**context, "result": "No se registró un acuerdo.",
                            "messages": context["messages"] + [{"message_id": 2, "sender_type": "twin",
                                                               "content": reply, "kind": "counteroffer"}]}
        yield Example(**common, id=f"{domain}-analysis", task="analysis", context=analysis_context,
                      expected={"summary": f"Se presentó una oferta y una alternativa en {domain}.",
                                "strategies": [strategy], "strengths": ["Expresa una petición concreta."],
                                "improvement_areas": ["Explorar los intereses y justificar las condiciones."],
                                "dimensions": {name: dimension for name in DIMENSION_NAMES},
                                "outcome": "No se registró un acuerdo.",
                                "objective_evaluation": "El resultado registrado no demuestra que se haya alcanzado el objetivo.",
                                "recommendations": ["Pregunta por una condición intercambiable antes de conceder."],
                                "exercises": [{"title": "Concesión condicional", "instructions": "Formula una propuesta si-entonces y explica el beneficio recíproco.",
                                               "scenario": scenario}], "alerts": []},
                      rationale="Ejemplo sintético de formato y evidencias, no etiqueta experta: " + rationale)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="training/datasets/synthetic.jsonl")
    args = parser.parse_args()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(item.model_dump_json() + "\n" for item in examples()), encoding="utf8")
    print(f"Wrote {len(CASES) * 2} synthetic examples; human review required.")
