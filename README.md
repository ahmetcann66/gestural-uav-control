# gestural-uav-control

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-FF6F00?style=flat-square)
![ArduPilot](https://img.shields.io/badge/ArduPilot-SITL-02569B?style=flat-square)
![MAVLink](https://img.shields.io/badge/MAVLink-v1-00897B?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-orange?style=flat-square)

> **Real-time markerless hand gesture recognition pipeline for autonomous UAV flight control via MAVLink protocol — no physical controller required.**

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
- [Sistem Mimarisi](#sistem-mimarisi)
- [Teorik Arka Plan](#teorik-arka-plan)
- [Dosya Yapısı](#dosya-yapısı)
- [Kullanılan Teknolojiler](#kullanılan-teknolojiler)
- [Kurulum](#kurulum)
- [Kontrol Referansı](#kontrol-referansı)
- [Yapılandırma Parametreleri](#yapılandırma-parametreleri)
- [Akademik Referanslar](#akademik-referanslar)
- [Güvenlik](#güvenlik)
- [Lisans](#lisans)

---

## Projeye Genel Bakış

Bu proje, herhangi bir fiziksel RC kumanda cihazına ihtiyaç duymaksızın, yalnızca standart bir USB web kamerası ve Python yazılım yığını aracılığıyla bir quadrotor İHA'yı (İnsansız Hava Aracı) gerçek zamanlı el hareketleriyle kontrol etmeyi amaçlayan bir araştırma-geliştirme sistemidir.

Sistem iki bağımsız modülden oluşmaktadır:

| Modül | Dosya | Görev |
|---|---|---|
| **El Takip Motoru** | `hand_tracker.py` | Bağımsız hareket tespiti ve komut üretimi (DroneKit gerektirmez) |
| **Ana Kontrol Birimi** | `master_kontrol.py` | Hibrit gesture + parmak kombinasyon kontrolü, MAVLink entegrasyonu |

> *"The use of hand gestures provides a natural and intuitive way to interact with machines, eliminating the need for complex physical interfaces."*
> — Mitra & Acharya (2007), IEEE Transactions on Systems, Man, and Cybernetics

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
                    │  PID Loop    │     │              │
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
  └─ alpha = 0.05 (smooth_factor)

KATMAN 5 — MAVLink Iletisimi
  └─ SET_POSITION_TARGET_LOCAL_NED
  └─ MAV_FRAME_LOCAL_NED referans cercevesi
  └─ TCP (SITL) veya USB telemetri

KATMAN 6 — Flight Controller
  └─ ArduPilot GUIDED modu
  └─ Ic PID dongusu → 4x ESC PWM sinyali
```

---

## Teorik Arka Plan

### El Iskeleti Modeli (Hand Landmark Model)

MediaPipe Hands, her goruntu karesinde **21 adet 3 boyutlu el eklemi noktasi** cikarimi yapar. Model, iki asamali bir derin ogrenme pipeline'i kullanir:

1. **BlazePalm** — avuc ici bolge tespiti (mobilenet-tabanli)
2. **Hand Landmark Model** — 21 anahtar nokta regresyonu

```
Parmak uclari (tipIds):  8   12  16  20
                         |   |   |   |
PIP eklemleri (pipIds):  6   10  14  18
                         |   |   |   |
MCP eklemleri:           5    9  13  17
                          \   |   |  /
                           \  |   | /
Basparmak:                  2  3  
                            |      
                            1      
                                   
Bilek (Wrist):              0  ← Birincil kontrol referansi
```

Bu projede kullanilan kritik noktalar:
- **Landmark 0** (bilek) → birincil pozisyon referansi
- **Landmark 8, 12, 16, 20** (`tipIds`) → parmak ucu tespiti
- **Landmark 6, 10, 14, 18** (`pipIds`) → PIP eklemi karsilastirma referansi

### Hareket Tespiti — Iki Farkli Yaklasim

#### Yaklasim A — Delta-Konum Motoru (`hand_tracker.py`)

Bilek noktasinin ardisik kareler arasindaki piksel kaymasini olcer:

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

Avantaji: Kamera cercevesine bagimsiz, goreceli hareket tespiti.

#### Yaklasim B — Hibrit Gesture (`master_kontrol.py`)

Iki katmanli komut sistemi:

```
KATMAN A — Parmak sayimi (ileri/geri):
  tipId[i].y < pipId[i].y  →  parmak acik (1)
  tipId[i].y >= pipId[i].y →  parmak kapali (0)

  [1,0,0,0] → 1 parmak acik → ILERI (vx = +1.5 m/s)
  [1,1,0,0] → 2 parmak acik → GERI  (vx = -1.5 m/s)

KATMAN B — Bilek pozisyonu (sag/sol):
  cx > center_x + tolerance → SAGA (vy = +1.5 m/s)
  cx < center_x - tolerance → SOLA (vy = -1.5 m/s)

Kombine komutlar desteklenir: "2 FINGERS -> BWD & RIGHT"
```

### Sinyal Yumusatma — Ustel Low-Pass Filtre

Ham el koordinatlari, goruntu gurultusu ve titreme nedeniyle yuksek frekanslı bilesenleri icerir. Drone'a ani hiz komutlari gondermek mekanik kararsiziliga yol acar. Bu nedenle **discrete-time IIR low-pass filtre** uygulanmistir:

```
v[n] = v[n-1] + alpha x (v_target[n] - v[n-1])

Burada:
  v[n]        → n. karedeki drone'a gonderilen gercek hiz
  v_target[n] → n. karedeki hedef (ham) hiz
  alpha       → smooth_factor (0 < alpha <= 1)
```

alpha degerinin etkileri:

| alpha degeri | Davranis | Kullanim durumu |
|---|---|---|
| 0.02 – 0.04 | Cok yumusak, sinematik | Ince hassasiyet gerektiren gorevler |
| **0.05 (mevcut)** | **Dengeli** | **Genel kullanim** |
| 0.10 – 0.15 | Hizli tepki | Yarisma / hiz gerektiren gorevler |
| 1.0 | Filtre yok (ham) | Test amacli |

### MAVLink SET_POSITION_TARGET_LOCAL_NED

```
Mesaj tipi  : SET_POSITION_TARGET_LOCAL_NED (#84)
Cerceve     : MAV_FRAME_LOCAL_NED
Type mask   : 0b0000111111000111
              (yalnizca hiz bilesenleri aktif)

Koordinat sistemi (NED):
  +X → Kuzey (Ileri)
  +Y → Dogu  (Saga)
  +Z → Asagi (Yukseklik azalir — dikkat!)

Drone'a gonderilen:
  velocity_x = vx  (kuzey bileseni)
  velocity_y = vy  (dogu bileseni)
  velocity_z = vz  (dikey — ASAGI pozitif!)
```

---

## Dosya Yapısı

```
gestural-uav-control/
│
├── master_kontrol.py       # Ana kontrol birimi
│                           # Hibrit gesture + MAVLink entegrasyonu
│                           # DroneKit baglantisi, arm/takeoff, velocity loop
│
├── hand_tracker.py         # El takip motoru (bagimsiz modul)
│                           # Delta-konum tabanli hareket tespiti
│                           # DroneKit gerektirmez — izole test edilebilir
│
├── requirements.txt        # Python bagimliliklar
│
├── .gitignore              # drone_env/ ve __pycache__/ haric tut
│
└── README.md               # Bu dosya
```

> **Not:** `drone_env/` klasoru `.gitignore` ile haric tutulmalidir — repoya eklenmez.

---

## Kullanılan Teknolojiler

### Yazılım Yığını

| Teknoloji | Versiyon | Gorev |
|---|---|---|
| **Python** | 3.10+ | Ana programlama dili |
| **OpenCV** (`opencv-python`) | 4.x | Kamera yakalama, goruntu isleme, UI |
| **MediaPipe** | 0.10+ | El iskelet tespiti, 21 landmark |
| **DroneKit-Python** | 2.9.x | MAVLink soyutlama katmani, vehicle API |
| **PyMAVLink** | 2.x | Dusuk seviye MAVLink mesaj fabrikasi |
| **NumPy** | 1.24+ | Koordinat vektor hesaplamalari |

### Donanım (Geliştirme Ortamı)

| Bilesyen | Oneri |
|---|---|
| Frame | F450 Quadrotor |
| Flight Controller | Matek F405-WING (ArduPilot uyumlu) |
| GPS | M8N 6M |
| Motor | EMAX 2216 810KV × 4 |
| ESC | BLHeli 30A × 4 |
| Batarya | LiPo 4S 2200mAh 30C |
| Telemetri | SiK 433MHz cift yonlu |
| Kamera | USB Webcam ≥720p, ≥30fps |

### Simülasyon Ortamı

| Arac | Gorev |
|---|---|
| **ArduPilot SITL** | Sanal flight controller simulasyonu |
| **QGroundControl** | Telemetri izleme, harita gorunumu |
| **MAVProxy** | Komut satiri MAVLink proxy |

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

`requirements.txt`:
```
mediapipe>=0.10.0
opencv-python>=4.8.0
dronekit>=2.9.2
pymavlink>=2.4.41
numpy>=1.24.0
```

### 4. Python uyumluluk yaması

DroneKit, Python 3.10+ ile `collections.MutableMapping` hatasi verir. Her iki dosyanin en ustunde bu yama mevcuttur:

```python
import collections
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping
```

### 5. SITL ile test

```bash
# Terminal 1 — SITL baslat
sim_vehicle.py -v ArduCopter --console --map

# Terminal 2 — El takip modulunu izole test et
python hand_tracker.py

# Terminal 3 — Ana kontrol (SITL ile)
python master_kontrol.py
```

### 6. Gerçek donanıma geçiş

```python
# SITL:
vehicle = connect('tcp:127.0.0.1:5762', wait_ready=True)

# Gercek drone — Linux:
vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=True)

# Gercek drone — Windows:
vehicle = connect('COM3', baud=57600, wait_ready=True)
```

---

## Kontrol Referansı

### `master_kontrol.py` — Hibrit Kontrol

| Gesture | Drone Aksiyonu | Hiz |
|---|---|---|
| 1 parmak acik `[1,0,0,0]` | ILERI | +vx = 1.5 m/s (smooth) |
| 2 parmak acik `[1,1,0,0]` | GERI | -vx = 1.5 m/s (smooth) |
| Bilek saga kayma | SAGA | +vy = 1.5 m/s (smooth) |
| Bilek sola kayma | SOLA | -vy = 1.5 m/s (smooth) |
| El gorunmuyor | HOVER | tum hiz → 0 |
| `T` tusu | ARM + TAKEOFF (2m) | — |
| `Q` tusu | Kapat / Failsafe | — |

Kombine komutlar desteklenir: ornegin `"2 FINGERS -> BWD & RIGHT"`

### `hand_tracker.py` — Delta Hareket Motoru

| Hareket | Komut | Esik |
|---|---|---|
| Bilek hizli saga | SAGA DON | delta_x > 10 px |
| Bilek hizli sola | SOLA DON | delta_x < -10 px |
| Bilek hizli yukari | YUKARI | delta_y < -10 px |
| Bilek hizli asagi | ASAGI | delta_y > 10 px |
| Hareketsiz | HOVER | 5 kare bekle |
| El kayip | HOVER (Goruntu Kaybi) | — |

---

## Yapılandırma Parametreleri

```python
# master_kontrol.py
smooth_factor = 0.05   # Low-pass filtre katsayisi (0 < alpha <= 1)
tolerance = 70         # Merkez olü bolge yaricapi (piksel)
target_vx = 1.5        # Ileri/geri maksimum hiz (m/s)
target_vy = 1.5        # Sag/sol maksimum hiz (m/s)
TAKEOFF_ALT = 2.0      # Kalkis yuksekligi (metre)
min_detection_confidence = 0.75

# hand_tracker.py
hassasiyet = 10        # Delta hareket esigi (piksel)
komut_sayaci = 5       # Komut tutma suresi (kare sayisi)
min_detection_confidence = 0.70
```

---

## Akademik Referanslar

1. **Zhang, F. et al.** (2020). *MediaPipe Hands: On-device Real-time Hand Tracking.* arXiv preprint arXiv:2006.10214. Google Research.

2. **Mitra, S. & Acharya, T.** (2007). *Gesture Recognition: A Survey.* IEEE Transactions on Systems, Man, and Cybernetics, Part C, 37(3), 311–324. DOI: 10.1109/TSMCC.2007.893280

3. **Meier, L., Tanskanen, P., Fraundorfer, F., & Pollefeys, M.** (2011). *PIXHAWK: A System for Autonomous Flight using Onboard Computer Vision.* Proceedings of the IEEE ICRA, 2992–2997.

4. **Bazarevsky, V. et al.** (2019). *BlazeFace: Sub-millisecond Neural Face Detection on Mobile GPUs.* arXiv:1907.05047. Google Research.

5. **Luckcuck, M. et al.** (2019). *Formal Specification and Verification of Autonomous Robotic Systems: A Survey.* ACM Computing Surveys, 52(5), 1–41.

---

## Güvenlik

> **Bu sistem arastirma amaclıdır. Gercek ucuslarda asagidaki kurallara uyulmasi zorunludur.**

- Ilk ucuslari **kapali alan veya kafes** icinde gerceklestirin
- Etrafta insan varken kesinlikle ucurmayin — minimum **10 metre** guvenlik cevresi
- **SHGM:** Turkiye'de 500 gram uzeri tum IHA'lar kayit yaptirılmalidir
- `Q` tusu her zaman erisebilir **kill-switch** olarak kullanilmalidir
- Ilk ucuslarda **pervane koruyucu (prop guard)** takili olmalidir
- Batarya seviyesi `%20` altina inmeden RTL devreye alinmalidir
- Ruzgar hizi **4 m/s** uzerinde ucus yapilmamalidir

---

## Lisans

Bu proje [MIT Lisansi](LICENSE) altinda dagitilmaktadir.

```
MIT License — Copyright (c) 2026 ahmetcann66
```

---

<div align="center">

**gestural-uav-control** — Computer Vision x UAV Control Systems

`ahmetcann66` · MIT License · 2026

</div>
