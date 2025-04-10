# Databricks notebook source
# MAGIC %md
# MAGIC # Laboratorio Práctico: Construcción de Sistemas de Agentes con Databricks
# MAGIC
# MAGIC ## Parte 2 - Evaluación del Agente  
# MAGIC Ahora que hemos creado un agente, ¿cómo evaluamos su rendimiento?  
# MAGIC Para esta segunda parte, vamos a crear un agente más básico para poder enfocarnos en la evaluación.  
# MAGIC Este agente utilizará un enfoque RAG para ayudar a responder preguntas sobre productos usando la documentación del producto.
# MAGIC
# MAGIC ### 2.1 Definir nuestro nuevo Agente y herramienta de recuperación
# MAGIC - **Búsqueda Vectorial**: Hemos creado un endpoint de Búsqueda Vectorial que puede ser consultado para encontrar documentación relacionada con un producto específico.
# MAGIC - **Crear Función de Recuperación**: Define algunas propiedades sobre nuestro recuperador y empaquétalo para que pueda ser llamado por nuestro LLM.
# MAGIC
# MAGIC Nota: También puedes cambiar el prompt del sistema tal como lo definimos en el playground dentro del archivo config.yml.

# COMMAND ----------

# MAGIC %md
# MAGIC # Agent Notebook
# MAGIC
# MAGIC Este notebook es muy similar a uno autogenerado por una exportación desde AI Playground. Hay tres notebooks en la misma carpeta:
# MAGIC - [**agent**]($./agent): contiene el código para construir el agente.
# MAGIC - [config.yml]($./config.yml): contiene las configuraciones.
# MAGIC - [driver]($./driver): registra, evalúa, registra en catálogo y despliega el agente.
# MAGIC
# MAGIC Este notebook utiliza el Marco de Trabajo Mosaic AI Agent ([AWS](https://docs.databricks.com/en/generative-ai/retrieval-augmented-generation.html) | [Azure](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/retrieval-augmented-generation)) para crear tu agente. Define un agente de LangChain que tiene acceso a herramientas, las cuales también definimos en este notebook.
# MAGIC
# MAGIC Usa este notebook para iterar y modificar el agente. Por ejemplo, podrías agregar más herramientas o cambiar el prompt del sistema.
# MAGIC
# MAGIC **_NOTA:_** Este notebook utiliza LangChain, sin embargo, el Marco de Trabajo AI Agent también es compatible con otros frameworks de agentes como Pyfunc y LlamaIndex.
# MAGIC
# MAGIC ## Requisitos Previos
# MAGIC
# MAGIC - Revisa el contenido de [config.yml]($./config.yml), ya que define las herramientas disponibles para tu agente, el endpoint del LLM y el prompt del agente.
# MAGIC
# MAGIC ## Próximos Pasos
# MAGIC
# MAGIC Después de probar e iterar sobre tu agente en este notebook, ve al notebook autogenerado [driver]($./driver) en esta carpeta para registrar, evaluar y desplegar el agente.

# COMMAND ----------

# MAGIC %pip install -U -qqqq mlflow-skinny langchain==0.2.16 langgraph-checkpoint==1.0.12 langchain_core langchain-community==0.2.16 langgraph==0.2.16 pydantic langchain_databricks
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Importar y configurar
# MAGIC
# MAGIC Usa `mlflow.langchain.autolog()` para configurar [trazas de MLflow](https://docs.databricks.com/en/mlflow/mlflow-tracing.html).

# COMMAND ----------

import mlflow
from mlflow.models import ModelConfig

mlflow.langchain.autolog()
config = ModelConfig(development_config="config.yml")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Definir el modelo de chat y las herramientas  
# MAGIC Crea un modelo de chat de LangChain que sea compatible con llamadas a herramientas de [LangGraph](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/).
# MAGIC
# MAGIC Importaremos herramientas desde UC, además de definir un recuperador. Consulta [LangChain - Cómo crear herramientas](https://python.langchain.com/v0.2/docs/how_to/custom_tools/) y [LangChain - Uso de herramientas integradas](https://python.langchain.com/v0.2/docs/how_to/tools_builtin/).
# MAGIC
# MAGIC **_NOTA:_** Este notebook utiliza LangChain, sin embargo, el Marco de Trabajo AI Agent también es compatible con otros frameworks de agentes como Pyfunc y LlamaIndex.

# COMMAND ----------

from langchain_community.chat_models import ChatDatabricks
from langchain_community.tools.databricks import UCFunctionToolkit
from databricks.sdk import WorkspaceClient

# Crear el llm
llm = ChatDatabricks(endpoint=config.get("llm_endpoint"))

uc_functions = config.get("uc_functions")

tools = (
    UCFunctionToolkit(warehouse_id=config.get("warehouse_id"))
    .include(*uc_functions)
    .get_tools()
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Usar la recuperación de Databricks Vector Search como herramienta en tu Agente LangGraph
# MAGIC
# MAGIC Un caso de uso común para agentes es la Generación Aumentada por Recuperación (RAG). En RAG, el agente puede utilizar un recuperador basado en búsqueda vectorial para consultar un corpus de documentos y proporcionar contexto adicional al LLM.  
# MAGIC Si ya tienes un endpoint e índice de búsqueda vectorial en Databricks, puedes crear fácilmente una herramienta que realice la recuperación contra el índice y pase los resultados a tu agente.

# COMMAND ----------

from langchain.tools.retriever import create_retriever_tool
from langchain_databricks.vectorstores import DatabricksVectorSearch

# Conectar a un endpoint y un índice existentes de Databricks Vector Search
vector_store = DatabricksVectorSearch(
  endpoint="one-env-shared-endpoint-14", 
  index_name="retail_prod.agents.product_docs_vs", 
  columns=[
    "product_category",
    "product_sub_category",
    "product_name",
    "product_doc",
    "product_id",
    "indexed_doc"
  ]
).as_retriever(search_kwargs={"k": 5}) 
#Este parámetro determina cuántos resultados se devuelven - importante para la afinación de la recuperación

# Crear un objeto herramienta que realice la recuperación contra nuestro índice de búsqueda vectorial
retriever_tool = create_retriever_tool(
  vector_store,
  name="search_product_docs", 
  description="Use this tool to search for product documentation.", 
)

# Especificar el esquema del tipo de retorno de nuestro recuperador, para que la evaluación y las UIs puedan
# mostrar automáticamente los fragmentos recuperados
mlflow.models.set_retriever_schema(
    primary_key="product_id",
    text_column="indexed_doc",
    doc_uri="product_id",
    name="retail_prod.agents.product_docs_index",
)

tools.append(retriever_tool)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parsers de salida  
# MAGIC Las interfaces de Databricks, como el AI Playground, pueden mostrar opcionalmente las llamadas a herramientas con un formato legible.
# MAGIC
# MAGIC Usa las siguientes funciones auxiliares para analizar la salida del LLM en el formato esperado.

# COMMAND ----------

from typing import Iterator, Dict, Any
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
    MessageLikeRepresentation,
)

import json

def stringify_tool_call(tool_call: Dict[str, Any]) -> str:
    """
    Convert a raw tool call into a formatted string that the playground UI expects if there is enough information in the tool_call
    """
    try:
        request = json.dumps(
            {
                "id": tool_call.get("id"),
                "name": tool_call.get("name"),
                "arguments": json.dumps(tool_call.get("args", {})),
            },
            indent=2,
        )
        return f"<tool_call>{request}</tool_call>"
    except:
        return str(tool_call)


def stringify_tool_result(tool_msg: ToolMessage) -> str:
    """
    Convert a ToolMessage into a formatted string that the playground UI expects if there is enough information in the ToolMessage
    """
    try:
        result = json.dumps(
            {"id": tool_msg.tool_call_id, "content": tool_msg.content}, indent=2
        )
        return f"<tool_call_result>{result}</tool_call_result>"
    except:
        return str(tool_msg)


def parse_message(msg) -> str:
    """Parse different message types into their string representations"""
    # tool call result
    if isinstance(msg, ToolMessage):
        return stringify_tool_result(msg)
    # tool call
    elif isinstance(msg, AIMessage) and msg.tool_calls:
        tool_call_results = [stringify_tool_call(call) for call in msg.tool_calls]
        return "".join(tool_call_results)
    # normal HumanMessage or AIMessage (reasoning or final answer)
    elif isinstance(msg, (AIMessage, HumanMessage)):
        return msg.content
    else:
        print(f"Unexpected message type: {type(msg)}")
        return str(msg)


def wrap_output(stream: Iterator[MessageLikeRepresentation]) -> Iterator[str]:
    """
    Process and yield formatted outputs from the message stream.
    The invoke and stream langchain functions produce different output formats.
    This function handles both cases.
    """
    for event in stream:
        # the agent was called with invoke()
        if "messages" in event:
            for msg in event["messages"]:
                yield parse_message(msg) + "\n\n"
        # the agent was called with stream()
        else:
            for node in event:
                for key, messages in event[node].items():
                    if isinstance(messages, list):
                        for msg in messages:
                            yield parse_message(msg) + "\n\n"
                    else:
                        print("Unexpected value {messages} for key {key}. Expected a list of `MessageLikeRepresentation`'s")
                        yield str(messages)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Crear el agente  
# MAGIC Aquí proporcionamos un grafo simple que utiliza el modelo y las herramientas definidas en [config.yml]($./config.yml). Este grafo está adaptado de [esta guía de LangGraph](https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/).
# MAGIC
# MAGIC Para personalizar aún más tu agente de LangGraph, puedes consultar:
# MAGIC * [LangGraph - Inicio Rápido](https://langchain-ai.github.io/langgraph/tutorials/introduction/) para explicaciones de los conceptos utilizados en este agente LangGraph  
# MAGIC * [LangGraph - Guías Prácticas](https://langchain-ai.github.io/langgraph/how-tos/) para ampliar la funcionalidad de tu agente

# COMMAND ----------

from typing import (
    Annotated,
    Optional,
    Sequence,
    TypedDict,
    Union,
)

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool

from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt.tool_executor import ToolExecutor
from langgraph.prebuilt.tool_node import ToolNode


# Creamos el estado del agente que pasaremos
# Esto simplemente implica una lista de mensajes
class AgentState(TypedDict):
    """El estado del agente."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


def create_tool_calling_agent(
    model: LanguageModelLike,
    tools: Union[ToolExecutor, Sequence[BaseTool]],
    agent_prompt: Optional[str] = None,
) -> CompiledGraph:
    model = model.bind_tools(tools)

    # Definir la función que determina a qué nodo ir
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # Si no hay llamada a función, entonces terminamos
        if not last_message.tool_calls:
            return "end"
        else:
            return "continue"

    if agent_prompt:
        system_message = SystemMessage(content=agent_prompt)
        preprocessor = RunnableLambda(
            lambda state: [system_message] + state["messages"]
        )
    else:
        preprocessor = RunnableLambda(lambda state: state["messages"])
    model_runnable = preprocessor | model

    # Definir la función que llama al modelo
    def call_model(
        state: AgentState,
        config: RunnableConfig,
    ):
        response = model_runnable.invoke(state, config)
        return {"messages": [response]}

    workflow = StateGraph(AgentState)

    workflow.add_node("agent", RunnableLambda(call_model))
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        # Primero, definimos el nodo de inicio. Usamos agent.
        # Esto significa que estos son los bordes tomados después de llamar al nodo agent.
        "agent",
        # A continuación, pasamos la función que determinará a qué nodo llamar a continuación.
        should_continue,
        # El mapeo a continuación se utilizará para determinar a qué nodo ir
        {
            # Si continue, entonces llamamos al nodo de herramientas.
            "continue": "tools",
            # END es un nodo especial que marca que el gráfico debe terminar.
            "end": END,
        },
    )
    # Ahora agregamos un borde incondicional de tools a agent.
    workflow.add_edge("tools", "agent")

    return workflow.compile()

# COMMAND ----------

from langchain_core.runnables import RunnableGenerator
from mlflow.langchain.output_parsers import ChatCompletionsOutputParser

# Crear el agente con el mensaje del sistema si existe
try:
    agent_prompt = config.get("agent_prompt")

    agent_with_raw_output = create_tool_calling_agent(
        llm, 
        tools, 
        agent_prompt=agent_prompt
    )
except KeyError:
    agent_with_raw_output = create_tool_calling_agent(llm, tools)

agent = agent_with_raw_output | RunnableGenerator(wrap_output) | ChatCompletionsOutputParser()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Probar el agente
# MAGIC
# MAGIC Interactúa con el agente para probar su salida.  
# MAGIC Como este notebook llamó a `mlflow.langchain.autolog()`, puedes visualizar el rastro de cada paso que realiza el agente.

# COMMAND ----------

for event in agent.stream({"messages": [{"role": "user", "content": "Can you give me some troubleshooting steps for SoundWave X5 Pro Headphones that won't connect?"}]}):
    print(event, "---" * 20 + "\n")

# COMMAND ----------

# Registrar agente

mlflow.models.set_model(agent)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Próximos pasos
# MAGIC
# MAGIC Puedes volver a ejecutar las celdas anteriores para iterar y probar el agente.
# MAGIC
# MAGIC Dirígete al notebook autogenerado [driver]($./driver) en esta carpeta para registrar, evaluar y desplegar el agente.
