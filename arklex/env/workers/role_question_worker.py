import os
import logging
import sqlite3
from langgraph.graph import StateGraph, START
from arklex.env.workers.worker import BaseWorker, register_worker
from arklex.types import EventType 
from arklex.utils.graph_state import MessageState

logger = logging.getLogger(__name__)



@register_worker
class RoleQuestionWorker(BaseWorker):

    description = "Asks for the candidate's email and role and uses that information to ask role-based interview questions."
    def __init__(self):
        super().__init__()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "..", "database", "mydb.db")

        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.action_graph = self._create_action_graph()

        self.personal_asked = 0
        self.behavioural_count = 0
        self.technical_count = 0
        self.role = None
        self.candidate_id = None


    def get_next_question(self, state: MessageState) -> MessageState:
        # Ask for candidate's name if not provided
        # if not state["candidate_id"]:
        if not self.candidate_id:
            state["response"] = "Welcome! Can I get your email?"
            return state
        self.candidate_id = state["user_message"]
        
        if not self.role:
            state["response"] = "Thank you. What role are you applying for?"
            return state
        self.role = state["user_message"]

        if self.role:
            state["response"] = "Thank you! Let's start with the interview questions"
            return state

        if  self.personal_asked < 2:
            query = "SELECT question_text FROM question_bank WHERE category = 'personal' LIMIT 1 OFFSET ?"
            self.cursor.execute(query, (self.personal_asked,))
            row = self.cursor.fetchone()
            if row:
                state["response"] = row[0]
                self.personal_asked += 1
                return state
        
        if self.behavioural_count < 3:
            query = "SELECT question_text FROM question_bank WHERE category = 'behavioural' LIMIT 1 OFFSET ?"
            self.cursor.execute(query, (self.behavioural_count,))
            row = self.cursor.fetchone()
            if row:
                state["response"] = row[0]
                self.behavioural_count += 1
                # self.set_slot_value(state, "behavioural_count", behavioural_count + 1)
                return state
            else: 
                state["response"] = "No more questions available in this category"

        if self.technical_count < 6:
            query = "SELECT question_text FROM question_bank WHERE category = 'technical' AND role = ? LIMIT 1 OFFSET ?"
            self.cursor.execute(query, (self.role, self.technical_count))
            row = self.cursor.fetchone()
            if row:
                state["response"] = row[0]
                self.technical_count += 1
                return state
            
        state["response"] = "We have come to the end of your interview"
        return state 
    
    def choose_generator(Self, state: MessageState):
        if state["is_stream"]:
            return "stream_generator"
        return "get_next_question"
    
    def stream_generator(self, state: MessageState) -> MessageState:
        # Same logic as get_next_question but streamed chunk-by-chunk
        updated_state = self.get_next_question(state)
        state["message_queue"].put({
            "event": EventType.CHUNK.value,
            "message_chunk": updated_state["response"]
        })
        return updated_state
       
    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each worker
        workflow.add_node("get_next_question", self.get_next_question)
        workflow.add_node("stream_generator", self.stream_generator)
        workflow.add_conditional_edges(START, self.choose_generator)
        return workflow
    

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result
    
    def __del__(self):
        self.conn.close()