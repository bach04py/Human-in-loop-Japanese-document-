from app.schemas import FeedbackRequest, FeedbackResponse


class CorrectionMemoryService:
    """In-memory placeholder for week 1; Postgres/vector memory comes later."""

    def __init__(self) -> None:
        self._feedback: list[FeedbackRequest] = []

    async def store_feedback(self, feedback: FeedbackRequest) -> FeedbackResponse:
        self._feedback.append(feedback)
        return FeedbackResponse(document_id=feedback.document_id, stored=True)
