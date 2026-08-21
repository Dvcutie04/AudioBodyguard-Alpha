import asyncio
from src.voice.orchestrator import SpatialVoiceEngine

class AsyncVoiceStream:
    def __init__(self):
        self.engine = SpatialVoiceEngine()

    async def process_stream(self, frame_queue):
        results = []
        while not frame_queue.empty():
            frame = await frame_queue.get()
            res = self.engine.process_frame(frame)
            results.append(res)
            frame_queue.task_done()
        return results
