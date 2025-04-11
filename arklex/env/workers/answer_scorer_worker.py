import logging
from typing import Any
import re

from langgraph.graph import StateGraph, START
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
# from langchain.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser

from arklex.env.workers.worker import BaseWorker, register_worker
from arklex.env.prompts import load_prompts
from arklex.types import EventType
from arklex.utils.utils import chunk_string
from arklex.utils.graph_state import MessageState
from arklex.utils.model_config import MODEL
from arklex.utils.model_provider_config import PROVIDER_MAP


logger = logging.getLogger(__name__)

@register_worker
class AnswerScorerWorker(BaseWorker):

    description = "The worker scores a candidate's interview answer based on its accuracy, clarity, relevance, structure and completeness."


    def __init__(self):
        super().__init__()
        self.llm = PROVIDER_MAP.get(MODEL['llm_provider'], ChatOpenAI)(
            model=MODEL["model_type_or_path"], timeout=30000
        )
        self.action_graph = self._create_action_graph()

    def generator(self, state: MessageState) -> MessageState:
        # get the input message
        user_message = state['user_message']
        orchestrator_message = state['orchestrator_message']
        answer = user_message.message #assuming the user's answer is here
        question = orchestrator_message.message or "the interview question"

        prompts = load_prompts(state["bot_config"])
        prompt = PromptTemplate.from_template(prompts["answer_review_prompt"])
        input_prompt = prompt.invoke({
            "question": question,
            "answer": answer,
            "sys_instruct": state["sys_instruct"]
        })

        # logger.info(f"[AnswerReviewWorker] Prompt: {input_prompt.text}")
        # logger.debug()
        chunked_prompt = chunk_string(input_prompt.text, tokenizer=MODEL["tokenizer"], max_length=MODEL["context"])
        
        # final_chain = self.llm | self.parser()
        final_chain = self.llm | StrOutputParser()

        # Process the data to select only the score using regex
        raw_output = final_chain.invoke(chunked_prompt)
        match = re.search(r"\d+", raw_output)
        score = int(match.group()) if match else 0
        state["score"] = score

        # state["response"] = score_output
        return state
    
    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("generator", self.generator)
        workflow.set_entry_point("generator")
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result