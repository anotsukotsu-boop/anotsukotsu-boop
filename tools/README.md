# tools

Semua animasi di profil ini adalah SVG buatan tangan: CSS keyframes + SMIL, tanpa GIF,
tanpa JavaScript, dan tanpa layanan pihak ketiga. Teks dirender sebagai outline glyph
(Shippori Mincho B1, JetBrains Mono, Yuji Syuku — semuanya lisensi OFL). Jadi tampilannya
sama persis di semua browser dan tidak bergantung pada font yang terpasang.

Paletnya diambil dari adegan tangga Subaru: 夜 hitam-teal, 翠 hijau neon, dan 黄 kuning
asam dari cahaya di wajahnya. 朱 vermilion hanya dipakai untuk momen mati dan stempel
hanko. Motifnya Jepang: jam wadokei, kelopak berjatuhan, tangan bayangan Penyihir,
stempel 「死」, kanji 7 dosa, dan 三つ巴 di dalam ensō. Semua warna ada di `C`
dalam `svgkit.py`.

Header dan divider transparan, jadi masing-masing punya versi `-light.svg` untuk mode
terang GitHub. README memilihnya otomatis lewat `<picture>`.

| File | Isi |
| :-- | :-- |
| `svgkit.py` | toolkit: download font, teks → glyph `<use>`, palet warna |
| `build_static.py` | hero, divider, header, terminal, skill bar, orbit, footer |
| `build_stats.py` | kartu statistik live, dijalankan tiap hari oleh `.github/workflows/loop-stats.yml` |

```bash
pip install fonttools
python tools/build_static.py     # regenerate semua SVG statis
python tools/build_stats.py      # regenerate assets/stats.svg (tanpa token pun jalan)
```

Latar hero adalah video HD tangga Subaru (`subaru-stairs_processed.mp4`, 1280×588).
Video itu dipotong sekali menjadi `assets/bg/subaru-stairs.webp` (WebP animasi 1000×380,
12 fps, kualitas 40, sekitar 2,1 MB) lalu di-embed ke `hero.svg`, karena SVG yang tampil
sebagai gambar tidak boleh memuat file luar. File WebP itu ikut di-commit, jadi build
biasa tidak butuh videonya. Mau ganti latar? Hapus WebP-nya, arahkan `BG_VIDEO` di
`build_static.py` ke video lain, lalu jalankan dengan `pip install imageio-ffmpeg`.
Tajam dan ukuran bisa diatur lewat `BG_FPS` dan `BG_QUALITY`.

Mau ganti isi? Semua teks (nama, role, neofetch, 7 dosa/skill, tech orbit, judul
section) ada di blok konten paling atas `build_static.py`. Edit di situ, lalu jalankan ulang.

Font diunduh sekali dari repo `google/fonts` ke `tools/.fonts/` (di-ignore git).
Set `HIDE_LANGS="HTML,Blade"` saat menjalankan `build_stats.py` kalau ingin
menyembunyikan bahasa tertentu dari bar bahasa.
