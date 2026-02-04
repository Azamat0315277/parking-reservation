from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from src.workflow.nodes import (
    assistant_node,
    classify_intent_node,
    human_approval_node,
    reservation_node,
    file_recording_node,
    denial_node,
    succesfull_reservation_node,
    route_after_approval,
    route_after_reservation,
    route_after_classification,
    ParkingState
)


workflow = StateGraph(ParkingState)

workflow.add_node("assistant", assistant_node)
workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("human_approval", human_approval_node)
workflow.add_node("reservation", reservation_node)
workflow.add_node("file_recording", file_recording_node)
workflow.add_node("denial", denial_node)
workflow.add_node("succesfull_reservation", succesfull_reservation_node)

workflow.add_edge(START, "assistant")
workflow.add_edge("assistant", "classify_intent")
workflow.add_conditional_edges("classify_intent", route_after_classification)
workflow.add_conditional_edges("human_approval", route_after_approval)
workflow.add_conditional_edges("reservation", route_after_reservation)
workflow.add_edge("file_recording", "succesfull_reservation")
workflow.add_edge("succesfull_reservation", END)
workflow.add_edge("denial", END)

parking_graph = workflow.compile(checkpointer=InMemorySaver())