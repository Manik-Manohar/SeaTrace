\# 🌊 SeaTrace



\## Maritime Oil-Spill Intelligence



\### Detect → Trace → Attribute



SeaTrace is an AI-assisted maritime intelligence platform that combines \*\*Sentinel-1 SAR imagery, machine learning, environmental drift analysis, and AIS vessel data\*\* to support the investigation of potential oil-spill incidents.



The system follows the complete chain:



\*\*Satellite Observation → Spill Detection → Slick Analysis → Drift Hindcasting → Source Estimation → AIS Correlation → Vessel Attribution\*\*



> \*\*SeaTrace is an investigation-support prototype. Vessel attribution results are ranked evidence signals and do not establish legal or causal responsibility.\*\*



\---



\## 🚀 What SeaTrace Does



Oil-spill investigation is not only about detecting a slick.



Once a potential spill is detected, investigators also need to understand:



\- Where is the slick?

\- How large and what shape is it?

\- Where could it have originated?

\- What was happening in the ocean during that period?

\- Which vessels were operating around the probable source?

\- Which vessels should be investigated first?



SeaTrace connects these steps into one workflow.



```text

&#x20;               SENTINEL-1 SAR

&#x20;                     │

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │  Spill Detection │

&#x20;            └────────┬────────┘

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │  Slick Analysis │

&#x20;            └────────┬────────┘

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │ AI Verification │

&#x20;            └────────┬────────┘

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │ Drift Hindcast  │

&#x20;            │ Wind + Current  │

&#x20;            └────────┬────────┘

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │ Source Region   │

&#x20;            │ Estimation      │

&#x20;            └────────┬────────┘

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │ AIS Correlation │

&#x20;            └────────┬────────┘

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │ Vessel Ranking  │

&#x20;            └────────┬────────┘

&#x20;                     ▼

&#x20;            ┌─────────────────┐

&#x20;            │ Investigation   │

&#x20;            │ Dashboard       │

&#x20;            └─────────────────┘



🛰️ Key Features

1\. Sentinel-1 SAR Analysis: Processes Sentinel-1 SAR imagery to identify dark ocean-surface anomalies that may correspond to potential oil slicks.



2\. AI-Based Screening: A ResNet-18 image classification model is used to distinguish between:



oil\_spill

clean\_area



Grad-CAM is also used during the analysis workflow to visualize regions contributing to model predictions.



3\. Slick Characterisation: Candidate regions can be analysed using spatial and image-based properties including:



Area

Centroid

Bounding box

Aspect ratio

Fill ratio

VV anomaly

VH support

AI confidence



4\. Drift Hindcasting: Historical wind and ocean-current information is used to simulate the observed slick backwards in time.



The prototype currently performs:



* 6-hour backtracking
* 1-hour time steps
* Windage-based surface drift estimation



The result is treated as a plausible source corridor, rather than a confirmed origin.



5\. AIS Vessel Correlation: Historical AIS observations are compared with the estimated source corridor and relevant time window.



The system considers:



* Source proximity
* Acquisition proximity
* Temporal alignment
* AIS observation coverage
* Vessel identity information



6\. Drift-Aware Attribution: Multiple evidence signals are combined into an investigation score.



The resulting vessels are ranked for further investigation.



7\. Interactive Investigation Dashboard: The dashboard brings the different evidence layers together:



Sentinel-1 SAR imagery

Oil-spill candidates

Estimated source regions

Drift trajectories

AIS vessel positions

Attribution scores

Investigation evidence



🖥️ Dashboard



Investigation Overview



The main dashboard provides a geographic overview of the SAR scene along with detected spill candidates, estimated source regions, drift trajectories, and AIS vessel information.



SAR + Drift Investigation View



The map allows the investigator to examine the relationship between the detected spill locations and their estimated backtracked source regions.



Candidate #3 Investigation



The investigation panel combines satellite evidence, drift reconstruction, AIS correlation, and the resulting attribution score.



Example prototype result:



AI Oil Score          98.4

SAR Score             69.7

Attribution Score     69.9

Source Distance       34.2 km



Potential Vessel:

ZHONG HANG SHENG



Best Matching Hour:

11:00 UTC



Evidence Strength:

Moderate

Candidate #8 Investigation



Candidate investigations can be selected independently, allowing the user to compare different potential spill events and their associated vessel correlations.



⚙️ Technical Approach



Stage 1 — Satellite Input



The system starts with Sentinel-1 SAR imagery.



The prototype works with VV/VH SAR information and processes the imagery to identify anomalously dark ocean regions.



Stage 2 — AI Detection



Potential candidates are screened using a ResNet-18 classifier trained on labelled oil-spill and clean-area imagery.



The classifier outputs probabilities for:



clean\_area

oil\_spill



The prototype also uses Grad-CAM to inspect which image regions contribute to the model's prediction.



Stage 3 — Slick Analysis



Detected regions are analysed to extract spatial characteristics.



These characteristics are used to support candidate filtering and downstream investigation.



Stage 4 — Drift Hindcasting



The detected slick location is used as the starting point for backward drift estimation.



The prototype combines:



Ocean Current

&#x20;    +

Wind × Windage

&#x20;    ↓

Surface Drift

&#x20;    ↓

Backward Trajectory



The current prototype uses a first-order drift model.



For example, Candidate #3 produced:



Detected position:

\-16.417958, 51.869334



Estimated 6-hour source:

\-16.381601, 51.900293



Backtracked displacement:

5.23 km

Stage 5 — AIS Correlation



The estimated source trajectory is compared with historical AIS vessel observations.



The system examines whether vessel positions are spatially and temporally consistent with the estimated source corridor.



Stage 6 — Vessel Attribution



The prototype combines several evidence components:



AI Oil-Spill Confidence

&#x20;       +

SAR Anomaly

&#x20;       +

Source-Corridor Proximity

&#x20;       +

Acquisition Proximity

&#x20;       +

Temporal Alignment

&#x20;       +

AIS Coverage

&#x20;       ↓

Drift-Aware Attribution Score



The result is a ranked list of potential source vessels for investigation.



📊 Example Prototype Output



The current prototype processed four AI-verified spill candidates through the downstream investigation workflow.



Candidate	AI Oil Score	SAR Score	Potential Source Vessel	Attribution	Source Distance	Evidence

\#3	98.37	69.74	ZHONG HANG SHENG	69.9	34.2 km	Moderate

\#5	67.20	68.81	OLENA	46.5	87.3 km	Weak

\#8	80.82	68.49	ZHONG HANG SHENG	63.0	48.1 km	Moderate

\#15	85.96	66.28	OLENA	53.0	81.8 km	Weak



These are example outputs from the current prototype investigation run, not general model-performance metrics.



🧠 Attribution Philosophy



SeaTrace does not treat vessel proximity alone as proof of responsibility.



Instead, the prototype attempts to combine:



Satellite evidence



→ Environmental reconstruction



→ Source corridor



→ Historical vessel movement



→ Temporal and spatial consistency



→ Investigation ranking



This produces a more structured evidence trail for investigators.



🛠️ Technology Stack

Category	Technology

Programming	Python

Machine Learning	PyTorch

Computer Vision	Torchvision, Pillow

Explainability	Grad-CAM

Satellite Data	Sentinel-1 SAR

Numerical Processing	NumPy, SciPy

Data Processing	Pandas

Geospatial Processing	Rasterio

Environmental Drift	Wind + Ocean Current Data

Vessel Tracking	AIS / Global Fishing Watch

Backend	FastAPI

Visualization	Leaflet

Frontend	HTML, CSS, JavaScript

Version Control	Git / GitHub



📁 Project Structure

SeaTrace/

│

├── backend/

│   └── main.py

│

├── data/

│   ├── processed/

│   ├── raw/

│   ├── results/

│   └── uploads/

│

├── docs/

│   └── screenshots/

│       ├── dashboard-overview.png

│       ├── dashboard-zoomed.png

│       ├── candidate-3-investigation.png

│       └── candidate-8-investigation.png

│

├── frontend/

│

├── models/

│   └── oil\_spill\_classifier.pth

│

├── scripts/

│   ├── train\_classifier.py

│   ├── evaluate\_classifier.py

│   ├── detect\_candidates.py

│   ├── classify\_sar\_candidates.py

│   ├── prepare\_spill\_candidates.py

│   ├── oil\_spill\_drift\_backtracking.py

│   ├── drift\_aware\_vessel\_attribution.py

│   ├── build\_final\_attribution.py

│   ├── generate\_investigation\_dashboard.py

│   └── ...

│

├── tests/

│

├── .gitignore

├── requirements.txt

└── README.md

🚀 Installation

Prerequisites

Python 3.11+

Git

Windows / Linux / macOS



Clone the repository:



git clone https://github.com/Manik-Manohar/SeaTrace.git

cd SeaTrace



Create a virtual environment:



python -m venv .venv



Activate it on Windows:



.venv\\Scripts\\Activate.ps1



Install dependencies:



pip install -r requirements.txt

▶️ Running the Pipeline



The project is organized into modular processing stages.



Prepare the dataset

python scripts\\prepare\_dataset.py

Split the dataset

python scripts\\split\_dataset.py

Train the classifier

python scripts\\train\_classifier.py

Prepare final spill candidates

python scripts\\prepare\_spill\_candidates.py



Output:



data/results/final\_spill\_candidates.csv

Run drift hindcasting

python scripts\\oil\_spill\_drift\_backtracking.py



Output:



data/results/environmental/oil\_spill\_backtracking\_results.json

Run vessel attribution

python scripts\\drift\_aware\_vessel\_attribution.py



Output:



data/results/drift\_aware\_vessel\_attribution.csv

Build final evidence

python scripts\\build\_final\_attribution.py



Output:



data/results/final\_attribution\_evidence.csv

Generate the dashboard

python scripts\\generate\_investigation\_dashboard.py



Open the dashboard:



start data/results/maritime\_investigation\_dashboard.html

📦 Important Data Note



Large raw satellite scenes, datasets, and generated artifacts may not be included in the GitHub repository.



The repository is primarily intended to contain the source code, configuration, documentation, and reproducible project structure.



Required datasets and external API access may need to be obtained separately.



⚠️ Limitations



SeaTrace is currently a research and hackathon prototype.



SAR False Positives



Dark SAR regions can result from several ocean-surface conditions and are not necessarily oil.



Environmental Uncertainty



Wind and ocean-current estimates contain uncertainty, which can affect the reconstructed source corridor.



AIS Limitations



AIS observations may contain gaps, incomplete coverage, or position uncertainty.



Model Uncertainty



AI confidence represents the model's output probability and should not be interpreted as definitive proof of an oil spill.



Attribution Uncertainty



A vessel that appears close to an estimated source corridor does not necessarily mean that it caused the spill.



The current system therefore produces an investigation ranking, not a causal determination.



🔮 Future Development



Potential future improvements include:



Automated Sentinel-1 scene ingestion

Multi-temporal SAR analysis

Improved oil-spill segmentation

Larger and more diverse training datasets

Adaptive drift backtracking

Higher-resolution oceanographic models

Higher-resolution AIS trajectories

Vessel behaviour and anomaly analysis

Probabilistic source-region modelling

Automated investigation reports

Real-time maritime monitoring

Cloud-scale processing

📚 Data Sources \& References

Copernicus Sentinel-1



Satellite SAR imagery used as the primary remote-sensing input.



https://dataspace.copernicus.eu/



Zenodo



Sentinel-1 oil-spill / clean-area imagery used for AI model development.



https://zenodo.org/



OpenDrift



Ocean-drift modelling framework used as a reference for environmental drift modelling.



https://opendrift.github.io/



Global Fishing Watch



AIS-derived vessel information used for vessel correlation and investigation.



https://globalfishingwatch.org/



🌍 Potential Impact



SeaTrace is designed to support several parts of a maritime response workflow.



Environmental Response

Faster identification of potential oil-spill events

Better understanding of slick movement

Support for response planning

Maritime Investigation

Connects satellite observations with vessel movements

Narrows large AIS datasets to relevant candidates

Provides a structured investigation trail

Decision Support

Combines multiple evidence sources in one interface

Provides geographic visualization of the investigation

Accountability



Creates a traceable chain:



Slick

&#x20; ↓

Source Region

&#x20; ↓

Time Window

&#x20; ↓

Vessel Track

&#x20; ↓

Investigation Ranking



👥 Team TrailBlazers



Manik Manohar

Team Lead

Hyderabad Institute of Technology and Management



Yeruva Shamsmitha

Team Member

Hyderabad Institute of Technology and Management



Mohammed Amaan

Team Member

Hyderabad Institute of Technology and Management



🏆 Hackathon



Developed as a prototype for Smart India Hackathon 2026.



Project



Leveraging Satellite Imagery to Identify Oil Spills in Sea along with AIS Data to determine Vessel responsible for it



The project explores how satellite imagery, environmental data, and AIS vessel movements can be combined to turn oil-spill detection into a traceable maritime investigation workflow.



⚖️ Disclaimer



SeaTrace is an experimental research and hackathon prototype.



The system's vessel attribution output represents a ranked set of potential source vessels based on available satellite, environmental, and AIS signals.



It should not be interpreted as proof of legal or causal responsibility.



Confirmation would require higher-resolution data, validated oceanographic modelling, complete vessel trajectories, and independent investigation.



⭐ Project Status



Prototype — End-to-end investigation workflow implemented



Component	Status

Sentinel-1 SAR Processing	✅

AI Oil-Spill Screening	✅

Slick Analysis	         ✅

Candidate Geolocation	✅

Drift Hindcasting	         ✅

AIS Correlation	         ✅

Vessel Attribution	✅

Evidence Dataset	         ✅

Investigation Dashboard	✅

<p align="center"> Built by <strong>TrailBlazers</strong> • iQOO Hackathon 2026 </p> ```



The project framing in this README follows your PPT's Detect → Trace → Attribute structure, while the implementation sections reflect the pipeline we've actually completed. Your PPT also explicitly identifies SAR false positives, drift uncertainty, AIS limitations, and error propagation, so those are retained in the limitations section rather than hiding them.

