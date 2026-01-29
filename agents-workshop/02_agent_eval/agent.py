import json
from typing import Any, Callable, Generator, Optional
from uuid import uuid4
import warnings

import backoff
import mlflow
import openai
from databricks.sdk import WorkspaceClient
from databricks_openai import UCFunctionToolkit, VectorSearchRetrieverTool
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)
from openai import OpenAI
from pydantic import BaseModel
from unitycatalog.ai.core.base import get_uc_function_client

############################################
# Define your LLM endpoint and system prompt
############################################
LLM_ENDPOINT_NAME = "databricks-gpt-oss-120b"
#LLM_ENDPOINT_NAME = "databricks-gpt-5-mini"


SYSTEM_PROMPT = "You are a customer success specialist that helps users with product questions as part of a Databricks lab. Use tools to retrieve all information needed and help customers fully understand the products they're asking about. Aim to provide value in every interaction."

#SYSTEM_PROMPT = """You are a customer success specialist that helps users with product questions as part of a Databricks lab. Use tools to retrieve all information needed and answer in a friendly, conversational tone. Answer only the specific question without adding made-up features, colors, or generic commentary. Do not tell the user to contact support - you are the support. Be concise. Use lists for options, steps for instructions."""



###############################################################################
## Define tools for your agent, enabling it to retrieve data or take actions
## beyond text generation
## To create and see usage examples of more tools, see
## https://docs.databricks.com/generative-ai/agent-framework/agent-tool.html
###############################################################################
class ToolInfo(BaseModel):
    """
    Class representing a tool for the agent.
    - "name" (str): The name of the tool.
    - "spec" (dict): JSON description of the tool (matches OpenAI Responses format)
    - "exec_fn" (Callable): Function that implements the tool logic
    """

    name: str
    spec: dict
    exec_fn: Callable


def create_tool_info(tool_spec, exec_fn_param: Optional[Callable] = None):
    tool_spec["function"].pop("strict", None)
    tool_name = tool_spec["function"]["name"]
    udf_name = tool_name.replace("__", ".")

    # Define a wrapper that accepts kwargs for the UC tool call,
    # then passes them to the UC tool execution client
    def exec_fn(**kwargs):
        function_result = uc_function_client.execute_function(udf_name, kwargs)
        if function_result.error is not None:
            return function_result.error
        else:
            return function_result.value
    return ToolInfo(name=tool_name, spec=tool_spec, exec_fn=exec_fn_param or exec_fn)


TOOL_INFOS = []

# You can use UDFs in Unity Catalog as agent tools
UC_TOOL_NAMES = ["agents_lab.product.*"]

uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)
uc_function_client = get_uc_function_client()
for tool_spec in uc_toolkit.tools:
    TOOL_INFOS.append(create_tool_info(tool_spec))


# Use Databricks vector search indexes as tools
# See [docs](https://docs.databricks.com/generative-ai/agent-framework/unstructured-retrieval-tools.html) for details

# # (Optional) Use Databricks vector search indexes as tools
# # See https://docs.databricks.com/generative-ai/agent-framework/unstructured-retrieval-tools.html
# # for details
VECTOR_SEARCH_TOOLS = []
# # TODO: Add vector search indexes as tools or delete this block
VECTOR_SEARCH_TOOLS.append(
    VectorSearchRetrieverTool(
        index_name="agents_lab.product.product_docs_index",
        tool_name="search_product_docs",
        tool_description="Use this tool to search for product documentation.",
        num_results=1,
        disable_notice=True)
    )
for vs_tool in VECTOR_SEARCH_TOOLS:
    TOOL_INFOS.append(create_tool_info(vs_tool.tool, vs_tool.execute))



class ToolCallingAgent(ResponsesAgent):
    """
    Class representing a tool-calling Agent
    """

    def __init__(self, llm_endpoint: str, tools: list[ToolInfo]):
        """Initializes the ToolCallingAgent with tools."""
        self.llm_endpoint = llm_endpoint
        self.workspace_client = WorkspaceClient()
        self.model_serving_client: OpenAI = (
            self.workspace_client.serving_endpoints.get_open_ai_client()
        )
        self._tools_dict = {tool.name: tool for tool in tools}

    def get_tool_specs(self) -> list[dict]:
        """Returns tool specifications in the format OpenAI expects."""
        return [tool_info.spec for tool_info in self._tools_dict.values()]

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tool_name: str, args: dict) -> Any:
        """Executes the specified tool with the given arguments."""
        return self._tools_dict[tool_name].exec_fn(**args)

    def call_llm(self, messages: list[dict[str, Any]]) -> Generator[dict[str, Any], None, None]:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="PydanticSerializationUnexpectedValue")
            for chunk in self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=to_chat_completions_input(messages),
                tools=self.get_tool_specs(),
                stream=True,
            ):
                chunk_dict = chunk.to_dict()
                if len(chunk_dict.get("choices", [])) > 0:
                    yield chunk_dict

    def handle_tool_call(
        self,
        tool_call: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> ResponsesAgentStreamEvent:
        """
        Execute tool calls, add them to the running message history, and return a ResponsesStreamEvent w/ tool output
        """
        args = json.loads(tool_call["arguments"])
        result = str(self.execute_tool(tool_name=tool_call["name"], args=args))

        tool_call_output = self.create_function_call_output_item(tool_call["call_id"], result)
        messages.append(tool_call_output)
        return ResponsesAgentStreamEvent(type="response.output_item.done", item=tool_call_output)

    def call_and_run_tools(
        self,
        messages: list[dict[str, Any]],
        max_iter: int = 10,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        for _ in range(max_iter):
            last_msg = messages[-1]
            if last_msg.get("role", None) == "assistant":
                return
            elif last_msg.get("type", None) == "function_call":
                yield self.handle_tool_call(last_msg, messages)
            else:
                yield from output_to_responses_items_stream(
                    chunks=self.call_llm(messages), aggregator=messages
                )

        yield ResponsesAgentStreamEvent(
            type="response.output_item.done",
            item=self.create_text_output_item("Max iterations reached. Stopping.", str(uuid4())),
        )

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        messages = to_chat_completions_input([i.model_dump(warnings="none") for i in request.input])
        if SYSTEM_PROMPT:
            messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        yield from self.call_and_run_tools(messages=messages)


# Log the model using MLflow
mlflow.openai.autolog()
AGENT = ToolCallingAgent(llm_endpoint=LLM_ENDPOINT_NAME, tools=TOOL_INFOS)
mlflow.models.set_model(AGENT)
