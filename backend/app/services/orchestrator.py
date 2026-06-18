from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from app.schemas import PipelineRunResponse, OcrResult, ExtractionResult, ValidationResult
from app.services.extraction import ExtractionService
from app.services.ocr import OcrService
from app.services.validation import ValidationService
from app.services.classification import ClassificationService


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
    """Coordinates the autonomous document processing workflow."""

    def __init__(
            self,
            extraction_service: ExtractionService,
            validation_service: ValidationService,
            classification_service: ClassificationService,
            summary_service: Any = None,
            ocr_service: Optional[OcrService] = None,
    ) -> None:
        self.ocr_service = ocr_service
        self.extraction_service = extraction_service
        self.validation_service = validation_service
        self.summary_service = summary_service
        self.classification_service = classification_service

        # Compile the graph when the service initializes
        self.workflow = self._build_graph()

    def _build_graph(self):
        """Builds and compiles the LangGraph state machine."""
        workflow = StateGraph(GraphState)

        # ==========================================
        # 1. Define the Agent Nodes
        # ==========================================
        async def ocr_node(state: GraphState):
            if state.get("ocr"):
                print("[Orchestrator] Using pre-computed OCR data from Microservice...")
                return {"ocr": state["ocr"]}

            try:
                print("[Orchestrator] Running local OCR engine...")
                result = await self.ocr_service.run(document_id=state["document_id"])
                return {"ocr": result}
            except Exception as e:
                return {"error": f"OCR Node Failed: {str(e)}"}

        async def classification_node(state: GraphState):
            if state.get("error"): return {}
            try:
                # Dynamically determine the document type using OCR text
                doc_type = await self.classification_service.classify(state["ocr"].text)
                return {"document_type": doc_type}
            except Exception as e:
                return {"error": f"Classification Node Failed: {str(e)}"}

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

        # ==========================================
        # Wire the Topology
        # ==========================================
        workflow.add_node("ocr_agent", ocr_node)
        workflow.add_node("classification_agent", classification_node)
        workflow.add_node("extraction_agent", extraction_node)
        workflow.add_node("validation_agent", validation_node)
        workflow.add_node("summary_agent", summary_node)

        workflow.set_entry_point("ocr_agent")

        # ==========================================
        # Define the Flow
        # ==========================================
        def route_on_error(state: GraphState, next_node: str):
            if state.get("error"):
                return END
            return next_node

        workflow.add_conditional_edges("ocr_agent", lambda s: route_on_error(s, "classification_agent"))
        workflow.add_conditional_edges("classification_agent", lambda s: route_on_error(s, "extraction_agent"))
        workflow.add_conditional_edges("extraction_agent", lambda s: route_on_error(s, "validation_agent"))
        workflow.add_conditional_edges("validation_agent", lambda s: route_on_error(s, "summary_agent"))
        workflow.add_edge("summary_agent", END)

        return workflow.compile()

    async def run_pipeline(
            self,
            document_id: str,
            precomputed_ocr: Optional[OcrResult] = None
    ) -> PipelineRunResponse:
        """Triggers the compiled LangGraph pipeline."""

        #Inject the precomputed OCR directly into LangGraph's starting state
        initial_state: GraphState = {
            "document_id": document_id,
            "document_type": "unknown",
            "ocr": precomputed_ocr,  # <--- INJECTED HERE
            "extraction": None,
            "validation": None,
            "summary": None,
            "error": None
        }

        # Execute the graph
        final_state = await self.workflow.ainvoke(initial_state)

        # Catch pipeline halts
        if final_state.get("error"):
            raise RuntimeError(final_state['error'])

        # Package and return the successful response
        return PipelineRunResponse(
            document_id=document_id,
            ocr=final_state["ocr"],
            extraction=final_state["extraction"],
            validation=final_state["validation"],
            summary=final_state.get("summary")
        )