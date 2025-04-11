import os
import logging
import sqlite3
from langgraph.graph import StateGraph, START
from arklex.env.workers.worker import BaseWorker, register_worker
from arklex.types import EventType 
from arklex.utils.graph_state import MessageState

logger = logging.getLogger(__name__)

@register_worker
class AnswerStorageWorker(BaseWorker):

    description = "Stores answered interview questions."

    def __init__(self):
        super().__init__()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "..", "database", "interview_db.db")

        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.action_graph = self._create_action_graph()

    def save_candidate_answer_to_db(self, candidate_id: str, question: str, answer: str, score: int) -> bool:
        try:
            self.cursor.execute("""
                                INSERT OR REPLACE INTO interview_session_logs (candidate_id, question_text, response_text, score, timestamp)
                                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                                """, (candidate_id, question, answer, score))
            self.conn.commit()

            logger.info(f"Answer saved for CandidateID={candidate_id}, Question={question}")

            return True
        except Exception as e:
            logger.error(f"Error saving answer: {e}")
            return False
    
    def generator(self, state: MessageState) -> MessageState:
        user_message = state['user_message']
        orchestrator_message = state['orchestrator_message']
        candidate_id = state.get('candidate_id', 'unknown')

        answer = user_message.message
        
        question = orchestrator_message.message or "the interview question"  # Fallback to generic question

        # score = int(state['score'])
        score = state.get('score', None)  # Optional score handling, if needed

        # Save to DB
        save_success = self.save_candidate_answer_to_db(candidate_id, question, answer, score)
        logger.info(f"[RoleQuestionWorker] Save success: {save_success}")

        # Optional: Respond with confirmation
        state["response"] = "Answer stored successfully." if save_success else "Failed to store answer."
        return state

    def choose_generator(self, state: MessageState):
        if state["is_stream"]:
            return "stream_generator"
        return "generator"
    
    def stream_generator(self, state:MessageState) -> MessageState:
        state = self.generator(state)
        state["message_queue"].put({
            "event": EventType.CHUNK.value,
            "message_chunk": state["response"]
        })
        return state

    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        workflow.add_node("generator", self.generator)
        workflow.add_node("stream_generator", self.stream_generator)
        workflow.add_conditional_edges(START, self.choose_generator)
        return workflow
    
    def execute(self, msg_state:MessageState):
        graph = self.action_graph.compile()
        return graph.invoke(msg_state)

    def __del__(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")