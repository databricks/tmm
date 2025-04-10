### Laboratorio Práctico: Construcción de Sistemas de Agentes con Databricks

Este laboratorio está dividido en dos partes. En la **Parte 1**, construirás y probarás un agente de Databricks con varias llamadas a herramientas en un escenario de atención al cliente. En la **Parte 2**, crearás un agente más simplificado que responda preguntas sobre productos y te enfocarás en evaluar su rendimiento.

---

### Parte 1: Diseña tu Primer Agente  
##### Notebook: 01_create_tools\01_create_tools

#### 1.1 Construir Herramientas  
- **Funciones SQL**  
  - Escribe consultas para acceder a datos críticos en el flujo de trabajo de devoluciones en atención al cliente.  
  - Estas funciones SQL se pueden invocar fácilmente desde un notebook o un agente.
- **Función Python Simple**  
  - Crea una función en Python para abordar limitaciones comunes de los modelos de lenguaje.  
  - Regístrala como una “herramienta” para que el agente pueda invocarla cuando la necesite.

#### 1.2 Integración con un LLM [AI Playground]  
- **Combina Herramientas y LLM**  
  - Usa el AI Playground de Databricks para combinar tus herramientas SQL/Python con el Modelo de Lenguaje (LLM).  
  - Modelo: Meta Llama 3.3 70B  
  - Herramientas: labuser##_##_vocareum_com.agents.*  
  - Herramientas de Respaldo: agents_lab.product.* (Úsalo si no encuentras tus herramientas)

#### 1.3 Probar el Agente [AI Playground]  
- **Prompt del Sistema**: Llama a las herramientas hasta que estés seguro de que se han cumplido todas las políticas de la empresa.  
- **Haz una Pregunta**: Según nuestras políticas, ¿deberíamos aceptar la última devolución en la cola?  
  - Observa el razonamiento paso a paso del agente y su respuesta final.  
- **Explora las Trazas de MLflow**  
  - Inspecciona las ejecuciones del agente en MLflow para entender cómo se invoca cada herramienta.

---

### Parte 2: Evaluación del Agente  
##### Notebook: 02_agent_eval\agent

#### 2.1 Definir un Nuevo Agente y Herramienta de Recuperación  
- **Búsqueda Vectorial**  
  - Hemos preparado un índice de Búsqueda Vectorial que recupera documentación relevante del producto.  
  - Este índice se encuentra en: agents_lab.product.product_docs_index  
- **Crear Función de Recuperación**  
  - Envuelve este índice de búsqueda vectorial en una función que el LLM pueda usar para consultar información del producto.  
  - Usa el mismo LLM para generar las respuestas finales.

##### Notebook: 02_agent_eval/driver

#### 2.2 Definir Conjunto de Evaluación  
- **Usar el Conjunto Proporcionado**  
  - Aprovecha el conjunto de datos de evaluación de ejemplo para probar la capacidad del agente para responder preguntas sobre productos.  
  - (Opcional) Experimenta con [generación de datos sintéticos](https://www.databricks.com/blog/streamline-ai-agent-evaluation-with-new-synthetic-data-capabilities).

#### 2.3 Evaluar el Agente  
- **Ejecutar `MLflow.evaluate()`**  
  - MLflow compara las respuestas de tu agente con un conjunto de datos de referencia.  
  - Jueces basados en LLM califican cada respuesta y recopilan feedback para facilitar su revisión.

#### 2.4 Refinar y Re-evaluar  
- **Mejorar Recuperación**  
  - Ajusta la configuración del recuperador (por ejemplo, cambia k=5 a k=1) en base al feedback.  
- **Re-ejecutar Evaluaciones**  
  - Inicia una nueva ejecución en MLflow  
  - Ejecuta nuevamente `MLflow.evaluate()` y compara los resultados.  
  - Observa las mejoras de rendimiento en la interfaz de evaluación de MLflow.

---

### Próximos Pasos  
- **Deja tus Comentarios sobre el Laboratorio**: ¡Nos encantaría saber cómo podemos mejorar! Por favor deja tus comentarios en esta [encuesta](https://www.surveymonkey.com/r/ZNW8KT7).  
- **Explora Más Herramientas**: Extiende tu agente con APIs, funciones avanzadas en Python o endpoints SQL adicionales.  
- **Despliegue en Producción**: Integra CI/CD para mejora continua, monitorea el rendimiento en MLflow y gestiona versiones del modelo.

---

¡Felicidades por construir y evaluar tu sistema de agentes en Databricks!