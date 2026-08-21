import unittest, asyncio
from src.voice.async_stream import AsyncVoiceStream

class TestAsyncVoiceStream(unittest.TestCase):
    def test_async_stream_processing(self):
        async def run_test():
            stream = AsyncVoiceStream()
            queue = asyncio.Queue()
            await queue.put([0.1, -0.2, 0.3])
            await queue.put([[0.001, -0.001], [0.002, -0.002]])
            return await stream.process_stream(queue)
        results = asyncio.run(run_test())
        self.assertEqual(len(results), 2)
        self.assertIn("route", results[0])
