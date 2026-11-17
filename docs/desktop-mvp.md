# MVP desktop STEMLab 0.2.0

Tujuan versi ini adalah aplikasi yang bisa dibuka dan dievaluasi langsung.
Fondasi numerik Phase 0 digunakan kembali tanpa menambahkan mesin fisika besar.

## Menjalankan

```bash
cd /home/dzaki/Developer/stemlab
./stemlab
```

Tidak perlu memasang paket. Launcher memuat `src` dari lokasi proyek dan
menjalankan Python 3.14 yang sudah memiliki PySide6. Alternatifnya:

```bash
PYTHONPATH=src python3.14 -m stemlab.desktop
```

Jendela menyesuaikan ukuran layar; panel bisa digulir bila ruang terbatas.
File `STEMLab.desktop` dapat dipakai sebagai peluncur lokal, dengan izin
peluncuran dari GNOME bila diminta. Ia belum dipasang ke menu aplikasi.

## Alur evaluasi singkat

1. **Buka aplikasi.** Contoh awal berjalan otomatis: benda pada 100 m,
   kecepatan awal nol, gravitasi −9.80665 m/s², durasi 2 s. Ada 201 sampel
   karena langkah desktop adalah 0.01 s. Contoh CLI lama tetap 21 sampel.
2. **Periksa hasil.** Posisi akhir sekitar 80.3867 m dan kecepatan akhir
   −19.6133 m/s. Kartu “Uji analitis” harus menunjukkan “Lulus”.
3. **Coba parameter.** Pilih sumbu X, posisi awal 0, kecepatan awal 0,
   percepatan tambahan 2. Dengan gravitasi X nol dan durasi 2 s, hasilnya
   sekitar 4 m dan 4 m/s. Tekan Jalankan setelah mengedit.
4. **Periksa waktu.** Putar, jeda, ubah kecepatan, geser slider, atau klik
   grafik. Pemutaran hanya membaca sampel yang telah dihitung.
5. **Coba lingkungan.** Pilih LAND/MARINE/AIR dan buka properti lingkungan
   tambahan. Ubah gravitasi untuk melihat pengaruhnya. Mengubah densitas,
   gesekan, angin, atau arus belum mengubah gerak pada model ini.
6. **Buka tab lainnya.** Tabel memuat setiap sampel beserta galat analitis.
   Tab model menjelaskan persamaan, parameter run terakhir, dan keterbatasan.
7. **Simpan.** Simpan konfigurasi untuk masukan, hasil JSON untuk catatan
   lengkap, dan CSV untuk analisis di aplikasi lain. Pilih nama file baru.
8. **Buka ulang.** Muat konfigurasi atau hasil JSON; pada hasil JSON,
   aplikasi hanya memuat konfigurasi untuk dihitung ulang pada versi aktif.

Shortcut: `Ctrl+O` membuka eksperimen, `Ctrl+S` menyimpan konfigurasi,
dan `Ctrl+R` menjalankan simulasi.

## Batas yang perlu diketahui saat mengevaluasi

- Satu model gerak 1D, satu metode RK4 dengan langkah tetap. Tidak ada model
  kendaraan, gaya berbasis massa, kontak tanah, fluida, atau aerodinamika.
- Profil tiga lingkungan independen dan dapat diedit, tetapi properti selain
  gravitasi baru disimpan; tidak ada gaya fisika yang disubstitusi diam-diam.
- Posisi bisa melewati bidang tanah karena tidak ada deteksi tumbukan. Tab
  model menandai kondisi ini pada run LAND dengan sumbu Z.
- Visualisasi jejak menggunakan skala otomatis dan arah nilai koordinat;
  bukan representasi geometris 3D atau lintasan kendaraan di medan.
- Riwayat utuh disimpan di RAM dengan batas 100,000 langkah. Grafik mereduksi
  titik untuk digambar; tabel virtual dan ekspor tetap memuat semua sampel.
- Simulasi berjalan dalam satu worker. Belum ada tombol pembatalan; tunggu
  perhitungan selesai sebelum menutup. Ini bukan percepatan komputasi paralel.
- Perubahan parameter tidak mengganti hasil lama. Badge menandai perubahan;
  ekspor tetap mengacu pada run terakhir yang berhasil.
- Penyimpanan menolak menimpa file dan belum tahan putus daya. Tidak ada
  autosave, proyek multieksperimen, impor riwayat numerik, atau session restore.
- Belum ada installer, AppImage, integrasi menu sistem otomatis, atau lisensi
  distribusi yang ditetapkan. Peluncur lokal cukup untuk evaluasi komputer ini.

## Pengujian dan bukti

Tes menggunakan unittest. Pengujian Qt dilakukan pada backend offscreen agar
tidak mengganggu desktop. Runtime numerik tetap dapat dijalankan dengan `-S`
tanpa Qt. Tidak ada kebutuhan QtTest, Matplotlib, GPU, atau jaringan.

Hasil pemeriksaan 2026-11-17:

- **39 pengujian lulus**, termasuk 10 pengujian integrasi desktop.
- Dengan `-S`: **26 pengujian inti lulus**, 13 pengujian opsional dilewati.
- Wheel `dist/stemlab-0.2.0-py3-none-any.whl` berhasil dibangun tanpa memasang
  paket, memuat schema dan ikon, serta lolos startup/simulasi/render offscreen.
  Hasil headless dari source dan wheel identik sampai byte berkas JSON.
- Screenshot grafik, tabel, dan model diperiksa; jendela 1280×740 juga dirender.
- Contoh desktop: galat maksimum posisi sekitar `1.56e-13 m`, kecepatan
  `3.20e-14 m/s`, keduanya di bawah toleransi yang dinyatakan.
- Pengukuran satu proses offscreen dengan contoh awal dan screenshot mencatat
  peak RSS sekitar **90.9 MiB**. Ini pengukuran contoh kecil, bukan jaminan
  penggunaan memori semua konfigurasi atau seluruh desktop.

Contoh hasil tersimpan di `results/desktop-demo.json` dan
`results/desktop-demo.csv`. Semua isi `results/` dan `dist/` diabaikan Git.

```bash
PYTHONPATH=src python3.14 -m unittest discover -s tests -v
PYTHONPATH=src python3.14 -S -m unittest discover -s tests -v
```

Screenshot untuk pemeriksaan tampilan disimpan di
`results/stemlab-desktop.png` (diabaikan oleh Git). Panduan ini bukan klaim
bahwa simulator untuk ketiga domain sudah selesai; ia menjelaskan tepat
apa yang dapat dievaluasi pada aplikasi saat ini.

Umpan balik yang paling berguna berikutnya: apakah alur mudah dipahami,
parameter apa yang kurang, model fisika mana yang perlu didahulukan, dan
bentuk visualisasi apa yang membantu Anda memahami hasil.
