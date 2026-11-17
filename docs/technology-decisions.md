# Technology decisions and compatibility evidence

Inspection date: **2026-11-17**. These observations describe this session's
host and interpreter, not a promise about every machine or upstream wheel.
The repository initially contained no project files or commits and no
applicable `AGENTS.md` was found. Only this repository and temporary files
were written; no packages were installed or OS/workspace settings modified.

## Local toolchain

| Capability | Observed result | Decision |
| --- | --- | --- |
| OS | Ubuntu 26.04.1 LTS, x86_64, glibc 2.43 | Linux development baseline |
| Python | `/usr/bin/python3.14`, 3.14.4, `cpython-314-x86_64-linux-gnu` | Tested Phase 0 runtime |
| NumPy | 2.3.5; import and vector dot product passed (`11.0`) | Available candidate for array-based models |
| SciPy | 1.16.3; `solve_ivp` smoke test succeeded | Candidate for adaptive/stiff ODE solvers |
| Matplotlib | 3.10.7 distro build; Agg canvas render succeeded | Candidate for scientific plots |
| PySide6 / Qt | 6.10.2; `QCoreApplication` creation and Qt version query passed | Candidate desktop shell; graphical rendering not tested |
| C++ / CMake | GNU C++ 15.2.0, CMake 4.2.3; version checks only | Available, not required or compiled in Phase 0 |
| Setuptools / pip | 78.1.1 / 25.1.1 importable | Existing build tools; no install required |
| pytest / jsonschema | 9.0.2 / 4.19.2 importable | Optional local test tools; unittest is sufficient |
| YAML | PyYAML 6.0.3 importable | Not selected; JSON avoids another dependency |
| Octave | 11.1.0 CLI version worked; no X11 display | Future optional numerical adapter; no interoperability test |
| KiCad / ngspice | `kicad-cli` 9.0.8, ngspice 45.2 version checks worked | Future circuit/CAD integrations only |
| ROS 2 | Lyrical CLI on PATH; Python 3.14 `rclpy` imported | Future adapter; no node/world was started |
| Gazebo | `gz` on PATH under ROS vendor tools; vendor sim 0.4.6 package present | Presence only; no simulator/physics/rendering validation |
| FreeCAD | No executable on PATH, Python import, or matching dpkg package found | Unverified availability; may exist by another install method |
| NVIDIA | `nvidia-smi` could not communicate with the driver | GPU availability unverified; never a Phase 0 dependency |
| Memory | `free -h` reported about 14 GiB total and 6.4 GiB available, no swap | Keep product design target at 8 GB; host reading is not a benchmark |

The Matplotlib smoke test reported that the user configuration directory was
not writable under the sandbox and used a temporary cache. It still rendered
successfully. Future headless plot checks can set `MPLCONFIGDIR` to a writable
temporary directory. No persistent configuration change is needed.

## Chosen dependencies and trade-offs

1. **Python 3.14, standard library runtime.** Dataclasses, protocols, `math`,
   JSON, hashing, argparse, and unittest cover the proof. This keeps the
   foundation inspectable and usable without installing native packages.
   `requires-python >=3.14` states the supported minimum; only 3.14.4 was
   actually exercised. Future interpreters still require CI validation.
2. **Setuptools build backend, `src` layout.** Conventional packaging and a
   CLI entry point without a bespoke build system. Schemas are package data.
   The existing local backend can build without network or installation;
   isolated installs elsewhere may need build dependencies, so they are not
   run automatically. Build dependency is `setuptools>=78`; runtime dependencies
   are empty. Exact runtime/source identity is recorded per experiment.
   The local backend successfully built a wheel containing both schemas;
   an unpacked-wheel `-S` run produced byte-identical results to the source
   checkout. This tested packaging without installing a package.
3. **Strict JSON rather than YAML.** Portable, non-executable, and supported
   by the standard library. Reject unknown keys, duplicate keys, nonfinite
   values, unsupported versions, and invalid domains. SI field names avoid
   implicit conversions. Verbosity and manually maintained schemas/validators
   are acceptable for this small scope; parity tests reduce drift.
4. **Reference fixed-step RK4 rather than a solver framework.** A short generic
   adapter demonstrates the model boundary and is independently tested for
   order of accuracy. Constant acceleration is integrated exactly in exact
   arithmetic. RK4 lacks adaptivity, stiffness handling, constraints, and
   event detection; do not stretch it to those problems.
5. **unittest as the required test runner.** Already in Python; no test setup
   installation. Existing jsonschema/referencing tools enable three optional
   offline schema checks. The runtime never imports them.
6. **Text JSON results.** Easy inspection and replay for small experiments.
   Full history and serialization use memory proportional to sample count;
   large experiments will need streaming/binary storage. No database yet.

## Candidate technologies, deferred commitments

PySide6 is now the optional desktop dependency because it exposes Qt 6 through
Python. Its official [getting-started guide](https://doc.qt.io/qtforpython-6/gettingstarted.html)
is the upstream integration reference. Beyond the initial core smoke test,
the desktop MVP exercised Qt Widgets, the event loop, worker signals,
QPainter plots, playback, tables, exports, and raster screenshots under
`QT_QPA_PLATFORM=offscreen`. PySide6 6.10.2 is the tested build; the declared
optional extra is `PySide6>=6.10,<7`. QtTest is not installed, so integration
tests use QEventLoop/QTimer instead of requiring another package. The GUI
uses the existing system installation, with no package installation.

NumPy/SciPy/Matplotlib are useful candidates, and this host's distro builds
ran successfully under Python 3.14. Upstream support matrices, binary wheels,
and distro patches can differ; consult the official
[SciPy toolchain roadmap](https://docs.scipy.org/doc/scipy/dev/toolchain.html)
when selecting a reproducible optional stack. Do not infer compatibility from
an importable package path alone or copy a current development version table
onto an older installed release. No optional dependency ranges or lock file
are claimed by Phase 0 because no optional stack is required.

Use C++ only after profiling a scientifically validated Python workload.
Keep numerical kernels independent of Qt and route bindings through adapters.
ROS/Gazebo and CAD/circuit tools may carry their own Python/Qt versions and
lifecycle constraints; subprocess exchange is a possible boundary when native
ABI combinations are incompatible. Their presence does not justify mandatory
dependencies or modification of existing workspaces. ORCA and unrelated
projects were neither inspected nor changed.

No microservices, GPU kernels, distributed execution, runtime plugin framework,
symbolic algebra framework, units library, or persistence framework is introduced.
Add one only when a concrete experiment demonstrates the need and compatibility
has been verified. Any package installation or operating-system change requires
user approval.
