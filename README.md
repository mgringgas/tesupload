# Analisis Ulasan Buruk dan Keterlambatan Pengiriman: Prioritas Rute dan Seller

**Final Project — Job Connector Business & Data Analyst (JCBDABSD-001), Purwadhika Digital Technology School | Kelompok Alpha**

**Anggota Kelompok:**
- Jessica Aulia
- Michael Gary Ringgas
- Axellia Verda Qania

Sekitar **1 dari 7 pesanan Olist berakhir dengan ulasan buruk** (bintang 1–2). Project ini mencari faktor operasional di balik ulasan buruk tersebut, lalu menentukan **rute pengiriman dan seller mana yang perlu diprioritaskan** untuk diperbaiki.

**Dashboard (Looker Studio):** https://datastudio.google.com/reporting/40d02c18-082d-4e9a-a3c7-81aa37028754

**Notebook:** [`Notebook/Alpha - FINPRO - Analisis Ulasan Buruk dan Keterlambatan Olist.ipynb`](<Notebook/Alpha - FINPRO - Analisis Ulasan Buruk dan Keterlambatan Olist.ipynb>)

---

## Latar Belakang

Olist adalah *marketplace* di Brasil yang menghubungkan pelanggan dengan banyak seller dari berbagai state. Satu pesanan melewati beberapa tahap: *checkout* → pembayaran disetujui → seller menyerahkan barang ke kurir → kurir mengantar ke pelanggan. Saat *checkout*, pelanggan dijanjikan tanggal estimasi barang sampai. Setelah pesanan selesai, pelanggan memberi skor ulasan 1–5.

Skor ulasan hanya menunjukkan **bahwa** pelanggan kecewa, tetapi tidak menjelaskan **mengapa**. Karena itu, project ini menelusuri faktor operasional yang berkaitan dengan ulasan buruk secara bertahap.

## Problem Statement

> **Seller dan rute pengiriman mana yang perlu diprioritaskan perbaikannya agar proporsi ulasan buruk di Olist dapat ditekan?**

| Pilar | Pertanyaan |
|---|---|
| **1 — WHAT** | Faktor operasional apa saja yang paling berkaitan dengan ulasan buruk di Olist? |
| **2 — WHERE & WHEN** | Di rute, jarak, wilayah, dan bulan apa keterlambatan paling sering terjadi? |
| **3 — WHY & WHO** | Seberapa sering keterlambatan sudah terjadi di sisi seller, dan seller mana yang perlu diprioritaskan? |

**Stakeholder:** Tim Operasional & Logistik Olist (utama), Tim Seller Management Olist dan Tim Customer Experience Olist (pendukung).

## Business Metrics

| Metrik | Definisi | Baseline |
|---|---|---|
| **Low Review Rate** | Pesanan dengan skor ulasan 1–2 ÷ pesanan dengan ulasan valid | **14,61%** |
| **Late Delivery Rate** | Pesanan yang sampai setelah tanggal estimasi ÷ pesanan delivered | **6,79%** |
| **Seller Late Handover Rate** | Pesanan yang diserahkan ke kurir setelah `shipping_limit_date` ÷ pesanan 1 seller dengan data handover valid | **9,09%** |

## Data

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle). Data transaksi nyata Olist yang sudah dianonimkan, terdiri dari **9 tabel** dengan ±99 ribu pesanan (September 2016 – Oktober 2018).

| File | Isi |
|---|---|
| `olist_orders_dataset.csv` | Pesanan, status, dan tanggal setiap tahap (tabel pusat) |
| `olist_customers_dataset.csv` | Lokasi pelanggan |
| `olist_order_items_dataset.csv` | Barang per pesanan, seller, harga, ongkir, batas serah ke kurir |
| `olist_order_payments_dataset.csv` | Pembayaran per pesanan |
| `olist_order_reviews_dataset.csv` | Skor dan komentar ulasan |
| `olist_products_dataset.csv` | Kategori dan atribut produk |
| `olist_sellers_dataset.csv` | Lokasi seller |
| `olist_geolocation_dataset.csv` | Koordinat per kode pos |
| `product_category_name_translation.csv` | Terjemahan kategori ke bahasa Inggris |

## Alur Pengerjaan

1. **Business Understanding** — problem statement, stakeholder, metrik, asumsi, dan batasan.
2. **Data Merging** — 9 tabel digabung satu per satu ke tabel `orders` sebagai pusat. Tabel pembayaran dan geolocation diringkas dulu (1 baris per pesanan / per kode pos) agar baris tidak tergandakan.
3. **Data Cleaning** — setiap langkah ditulis dengan format *Temuan → Keputusan → Alasan*:
   - profil 9 tabel sumber, cek kunci unik, dan tipe data;
   - duplikat akibat ulasan ganda: dipakai 1 ulasan terbaru per pesanan (`review_id` tidak dipakai sebagai kunci);
   - missing value dicek sesuai status pesanan dan tidak diisi (tidak diimputasi);
   - nama kategori yang salah ketik diperbaiki;
   - anomali logika diberi *flag*: urutan waktu terbalik, batas serah tahun 2020, ulasan sebelum pembelian;
   - lokasi disamakan dengan **kode pos sebagai acuan**: state seller dikoreksi, nama kota diambil dari kode pos, titik koordinat yang salah dibuang, koordinat kosong diperkirakan dari kode pos tetangga;
   - outlier dipertahankan;
   - periode dibatasi ke **Januari 2017 – Agustus 2018** (data akhir Agustus 2018 tidak lengkap).
4. **Feature Engineering** — dibuat tabel level pesanan (`df_order`, 99.092 pesanan). Isinya kolom ulasan buruk, keterlambatan (dibandingkan **per tanggal**), durasi per tahap, handover seller (pesanan 1 seller), komposisi pesanan, geografi (rute, region, jarak Haversine), dan bulan pembelian. Tabel ini diekspor **sekali** sebagai `olist_order_level.csv`, satu-satunya sumber data dashboard.
5. **Exploratory Data Analysis** — tiga pilar:
   - uji **Chi-Square**, uji normalitas **D'Agostino-Pearson**, **Mann-Whitney**, dan **One Way ANOVA** untuk pola hari & tanggal pemesanan (α = 0,05);
   - **z-test proporsi satu sisi** untuk seller & kategori berisiko, serta untuk membandingkan setiap rute prioritas dengan rate wajar menurut jaraknya (α = 0,01);
   - peta rute prioritas (garis state → state di atas batas wilayah IBGE) dan perhitungan kebutuhan kapasitas saat lonjakan;
   - median untuk data yang miring, dan perbandingan ulang pada kelompok yang lebih sempit (misalnya hanya pesanan 1 barang yang tepat waktu);
   - batas minimum jumlah pesanan sebelum rute dan seller diberi peringkat;
   - isi komentar ulasan buruk diberi label (keluhan utama, posisi pesanan, pihak yang disalahkan) oleh **Claude** di luar notebook (`Notebook/llm_labeling/`), lalu dianalisis di bagian 5.1.8;
   - rute dianalisis per state, karena rute per kota terlalu tersebar (5.2.4).
6. **Prioritas & Estimasi Dampak** — skenario berbasis data historis, termasuk batas atas dan hubungan antar-metrik.
7. **Kesimpulan & Rekomendasi** — termasuk trade-off, urutan pelaksanaan, keterbatasan, dan future work.
8. **Ringkasan Angka Utama** — angka kunci dicetak langsung dari hasil analisis sebagai acuan slide.

## Temuan Utama

**Pilar 1 — WHAT**

| # | Temuan | Angka kunci |
|---|---|---|
| 1 | **Keterlambatan adalah faktor operasional paling berkaitan dengan ulasan buruk** | Pesanan telat: **62,4%** ulasan buruk vs **9,2%** pesanan tepat waktu (±6,8×). Hanya ±6,5% pesanan, tetapi menyumbang **±28%** ulasan buruk |
| 2 | Semakin lama telat, semakin buruk ulasannya | 32% (telat 1–3 hari) → 68% (4–7 hari) → ±80% (> 1 minggu) |
| 3 | Pada pesanan telat, pelanggan sering menilai **sebelum barangnya sampai** | ±74,5% pesanan telat sudah dikirimi survei sebelum barang tiba. Survei terkirim ±2 hari setelah estimasi lewat, dan Low Review Rate kelompok ini **75,2%** |
| 4 | Kompleksitas pesanan menjadi sumber ketidakpuasan tersendiri | Multi-seller **47,2%**, 4+ barang **35,3%**, tetap tinggi meskipun tepat waktu. ±72–78% ulasan buruknya mengeluhkan barang kurang atau salah, dan ±70% pesanan 2+ barang baru diterima sebagian |
| 5 | Ulasan buruk pesanan **tepat waktu** umumnya soal **barang yang diterima**, bukan pengiriman | Keluhan pesanan tepat waktu: barang kurang/salah **±47%**, kualitas produk **±25%**; pelanggan menyalahkan seller ±68% vs kurir ±9% |
| 6 | Setiap jenis keluhan punya asal yang berbeda, sehingga tindakannya juga berbeda | Barang salah/tidak sesuai: 53% dari pesanan 1 barang. Kualitas produk: 10% seller teratas = 50% keluhan. Layanan seller: 55% dari pesanan tidak sampai. Proses pengiriman: kurir disalahkan 56,5% |
| 7 | Ongkos kirim dan nilai pesanan hanya berkaitan **tidak langsung**; metode pembayaran **tidak terbukti berkaitan** | Pada pesanan 1 barang yang tepat waktu: ongkir 7,1% → 8,3%, nilai pesanan 7,3% → 8,0%. Metode bayar 13–16% (p = 0,057 ≥ 0,05, gagal menolak Ho) |

**Pilar 2 — WHERE & WHEN**

| # | Temuan | Angka kunci |
|---|---|---|
| 8 | Keterlambatan terkonsentrasi pada **11 rute prioritas** | ±23% pesanan → **±40%** pesanan telat |
| 9 | **SP → RJ** adalah rute dengan dampak terbesar, dan tidak dijelaskan oleh jarak | 14,4% telat (±1.150 pesanan) dengan jarak ±383 km, padahal rate wajar untuk jarak itu ±5,3% |
| 10 | **5 rute prioritas telat melebihi wajar** untuk jaraknya, sedangkan 3 rute telat karena jaraknya > 2.000 km | Melebihi wajar: SP → RJ, PR → RJ, SP → BA, SP → ES, SP → SC. Pengiriman jarak pendek di wilayah tujuan jarang telat: di dalam RJ **4,8%**, ke Nordeste dari ≤ 700 km **7,0%** |
| 11 | Pengiriman jauh dan ke Nordeste paling sering telat | > 1.500 km: **11,7%**; Nordeste: **12,8%** |
| 12 | Keterlambatan melonjak di semua region pada bulan tertentu | Nov 2017 (12,4%) bertepatan dengan Black Friday: volume minggu puncak **2,79×** normal, padahal yang selama ini masih tertangani hanya **1,59×**. Feb 2018 (14,1%) dan Mar 2018 (**19,0%**): volume stabil, tetapi transit melambat tanpa penyesuaian estimasi |
| 13 | Permintaan memuncak **Senin–Selasa**, dan **tidak ada lonjakan saat masa gajian** | Indeks harian Senin–Selasa 1,13× vs Sabtu 0,77×; awal bulan p = 0,23 (One Way ANOVA). Pesanan Jumat diproses seller ±3,2 hari vs ±1,3 hari |

**Pilar 3 — WHY & WHO**

| # | Temuan | Angka kunci |
|---|---|---|
| 14 | Perbedaan durasi terbesar ada di **tahap transit**; **27,8%** pesanan telat juga telat diserahkan oleh seller (72,2% diserahkan tepat waktu) | Transit pesanan telat ±26 hari vs ±7 hari; proses seller ±3,1 vs ±1,8 hari |
| 15 | Pesanan yang telat diserahkan seller ±3,9× lebih sering telat sampai | 21,3% vs 5,5% |
| 16 | Masalah seller terkonsentrasi pada **121 seller prioritas** | ±17% pesanan → **±40%** pesanan telat serah |
| 17 | Ada **30 seller berisiko** dengan keluhan produk walaupun tepat waktu, dan hanya sebagian yang juga telat serah | 14 dari 30 juga termasuk seller prioritas, jadi kedua daftar saling melengkapi |

## Rekomendasi

| # | Rekomendasi | Pemilik | Potensi dampak (skenario) |
|---|---|---|---|
| 1 | Tindak lanjut 11 rute prioritas: buka **gudang di Rio de Janeiro**, lalu **gudang Nordeste di Aracaju**; evaluasi mitra logistik pada 5 rute yang telat melebihi wajar; estimasi realistis untuk rute > 1.500 km; pantau per rute setiap minggu | Operasional & Logistik | ±1.130 pesanan telat, ±590 ulasan buruk (kedua gudang sendiri ±555 pesanan telat) |
| 2 | Persiapan bulan sibuk: kapasitas kurir **+75%** lalu **+22%** pada 2 minggu setelah Black Friday, siapkan ±60 seller terbesar 2–4 minggu sebelumnya, buffer estimasi **+3 hari**, tanda bahaya median transit mingguan > 8 hari, dan kapasitas harian mengikuti pola Senin–Selasa | Operasional & Logistik | hingga ±2.200 pesanan telat, ±1.150 ulasan buruk |
| 3 | Tindak lanjut per jenis keluhan: pelacakan per paket dan penundaan survei untuk pesanan multi-paket, checklist packing, evaluasi produk 30 seller berisiko dan 6 kategori berisiko, pantau stok dan pembatalan per seller | Seller Management & Customer Experience | seller berisiko: ±500 ulasan buruk; pesanan kompleks diterima lengkap: hingga ±1.380 (batas atas) |

**Gabungan perbaikan rute prioritas dan seller prioritas (skenario A + B, notebook 5.4):**
- Late Delivery Rate 6,79% → **±5,3%** (−22% pesanan telat).
- **±750 ulasan buruk** lebih sedikit (±450 per tahun).
- **Low Review Rate 14,61% → ±13,84%** (−0,8 poin persen, atau ±5% ulasan buruk).
- Skenario seller: Seller Late Handover Rate 121 seller prioritas turun ke baseline 9,1%.

**Batas atas:** walaupun seluruh keterlambatan dihilangkan, ulasan buruk hanya berkurang ±23,6% (Low Review Rate 14,61% → ±11,2%). Jadi faktor di luar keterlambatan (pesanan tidak sampai, pesanan kompleks, serta kualitas dan kesesuaian produk) tetap perlu ditangani.

**Urutan pelaksanaan yang disarankan:**
- **Segera:** Rekomendasi 1, karena daftar rute prioritas sudah tersedia dan dapat dipantau lewat dashboard.
- **Uji coba terbatas:** penundaan survei pada Rekomendasi 3.
- **Menjelang periode puncak:** Rekomendasi 2, disiapkan sebelum Black Friday.
- **Jangka menengah:** gudang Rio de Janeiro lalu gudang Nordeste (Rekomendasi 1), serta pelacakan per paket (Rekomendasi 3), karena membutuhkan investasi dan perubahan sistem.

> Estimasi dampak adalah skenario berbasis data historis. Angkanya menunjukkan **keterkaitan**, bukan sebab-akibat.

## Struktur Repository

```
├── README.md
├── Notebook/
│   ├── Alpha - FINPRO - Analisis Ulasan Buruk dan Keterlambatan Olist.ipynb   # notebook analisis utama
│   └── llm_labeling/                                                            # labeling isi ulasan dengan Claude: script, codebook, konteks, contoh QA
├── Dataset/
│   ├── olist_*.csv, product_category_name_translation.csv                      # 9 file data mentah dari Kaggle
│   ├── review_labels_llm.csv                                                    # label isi ulasan buruk dari Claude (dibaca notebook di 5.1.8)
│   ├── brazil_uf_ibge.geojson                                                   # batas wilayah state dari IBGE (peta rute di 5.2.4)
│   └── olist_order_level.csv                                                    # TIDAK di-upload; dibuat oleh notebook (langkah 4.8), sumber dashboard
└── PPT/                                                                         # slide presentasi
```

> Notebook hanya mengekspor **satu file**, yaitu `olist_order_level.csv`. File ini dipakai sebagai sumber data dashboard karena ketiga metrik dihitung per pesanan.
>
> Seluruh 9 file data mentah Olist sudah ada di folder `Dataset/`, termasuk `olist_geolocation_dataset.csv` (±61 MB). `olist_order_level.csv` (±71 MB) **tidak di-upload** (ada di `.gitignore`) karena dibuat ulang otomatis saat notebook dijalankan.

## Cara Menjalankan

1. Install library:
   ```
   pip install pandas numpy matplotlib seaborn scipy statsmodels
   ```
   Dijalankan dengan Python 3.13, pandas 3.0, NumPy 2.5, Matplotlib 3.11, seaborn 0.13, SciPy 1.18, dan statsmodels 0.14.
2. Pastikan folder `Dataset/` berisi 9 file CSV Olist, `review_labels_llm.csv`, dan `brazil_uf_ibge.geojson`. File label tidak perlu dibuat ulang. Jika ingin membuat ulang, lihat petunjuk di `Notebook/llm_labeling/run_claude_code.py` (membutuhkan Claude Code).
3. Buka notebook di folder `Notebook/`, lalu jalankan semua cell (**Run All**). Notebook membaca data dari `../Dataset/`. Jika dijalankan di Google Colab, ubah variabel `DATA_PATH` sesuai lokasi file.

## Keterbatasan

- Temuan adalah **keterkaitan** pada data historis 2017–2018, bukan bukti sebab-akibat.
- Tidak ada data identitas kurir, sehingga hambatan transit tidak dapat dikaitkan ke mitra logistik tertentu.
- Tidak ada data penyebab internal seller (stok, kapasitas, packing).
- Analisis rute dan seller memakai pesanan 1 seller (±98,7% pesanan dengan barang), karena tanggal serah ke kurir dicatat per pesanan.
- Jarak adalah jarak garis lurus antar titik tengah kode pos, bukan jarak tempuh sebenarnya.
- Potensi gudang memakai asumsi gudang melayani 50% pesanan rutenya. Jika hanya 30%, dampaknya turun menjadi ±60% (gudang RJ ±262, gudang Nordeste ±71 pesanan telat).
- Kebutuhan kapasitas saat lonjakan dihitung dari volume dataset. Untuk kondisi nyata, yang dipakai adalah persentasenya (+75% dan +22%), bukan jumlah paketnya.
- Label isi ulasan dibuat oleh Claude dari teks komentar saja. QA manual oleh tim pada 150 ulasan acak: **Pain Points 94,0%**, **Review Stage 94,7%**, **Blame Target 79,3%**.
  - Blame Target paling rendah, terutama pada label *Not Mentioned*, karena label ini paling bergantung pada tafsir. Karena itu Blame Target hanya dipakai sebagai gambaran persepsi pelanggan.
  - Label hanya mencakup ±75% ulasan buruk yang berkomentar.
  - Keluhan yang dilabel adalah persepsi pelanggan, bukan penyebab yang terbukti.
- Kode pos di dataset hanya 5 digit awal, sehingga nama kota dapat tertukar dengan kota tetangga; karena itu rute dianalisis per state.
- Data akhir Agustus 2018 tidak lengkap, sehingga angka bulan tersebut perlu dibaca hati-hati.

## Referensi

- Olist & André Sionek. *Brazilian E-Commerce Public Dataset by Olist*. Kaggle. https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Rentang kode pos (CEP) per state: Correios, *Tudo sobre CEP*, https://www.correios.com.br/enviar/precisa-de-ajuda/tudo-sobre-cep ; Remessa Online, *Código postal*, https://www.remessaonline.com.br/blog/codigo-postal-2/
- Batas wilayah state untuk peta rute: IBGE, *API de Malhas Geográficas* (malha UF, kualitas minimum), https://servicodados.ibge.gov.br/api/docs/malhas?versao=3 (disimpan sebagai `Dataset/brazil_uf_ibge.geojson`)
- Pembagian 5 region resmi Brasil: IBGE, *Divisões regionais do Brasil*, https://agenciadenoticias.ibge.gov.br/pt/agencia-noticias/19383-dividir-para-conhecer-as-diversas-divisoes-regionais-do-brasil.html
- Mogok pegawai Correios 12–13 Maret 2018: Brasil de Fato, https://www.brasildefato.com.br/2018/03/12/funcionarios-dos-correios-entram-em-greve-nesta-segunda-feira-12/ ; Banda B, https://www.bandab.com.br/nacional/funcionarios-dos-correios-encerram-greve-apos-derrota-na-justica-sobre-planos-de-saude/amp/
- Batas pembayaran gaji bulanan (hari kerja ke-5 bulan berikutnya): Brasil, *Consolidação das Leis do Trabalho* (Decreto-Lei 5.452/1943), Pasal 459 §1, https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm
- Jadwal pembayaran gaji ke-13: Brasil, *Lei 4.749/1965*, Pasal 1–2, https://www.planalto.gov.br/ccivil_03/leis/l4749.htm
- Libur Karnaval 10–14 Februari 2018: timeanddate.com, https://www.timeanddate.com/holidays/brazil/2018
- SciPy documentation (`chi2_contingency`, `normaltest`, `mannwhitneyu`, `f_oneway`): https://docs.scipy.org/doc/scipy/reference/stats.html
- statsmodels documentation (`proportions_ztest`): https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportions_ztest.html
- Sinnott, R. W. (1984). *Virtues of the Haversine*. Sky and Telescope, 68(2), 159.
- Materi Module 1–3 Purwadhika JC Business & Data Analyst.

**Pernyataan penggunaan AI:** Claude (Anthropic) dipakai untuk memberi label isi komentar ulasan buruk. Akurasinya sudah dicek manual oleh tim pada 150 sampel acak: Pain Points 94,0%, Review Stage 94,7%, Blame Target 79,3%.
