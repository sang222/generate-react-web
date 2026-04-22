from __future__ import annotations

import tempfile
import unittest

from core.runtime.checkpoints import Checkpointer
from core.runtime.graph import RuntimeGraph
from core.runtime.node_result import NodeResult
from core.runtime.nodes.base import RuntimeNode
from core.runtime.state import RunIdentity, RuntimeState


class DoneNode(RuntimeNode):
    name = "done_node"

    def run(self, state: RuntimeState) -> NodeResult:
        return NodeResult(status="DONE", updates={"execution_mode": "frontend_only"})


class RuntimeGraphTest(unittest.TestCase):
    def test_graph_runs_node_and_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = RuntimeState(
                identity=RunIdentity(project_id="p", epic_id="e", story_id="s", run_id="r"),
                task="build ui",
            )
            state.execution.phase = "bootstrap"
            graph = RuntimeGraph(nodes={"bootstrap": DoneNode()}, checkpointer=Checkpointer(tmp))
            result = graph.run(state)
            self.assertEqual(result.execution.phase, "done")
            self.assertEqual(result.execution_mode, "frontend_only")
