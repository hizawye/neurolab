# 🧠 NeuroLab: AI-Powered Drug Discovery Platform

NeuroLab is a modular, intelligent, and fully automated platform for drug discovery and neuroenhancement research. It supports end-to-end workflows—from target selection and molecule generation to docking, simulation, and property prediction—by unifying open-source tools, public datasets, and scalable compute infrastructure.

---

## 🚀 Key Features

* **End-to-End Automation**: Fully integrated drug discovery pipelines with just a few clicks or API calls.
* **Intelligent Agents**: AI-driven agents plan, generate, evaluate, and optimize candidates.
* **Modular Architecture**: Plug-and-play components with CLI, GUI, and API access.
* **Multi-Target Capable**: Supports enzymes, receptors, and transporters (e.g. MAO-B, DAT, NMDA).
* **Customizable Workflows**: Build workflows visually or via YAML.
* **Cross-Platform Compute**: Run on local machines, GPU clusters, or cloud (GCP, Vast.ai, etc.).

---

## 📦 Project Structure

```
neurolab/
├— agents/               # Autonomous AI agents
├— backend/              # FastAPI backend
├— frontend/             # React UI
├— modules/              # Core engine modules (docking, prediction, etc.)
├— workflows/            # Built-in and user-defined pipelines
├— data/                 # Cache for molecules, results, metadata
├— configs/              # Model and environment configurations
├— scripts/              # Utility scripts and CLI tools
├— docker/               # Docker build files
├— docs/                 # Documentation and architecture
└— README.md
```

---

## ⚙️ Installation (Developer Mode)

```bash
git clone https://github.com/your-org/neurolab
cd neurolab

# Backend setup
cd backend
conda env create -f environment.yml
conda activate neurolab
uvicorn main:app --reload

# Frontend setup
cd ../frontend
npm install
npm run dev
```

> 💡 Requirements: Python 3.10+, Node.js 18+, Conda. GPU recommended for AI modules and docking.

---

## 🐳 Docker Setup (Production-Ready)

NeuroLab comes with Docker support for streamlined deployment:

### 1. **Build the containers**

```bash
docker-compose build
```

### 2. **Start all services**

```bash
docker-compose up -d
```

This will launch:

* 🚀 `FastAPI backend` on port `8000`
* 🌐 `React frontend` on port `3000`
* 🧠 `Celery workers` for background tasks
* 🔋 `Redis` and `PostgreSQL` for data caching and storage

### 3. **Access**

* Frontend: [http://localhost:3000](http://localhost:3000)
* API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. **Stop**

```bash
docker-compose down
```

> 📁 You can customize `.env`, ports, or volumes in `docker-compose.yml`.

---

## 🛠️ Deployment Guide

### ▶️ Option 1: Deploy on Local/On-Prem GPU Server

1. Install Docker + Docker Compose
2. Set up NVIDIA GPU drivers + `nvidia-docker` runtime
3. Update `docker-compose.gpu.yml` (use GPU-accelerated containers)
4. Launch:

```bash
docker compose -f docker-compose.gpu.yml up --build
```

---

### ☑️ Option 2: Deploy on Cloud

#### **Vast.ai (GPU on demand)**

1. Launch an instance with Docker + GPU
2. Clone your repo:

```bash
git clone https://github.com/your-org/neurolab.git
cd neurolab
```

3. Run Docker deployment
4. Access via public IP and mapped ports

#### **Google Cloud / AWS / Azure**

* Use GPU-enabled VM (e.g., T4, A100)
* Install Docker and follow same deployment as above
* Use reverse proxy (NGINX or Caddy) + SSL (Let's Encrypt)

---

## 🔁 Sample Workflow: Neuroenhancer Discovery

> *Goal*: Identify BBB-permeable MAO-B inhibitors for enhanced dopamine availability.

1. **Select Target**: MAO-B (e.g., PDB: `2V5Z`)
2. **Ligand Retrieval**: Use PubChem to fetch Selegiline, Rasagiline, Hordenine
3. **Docking**: AutoDock Vina for binding affinity estimation
4. **Property Prediction**: Use SwissADME for BBB, logP, TPSA
5. **Toxicity Screening**: Run through ProTox-II
6. **Molecule Optimization**: Generate analogs with Chai-1
7. **Simulation**: Run GROMACS or OpenMM dynamics on top ligands
8. **AI Scoring**: Evaluate candidates via `Evaluator` agent
9. **Export**: Save as SDF, visualize in GUI, or export report

All steps can be executed via GUI, CLI, or API.

---

## 📱 API Access

FastAPI endpoints support:

* Pipeline execution
* Protein/ligand upload
* Docking job control
* ADMET querying
* Molecule generation

See full Swagger at `/docs`.

---

## 🤝 Contributing

We welcome contributions, bug reports, new agent ideas, and feature requests. Open issues or pull requests to collaborate.

---

## 📜 License

MIT License. See [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

NeuroLab is built on top of powerful open-source libraries and datasets:

* [RDKit](https://www.rdkit.org/)
* [AutoDock Vina](http://vina.scripps.edu/)
* [SwissADME](http://www.swissadme.ch/)
* [ChEMBL](https://www.ebi.ac.uk/chembl/)
* [OpenMM](https://openmm.org/)
* [HuggingFace Transformers](https://huggingface.co/)
* [Chai (Molecule LLM)](https://chai-research.com/)
