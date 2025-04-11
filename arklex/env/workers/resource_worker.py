import logging

from langgraph.graph import StateGraph, START
from langchain_openai import ChatOpenAI


from arklex.env.workers.worker import BaseWorker, register_worker
from arklex.utils.graph_state import MessageState
from arklex.env.tools.utils import ToolGenerator
from arklex.env.tools.RAG.search import SearchEngine
from arklex.utils.model_config import MODEL
from arklex.utils.model_provider_config import PROVIDER_MAP


logger = logging.getLogger(__name__)

class ResourceSearchEngine(SearchEngine):
      def search(self, state: MessageState):
            # Add custom search filter, e.g. Youtube, LeetCode, etc
            state["input"] += "site:youtube.com OR site:leetcode.com OR site:geeksforrgeeks.org"
            return super().search(state)

@register_worker
class ResourcesWorker(BaseWorker):

    description = "Recommend high-quality external resources (e.g LeetCode, Yotube videos, blogs)"
                  "based on the user's role, company or domain to help them prepare for interviews."

    def __init__(self):
        super().__init__()
        self.action_graph = self._create_action_graph()
        self.llm = PROVIDER_MAP.get(MODEL['llm_provider'], ChatOpenAI)(
            model=MODEL["model_type_or_path"], timeout=30000
        )
     
    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker

        resource_search_engine = ResourceSearchEngine()
        workflow.add_node("resource_search_engine", resource_search_engine.search)
        workflow.add_node("tool_generator", ToolGenerator.context_generate)
        # Add edges
        workflow.add_edge(START, "resource_search_engine")
        workflow.add_edge("resource_search_engine", "tool_generator")
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result
