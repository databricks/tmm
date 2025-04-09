# Databricks notebook source
# MAGIC %md
# MAGIC # Hands-On Lab: Building Agent Systems with Databricks
# MAGIC
# MAGIC ## Part 2 - Agent Evaluation
# MAGIC Now that we've created an agent, how do we evaluate its performance?
# MAGIC For the second part, we're going to create a more basic agent so we can focus on evaluation.
# MAGIC This agent will use a RAG approach to help answer questions about products using the product documentation.
# MAGIC
# MAGIC ### 2.1 Define our new Agent and retriever tool
# MAGIC - **Vector Search**: We've created a Vector Search endpoint that can be queried to find related documentation about a specific product.
# MAGIC - **Create Retriever Function**: Define some properties about our retriever and package it so it can be called by our LLM.
# MAGIC
# MAGIC Note: You can also change the system prompt as we defined in the playground within the config.yml file

# COMMAND ----------

# MAGIC %md
# MAGIC #Agent notebook
# MAGIC
# MAGIC This is very similar to an auto-generated notebook created by an AI Playground export. There are three notebooks in the same folder:
# MAGIC - [**agent**]($./agent): contains the code to build the agent.
# MAGIC - [config.yml]($./config.yml): contains the configurations.
# MAGIC - [driver]($./driver): logs, evaluate, registers, and deploys the agent.
# MAGIC
# MAGIC This notebook uses Mosaic AI Agent Framework ([AWS](https://docs.databricks.com/en/generative-ai/retrieval-augmented-generation.html) | [Azure](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/retrieval-augmented-generation)) to create your agent. It defines a LangChain agent that has access to tools, which we define in this notebook as well.
# MAGIC
# MAGIC Use this notebook to iterate on and modify the agent. For example, you could add more tools or change the system prompt.
# MAGIC
# MAGIC  **_NOTE:_**  This notebook uses LangChain, however AI Agent Framework is compatible with other agent frameworks like Pyfunc and LlamaIndex.
# MAGIC
# MAGIC ## Prerequisites
# MAGIC
# MAGIC - Review the contents of [config.yml]($./config.yml) as it defines the tools available to your agent, the LLM endpoint, and the agent prompt.
# MAGIC
# MAGIC ## Next steps
# MAGIC
# MAGIC After testing and iterating on your agent in this notebook, go to the auto-generated [driver]($./driver) notebook in this folder to log, register, evaluate, and deploy the agent.

# COMMAND ----------

# MAGIC %pip install -U -qqqq mlflow-skinny langchain==0.2.16 langgraph-checkpoint==1.0.12 langchain_core langchain-community==0.2.16 langgraph==0.2.16 pydantic langchain_databricks
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import and setup
# MAGIC
# MAGIC Use `mlflow.langchain.autolog()` to set up [MLflow traces](https://docs.databricks.com/en/mlflow/mlflow-tracing.html).

# COMMAND ----------

import mlflow
from mlflow.models import ModelConfig

mlflow.langchain.autolog()
config = ModelConfig(development_config="config.yml")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define the chat model and tools
# MAGIC Create a LangChain chat model that supports [LangGraph tool](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/) calling.
# MAGIC
# MAGIC We'll be importing tools from UC as well as defining a retriever. See [LangChain - How to create tools](https://python.langchain.com/v0.2/docs/how_to/custom_tools/) and [LangChain - Using built-in tools](https://python.langchain.com/v0.2/docs/how_to/tools_builtin/).
# MAGIC
# MAGIC  **_NOTE:_**  This notebook uses LangChain, however AI Agent Framework is compatible with other agent frameworks like Pyfunc and LlamaIndex.

# COMMAND ----------

from langchain_community.chat_models import ChatDatabricks
from langchain_community.tools.databricks import UCFunctionToolkit
from databricks.sdk import WorkspaceClient

# Create the llm
llm = ChatDatabricks(endpoint=config.get("llm_endpoint"))

uc_functions = config.get("uc_functions")

tools = (
    UCFunctionToolkit(warehouse_id=config.get("warehouse_id"))
    .include(*uc_functions)
    .get_tools()
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Using Databricks Vector Search retrieval as a tool in your LangGraph Agent
# MAGIC
# MAGIC A common agent use case is Retrieval Augmented Generation (RAG). In RAG, the agent can use a vector search retriever to query a corpus of documents to provide additional context to the LLM. If you already have a Databricks vector search endpoint and index, you can easily create a tool that performs retrieval against the index and passes the results to your agent.
# MAGIC

# COMMAND ----------

from langchain.tools.retriever import create_retriever_tool
from langchain_databricks.vectorstores import DatabricksVectorSearch

# Connect to an existing Databricks Vector Search endpoint and index
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
#This parameter determines how many results are returned - important for retrieval tuning

# Create a tool object that performs retrieval against our vector search index
retriever_tool = create_retriever_tool(
  vector_store,
  name="search_product_docs", 
  description="Use this tool to search for product documentation.", 
)

# Specify the return type schema of our retriever, so that evaluation and UIs can
# automatically display retrieved chunks
mlflow.models.set_retriever_schema(
    primary_key="product_id",
    text_column="indexed_doc",
    doc_uri="product_id",
    name="retail_prod.agents.product_docs_index",
)

tools.append(retriever_tool)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Output parsers
# MAGIC Databricks interfaces, such as the AI Playground, can optionally display pretty-printed tool calls.
# MAGIC
# MAGIC Use the following helper functions to parse the LLM's output into the expected format.

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
# MAGIC ## Create the agent
# MAGIC Here we provide a simple graph that uses the model and tools defined by [config.yml]($./config.yml). This graph is adapated from [this LangGraph guide](https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/).
# MAGIC
# MAGIC
# MAGIC To further customize your LangGraph agent, you can refer to:
# MAGIC * [LangGraph - Quick Start](https://langchain-ai.github.io/langgraph/tutorials/introduction/) for explanations of the concepts used in this LangGraph agent
# MAGIC * [LangGraph - How-to Guides](https://langchain-ai.github.io/langgraph/how-tos/) to expand the functionality of your agent
# MAGIC

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


# We create the AgentState that we will pass around
# This simply involves a list of messages
class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


def create_tool_calling_agent(
    model: LanguageModelLike,
    tools: Union[ToolExecutor, Sequence[BaseTool]],
    agent_prompt: Optional[str] = None,
) -> CompiledGraph:
    model = model.bind_tools(tools)

    # Define the function that determines which node to go to
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # If there is no function call, then we finish
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

    # Define the function that calls the model
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
        # First, we define the start node. We use agent.
        # This means these are the edges taken after the agent node is called.
        "agent",
        # Next, we pass in the function that will determine which node is called next.
        should_continue,
        # The mapping below will be used to determine which node to go to
        {
            # If tools, then we call the tool node.
            "continue": "tools",
            # END is a special node marking that the graph should finish.
            "end": END,
        },
    )
    # We now add a unconditional edge from tools to agent.
    workflow.add_edge("tools", "agent")

    return workflow.compile()

# COMMAND ----------

from langchain_core.runnables import RunnableGenerator
from mlflow.langchain.output_parsers import ChatCompletionsOutputParser

# Create the agent with the system message if it exists
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
# MAGIC ## Test the agent
# MAGIC
# MAGIC Interact with the agent to test its output. Since this notebook called `mlflow.langchain.autolog()` you can view the trace for each step the agent takes.

# COMMAND ----------

# TODO: replace this placeholder input example with an appropriate domain-specific example for your agent
for event in agent.stream({"messages": [{"role": "user", "content": "Can you give me some troubleshooting steps for SoundWave X5 Pro Headphones that won't connect?"}]}):
    print(event, "---" * 20 + "\n")

# COMMAND ----------

# Log agent 

mlflow.models.set_model(agent)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps
# MAGIC
# MAGIC You can rerun the cells above to iterate and test the agent.
# MAGIC
# MAGIC Go to the auto-generated [driver]($./driver) notebook in this folder to log, register, and deploy the agent.
