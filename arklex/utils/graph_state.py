from typing import TypedDict, Any, Annotated, Optional, Union, List
import janus
from pydantic import BaseModel
from enum import Enum


### Bot-related classes
class BotConfig(BaseModel):
    bot_id: str
    version: str
    language: str
    bot_type: str

### Message-related classes

class ConvoMessage(BaseModel):
    history: str # it could be the whole original message or the summarization of the previous conversation from memory module
    message: str


class OrchestratorMessage(BaseModel):
    message: str
    attribute: dict


### Slot-related classes

class Slot(BaseModel):
    name: str
    type: Union[str, int, float, bool, None]
    value: Union[str, int, float, bool, List[str], None]
    enum: Optional[list[Union[str, int, float, bool, None]]]
    description: str
    prompt: str
    required: bool
    verified: bool


class Slots(BaseModel):
    slots: list[Slot]

# May not be needed
class SlotDetail(Slot):
    verified_value: str
    confirmed: bool

class Verification(BaseModel):
    thought: str
    verification_needed: bool


### Task status-related classes

class StatusEnum(Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    STAY = "stay"


# class Score(BaseModel):
    # score: int


class MessageState(TypedDict):
    # Candidate email
    candidate_id: str

    # Role candidate applied for
    applied_role: str
    
    # personal questions
    personal_asked: int

    # number of behavioural questions asked
    behavioural_count: int

    # number of technical questions asked
    technical_count: int

    # score of the candidate
    score: int

    # system configuration
    sys_instruct: str
    # bot configuration
    bot_config: BotConfig
    # input message
    user_message: ConvoMessage
    orchestrator_message: OrchestratorMessage
    # action trajectory
    trajectory: list[dict[str, any]]
    # message flow between different nodes
    message_flow: Annotated[str, "message flow between different nodes"]
    # final response
    response: str
    # task-related params
    status: StatusEnum
    slots: dict[str, list[Slot]]  # record the dialogue states of each action
    metadata: dict[str, any]
    # stream
    is_stream: bool
    message_queue: janus.SyncQueue


class Timing(TypedDict):
    taskgraph: Optional[float]

class PathNode(TypedDict):
    node_id: str
    is_skipped: bool
    in_flow_stack: bool
    nested_graph_node_value: Optional[str]
    nested_graph_leaf_jump: Optional[str]


class Metadata(TypedDict):
    chat_id: str
    turn_id: int
    hitl: Optional[str]
    timing: Timing

class Taskgraph(TypedDict):
    dialog_states: dict[str, Any]
    path: list[PathNode]
    curr_node: Optional[str]
    intent: Optional[str]
    node_limit: dict[str, int]
    nlu_records: list
    node_status: dict[str, StatusEnum]
    available_global_intents: list

class Memory(TypedDict):
    history: list[dict[str, Any]]
    tool_response: dict

class Params(TypedDict):
    metadata: Metadata
    taskgraph: Taskgraph
    memory: Memory

class NodeInfo(TypedDict):
    resource_id: str
    resource_name: str
    can_skipped: bool
    is_leaf: bool
    attributes: dict[str, Any]
    add_flow_stack: Optional[bool]