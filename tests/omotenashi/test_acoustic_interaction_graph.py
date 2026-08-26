from unittest import TestCase
from src.omotenashi.acoustic_interaction_graph import (
    AcousticEvent,
    InteractionEdge,
    AcousticInteractionGraph
)

class TestAcousticInteractionGraph(TestCase):
    def test_event_and_edge_insertion(self):
        graph = AcousticInteractionGraph()
        
        evt1 = AcousticEvent(
            event_id="evt_1",
            timestamp_ns=1000000,
            source_class="human_speech",
            spatial_sector=1,
            speech_probability=0.92,
            energy=0.65,
            duration_ms=400
        )
        
        evt2 = AcousticEvent(
            event_id="evt_2",
            timestamp_ns=1500000,
            source_class="human_speech",
            spatial_sector=1,
            speech_probability=0.88,
            energy=0.60,
            duration_ms=350
        )
        
        graph.add_event(evt1)
        graph.add_event(evt2)
        
        edge = InteractionEdge(
            source_event_id="evt_1",
            target_event_id="evt_2",
            temporal_delta_ms=500,
            spatial_delta=0.0,
            correlation=0.85,
            turn_transition_score=0.90
        )
        
        graph.add_edge(edge)
        
        self.assertIn("evt_1", graph.events)
        self.assertIn("evt_2", graph.events)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(len(graph.get_neighbors("evt_1")), 1)

if __name__ == "__main__":
    import unittest
    unittest.main()
