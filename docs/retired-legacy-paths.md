# Paths retired from the active phone snapshot

The verified 423-file phone export includes every current source and test in `src` and `tests` except the deliberately excluded quarantine directory. The older GitHub main branch has the paths below that are absent from both phone exports, as well as one corrupt module present in the supplement. Older tests refer to incompatible APIs. The current snapshot has no static imports of the retired modules.

These paths are removed from the proposed active tree so the repository runs the phone's current set of tests. Their contents remain available in Git history at commit `bb94b174e11ddbe09e11c05598f80aa9e7161be0`; this is a scoped migration, not a claim that each old test is covered by an equivalent new test. Reconsider any retired invariant as a separate future migration with an appropriate test against the current contract.

## Unused, preexisting corrupt module (1)

- `audio_engine/mesh_fusion.py` — byte-identical in the phone supplement and old GitHub commit, but contains multiple invalid Python tokens and is not imported by current source or tests. It was retired without introducing replacement logic; future mesh fusion work requires a qualified implementation and dedicated tests.

## Legacy source modules (39)

- `src/acoustic/event_graph.py`
- `src/audit/receipt.py`
- `src/bridges/__init__.py`
- `src/bridges/codec.py`
- `src/bridges/envelope.py`
- `src/bridges/protocol.py`
- `src/bridges/validator.py`
- `src/control/canonical.py`
- `src/device_fabric/adapter.py`
- `src/device_fabric/digital_twin.py`
- `src/device_fabric/event_log.py`
- `src/device_fabric/lineage.py`
- `src/device_fabric/precondition.py`
- `src/device_fabric/registry.py`
- `src/device_fabric/router.py`
- `src/device_fabric/transaction.py`
- `src/edge/protocol.py`
- `src/inference/evidence.py`
- `src/inference/gate.py`
- `src/inference/threat_inference_engine.py`
- `src/intent/action_intent.py`
- `src/omotenashi/acoustic_interaction_graph.py`
- `src/omotenashi/conversation_policy.py`
- `src/omotenashi/hypothesis_gate.py`
- `src/omotenashi/safety_governor.py`
- `src/personalization/omotenashi.py`
- `src/policy/governor.py`
- `src/predictive_mitigation.py`
- `src/quantum/classifier.py`
- `src/quantum/quantum_state_mapping.py`
- `src/router/signal_router.py`
- `src/security/causal_trust_mesh.py`
- `src/src/device_fabric/adapter.py`
- `src/src/security/causal_attestation.py`
- `src/src/security/causal_mesh.py`
- `src/src/security/causal_trust.py`
- `src/src/security/causal_undo.py`
- `src/telemetry/telemetry_node.py`
- `src/tv/tv_state_machine.py`

## Legacy test modules and fixtures (30)

- `src/src/security/test_causal_attestation.py`
- `src/src/security/test_causal_mesh.py`
- `src/src/security/test_causal_trust.py`
- `src/src/security/test_causal_undo.py`
- `tests/conftest.py`
- `tests/device_fabric/test_contracts.py`
- `tests/device_fabric/test_device_fabric_adversarial_hil.py`
- `tests/inference/test_integrated_trajectory.py`
- `tests/inference/test_threat_trajectory.py`
- `tests/integration/test_full_pipeline_trace.py`
- `tests/omotenashi/__init__.py`
- `tests/omotenashi/test_acoustic_interaction_graph.py`
- `tests/omotenashi/test_conversation_policy.py`
- `tests/omotenashi/test_hypothesis_gate.py`
- `tests/omotenashi/test_safety_governor.py`
- `tests/test_bridges.py`
- `tests/test_causal_trust_mesh_engine.py`
- `tests/test_device_fabric.py`
- `tests/test_device_fabric_digital_twin.py`
- `tests/test_device_fabric_lineage.py`
- `tests/test_edge_protocol.py`
- `tests/test_end_to_end_pipeline.py`
- `tests/test_full_pipeline_end_to_end.py`
- `tests/test_phase2_capstone.py`
- `tests/test_phase_b_integration.py`
- `tests/test_quantum_state_mapping_engine.py`
- `tests/test_telemetry_node.py`
- `tests/test_threat_inference_engine.py`
- `tests/test_tv_state_machine.py`
- `tests/test_vertical_slice_lineage.py`

## Old recovery/backup copies (5)

- `src/core/sensor_trust/trust_model.py.bak-before-aqss-fix`
- `src/core/sensor_trust/trust_model.py.bak-before-clean-repair`
- `src/engine/benchmark.py.pre-encoding-repair`
- `src/research_loop/phase15/dataset.py.phase15-prehardening`
- `tests/inference/tests/inference`

## Older root files outside the current phone exports (20)

The review branch retains the project README, credential-free `.env.example`, and restoration documentation. The other older root files below are absent from both verified phone exports and are not needed by current tests. Several are broken or misleading: the encoded text is incomplete, `audio/fingerprint.py` imports the missing `send_home`, the bare `bridges` file is not a Python package, and `scripts/pair_device.py` bypasses TLS certificate checks. The reports and example profiles below have not been revalidated against this snapshot. Their contents remain available in Git history.

- `Claude’s response /text.txt`
- `analyze_logs.py`
- `aqss_instructor_report.md`
- `aqss_phase1_core.py`
- `aqss_trials.json`
- `audio/fingerprint.py`
- `bell_test.py`
- `bridges`
- `docs/bayesian_adapter_architecture.md`
- `haptic_bridge.py`
- `include/aqss_core.h`
- `live_test_profile.json`
- `make_report.py`
- `mock_test_profile.json`
- `omega_truth.py`
- `research_loop_benchmark.json`
- `scripts/benchmark_latency.py`
- `scripts/pair_device.py`
- `test_profile.json`
- `test_router_profile.json`
