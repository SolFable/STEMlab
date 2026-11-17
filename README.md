# STEMLab

Integrated STEM Computational Laboratory — laboratorium desktop untuk
memahami model matematika, metode numerik, dan perilaku fisika.

**MVP desktop 0.2.0 sudah dapat dibuka.** Fondasi Phase 0 tetap tersedia,
ditambah antarmuka PySide6 untuk mengubah parameter dan mengevaluasi hasil.

## Membuka aplikasi

Dari folder proyek, jalankan:

```bash
./stemlab
```

Atau dari terminal mana pun:

```bash
/home/dzaki/Developer/stemlab/stemlab
```

Launcher menggunakan `python3.14` dan kode proyek secara langsung; tidak
perlu `pip install` atau aktivasi lingkungan. Python sistem dan PySide6
6.10.2 yang sudah tersedia pada komputer ini digunakan tanpa pemasangan paket.
Jika memakai interpreter lain, tentukan `STEMLAB_PYTHON=/path/to/python ./stemlab`.

`STEMLab.desktop` juga tersedia di folder proyek. Peluncur tersebut memakai
lokasi absolut checkout saat ini; sesuaikan `Exec`, `Path`, dan `Icon` jika
memindahkan proyek. GNOME dapat meminta Anda mengizinkan peluncuran file
`.desktop`. Tidak ada pemasangan otomatis ke menu aplikasi atau perubahan OS.

## Yang bisa dicoba

1. Aplikasi otomatis menjalankan contoh benda jatuh selama 2 detik.
2. Pilih profil **LAND**, **MARINE**, atau **AIR**, lalu ubah gravitasi,
   sumbu gerak, posisi/kecepatan awal, percepatan tambahan, dan langkah waktu.
   Panel parameter dapat digulir; tombol **Jalankan simulasi** tetap terlihat.
3. Tekan **Jalankan simulasi**. Grafik menampilkan RK4 dan solusi analitis,
   dengan posisi akhir, kecepatan akhir, dan hasil validasi.
4. Klik **Putar**, atur kecepatan pemutaran, geser waktu, atau klik grafik
   untuk memeriksa koordinat yang sudah dihitung.
5. Buka tab **Tabel data** dan **Model dan validasi** untuk melihat angka,
   persamaan, asumsi, dan galat perhitungan.
6. Simpan konfigurasi JSON, hasil lengkap JSON, atau data CSV. File yang
   sudah ada tidak ditimpa; pilih nama baru.

Mengubah parameter tidak mengubah hasil lama. Grafik dan ekspor mempertahankan
snapshot eksperimen terakhir sampai Anda menjalankan ulang. Membuka file hasil
JSON memuat konfigurasinya untuk dihitung ulang; ini bukan pemuatan kembali
hasil numerik lama tanpa komputasi. Simpan JSON lengkap untuk provenance;
CSV hanya memuat data tabular dan galat analitis.

**Batas MVP:** hanya model gerak 1D dengan percepatan konstan. Profil lingkungan
selain gravitasi baru disimpan sebagai konfigurasi; gesekan, gaya apung,
hambatan fluida, lift, dan tumbukan belum dihitung. Animasi adalah pemutaran
koordinat pada skala otomatis. Aplikasi belum menjadi simulator mobil,
kapal, atau pesawat. Keterbatasan ini juga ditampilkan di dalam aplikasi.

## Persyaratan dan pengujian

Python **3.14 atau lebih baru** diperlukan; yang diuji adalah 3.14.4.
Desktop memerlukan PySide6 (extra paket `desktop`), sedangkan mesin numerik
dan CLI hanya memakai standard library. Matplotlib, SciPy, GPU, dan mesin
eksternal tidak diperlukan. Grafik digambar melalui Qt pada CPU.

```bash
PYTHONPATH=src python3.14 -m unittest discover -s tests -v
```

Pengujian desktop memakai backend Qt `offscreen`, sehingga tidak membuka
jendela pada desktop. Pengujian tersebut mencakup startup, worker, parameter,
profil, grafik/tabel, pemutaran, impor/ekspor, dan ukuran jendela laptop.
QtTest tidak diperlukan. Pengujian opsional dilewati jika pustakanya tidak ada;
tidak ada pengujian yang memasang paket atau memakai jaringan.

## Run the proof experiment

From the repository root:

```bash
PYTHONPATH=src python3.14 -m stemlab examples/constant_acceleration.json --output results/phase0.json
PYTHONPATH=src python3.14 -m unittest discover -s tests -v
```

The experiment records 21 samples over 2 seconds. Its final position is
approximately **80.3867 m** and final velocity **−19.6133 m/s**. Every sample
is checked against the analytical solution. Choose a new output filename
for another run: existing results are preserved.

`results/phase0.json` contains the full normalized configuration, physical
metadata, resolved acceleration, time/state history, validation tolerances
and errors, source/configuration hashes, and Python/platform provenance.
Replay by passing its `configuration` object to `ExperimentConfig.from_dict`
and then `run_experiment`; result files themselves are not experiment inputs.

To verify independence from installed third-party packages:

```bash
PYTHONPATH=src python3.14 -S -m unittest discover -s tests -v
```

Pada pemeriksaan dengan `-S`, pengujian desktop dan tiga pengujian schema
opsional dilewati. Pengujian inti serta CLI tetap berjalan tanpa paket tambahan.

The `src` package layout and `pyproject.toml` support a conventional local
package installation later. Setuptools is a build dependency only; the
commands above need no build or installation. Do not alter system Python
or install optional packages without approval.

## Repository map

```text
docs/
  vision.md                  Product goals and scope
  architecture.md            Modules, dependencies, extension paths
  module-contracts.md        Interfaces, serialized formats, error behavior
  technology-decisions.md    Local compatibility evidence and choices
  roadmap.md                 Phase gates and next work
  scientific-validation.md   Equations, RK4 method, assumptions, validation
  desktop-mvp.md             Panduan penggunaan dan evaluasi desktop
examples/
  constant_acceleration.json
  environments/{land,marine,air}.json
src/stemlab/
  application.py             Workflow composition
  __main__.py                Headless CLI
  validation.py              Strict input validation
  environments.py            Independent ambient profiles
  modeling.py                Physical model protocol and scientific metadata
  models/constant_acceleration.py
  engines/{base,rk4}.py       Adapter protocol and reference integrator
  experiments/{config,results,export}.py
  desktop/                  Qt shell, plots, playback, table, presets, icon
  analysis.py                Analytical comparison
  schemas/{environment,experiment}.schema.json
tests/                       Core, desktop, export, and schema checks
stemlab                      Executable desktop launcher
STEMLab.desktop              Local desktop entry
pyproject.toml
.gitignore
```

Start with [the architecture](docs/architecture.md) and
[the scientific validation](docs/scientific-validation.md).

LAND, MARINE, and AIR are reusable **configuration profiles**, not completed
simulators. The proof uses only gravity and prescribed acceleration; it
does not model contact, friction, buoyancy, drag, or aerodynamic lift.
Tidak ada integrasi mesin eksternal, plugin loader, atau coupled solver.
Lihat [panduan evaluasi MVP](docs/desktop-mvp.md) dan [roadmap](docs/roadmap.md).
# STEMlab
