class DocumentNotFoundError(Exception):
    pass


class LLMError(Exception):
    pass


class EmbeddingError(Exception):
    pass


class VectorStoreError(Exception):
    pass


class GuardrailViolation(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Guardrail violation: {reason}")


class UnsupportedSourceError(Exception):
    pass
