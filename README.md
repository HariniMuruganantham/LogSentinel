# 🔍 AiOps Log Anomaly Detective

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Vite-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![LocalStack](https://img.shields.io/badge/LocalStack-Pro-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)

![AWS CloudWatch](https://img.shields.io/badge/AWS-CloudWatch_Logs-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-Alpine-009639?style=for-the-badge&logo=nginx&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A production-grade AIOps portfolio project that detects anomalies in microservice logs using Isolation Forest + GPT-4o-mini, backed by LocalStack CloudWatch and a real-time React dashboard.**

[Portfolio](https://harini-devops-portfolio.vercel.app) · [Report Bug](https://github.com/HariniMuruganantham/AiOps-Log-Anamoly-Detective/issues)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [LocalStack Integration](#-localstack-integration)
- [Author](#-author)

---

## 🧠 Overview

**AiOps Log Anomaly Detective** is a full-stack AIOps project that simulates a microservice environment, ingests service logs into AWS CloudWatch (via LocalStack), detects anomalies using an Isolation Forest model, and generates human-readable incident reports using GPT-4o-mini.

Built as a portfolio project to demonstrate real-world DevOps and MLOps skills — containerisation, cloud-native observability, and AI-driven alerting — all running locally with production-grade tooling.

> **Why this project?** Most anomaly detection demos are Jupyter notebooks. This one ships with Docker Compose, LocalStack CloudWatch integration, and a live React dashboard — the way it would actually be built on the job.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network: p1-net                   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  auth-svc    │  │ payment-svc  │  │   inventory-svc      │  │
│  │  Flask :5001 │  │ Flask :5002  │  │   Flask :5003        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └─────────────────┼──────────────────────┘              │
│                           │ PutLogEvents                        │
│                    ┌──────▼──────────┐                          │
│                    │   LocalStack    │                          │
│                    │  CloudWatch     │                          │
│                    │  Logs :4566     │                          │
│                    └──────┬──────────┘                          │
│                           │ GetLogEvents                        │
│                    ┌──────▼──────────┐                          │
│                    │    Backend      │                          │
│                    │  FastAPI :8000  │                          │
│                    │                 │                          │
│                    │ Isolation Forest│                          │
│                    │  + GPT-4o-mini  │                          │
│                    └──────┬──────────┘                          │
│                           │                                     │
│                    ┌──────▼──────────┐                          │
│                    │    Frontend     │                          │
│                    │  React/Vite     │                          │
│                    │  Nginx :3001    │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI, Uvicorn, Python 3.12 |
| **Anomaly Detection** | Scikit-learn Isolation Forest |
| **AI Analysis** | OpenAI GPT-4o-mini |
| **Microservices** | Flask (auth, payment, inventory) |
| **Frontend** | React 18, Vite, Nginx Alpine |
| **Cloud Emulation** | LocalStack Pro (CloudWatch Logs, EC2) |
| **Containerisation** | Docker, Docker Compose |
| **Observability** | AWS CloudWatch Logs |

---

## ✨ Features

- **Real-time log ingestion** — 3 Flask microservices continuously ship logs to LocalStack CloudWatch
- **Anomaly detection** — Isolation Forest model scores log patterns and flags outliers
- **AI-powered reports** — GPT-4o-mini generates plain-English incident summaries from anomalous log events
- **Service crash simulation** — trigger controlled failures via the UI to test detection
- **Live dashboard** — React frontend polls service health and anomaly reports in real time
- **LocalStack CloudWatch** — full AWS CloudWatch Logs API emulation locally, no real AWS account needed
- **EC2 topology** — mock EC2 instances seeded per microservice for infrastructure visualisation
- **Multi-stage Docker builds** — production-optimised images with non-root users

---

## 📁 Project Structure

```
AiOps-Log-Anamoly-Detective/
├── backend/                  # FastAPI anomaly detection engine
│   ├── main.py               # API routes + Isolation Forest + GPT integration
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # React + Vite dashboard
│   ├── src/
│   ├── nginx.conf
│   ├── package.json
│   └── Dockerfile
├── services/
│   ├── auth/                 # Auth microservice (Flask :5001)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── payment/              # Payment microservice (Flask :5002)
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── inventory/            # Inventory microservice (Flask :5003)
│       ├── app.py
│       ├── requirements.txt
│       └── Dockerfile
├── scripts/
│   └── init-aws.sh           # LocalStack bootstrap (log groups + EC2 instances)
├── .env.example
├── .gitignore
└── docker-compose.yml
```

---

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with WSL2 backend on Windows)
- [LocalStack account](https://app.localstack.cloud) — free tier works
- OpenAI API key

### 1. Clone the repository

```bash
git clone https://github.com/HariniMuruganantham/AiOps-Log-Anamoly-Detective.git
cd AiOps-Log-Anamoly-Detective
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
OPENAI_API_KEY=sk-...
LOCALSTACK_AUTH_TOKEN=ls-...
```

### 3. Start the stack

```bash
docker compose up --build
```

> First run pulls LocalStack Pro and all base images — allow 3-5 minutes.

### 4. Access the dashboard

| Service | URL |
|---|---|
| Frontend Dashboard | http://localhost:3001 |
| Backend API | http://localhost:8001 |
| LocalStack | http://localhost:4566 |
| Auth Service | http://localhost:5001 |
| Payment Service | http://localhost:5002 |
| Inventory Service | http://localhost:5003 |

### 5. Tear down

```bash
docker compose down -v
```

---

## 🔐 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o-mini | Yes |
| `LOCALSTACK_AUTH_TOKEN` | LocalStack Pro auth token | Yes |

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend health check |
| `GET` | `/services/status` | Poll health of all 3 microservices |
| `GET` | `/analyze` | Run anomaly detection + GPT report |
| `POST` | `/services/{name}/crash` | Simulate a service crash |
| `POST` | `/services/{name}/recover` | Recover a crashed service |

### Query parameters for `/analyze`

| Parameter | Default | Description |
|---|---|---|
| `minutes_back` | `5` | How far back to fetch logs |
| `max_reports` | `8` | Maximum anomaly reports to return |

---

## ☁️ LocalStack Integration

The project uses LocalStack Pro to emulate AWS CloudWatch Logs locally. The `scripts/init-aws.sh` bootstrap script runs on container startup and creates:

- **Log group**: `/aiops/services`
- **Log streams**: `auth-service`, `payment-service`, `inventory-api`
- **EC2 instances**: one per microservice for topology visualisation

View your resources at [app.localstack.cloud](https://app.localstack.cloud) → Resource Browser → CloudWatch Logs.

---

## 👩‍💻 Author

**Harini Muruganantham**
Junior DevOps Engineer · AiOps Enthusiast

[![Portfolio](https://img.shields.io/badge/Portfolio-harini--devops-blue?style=flat-square&logo=vercel)](https://harini-devops-portfolio.vercel.app)
[![GitHub](https://img.shields.io/badge/GitHub-HariniMuruganantham-181717?style=flat-square&logo=github)](https://github.com/HariniMuruganantham)

---

<div align="center">

⭐ If this project helped you, consider giving it a star!

</div>