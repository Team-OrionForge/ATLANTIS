# Project Atlantis — Autonomous Multi-Class Marine Target & Debris Detection

Project Atlantis is a production-grade system for autonomous multi-class marine debris and target detection from dual-channel side-scan sonar (SSS) waterfall imagery.

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Node.js 18+ & npm

### 1. Backend Setup
```bash
# From workspace root
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
# In a separate terminal, from workspace root
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🎬 2-Minute Demo Script (Synthetic Pipeline)

1. Open the web interface at `http://localhost:5173`.
2. Click the **"Run Mock Demo"** button on the header toolbar.
3. The system executes the full end-to-end synthetic sonar generation, CLAHE/bilateral preprocessing, YOLO + physics shadow verification, heuristic classification, and geotagging.
4. Review the results:
   - **Preprocess View**: Side-by-side raw vs. CLAHE + Bilateral Port/Starboard channels.
   - **Detection Overlay**: Interactive canvas displaying polygon bounding boxes color-coded across all 6 target classes (`ghost_net`, `metal_debris`, `chemical_container`, `pipeline`, `marine_plastic`, `shipwreck`).
   - **Telemetry HUD**: Hazard Priority Index (HPI) breakdown, elevation estimates, target surface area, and class distribution charts.
   - **Mission Map**: Interactive Leaflet map displaying geotagged target pins.
5. Click **"Export GeoJSON"** or **"Export CSV"** to download the structured mission log artifacts.

---

## 📊 Batch Mode Setup (Real Dataset Processing)

To process a dataset of 500+ dual-channel side-scan sonar images:
1. Place your dataset directory inside `backend/data/dataset/<your_folder_name>/` (e.g. `backend/data/dataset/Atlantis_500/` or point to the root `Dataset/` folder).
2. Open the **Batch Dataset View** tab in the operator UI.
3. Enter the dataset folder path or drop images into the upload area and click **"Start Batch Processing"**.
4. The system processes images with bounded parallel workers, updating progress live in the UI.
5. Review the aggregate report: total images processed, per-class breakdown, HPI risk distribution, estimated vs exact geolocation flags, and export full-dataset GeoJSON/CSV mission logs.

---

## 🧪 Running Tests

```bash
cd backend
pytest -v
```
