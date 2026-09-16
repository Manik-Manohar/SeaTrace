# SeaTrace

### Maritime Oil-Spill Intelligence

**Detect. Trace. Attribute.**

SeaTrace is an AI-assisted maritime intelligence platform that combines **Sentinel-1 SAR imagery, machine learning, environmental drift analysis, and AIS vessel data** to support the investigation of potential oil-spill incidents.

The system connects satellite observations with ocean conditions and vessel movements to build a traceable investigation workflow.

> **SeaTrace provides investigation support and ranked evidence signals. Vessel attribution does not establish legal or causal responsibility.**

---

## The Idea

Detecting an oil slick is only the beginning.

The bigger challenge is understanding:

- Where the slick is located
- What region of the image represents the potential spill
- Where the slick may have originated
- How environmental conditions could have moved it
- Which vessels were present around the estimated source
- Which vessels should be examined first

SeaTrace brings these stages together in a single workflow.

```text
Satellite SAR
      ↓
Oil-Spill Detection
      ↓
AI Verification
      ↓
Slick Analysis
      ↓
Drift Hindcasting
      ↓
Source Estimation
      ↓
AIS Correlation
      ↓
Vessel Attribution
      ↓
Investigation Dashboard
```
## What SeaTrace Does
|         Stage             |                              Purpose                                 |
|-------------------------- | -------------------------------------------------------------------- |
|  SAR Analysis             | Process Sentinel-1 imagery and identify potential dark slick regions |
|  AI Verification          | Classify candidate regions as potential oil spill or clean area      |
|  Slick Analysis           | Extract candidate location and image-based characteristics           |
|  Drift Hindcasting        | Reconstruct possible slick movement using wind and ocean currents    |
|  Source Estimation        | Estimate a plausible region from which the slick may have originated |
|  AIS Correlation          | Compare the source corridor with historical vessel positions         |
|  Attribution              | Rank potential source vessels using multiple evidence signals        |
|  Investigation Dashboard  | Present the complete investigation in one interface                  |

## System Architecture

                   SENTINEL-1 SAR
                         │
                         ▼
                ┌─────────────────┐
                │ Spill Detection │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ AI Verification │
                │   ResNet-18     │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Slick Analysis  │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Drift Hindcast  │
                │ Wind + Current  │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Source Region   │
                │   Estimation    │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ AIS Correlation │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Vessel Ranking  │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Investigation   │
                │    Dashboard    │
                └─────────────────┘

## AI-Based Oil-Spill Detection
The prototype uses a ResNet-18 image classification model trained to distinguish between:
- oil_spill
- clean_area

The detection workflow also uses Grad-CAM to inspect the regions contributing to model predictions.
Candidate regions are further analysed using properties such as:

- Area
- Centroid
- Bounding box
- Aspect ratio
- Fill ratio
- VV anomaly
- VH support
- AI confidence

## Drift Hindcasting
Once a potential slick is detected, SeaTrace works backwards to estimate where it could have originated.

The prototype combines:

```
Ocean Current + Wind × Windage
             ↓
       Surface Drift
             ↓
    Backward Trajectory
```
Current prototype configuration:
- 6-hour backtracking
- 1-hour time steps
- Windage-based surface drift estimation

Example
For one prototype candidate:

Detected position
-16.417958, 51.869334

Estimated 6-hour source
-16.381601, 51.900293

Backtracked displacement
5.23 km

The estimated source is treated as a plausible source region, not a confirmed spill origin.

## AIS Vessel Attribution
The estimated source corridor is compared against historical AIS vessel observations.

SeaTrace considers multiple signals rather than vessel proximity alone:
```
      AI Oil-Spill Confidence
                  +
             SAR Anomaly
                  +
      Source-Corridor Proximity
                  +
        Acquisition Proximity
                  +
          Temporal Alignment
                  +
             AIS Coverage
                  ↓
    Drift-Aware Attribution Score
```

This produces a ranked list of potential vessels for further investigation.
## Investigation Dashboard
The prototype provides a visual investigation interface combining satellite, environmental, and vessel information.

Dashboard Overview

SAR and Drift View

Candidate Investigation

Additional Candidate Analysis

## Prototype Output
The current prototype processes four AI-verified spill candidates through the downstream investigation workflow.
| Candidate | AI Oil Score | SAR Score | Potential Vessel | Attribution | Source Distance |
| --------: | -----------: | --------: | ---------------- | ----------: | --------------: |
|        #3 |        98.37 |     69.74 | ZHONG HANG SHENG |        69.9 |         34.2 km |
|        #5 |        67.20 |     68.81 | OLENA            |        46.5 |         87.3 km |
|        #8 |        80.82 |     68.49 | ZHONG HANG SHENG |        63.0 |         48.1 km |
|       #15 |        85.96 |     66.28 | OLENA            |        53.0 |         81.8 km |

These values represent an example investigation run, not general model-performance metrics.

## Technology
| Area                   | Technology                     |
| ---------------------- | ------------------------------ |
| Language               | Python                         |
| Machine Learning       | PyTorch                        |
| Computer Vision        | Torchvision, Pillow            |
| Explainability         | Grad-CAM                       |
| Satellite Data         | Sentinel-1 SAR                 |
| Numerical Processing   | NumPy, SciPy                   |
| Data Processing        | Pandas                         |
| Geospatial Processing  | Rasterio                       |
| Environmental Analysis | Wind + Ocean Current Data      |
| Vessel Tracking        | AIS / Global Fishing Watch     |
| Backend                | FastAPI                        |
| Dashboard              | HTML, CSS, JavaScript, Leaflet |
| Version Control        | Git / GitHub                   |

## Project Structure
```
SeaTrace/
│
├── backend/
├── data/
├── docs/
│   └── screenshots/
├── frontend/
├── models/
├── scripts/
├── tests/
│
├── .gitignore
├── requirements.txt
└── README.md 
```
