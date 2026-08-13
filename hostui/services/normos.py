from hostui.services.registry import RegistryService
from hostui.services.markup import analyze_document_pipeline
from hostui.services.exporter import record_oov_proposal

# Единый кэшированный экземпляр реестра
_GLOBAL_REGISTRY = RegistryService()

def analyze_document(text: str, layers: list = None) -> dict:
    """Точка входа для обратной совместимости."""
    return analyze_document_pipeline(text=text, layers=layers, registry=_GLOBAL_REGISTRY)