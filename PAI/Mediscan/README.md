# 🏥 MediScan AI — Medical Image & Report Assistant

> An end-to-end AI pipeline that takes a raw medical scan (X-ray, CT, MRI), classifies it with a fine-tuned Vision Transformer, scores it for anomalies, and generates a structured radiology report using LLaMA 3.1 — served via a FastAPI REST endpoint.

---

## Pipeline Overview

```
Upload Scan (JPEG/PNG)
        │
        ▼
┌─────────────────────┐
│  OpenCV             │  CLAHE contrast enhancement + denoising
│  Preprocessor       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  HuggingFace        │  ViT fine-tuned on chest X-ray data
│  Classifier         │  → top-k labels + confidence scores
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  ResNet-18 +        │  512-dim feature vector extraction
│  IsolationForest    │  → anomaly score + risk level (low/medium/high)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  NLTK               │  Tokenise labels → structured prompt
│  Prompt Builder     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  LLaMA 3.1 70B      │  NVIDIA-hosted, OpenAI-compatible API
│  Report Generator   │  → FINDINGS / IMPRESSION / RECOMMENDATION
└─────────┬───────────┘
          │
          ▼
    FastAPI Response
    (JSON: labels + anomaly + report)
```

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Image preprocessing | OpenCV (CLAHE, NL-means denoising) |
| Classification | Hugging Face Transformers + PyTorch |
| HF Model | `nickmuchi/vit-finetuned-chest-xray-pneumonia` |
| Feature extraction | ResNet-18 backbone (torchvision) |
| Anomaly detection | Scikit-learn IsolationForest |
| Text processing | NLTK tokenisation |
| Report generation | LLaMA 3.1 70B Instruct via NVIDIA API |
| API server | FastAPI + Uvicorn |

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/ik-awais/mediscan-ai.git
cd mediscan-ai
pip install -r requirements.txt
```

### 2. Set API keys

Create a `.env` file in the project root:

```env
NVIDIA_API_KEY=your_nvidia_api_key_here
HF_TOKEN=your_huggingface_token_here
```

> Get your NVIDIA API key at [build.nvidia.com](https://build.nvidia.com)  
> Get your HF token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 3. Run the notebook

Open `mediscan_ai.ipynb` in Jupyter and run cells top to bottom.  
The server starts at **http://localhost:8000**.

---

## API Reference

### `GET /health`

```json
{
  "status": "ok",
  "device": "cpu",
  "model": "meta/llama-3.1-70b-instruct"
}
```

### `POST /analyze`

**Request** — multipart form:

| Field | Type | Description |
|-------|------|-------------|
| `file` | file | JPEG or PNG medical scan |
| `scan_type` | string | e.g. `"chest X-ray"`, `"CT scan"` |

**Response:**

```json
{
  "scan_type": "chest X-ray",
  "top_labels": [
    {"label": "PNEUMONIA", "score": 0.8741},
    {"label": "NORMAL", "score": 0.1259}
  ],
  "anomaly": {
    "anomaly_score": -0.1823,
    "risk_level": "high",
    "is_anomaly": true
  },
  "report": "FINDINGS:\n...\n\nIMPRESSION:\n...\n\nRECOMMENDATION:\n..."
}
```

**cURL example:**

```bash
curl -X POST http://localhost:8000/analyze \
  -F 'file=@/path/to/scan.jpg' \
  -F 'scan_type=chest X-ray'
```

---

## Project Structure

```
mediscan-ai/
├── mediscan_ai.ipynb     ← main notebook (all code, step-by-step)
├── .env.example          ← template for API keys (never commit .env)
├── requirements.txt
└── README.md
```

---

## ⚠️ Clinical Disclaimer

This tool is an **AI-assisted prototype** intended for research and educational purposes only. It is **not a medical device** and should **never replace** the clinical judgement of a licensed radiologist or physician. All outputs must be reviewed by a qualified clinician before any clinical decision is made.

---

## Roadmap

- [ ] Replace synthetic IsolationForest training data with real labelled scan embeddings  
- [ ] Add DICOM file support  
- [ ] Multi-modality support (CT, MRI, ultrasound)  
- [ ] Streamlit / React frontend  
- [ ] Docker container for one-command deployment  

---

## Author

**Muhammad Awais** — AI Engineer  
[Portfolio](https://ik-awais.github.io) · [LinkedIn](https://www.linkedin.com/in/muhammad-awais-ai-engineer/) · [GitHub](https://github.com/ik-awais)
