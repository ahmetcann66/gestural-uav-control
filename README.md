# gestural-uav-control

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-FF6F00?style=flat-square)
![ArduPilot](https://img.shields.io/badge/ArduPilot-SITL%20%2B%20Real%20HW-02569B?style=flat-square)
![MAVLink](https://img.shields.io/badge/MAVLink-v1-00897B?style=flat-square)
![Tested](https://img.shields.io/badge/Tested%20On-Real%20Drone%20%E2%9C%85-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-orange?style=flat-square)

> **Real-time markerless hand gesture recognition pipeline for autonomous UAV flight control via MAVLink protocol — no physical controller required.**
>
> ✅ **Tested on real hardware:** F450 Quadrotor + Matek F405 + ArduPilot — tüm kontrol komutları gerçek drone üzerinde doğrulanmıştır.

---

```
        ╔══════════════════════════════════════════╗
        ║                                          ║
        ║    ✋  →  🧠  →  📡  →  🚁              ║
        ║   Hand   CV   MAVLink  UAV               ║
        ║                                          ║
        ╚══════════════════════════════════════════╝

           gestural-uav-control  |  ahmetcann66
```

---

## İçindekiler

- [Projeye Genel Bakış](#projeye-genel-bakış)
- [Gerçek Donanım Test Sonuçları](#gercek-donanim-test-sonuclari)
- [Sistem Mimarisi](#sistem-mimarisi)
- [Teorik Arka Plan](#teorik-arka-plan)
- [Dosya Yapısı](#dosya-yapısı)
- [Kullanılan Teknolojiler](#kullanılan-teknolojiler)
- [Kurulum](#kurulum)
- [Hassasiyet Kalibrasyonu](#hassasiyet-kalibrasyonu)
- [Kontrol Referansı](#kontrol-referansı)
- [Güvenlik Uyarıları](#guvenlik-uyarilari)
- [Akademik Referanslar](#akademik-referanslar)
- [Lisans](#lisans)

---

## Projeye Genel Bakış

Bu proje, herhangi bir fiziksel RC kumanda cihazına ihtiyaç duymaksızın, yalnızca standart bir USB web kamerası ve Python yazılım yığını aracılığıyla bir quadrotor İHA'yı gerçek zamanlı el hareketleriyle kontrol etmeyi amaçlayan bir araştırma-geliştirme sistemidir.

Sistem iki bağımsız modülden oluşmaktadır:

| Modül | Dosya | Görev |
|---|---|---|
| **El Takip Motoru** | `hand_tracker.py` | Bağımsız hareket tespiti ve komut üretimi |
| **Ana Kontrol Birimi** | `master_kontrol.py` | Hibrit gesture + parmak kombinasyon kontrolü, MAVLink entegrasyonu |

> *"The use of hand gestures provides a natural and intuitive way to interact with machines, eliminating the need for complex physical interfaces."*
> — Mitra & Acharya (2007), IEEE Transactions on Systems, Man, and Cybernetics

---

## Gerçek Donanım Test Sonuçları

> ✅ Bu proje yalnızca simülatörde değil, **gerçek bir quadrotor drone üzerinde** başarıyla test edilmiştir.

### Test Ortamı

| Parametre | Değer |
|---|---|
| Platform | F450 Quadrotor (DIY) |
| Flight Controller | Matek F405-WING |
| Firmware | ArduPilot (GUIDED mod) |
| Telemetri | SiK 433MHz çift yönlü |
| Test Ortamı | Açık alan, rüzgarsız |
| Kalkış Yüksekliği | 2 metre |
| Kontrol Mesafesi | ~5–8 metre (USB telemetri) |

### Doğrulanan Komutlar

| Komut | SITL | Gerçek Drone |
|---|---|---|
| ARM + Takeoff | ✅ | ✅ |
| Hover (sabit bekleme) | ✅ | ✅ |
| İleri / Geri (parmak) | ✅ | ✅ |
| Sağa / Sola (bilek) | ✅ | ✅ |
| Low-pass filtre yumuşatma | ✅ | ✅ |
| Kill-switch (Q tuşu) | ✅ | ✅ |

### Gözlemlenen Davranışlar

- `smooth_factor = 0.05` değeri gerçek donanımda kararlı ve öngörülebilir hareket sağlamıştır
- `tolerance = 70 px` değeri istem dışı komutları önlemek için yeterli ölü bölge sağlamıştır
- El kaybında otomatik hover devreye girmiş, drone sürüklenmemiştir
- İlk uçuşlarda **pervane koruyucu (prop guard)** kullanılmıştır

> ⚠️ **Önemli:** Parametreleri (`smooth_factor`, `tolerance`, hız değerleri) değiştirmeden önce mutlaka aşağıdaki [Hassasiyet Kalibrasyonu](#hassasiyet-kalibrasyonu) bölümünü okuyun.

---

## Sistem Mimarisi

### Genel Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     GESTURAL UAV CONTROL                        │
│                      SYSTEM PIPELINE                            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  GORUNTU     │    │  EL TESPITI  │    │  YORUMLAMA   │
│  YAKALAMA    │───▶│  KATMANI     │───▶│  MOTORU      │
│              │    │              │    │              │
│  OpenCV 4.x  │    │  MediaPipe   │    │  Python 3.10 │
│  30 FPS      │    │  Hands v2    │    │  Heuristics  │
│  640x480     │    │  21 landmark │    │  + Filter    │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                    ┌──────────────┐           │
                    │  FLIGHT      │           ▼
                    │  CONTROLLER  │◀─── ┌──────────────┐
                    │              │     │  MAVLink     │
                    │  ArduPilot   │     │  PAKETI      │
                    │  GUIDED mod  │     │              │
                    │  4x ESC/PWM  │     │  DroneKit    │
                    └──────────────┘     │  SiK 433MHz  │
                                        └──────────────┘
```

### Katman Detayları

```
KATMAN 1 — Goruntu Yakalama
  └─ cv2.VideoCapture(0) → 30 FPS MJPEG akisi
  └─ cv2.flip(img, 1)    → ayna simetri duzeltmesi

KATMAN 2 — El Tespiti (MediaPipe Hands)
  └─ BlazePalm dedektoru → el bolgesi tespiti
  └─ Hand Landmark Model → 21 x (x, y, z) koordinat tahmini
  └─ min_detection_confidence = 0.75

KATMAN 3 — Hareket Yorumlama
  ├─ hand_tracker.py   → delta-konum tabanli motor (dx, dy)
  └─ master_kontrol.py → hibrit: parmak sayimi + bilek pozisyonu

KATMAN 4 — Sinyal Yumusatma
  └─ Ustel Low-Pass Filtre: v_out += (v_target - v_out) x alpha
  └─ alpha = 0.05 (smooth_factor) — gercek drone uzerinde test edildi

KATMAN 5 — MAVLink Iletisimi
  └─ SET_POSITION_TARGET_LOCAL_NED
  └─ MAV_FRAME_LOCAL_NED referans cercevesi
  └─ TCP (SITL) veya USB telemetri (SiK 433MHz)

KATMAN 6 — Flight Controller
  └─ ArduPilot GUIDED modu
  └─ Ic PID dongusu → 4x ESC PWM sinyali
```

---

## Teorik Arka Plan

### El Iskeleti Modeli (Hand Landmark Model)

MediaPipe Hands, her goruntu karesinde **21 adet 3 boyutlu el eklemi noktasi** cikarimi yapar:

```
Parmak uclari (tipIds):  8   12  16  20
                         |   |   |   |
PIP eklemleri (pipIds):  6   10  14  18
                         |   |   |   |
MCP eklemleri:           5    9  13  17
                          \   |   |  /
Basparmak:                 2   3
                           |
                           1
Bilek (Wrist):             0  ← Birincil kontrol referansi
```

### Hareket Tespiti — Iki Farkli Yaklasim

#### Yaklasim A — Delta-Konum Motoru (`hand_tracker.py`)

```
delta_x = cx(t) - cx(t-1)
delta_y = cy(t) - cy(t-1)

if |delta_x| > |delta_y|:
    delta_x > hassasiyet  →  SAGA
    delta_x < -hassasiyet →  SOLA
else:
    delta_y < -hassasiyet →  YUKARI
    delta_y > hassasiyet  →  ASAGI
```

#### Yaklasim B — Hibrit Gesture (`master_kontrol.py`)

```
KATMAN A — Parmak sayimi:
  [1,0,0,0] → 1 parmak acik → ILERI (vx = +1.5 m/s)
  [1,1,0,0] → 2 parmak acik → GERI  (vx = -1.5 m/s)

KATMAN B — Bilek pozisyonu:
  cx > center_x + tolerance → SAGA (vy = +1.5 m/s)
  cx < center_x - tolerance → SOLA (vy = -1.5 m/s)
```

### Sinyal Yumusatma — Ustel Low-Pass Filtre

```
v[n] = v[n-1] + alpha x (v_target[n] - v[n-1])

alpha = 0.05  →  Gercek drone uzerinde test edilmis, onerilen deger
```

| alpha | Davranis | Durum |
|---|---|---|
| 0.02 – 0.04 | Cok yumusak | Dar alan, hassas gorevler |
| **0.05** | **Dengeli** | **Gercek drone testi — onerilen** |
| 0.10 – 0.15 | Hizli tepki | Acik alan, deneyimli kullanici |
| 1.0 | Ham sinyal | Kesinlikle kullanilmayin |

---

## Dosya Yapısı

```
gestural-uav-control/
│
├── master_kontrol.py       # Ana kontrol birimi
│                           # Hibrit gesture + MAVLink entegrasyonu
│
├── hand_tracker.py         # El takip motoru (bagimsiz modul)
│                           # DroneKit gerektirmez — izole test edilebilir
│
├── requirements.txt        # Python bagimliliklar
│
├── .gitignore              # drone_env/ ve cache dosyalarini haric tut
│
└── README.md               # Bu dosya
```

---

## Kullanılan Teknolojiler

| Teknoloji | Versiyon | Gorev |
|---|---|---|
| **Python** | 3.10+ | Ana programlama dili |
| **OpenCV** | 4.x | Kamera yakalama, goruntu isleme |
| **MediaPipe** | 0.10+ | El iskelet tespiti, 21 landmark |
| **DroneKit-Python** | 2.9.x | MAVLink soyutlama katmani |
| **PyMAVLink** | 2.x | Dusuk seviye MAVLink mesaj fabrikasi |
| **NumPy** | 1.24+ | Vektor hesaplamalari |
| **ArduPilot SITL** | — | Sanal simulasyon ortami |

---

## Kurulum

### 1. Repoyu klonlayın

```bash
git clone https://github.com/ahmetcann66/gestural-uav-control.git
cd gestural-uav-control
```

### 2. Sanal ortam oluşturun

```bash
python -m venv drone_env

# Windows:
drone_env\Scripts\activate

# Linux / macOS:
source drone_env/bin/activate
```

### 3. Bağımlılıkları kurun

```bash
pip install -r requirements.txt
```

### 4. Python uyumluluk yaması

DroneKit, Python 3.10+ ile `collections.MutableMapping` hatasi verir. Her iki dosyanin en ustunde bu yama mevcuttur — ek bir islem gerekmez.

### 5. SITL ile test

```bash
# Terminal 1
sim_vehicle.py -v ArduCopter --console --map

# Terminal 2
python hand_tracker.py   # DroneKit gerektirmez, izole test

# Terminal 3
python master_kontrol.py
```

### 6. Gerçek donanıma geçiş

```python
# master_kontrol.py icinde:

# SITL:
vehicle = connect('tcp:127.0.0.1:5762', wait_ready=True)

# Gercek drone — Linux:
vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=True)

# Gercek drone — Windows:
vehicle = connect('COM3', baud=57600, wait_ready=True)
```

---

## Hassasiyet Kalibrasyonu

> ⚠️ **UYARI: Aşağıdaki parametreleri değiştirmeden önce bu bölümü tamamen okuyun.**
> Yanlış yapılandırma drone'un kontrolden çıkmasına yol açabilir.

Parametreleri kodu açmadan önce kafanızda simüle edin. Her değişiklikten sonra **önce SITL'de test edin**, ardından gerçek drone'a geçin.

---

### `smooth_factor` — Hareket Yumuşatma

```python
smooth_factor = 0.05  # master_kontrol.py satir 28
```

Bu değer, drone'a gönderilen hızın ne kadar "yumuşak" artacağını belirler.

```
Dusuk alpha (0.02):
  Komut verildi → drone cok yavas tepki verir
  Avantaj: Titremez, cok kararli
  Dezavantaj: Gecikmeli, agir hisseder

Yuksek alpha (0.15+):
  Komut verildi → drone hemen tepki verir
  Avantaj: Hizli, duyarli
  Dezavantaj: Gürültüye duyarli, ani sarsintılar olabilir

ONERILEN: 0.04 – 0.06 arasi
GERCEK DRONE TESTINDE KULLANILAN: 0.05
```

**Degistirme sırası:**
1. SITL'de 0.03 deneyin → cok mu yavas?
2. 0.07 deneyin → cok mu sert?
3. Aralarinda bir deger secin
4. Ancak sonra gercek drone'da deneyin

---

### `tolerance` — Ölü Bölge

```python
tolerance = 70  # master_kontrol.py satir 34
```

Ekranin merkezinde bu piksel yaricapindaki alana girildiginde hover komutu verilir. Bilek bu alanin disina cikinca hareket komutu baslar.

```
Kucuk tolerance (30–40 px):
  El cok az oynarsa bile komut baslar
  Dezavantaj: El titremesi yanlis komutlara yol acar

Buyuk tolerance (80–100 px):
  Daha genis "sessiz bolge"
  Dezavantaj: Komut verisi icin elin cok hareket etmesi gerekir

ONERILEN: 60 – 80 px arasi
GERCEK DRONE TESTINDE KULLANILAN: 70
```

---

### Hız Değerleri — `target_vx` ve `target_vy`

```python
target_vx = 1.5   # ileri/geri hiz (m/s) — master_kontrol.py
target_vy = 1.5   # sag/sol hiz (m/s)
```

```
1.5 m/s → Yavas, guvenli, onerilen baslangic
3.0 m/s → Orta hiz, deneyimli kullanici
5.0+ m/s → Tehlikeli, dar alanda kullanilmaz

GERCEK DRONE TESTINDE KULLANILAN: 1.5 m/s
KESINLIKLE DENEMEYIN: 5.0 m/s (orijinal ilk deger — kontrolden cikabilir)
```

---

### `hassasiyet` — Delta Motor Eşiği (`hand_tracker.py`)

```python
hassasiyet = 10  # hand_tracker.py satir 13
```

Delta-konum motorunda kac piksel hareketten sonra komut uretilecegini belirler.

```
Dusuk (5 px):  En kucuk el titremesi bile komut uretir
Yuksek (20 px): El belirgin sekilde hareket etmeli
ONERILEN: 8 – 12 px arasi
```

---

### Kalibrasyonu Test Etme (Drone Olmadan)

`hand_tracker.py` dosyasini calistirin — bu modul DroneKit gerektirmez:

```bash
python hand_tracker.py
```

Ekranda komutlarin dogru tetiklenip tetiklenmedigini gozlemleyin. Yalnizca bu moduldeki davranistan memnun oldugunuzda `master_kontrol.py` ve gercek drone'a gecin.

---

## Kontrol Referansı

### `master_kontrol.py`

| Gesture | Drone Aksiyonu | Hiz |
|---|---|---|
| 1 parmak acik `[1,0,0,0]` | ILERI | +vx = 1.5 m/s |
| 2 parmak acik `[1,1,0,0]` | GERI | -vx = 1.5 m/s |
| Bilek saga | SAGA | +vy = 1.5 m/s |
| Bilek sola | SOLA | -vy = 1.5 m/s |
| El gorunmuyor | HOVER | tum hiz → 0 |
| `T` tusu | ARM + TAKEOFF (2m) | — |
| `Q` tusu | Kapat / Failsafe | — |

### `hand_tracker.py`

| Hareket | Komut | Esik |
|---|---|---|
| Bilek hizli saga | SAGA DON | delta_x > 10 px |
| Bilek hizli sola | SOLA DON | delta_x < -10 px |
| Bilek hizli yukari | YUKARI | delta_y < -10 px |
| Bilek hizli asagi | ASAGI | delta_y > 10 px |
| Hareketsiz | HOVER | 5 kare bekle |

---

## Güvenlik Uyarıları

> 🚨 **BU BOLUMU ATLAYAMAZSINIZ. Gercek drone kullanmadan once okuyun.**

### Ucus Oncesi Kontrol Listesi

Asagidaki her maddeyi ucustan once tek tek kontrol edin:

- [ ] Drone'un etrafinda minimum **10 metre** bos alan var
- [ ] Etrafta insan, hayvan veya engel yok
- [ ] Batarya en az **%80** dolu
- [ ] GPS kilidi alinmis (QGroundControl'de 3D Fix gorunuyor)
- [ ] Pervane koruyucu (prop guard) takili
- [ ] `Q` tusuna erisim rahat — acil durumda 1 saniyede ulasabilirsiniz
- [ ] Kamera goruntu akisi stabil, el tespiti calisıyor
- [ ] SITL testleri tamamlanmis

### Parametre Degisikliklerinde Uyari

```
⚠️  smooth_factor > 0.10 → Once SITL'de test et
⚠️  hiz degerleri > 2.0 m/s → Genis acik alan gerektirir
⚠️  tolerance < 50 px → El titremesine karsi cok duyarli olur
⚠️  min_detection_confidence < 0.60 → Yanlis el tespitleri artar
```

### Turkiye Mevzuati

- 500 gram uzeri tum IHA'lar **SHGM'ye kayit yaptırılmalidir**
- Izinsiz ucus yapilabilecek bolgeler icin **SHGM IHA Portali**'ni kontrol edin
- Yerlesim alanlari, havalanlar ve askeri bolgelerin yakininda ucus yasaklidir

### Acil Durum Protokolu

```
1. Q tusuna basin → program kapanir, drone failsafe'e gecer
2. ArduPilot otomatik olarak RTL (Return to Launch) moduna gerer
3. Drone kalkis noktasina donup iner
```

---

## Akademik Referanslar

1. **Zhang, F. et al.** (2020). *MediaPipe Hands: On-device Real-time Hand Tracking.* arXiv:2006.10214. Google Research.

2. **Mitra, S. & Acharya, T.** (2007). *Gesture Recognition: A Survey.* IEEE Transactions on Systems, Man, and Cybernetics, Part C, 37(3), 311–324.

3. **Meier, L. et al.** (2011). *PIXHAWK: A System for Autonomous Flight using Onboard Computer Vision.* IEEE ICRA, 2992–2997.

4. **Bazarevsky, V. et al.** (2019). *BlazeFace: Sub-millisecond Neural Face Detection on Mobile GPUs.* arXiv:1907.05047.

5. **Luckcuck, M. et al.** (2019). *Formal Specification and Verification of Autonomous Robotic Systems: A Survey.* ACM Computing Surveys, 52(5), 1–41.

---

## Lisans

Bu proje [MIT Lisansi](LICENSE) altinda dagitilmaktadir.

```
MIT License — Copyright (c) 2026 ahmetcann66
```

---

<div align="center">

**gestural-uav-control** — Computer Vision x UAV Control Systems

Tested on real hardware · `ahmetcann66` · MIT License · 2026

</div>
