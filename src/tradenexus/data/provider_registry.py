from typing import Dict, List
from tradenexus.data.provider_interface import DataProvider

_registry: Dict[str, DataProvider] = {}
_fallback_order: List[str] = []

def register_provider(provider: DataProvider):
    """
    Registers a DataProvider in the system registry.
    """
    name = provider.provider_name
    _registry[name] = provider
    if name not in _fallback_order:
        _fallback_order.append(name)

def get_provider(name: str) -> DataProvider:
    """
    Retrieves the registered DataProvider instance by name.
    """
    if name not in _registry:
        raise ValueError(f"Provider '{name}' is not registered.")
    return _registry[name]

def list_registered_providers() -> List[str]:
    """
    Returns the names of all registered providers.
    """
    return list(_registry.keys())

def get_fallback_chain() -> List[str]:
    """
    Returns the configured fallback search order of provider names.
    """
    return _fallback_order

def set_fallback_chain(order: List[str]):
    """
    Overrides the fallback search order.
    """
    global _fallback_order
    # Verify that all providers exist in registry
    for name in order:
        if name not in _registry:
            raise ValueError(f"Cannot set fallback order: provider '{name}' is not registered.")
    _fallback_order = list(order)
