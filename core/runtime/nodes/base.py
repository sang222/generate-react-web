from __future__ import annotations

from abc import ABC, abstractmethod

from core.runtime.node_result import NodeResult
from core.runtime.state import RuntimeState


class RuntimeNode(ABC):
    name: str

    @abstractmethod
    def run(self, state: RuntimeState) -> NodeResult:
        raise NotImplementedError
