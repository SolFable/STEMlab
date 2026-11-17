# Roadmap and phase gates

## Current status — desktop MVP 0.2.0

Phase 0 is complete. The user subsequently authorized continuing to an
application they can open and evaluate. That increment provides a PySide6
window, independent environment profiles, parameter editing, an asynchronous
run, numerical/reference plots, 1D playback, a virtual data table, scientific
notes, JSON configuration/results, CSV export, and repository-local launchers.

The scientific model is still constant acceleration; this does not claim
completion of the full Phase 1 gate below. The next evaluation should collect
usability feedback before choosing the next physical model. See
[the desktop guide](desktop-mvp.md). No packages were installed.

## Phase 0 — architecture and foundation

Acceptance criteria:

- Inspect the repository and actual toolchain without installing packages or
  changing ROS, Gazebo, ORCA, OS settings, or unrelated workspaces.
- Document vision, modular responsibilities, contracts, dependency trade-offs,
  local compatibility, scientific assumptions, and incremental plans.
- Supply a typed installable Python package, JSON schemas, independent LAND,
  MARINE, and AIR profiles, a model protocol, and an adapter protocol.
- Load a strict experiment configuration, construct a model, run deterministic
  RK4, record history, validate every sample, and save reproducible results.
- Run configuration, numerical, schema, provenance, and CLI checks. Demonstrate
  that the core works without third-party site packages.

Phase 0 does not establish full physical support for any environment category.
It establishes the boundaries those future simulators must respect.

## Recommended Phase 1 — one validated vertical slice

The desktop portion has been authorized and implemented. Keep subsequent
physical-model work narrow and subject to evaluation priorities:

1. Select a one-dimensional LAND force-based body model with mass and a
   documented scope. Choose a tractable force law, such as linear drag, and
   validate its transient and limiting behavior analytically. Do not add
   wheeled contact or friction without defining static/kinetic behavior and
   event handling.
2. Add a second model through an explicit factory map to test extension
   boundaries. Introduce capability checks before allowing incompatible
   model/solver combinations. Define schema versioning and result loading
   from the concrete needs of this second model.
3. Probe Qt widgets, display backend, event loop, and plotting integration
   under the real desktop session. If successful, add a minimal PySide6
   shell for selecting profiles, editing validated parameters, running an
   experiment, and plotting state/error versus time with units. Preserve
   the headless CLI and numerical tests.
4. Measure CPU and memory on the 8 GB target. If runs can block interaction,
   add one cancellable worker and immutable progress snapshots; define
   cancellation and failure states before threading the workflow.
5. Record model-specific accuracy requirements, time-step convergence,
   reference comparisons, and physical-domain checks. Add CI for Python 3.14
   and review optional dependency versions before any installation.

Exit gate: both models validated independently, configuration/result replay
preserved, optional UI cannot change numerical behavior, and a documented
CPU/memory measurement meets the target. Avoid simultaneous land, marine,
air, circuit, robotics, and 3D implementations.

## Later increments — provisional, independently approved

- **Marine:** buoyancy from displaced volume and density, then drag relative
  to currents; validate hydrostatics and terminal speed.
- **Air:** start with a defined low-order aerodynamic regime; declare density,
  frame, coefficient sources, validity limits, and wind-relative velocity.
- **Analysis and learning:** experiment comparison, uncertainty and sensitivity
  studies, equations/error views, and reports linked to immutable results.
- **3D visualization:** renderer-independent scene transforms and playback,
  with physical coordinates and reference frames preserved.
- **External engines and CAD:** optional ngspice/Octave/ROS/Gazebo/FreeCAD
  adapters after compatibility and lifecycle tests in isolated project data.
- **Multiphysics:** first shared-solver composition, then only justified
  co-simulation with conservation and coupling-convergence checks.
- **Plugins:** local provider descriptors, compatibility/capability checks,
  explicit registration, then discovery if real extension needs justify it.
- **C++ acceleration:** profile first; validate equivalence and maintain a
  CPU reference path. GPU/distributed work remains optional future research.
