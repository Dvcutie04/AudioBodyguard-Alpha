from __future__ import annotations
import json
import statistics
import time
from pathlib import Path
from .classical_backend import ClassicalReferenceBackend
from .quantum_work_item import QuantumWorkItem
from .metrics import rmse, mae

POLICY="benchmark-v1"
SIZES=(4,8,16,32)
SEEDS=tuple(range(1,11))

def make_item(n:int,seed:int)->QuantumWorkItem:
    values=[((i+1)*(seed+3)%97)/97.0 for i in range(n)]
    return QuantumWorkItem.from_features(f"bench-n={n}-seed={seed:02d}",values,"v1","aqss_bayesian_v1","0.1.0")

def run_once(backend,item):
    t0=time.perf_counter_ns()
    result=backend.execute(item)
    wall=time.perf_counter_ns()-t0
    result["wall_runtime_ns"]=wall
    result["compute_runtime_ns"]=result.get("classical_runtime_ns",result.get("quantum_runtime_ns"))
    result["rmse"]=rmse(result["result"],list(item.feature_vector))
    result["mae"]=mae(result["result"],list(item.feature_vector))
    return result

def main():
    backend=ClassicalReferenceBackend()
    rows=[]
    for n in SIZES:
        for seed in SEEDS:
            item=make_item(n,seed)
            r=run_once(backend,item)
            rows.append({"n":n,"seed":seed,"backend":r["backend"],"status":r["status"],"wall_runtime_ns":r["wall_runtime_ns"],"compute_runtime_ns":r["compute_runtime_ns"],"rmse":r["rmse"],"mae":r["mae"],"shots":r["shots"],"qubits":r["qubits"],"telemetry_hash":r["telemetry_hash"]})
    summary=[]
    for n in SIZES:
        g=[r for r in rows if r["n"]==n]
        summary.append({"n":n,"runs":len(g),"median_wall_runtime_ns":int(statistics.median(r["wall_runtime_ns"] for r in g)),"median_compute_runtime_ns":int(statistics.median(r["compute_runtime_ns"] for r in g)),"max_rmse":max(r["rmse"] for r in g),"max_mae":max(r["mae"] for r in g)})
    out={"protocol":POLICY,"sizes":list(SIZES),"seeds":list(SEEDS),"rows":rows,"summary":summary}
    Path("research_loop_benchmark.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    print("BENCHMARK_V1_OK")
    print("ROWS=",len(rows))
    print("SIZES=",[x["n"] for x in summary])
    print("RUNS_PER_SIZE=",[x["runs"] for x in summary])
    print("MAX_RMSE=",max(r["rmse"] for r in rows))
    print("MAX_MAE=",max(r["mae"] for r in rows))

if __name__=="__main__":
    main()
