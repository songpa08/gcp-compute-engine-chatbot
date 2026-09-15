# GCP Compute Engine 챗봇 배포 및 HTTPS 암호화 적용 작업 로그

- **작업 일시**: 2026-09-15 15:48 (KST)
- **대상 인스턴스**: `gemini-chatbot-instance`
- **GCP 프로젝트 ID**: `iceu-songpa08` (Project Number: `298843281819`)
- **리전 및 존**: `us-central1-a` (Jupyter Notebook 비용 분석 결과 1위 최저가 리전)
- **공인 HTTPS 접속 URL**: **[https://35.226.198.227.nip.io](https://35.226.198.227.nip.io)** (Let's Encrypt 공인 SSL 인증서 적용 - 브라우저 보안 자물쇠 표시)
- **IP 직접 접속 URL**: **[https://35.226.198.227](https://35.226.198.227)** (HTTP 80 접속 시 HTTPS로 자동 301 리다이렉트)
- **연동 Secret Manager**: `projects/298843281819/secrets/GEMINI_API_KEY`

---

## 1. 인프라 사양 및 리소스 구성

| 항목 | 상세 설정값 | 비고 |
| :--- | :--- | :--- |
| **인스턴스명** | `gemini-chatbot-instance` | Compute Engine VM (RUNNING) |
| **머신 타입** | `e2-medium` (2 vCPU, 4GB Memory) | 비용 효율 최적화 |
| **운영체제** | Debian GNU/Linux 12 (Bookworm) | 최신 안정 버전 |
| **부팅 디스크** | 10GB Balanced Persistent Disk (`pd-balanced`) | 월 디스크 비용 최소화 |
| **서비스 계정** | `298843281819-compute@developer.gserviceaccount.com` | VM 기본 서비스 계정 |
| **방화벽 규칙** | `allow-gemini-chatbot-8000` | TCP 443 (HTTPS), 80 (HTTP), 8000 허용 |
| **웹 프록시 서버** | Nginx Reverse Proxy (SSL/TLS Termination) | 443 SSL 처리 후 로컬 8000 프록시 |
| **SSL 인증서** | Let's Encrypt 공인 인증서 + Self-Signed 백업 | 90일 자동 갱신 지원 (Certbot) |

---

## 2. 작업 단계별 실행 로그

### [1단계] GCP Secret Manager 권한 및 키 연동
1. **시크릿 키 확인**: `projects/298843281819/secrets/GEMINI_API_KEY` 정상 로드 확인.
2. **IAM 권한 부여**: VM 서비스 계정에 `roles/secretmanager.secretAccessor` 부여.
3. **앱 연동**: `app.py`에서 환경변수 및 Secret Manager SDK를 통해 API Key를 실시간 자동 로드하도록 구현.

---

### [2단계] GCP 방화벽 규칙 포트 443 (HTTPS) 개방
외부에서 보안 암호화 포트(443)로 접속할 수 있도록 방화벽 규칙을 업데이트했습니다.
```bash
gcloud compute firewall-rules update allow-gemini-chatbot-8000 \
  --project=iceu-songpa08 \
  --allow="tcp:8000,tcp:80,tcp:443"
```

---

### [3단계] Compute Engine VM 인스턴스 생성 및 환경 구성
- **생성 명령**:
  ```bash
  gcloud compute instances create gemini-chatbot-instance \
    --project=iceu-songpa08 \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=10GB \
    --boot-disk-type=pd-balanced \
    --service-account=298843281819-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=http-server
  ```
- **할당 IP**:
  - 내부 IP: `10.128.0.4`
  - 외부 공용 IP: `35.226.198.227`

---

### [4단계] Nginx 웹 서버 및 Let's Encrypt 공인 SSL 인증서 발급
1. **Nginx 및 Certbot 설치**:
   ```bash
   sudo apt-get update -y
   sudo apt-get install -y nginx certbot python3-certbot-nginx
   ```
2. **Let's Encrypt 공인 인증서 발급**:
   - 도메인: `35.226.198.227.nip.io`
   - 인증서 경로: `/etc/letsencrypt/live/35.226.198.227.nip.io/fullchain.pem`
   - 개인키 경로: `/etc/letsencrypt/live/35.226.198.227.nip.io/privkey.pem`
3. **Nginx 가상 호스트 및 리버스 프록시 설정 (`/etc/nginx/sites-available/gemini-chatbot`)**:
   - **80번 포트**: HTTPS로 301 영구 리다이렉트 (`return 301 https://$host$request_uri;`)
   - **443번 포트**: TLSv1.2, TLSv1.3 암호화 적용 및 로컬 Uvicorn(`http://127.0.0.1:8000`)으로 리버스 프록시
   - WebSocket 및 실시간 스트리밍 헤더 지원 추가

---

### [5단계] Systemd 상시 가동 데몬 서비스 등록
1. **FastAPI 서비스 (`gemini-chatbot.service`)**:
   - 상태: `Active: active (running)` (포트 127.0.0.1:8000)
2. **Nginx 서비스 (`nginx.service`)**:
   - 상태: `Active: active (running)` (포트 80, 443)

---

## 3. HTTPS 검증 및 최종 테스트 결과

### 1) HTTP -> HTTPS 301 리다이렉트 검증
- 요청: `http://35.226.198.227`
- 응답: `HTTP 301 Moved Permanently` -> `Location: https://35.226.198.227/` (성공)

### 2) Let's Encrypt 공인 SSL 유효성 검증
- 요청: `https://35.226.198.227.nip.io/api/health` (공인 CA 신뢰성 검증 `verify=True`)
- 응답: `HTTP 200 OK` (`{"status":"ok","has_api_key":true}`)
- **브라우저 상태**: 보안 경고 없이 안전한 자물쇠 표시 완료!

### 3) HTTPS 암호화 대화 추론 테스트 (`/api/chat`)
- 요청 모델: `models/gemini-3.8-flash`
- 응답 본문:
  > *"네, 정상적으로 작동하고 있습니다. 현재 HTTPS(TLS) 암호화 연결을 통해 메시지가 안전하게 송수신되고 있으며, 응답 생성 및 처리 기능 모두 원활하게 동작하는 상태입니다."*

---

## 4. 접속 가이드

- **공인 HTTPS 권장 접속 URL (자물쇠 마크 표시)**:  
  👉 **[https://35.226.198.227.nip.io](https://35.226.198.227.nip.io)**
- **IP 직접 접속 (HTTPS)**:  
  👉 **[https://35.226.198.227](https://35.226.198.227)**
- **HTTP 기본 접속 (자동으로 HTTPS 리다이렉트)**:  
  👉 **[http://35.226.198.227](http://35.226.198.227)**

---

## 5. [과금 방지 가이드] 실습 종료 시 자원 정리 방법
```bash
# 1. VM 인스턴스 삭제
gcloud compute instances delete gemini-chatbot-instance --zone=us-central1-a --project=iceu-songpa08 --quiet

# 2. 방화벽 규칙 삭제
gcloud compute firewall-rules delete allow-gemini-chatbot-8000 --project=iceu-songpa08 --quiet
```
