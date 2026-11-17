# Scientific specification and validation

## Problem and coordinate convention

A point particle moves along a selected axis of a right-handed inertial world
frame. The z axis points upward. Time is measured from `t0 = 0 s`. Position is
relative to the world origin along that axis, not height above terrain in a
contact simulation. The proof selects z and uses a LAND ambient profile;
it is free flight above the reference plane throughout the interval.

| Quantity | Symbol | SI unit | Proof value |
| --- | --- | --- | --- |
| Initial position | q₀ | m | 100 |
| Initial velocity | v₀ | m/s | 0 |
| Gravity vector | g | m/s² | (0, 0, −9.80665) |
| Prescribed applied acceleration | a_applied | m/s² | 0 |
| Effective acceleration | a | m/s² | −9.80665 |
| Nominal time step | h | s | 0.1 |
| Number of steps | N | dimensionless | 20 |
| Final time | T | s | 2 |

The gravity value is an explicitly chosen constant, not an inference of local
gravity from location. Profile friction `0.6` and terrain height `0 m` are
illustrative ambient values; no material calibration is asserted.

## Governing equations and exact solution

State order is `y = (q, v)`:

```text
dq/dt = v
dv/dt = a
a = g_axis + a_applied
q(0) = q0
v(0) = v0

q(t) = q0 + v0*t + (1/2)*a*t^2
v(t) = v0 + a*t
```

Thus `q(2) = 80.3867 m` and `v(2) = −19.6133 m/s`. A prescribed acceleration
is a kinematic input; it is not a derived thrust, torque, or force law. Mass
is not a parameter of this problem.

## Numerical method

The adapter implements classical explicit fourth-order Runge-Kutta:

```text
k1 = f(t_n,       y_n)
k2 = f(t_n+h/2,   y_n + h*k1/2)
k3 = f(t_n+h/2,   y_n + h*k2/2)
k4 = f(t_n+h,     y_n + h*k3)
y_(n+1) = y_n + h*(k1 + 2*k2 + 2*k3 + k4)/6
```

The implementation evaluates the weighted sum as `k1/6 + k2/3 + k3/3 + k4/6`
to avoid needlessly large intermediate sums. Grid points are `t_n = n*dt_s`
in binary64; the actual interval width is the difference of adjacent grid
points. Initial and final states are both recorded. This method is exact for
constant acceleration in exact arithmetic; observed errors here are floating-
point roundoff. Its usual fourth-order global accuracy for smooth ODEs does
not imply stability or suitability for stiff, discontinuous, or constrained
systems. There is no adaptive local-error estimate.

## Validation evidence and acceptance

The application independently evaluates the analytical expressions at every
recorded time. Each position and velocity must satisfy:

```text
abs(numerical - analytical) <= max(atol, rtol * max(abs(numerical), abs(analytical)))
```

`atol = 1e-10` in the corresponding state's SI unit (m or m/s), and
`rtol = 1e-12` dimensionless. The result records both maximum absolute errors,
tolerances, reference equations, and the pass flag. These tolerances are
specific to this proof's smooth, small problem; they are not a universal
accuracy criterion. Nonfinite comparisons fail explicitly.

Automated verification covers every reference sample, final position/velocity,
zero acceleration, negative velocity, nonzero initial states, axis projection,
changed gravity, invalid/overflowing numerical data, and corrupted states.
An independent scalar test uses `y' = y + t`, `y(0) = 1`, with exact solution
`y(t) = 2*exp(t) - t - 1`. Halving the time step should reduce final error by
approximately 16; the test accepts a ratio from 14 to 18. This checks stage
times and fourth-order convergence that the polynomial proof alone cannot.

Repeated same-host runs must produce identical histories and saved JSON.
Tests also verify loading, round-trip configuration, provenance, output
preservation, and the CLI with site packages disabled. This is numerical
verification against exact solutions, not empirical validation of a real
vehicle or environment.

### Recorded Phase 0 run (2026-11-17)

`results/phase0.json` was generated locally (ignored by version control):

| Check | Observed result |
| --- | --- |
| Standard unittest run | 28 tests passed, no skips |
| Site packages disabled (`-S`) | 25 passed, 3 optional schema checks skipped |
| Recorded trajectory | 21 samples, t = 0 through 2 s |
| Final position | 80.3867 m |
| Final velocity | −19.613300000000006 m/s |
| Maximum position error | 1.4210854715202004 × 10⁻¹⁴ m |
| Maximum velocity error | 7.105427357601002 × 10⁻¹⁵ m/s |
| Offline wheel smoke test | Built with existing backend; both schemas included |
| Source versus unpacked wheel | Both ran with `-S`; saved JSON bytes identical |

The wheel was extracted into a temporary directory for the smoke test;
no package was installed. Temporary packaging output was cleaned up. Local
ignored `build/` and `src/stemlab.egg-info/` may remain from the build backend.

## Assumptions and limitations

- Constant uniform gravity and constant prescribed acceleration; inertial frame.
- Point particle constrained conceptually to one axis; no rotation or coupling.
- No contact, terrain enforcement, friction force, buoyancy, drag, wind/current
  force, aerodynamic lift, propulsion model, or mass variation.
- No event detection; a longer run can pass below the reference ground plane.
  Such a trajectory represents unconstrained mathematical motion, not impact.
- Other ambient profile values are preserved but unused, explicitly declared
  in saved model limitations. A marine/air profile does not change the equations
  into a marine/air vehicle model.
- No uncertainty propagation, calibration, measurement comparison, or general
  conservation-law analysis. Cross-platform equality is tolerance-based.

Adding a force law requires its own assumptions, dimensional checks, domain
tests, and reference validation. Coupling requires additional conservation
and communication-step convergence tests.
