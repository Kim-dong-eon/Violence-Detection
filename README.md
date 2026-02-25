
# 🚨 Violence Detection System  

YOLO 기반 실시간 폭력 상황 탐지 및 동작 분석 AI 시스템  

본 프로젝트는 CCTV 영상에서 폭력 상황을 자동으로 탐지하고,  
위험도를 분석하여 자동 녹화 및 알림을 수행하는 딥러닝 기반 모니터링 시스템입니다.

---

# 📌 Project Overview

본 시스템은 다음 기능을 제공합니다:

- 🔍 실시간 폭력 상황 탐지
- 🥊 펀치 / 킥 동작 세부 분석
- 🎥 자동 10초 영상 녹화
- 📊 동작 누적 기반 심각도 평가
- 🔔 음성 및 카카오톡 알림 전송
- 💾 MongoDB 기반 영상 저장 및 조회

---

# 🧠 AI Model Architecture

본 프로젝트는 단일 모델이 아닌 **2단계 탐지 구조**로 설계되었습니다.

## 1️⃣ Violence Detection Model

- Framework: Ultralytics YOLO
- Task: 폭력 상황 객체 탐지
- 실시간 프레임 단위 추론

### 📂 Dataset

- Roboflow Violence Dataset  
  https://universe.roboflow.com/crowdmanagement-6h2sr/violence-2oyig

- AI-Hub 폭력 영상 데이터셋  
  https://www.aihub.or.kr

영상 데이터를 프레임 단위로 변환하고  
YOLO 포맷(label txt)으로 재가공하여 학습을 진행했습니다.

### 🔧 Training Strategy

- Confidence threshold tuning
- IoU threshold optimization
- Data augmentation (Flip, Mosaic, Brightness)
- False Positive 감소를 위한 필터링 로직 설계
- 연속 프레임 누적 탐지 기반 이벤트 발생 구조

---

## 2️⃣ Punch / Kick Detection Model

폭력 발생 이후 세부 행동 분석을 위해  
별도의 YOLO 모델을 구축했습니다.

### 📂 Dataset

- Kick & Punch Dataset (Roboflow)  
  https://universe.roboflow.com/project-cu5ga/kick-and-punch-hna3g

### 🎯 Classes

- Punch
- Kick

### 🔧 Model Design

- 프레임 단위 실시간 추론
- Confidence 기반 필터링
- 녹화 중 발생한 동작 횟수 누적 카운팅
- 누적 횟수 기반 심각도 자동 판정

---

# ⚙️ System Pipeline

Live Camera Input  
→ Violence YOLO Model  
→ Detection Count Threshold 만족  
→ 10초 자동 녹화 시작  
→ Punch/Kick YOLO 분석  
→ 동작 카운트 누적  
→ 심각도 분류  
→ MongoDB 저장 + 알림 전송  

---

# 📊 Severity Classification Logic

| Punch/Kick Count | Severity |
|------------------|----------|
| 15+               | 경상 |
| 25+               | 중상 |
| 35+              | 치명상 |

단일 프레임 탐지가 아닌  
**누적 행동 기반 분석 방식**으로 설계하여  
실제 상황 반영도를 향상시켰습니다.

---

## 📁 Project Structure

```bash
Violence-Detection/
├── app.py
├── Polygon_Violence.pt
├── punch_kick.pt
├── templates/
│   ├── index.html
│   ├── cctv.html
│   └── videos.html
└── static/
    ├── css/
    └── js/
---
---
Roboflow 및 AI-Hub 데이터를 활용하여  
YOLO 기반 폭력 탐지 및 Punch/Kick 동작 분석 모델을 직접 설계·학습하고  
실시간 CCTV 모니터링 시스템에 적용한 AI 프로젝트입니다.

---

# 👨‍💻 My Role in the Project
  
AI Model Development & System Integration

- YOLO 기반 폭력 탐지 모델 학습
- Punch/Kick 동작 탐지 모델 구축
- 데이터 전처리 및 라벨 구조 설계
- 실시간 추론 최적화 및 임계값 튜닝
- 2단계 탐지 파이프라인 설계

수행자 [김동언]
