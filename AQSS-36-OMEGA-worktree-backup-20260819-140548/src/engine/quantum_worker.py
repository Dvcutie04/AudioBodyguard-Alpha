import queue, sqlite3, json
from src.engine.schemas import QuantumResearchJob

class IBMQuantumWorker:
    def __init__(self, job_queue: queue.Queue, db_path: str = "events.db", backend_name: str = "ibm_sherbrooke"):
        self.job_queue = job_queue
        self.db_path = db_path
        self.backend_name = backend_name
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS scientific_log (job_id TEXT PRIMARY KEY, experiment TEXT, shots INTEGER, circuit_spec TEXT, quantum_result TEXT, created_ns INTEGER, logged_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()
        conn.close()

    def process_job(self, job: QuantumResearchJob, mock_result: dict = None):
        result = mock_result or {"counts": {"00": job.shots // 2, "11": job.shots // 2}}
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO scientific_log (job_id, experiment, shots, circuit_spec, quantum_result, created_ns) VALUES (?, ?, ?, ?, ?, ?)", (job.job_id, job.experiment, job.shots, json.dumps(job.circuit_spec), json.dumps(result), job.created_ns))
        conn.commit()
        conn.close()
        print(f"[QUANTUM WORKER OK] Processed {job.job_id} | Shots: {job.shots}", flush=True)
