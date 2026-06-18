from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from app.schemas import PipelineRunResponse, OcrResult, ExtractionResult, ValidationResult
from app.services.extraction import ExtractionService
from app.services.ocr import OcrService
from app.services.validation import ValidationService


# Define the Global State Dictionary
class GraphState(TypedDict):
    document_id: str
    document_type: str
    ocr: Optional[OcrResult]
    extraction: Optional[ExtractionResult]
    validation: Optional[ValidationResult]
    summary: Optional[str]
    error: Optional[str]


class OrchestratorService:
    """Coordinates the baseline OCR -> extraction -> validation -> summary workflow."""

    def __init__(
            self,
            ocr_service: OcrService,
            extraction_service: ExtractionService,
            validation_service: ValidationService,
            summary_service: Any,
    ) -> None:
        self.ocr_service = ocr_service
        self.extraction_service = extraction_service
        self.validation_service = validation_service
        self.summary_service = summary_service

        # Compile the graph when the service initializes
        self.workflow = self._build_graph()

    def _build_graph(self):
        """Builds and compiles the LangGraph state machine."""
        workflow = StateGraph(GraphState)

        # Define the Agent Nodes
        async def ocr_node(state: GraphState):
            try:
                result = await self.ocr_service.run(document_id=state["document_id"])
                return {"ocr": result}
            except Exception as e:
                return {"error": f"OCR Node Failed: {str(e)}"}

        async def extraction_node(state: GraphState):
            if state.get("error"): return {}
            try:
                result = await self.extraction_service.extract(
                    document_id=state["document_id"],
                    ocr_text=state["ocr"].text,
                    layout_blocks=state["ocr"].blocks,
                    document_type=state["document_type"],
                )
                return {"extraction": result}
            except Exception as e:
                return {"error": f"Extraction Node Failed: {str(e)}"}

        async def validation_node(state: GraphState):
            if state.get("error"): return {}
            try:
                result = await self.validation_service.validate(
                    document_id=state["document_id"],
                    extracted_data=state["extraction"].data,
                )
                return {"validation": result}
            except Exception as e:
                return {"error": f"Validation Node Failed: {str(e)}"}

        async def summary_node(state: GraphState):
            if state.get("error"): return {}
            try:
                result = await self.summary_service.generate(
                    extracted_data=state["extraction"].data,
                    validation_issues=state["validation"].issues
                )
                return {"summary": result}
            except Exception as e:
                return {"error": f"Summary Node Failed: {str(e)}"}

        # Define Conditional Routing
        def route_after_ocr(state: GraphState):
            if state.get("error"): return END
            return "extraction_agent"

        def route_after_extraction(state: GraphState):
            if state.get("error"): return END
            return "validation_agent"

        # Wire the Topology
        workflow.add_node("ocr_agent", ocr_node)
        workflow.add_node("extraction_agent", extraction_node)
        workflow.add_node("validation_agent", validation_node)
        workflow.add_node("summary_agent", summary_node)

        # starting point
        workflow.set_entry_point("ocr_agent")

        # Conditional Edges
        workflow.add_conditional_edges("ocr_agent", route_after_ocr, {
            "extraction_agent": "extraction_agent",
            END: END
        })
        workflow.add_conditional_edges("extraction_agent", route_after_extraction, {
            "validation_agent": "validation_agent",
            END: END
        })

        workflow.add_edge("validation_agent", "summary_agent")
        workflow.add_edge("summary_agent", END)

        return workflow.compile()

    async def run_pipeline(
            self, document_id: str, document_type: str = "unknown"
    ) -> PipelineRunResponse:
        """Triggers the compiled LangGraph pipeline dynamically."""

        # Initialize the state
        initial_state: GraphState = {
            "document_id": document_id,
            "document_type": document_type,
            "ocr": None,
            "extraction": None,
            "validation": None,
            "error": None
        }

        # Execute the graph
        final_state = await self.workflow.ainvoke(initial_state)

        if final_state.get("error"):
            raise RuntimeError(f"Pipeline Execution Halted: {final_state['error']}")

        # Return expected
        return PipelineRunResponse(
            document_id=document_id,
            ocr=final_state["ocr"],
            extraction=final_state["extraction"],
            validation=final_state["validation"],
            summary=final_state.get("summary")
        )