CREDENCIALES PARA INICIAR:

CORREO: sebitasroja06@gmail.com
CONTRASEÑA: 1234567891112



Generador de Gemelos de Negociación 🤝
Plataforma web para practicar negociaciones con un gemelo de inteligencia artificial y analizar el desempeño con evidencias
El Generador de Gemelos de Negociación es una plataforma web que permite crear escenarios de negociación, practicar conversaciones con un gemelo de IA, consultar el historial de cada negociación y obtener análisis estructurados sobre las estrategias utilizadas.

El proyecto utiliza una arquitectura cliente-servidor dividida en dos repositorios: un frontend desarrollado con Angular y un backend desarrollado con FastAPI. El backend coordina la persistencia, la autenticación, los servicios gRPC, los eventos en tiempo real y la comunicación con Groq. PostgreSQL se utiliza como base de datos en el despliegue de Railway y Redis apoya la distribución de eventos y el control compartido de solicitudes de IA.

La IA no se entrena automáticamente con cada conversación. El sistema construye el contexto de cada negociación y lo envía al proveedor configurado para producir respuestas o análisis. También existe una ruta opcional de inferencia local y un pipeline de preparación de datos y entrenamiento LoRA/QLoRA, pero no hay actualmente un adaptador especializado entrenado y validado.

1. Objetivos del proyecto
Objetivo general
Desarrollar una plataforma de práctica de negociación que permita simular conversaciones con un gemelo de IA, administrar escenarios, conservar el historial de las interacciones y analizar habilidades de negociación mediante indicadores contextuales y evidencias extraídas de los mensajes.
Objetivos específicos
- Permitir el registro, autenticación y administración de cuentas de usuario.
- Crear escenarios configurables con objetivos, contexto, rol de la contraparte e información sobre sus límites.
- Iniciar y administrar negociaciones individuales a partir de escenarios.
- Generar respuestas del gemelo de IA considerando el escenario, los mensajes anteriores y el perfil contextual del usuario.
- Conservar los mensajes y estados de cada negociación.
- Analizar negociaciones finalizadas mediante cinco dimensiones de desempeño.
- Asociar las conclusiones del análisis con citas verificables de mensajes del usuario.
- Construir un perfil progresivo con indicadores de desempeño, fortalezas y oportunidades de mejora.
- Generar recomendaciones y ejercicios de práctica.
- Distribuir eventos en tiempo real mediante gRPC Streaming, Redis Pub/Sub y WebSockets.
- Mantener una arquitectura modular, con validaciones, pruebas automatizadas y despliegue separado del frontend y backend.

2. Repositorios del proyecto
El proyecto se encuentra separado en dos repositorios independientes:
Componente	Repositorio	Responsabilidad
Backend	generador-gemelos-back	API, lógica de negocio, persistencia, autenticación, IA, gRPC y eventos.
Frontend	generador-gemelos-front	Interfaz web, navegación, autenticación del cliente, chat, escenarios, análisis y conexión en tiempo real.El frontend consume la API existente del backend. No implementa una segunda lógica de negocio ni accede directamente a PostgreSQL, Redis o los servicios gRPC.
