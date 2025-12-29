from typing import Any, Dict, ItemsView


class ServiceRegistry:
    """Simple registry for application services.

    This placeholder can be replaced with real implementations (e.g. game
    engine, analytics, or data providers) without changing the UI code.
    """

    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        self._services[name] = service

    def get(self, name: str) -> Any:
        return self._services[name]

    def items(self) -> ItemsView[str, Any]:
        return self._services.items()

    def names(self) -> list[str]:
        return list(self._services.keys())
