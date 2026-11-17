# Product vision

STEMLab is a personal scientific and engineering laboratory for learning,
modeling, simulating, analyzing, and documenting STEM systems. The central
question is why a system behaves as it does. Animation is an interpretation
of computed state, never the definition of physical truth.

Users will define a model, choose an independent environment, declare
parameters and initial conditions, run an experiment, inspect numerical
and physical evidence, compare experiments, and record conclusions.
Long-term domains include robotics, vehicles, aerospace, marine systems,
electrical circuits, computational systems, physical AI, and machine learning.

Every supported physical model must expose governing equations, assumptions,
parameter and state definitions, units, required environment inputs, and
limitations. Every successful experiment must preserve the inputs, numerical
method, implementation identity, and results needed for a meaningful replay.
Scientific validation and numerical verification are separate from a
convincing visualization.

## Environments

- **LAND:** gravity, terrain, and surface conditions for ground vehicles and
  mobile robots; appropriate models later compute contact and friction.
- **MARINE:** gravity, density, and currents; appropriate models later compute
  buoyancy and fluid drag from both ambient and body properties.
- **AIR:** gravity, atmospheric properties, and wind; appropriate models later
  compute aerodynamic forces from body shape and relative air velocity.

An environment belongs to an experiment and can be reused for multiple
objects. Vehicle geometry, mass, displaced volume, and aerodynamic or drag
coefficients belong to physical models or bodies. New environment categories
must fit the same outer configuration format.

## Phase 0 success criteria

Deliver a documented architecture, a minimal Python package, strict versioned
JSON inputs, reusable environment examples, model/adapter contracts, and a
deterministic constant-acceleration experiment with saved results and
automated analytical validation. Run on a CPU with an 8 GB RAM design target.

This phase excludes full environment simulators, desktop UI implementation,
CAD/ROS/Gazebo/circuit integrations, runtime plugin discovery, multiphysics
coupling, machine learning, GPU computation, and distributed execution.
Those require independently validated increments and explicit scope decisions.
