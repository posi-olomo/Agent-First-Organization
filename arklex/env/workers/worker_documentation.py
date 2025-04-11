# Used to log information for debugging or monitoring
import logging


import os
from typing import Any, Iterator, Union

# StateGraph: A graph based workflow system used in Arklex AI
# START: The entry point of your workflow graph
# ChatOpenAI: The OpenAI LLM interface from LangChain (used to process
# natural language)
from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI

# BaseWorker: The base class that all custom workers inherit from.

# register_worker: A decorator that tells Arklex to load and recognize this worker.
from arklex.env.workers.worker import BaseWorker, register_worker
# MessageState: Defines the structure of data passed between nodes in your task graph (e.g., user query, context, metadata).
from arklex.utils.graph_state import MessageState
# ToolGenerator: Responsible for generating the final LLM-based response.
from arklex.env.tools.utils import ToolGenerator

from arklex.env.tools.RAG.retrievers.faiss_retriever import RetrieveEngine

# These pull your preferred LLM model (like GPT-4) and connect it to the ChatOpenAI provider.
from arklex.utils.model_config import MODEL
from arklex.utils.model_provider_config import PROVIDER_MAP


logger = logging.getLogger(__name__)

# Registers the class as a worker Arklex can use.
# Inherits from BaseWorker.
@register_worker
class FaissRAGWorker(BaseWorker):

    description = "Answer the user's questions based on the company's internal documentations (unstructured text data), such as the policies, FAQs, and product information"
    # This is a constructor. It calls the parent class constructor
    def __init__(self,
                 # stream_ reponse is a boolean value that determines whether the response should be streamed or not.
                 # i.e in the case of RagMessageWorker it should be set to false.
                 stream_response: bool = True):
        super().__init__()
        self.action_graph = self._create_action_graph()
        self.llm = PROVIDER_MAP.get(MODEL['llm_provider'], ChatOpenAI)(
            model=MODEL["model_type_or_path"], timeout=30000
        )
        self.stream_response = stream_response

    def choose_tool_generator(self, state: MessageState):
        if self.stream_response and state["is_stream"]:
            return "stream_tool_generator"
        return "tool_generator"

    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("retriever", RetrieveEngine.faiss_retrieve)
        workflow.add_node("tool_generator", ToolGenerator.context_generate)
        workflow.add_node("stream_tool_generator", ToolGenerator.stream_context_generate)

        # Add edges
        workflow.add_edge(START, "retriever")
        workflow.add_conditional_edges(
            "retriever", self.choose_tool_generator)
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result
