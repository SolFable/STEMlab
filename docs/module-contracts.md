# Module contracts

These are version-1 scientific data contracts with the 0.2.0 desktop shell,
not a stable public plugin ABI. The desktop does not change the input format.

## Mathematical model

`SimulationModel` in `modeling.py` is a structural Python protocol:

```python
description: ModelDescription
initial_state: tuple[float, ...]
def rhs(time_s: float, state: tuple[float, ...]) -> tuple[float, ...]: ...
```

`ModelDescription` declares a model ID/version, ordered state quantities with
units/descriptions, parameters with units/descriptions, equations, assumptions,
limitations, and consumed environment fields. Parameter values and initial
conditions live in the experiment configuration. Each derivative has the unit
of its corresponding state variable divided by seconds.

`rhs` is deterministic and free of external side effects; it cannot mutate
state, sample history, environment, or UI. State length/order must match the
description. The adapter checks size and finiteness for initial state, every
RHS result, intermediate states, and final samples. The model is responsible
for physical-domain validity. Runtime unit conversion and symbolic dimensional
analysis are deferred; exact documented SI conventions are mandatory.

## Environment

`EnvironmentConfig.from_dict` validates a JSON object containing:

| Field | Contract |
| --- | --- |
| `schema_version` | Integer 1 |
| `id` | Nonblank reusable profile identity |
| `category` | Lowercase identifier; built-ins `land`, `marine`, `air` |
| `gravity_m_s2` | Three finite numbers `[gx, gy, gz]` in the world frame |
| `properties` | Named finite scalars; exact keys/ranges for built-ins |

LAND stores `friction_coefficient` (dimensionless) and `terrain_height_m` (m).
MARINE stores `fluid_density_kg_m3` (kg/m³) and three `current_*_m_s` components.
AIR stores `fluid_density_kg_m3`, `temperature_K` (K), and three `wind_*_m_s`
components. These are user-specified uniform reference values, not calculated
material constants or an equation-of-state model. The environment is reusable
without knowledge of body mass, geometry, renderer, or engine.

`properties` is copied into a read-only mapping. Serializing with `to_dict`
returns a fresh JSON-compatible object. Existing built-in property sets are
deliberately strict; broader field descriptions need a schema revision.

## Experiment configuration

`load_experiment(path) -> ExperimentConfig` reads UTF-8 strict JSON.
`ExperimentConfig.from_dict(data)` and `to_dict()` support normalized round trips.
Inputs are frozen typed records. Directly constructed records are revalidated
at `run_experiment`; dataclass construction alone is not the validation API.

The experiment envelope contains exactly `schema_version`, `id`, `environment`,
`model`, and `solver`. Environments are embedded snapshots rather than external
paths so experiments remain self-contained. Reuse a standalone environment
example by copying its object into an experiment's `environment` field.

The only current model specification is:

```json
{
  "id": "constant_acceleration_1d",
  "version": "1",
  "axis": "z",
  "parameters": {"applied_acceleration_m_s2": 0.0},
  "initial_state": {"position_m": 100.0, "velocity_m_s": 0.0}
}
```

The solver specifies `id="python_rk4"`, `version="1"`, positive finite `dt_s`,
and an integer `steps` from 1 through 100,000. Time starts at 0 s, and the
history includes `steps + 1` samples. End time is `steps * dt_s`; no truncated
last step or interpolation is hidden in this configuration.

Packaged `schemas/*.schema.json` use JSON Schema Draft 2020-12. IDs under
`stemlab.example` are identifiers, not hosted services. Resolve the relative
environment reference from the packaged files or an offline schema registry.
The runtime uses explicit validators rather than a general schema library.
Parity tests cover common constraints. Runtime additionally rejects duplicate
keys, non-standard NaN/Infinity, floating-point overflow, half-step underflow,
and overflowing final time. Integer fields require actual Python/JSON integers,
whereas JSON Schema also treats integer-valued floats as integers. New schema
and validator changes must be reviewed together; no automatic migration occurs.

## Engine adapter

`SimulationAdapter` exposes `id`, `version`, and:

```python
def run(model: SimulationModel, solver: SolverConfig) -> tuple[Sample, ...]: ...
```

`Sample` is immutable, with `time_s` and an ordered state tuple. RK4 supports
explicit ODEs only, CPU binary64, fixed steps, no events or constraints.
Times are computed from integer indices rather than repeated addition;
each interval uses its actual floating-point width between adjacent grid points.
No engine-specific object crosses the model/result boundary.

An adapter must fail on unsupported settings, state shape errors, or nonfinite
results. `SimulationError` signals invalid numerical output. The reference
adapter does not estimate truncation error, prove stability, or enforce physical
conservation automatically. Future external engines need capability negotiation
and their own request/result types where an ODE interface is inappropriate.

## Application, analysis, and results

`run_experiment(config) -> ExperimentResult` composes the one supported model
and adapter and runs the proof's analytical validation. A failed comparison
raises `SimulationError`. `validate_constant_acceleration` reports maximum
position/velocity absolute errors and per-state absolute/relative tolerances.
It checks every sample; a small aggregate error cannot hide a failed sample.

`ExperimentResult.to_dict()` emits result schema version 1 with:

- `configuration`: full normalized experiment, including model/solver versions.
- `provenance`: input/source hashes, STEMLab/Python/platform identity, arithmetic,
  time grid, absence of randomness, adapter identity, runtime dependencies.
- `model_description` and `resolved_model`: scientific metadata and effective acceleration.
- `history`: ordered objects with `time_s` and `state` in declared order/units.
- `validation`: reference equations, tolerances, maximum errors, pass/fail.

`save_result(result, path)` creates parent directories and a new strict-JSON
file, refusing to overwrite existing paths. It serializes before opening the
file. It is not a transaction or crash-safe archive. The result format is
documented here; general result loading/migration and a result JSON Schema
are deferred until a second model tests the format's generality.

`ConfigurationError` is a `ValueError`; filesystem errors remain `OSError`.
The CLI returns 0 for a saved validated run, 1 for configuration/numerical/I/O
failure, and argparse's 2 for usage errors. No partial numerical history is
reported as success. The optional desktop lifecycle is described below.

## Desktop and tabular export

`desktop.window.MainWindow` builds Qt widgets and owns the active worker,
displayed `ExperimentResult`, and playback cursor. `configuration()` returns a
validated snapshot without rounding imported numbers to fixed decimal places.
`ExperimentWorker` invokes the same core `run_experiment`, with success/failure
signals delivered to the GUI thread. Views receive a completed immutable
result; they do not call physical equations to advance state.

Editing parameters leaves the last result intact and marks it stale. Only
another successful run replaces it. Failed input/runs preserve the previous
result. Result/CSV export therefore never combines old data with new inputs.
Closing while a worker is active is deferred; no forced termination or
cancellation is implemented. Running, ready, and failed states appear in
the UI, and inputs are disabled during a run.

`save_history_csv(result, path)` writes time, numerical position/velocity,
analytical position/velocity, and absolute errors with SI units in column
names. It creates a new file and refuses overwrites. CSV omits full provenance;
save the JSON result as the authoritative experiment record.

`load_configuration(path)` in the desktop accepts either a configuration
object or a saved result containing `configuration`. The latter explicitly
loads inputs for recomputation; it does not hydrate old numerical history or
claim to reproduce an unavailable implementation. CLI input remains a plain
experiment configuration.

## Visualization, learning, and future providers

Visualization consumes immutable sample snapshots and variable metadata;
plots display units and coordinate frames. A future 3D view maps physical
coordinates into renderer coordinates explicitly. Playback timing is separate
from simulation time. Parameter editing creates a new experiment configuration.
No Qt, Matplotlib, or GPU import belongs in model or integration modules.

Learning/reporting will consume configuration, physical metadata, numerical
settings, references, validation evidence, and user-authored interpretation.
Derived analyses must preserve source-result identity and their own method,
units, assumptions, and versions.

Future provider descriptors should expose provider ID/version, supported
contract/schema versions, capabilities, and validation metadata. Begin with an
explicit allowlist of local factories. Entry-point discovery, if later needed,
must reject duplicate IDs and incompatible versions, preserve provider identity
in results, and never silently select a different engine. Python plugins are
trusted executable code, not sandboxed data. No scanning, importing, or package
installation from configurations is allowed by the current implementation.
