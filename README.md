# 🍽️ 맛있구미(MatEatGumi) - Backend

## Overview
맛있구미는 최신 사용자 리뷰 데이터를 바탕으로 구미 지역 맛집 추천 서비스를 제공합니다. 이 프로젝트는 RAG(Retrieval-Augmented Generation) 파이프라인을 구현하며, 벡터 데이터베이스로 Pinecone을 활용합니다. 리뷰 데이터를 효율적으로 처리하기 위해 Upstage Solar Embedding API를 사용하며, Fly.io를 통해 안정적으로 배포되었습니다.

## Features
- **RAG 파이프라인 구현**: 최신 리뷰 데이터를 활용한 검색 및 추천 서비스를 제공합니다.
- **벡터 데이터베이스**: Pinecone을 사용하여 리뷰 데이터를 벡터화하고 저장합니다.
- **Upstage Solar Embedding API**: 임베딩 생성 및 벡터화 작업을 진행합니다.
- **데이터 크롤링 및 전처리**: 네이버 지도에서 "진평동 맛집", "인동 맛집" 등으로 검색한 50개의 식당과 100개의 리뷰를 수집 및 저장합니다.
- **최적화된 배포 환경**: Fly.io를 통해 안정적이고 효율적인 서버 배포가 가능합니다.

## Tech Stack
- **Backend Framework**: Python, FastAPI
- **Vector DB**: Pinecone
- **Embedding Model**: Upstage Solar Embedding API
- **LLM Model**: OpenAI Assistants API
- **Deployment**: Fly.io
- **Web Scraping**: Selenium

## File Structure
```
mateatgumi-backend/
├── dataset/               # JSON 파일 저장 폴더 (크롤링된 데이터)
│   └── gumi_restaurants.json  # 50개의 식당 및 100개의 리뷰 포함
├── .dockerignore          # Docker 빌드 시 제외할 파일 목록
├── .gitignore             # Git에서 제외할 파일 목록
├── Procfile               # Fly.io 배포 설정 파일
├── app.py                 # API 서버 메인 파일
├── crawler_Ver3_add.py    # 웹 스크래핑 파일
├── embed.py               # JSON 데이터 벡터화 및 Pinecone
│                            저장 코드
├── fly.toml               # Fly.io 배포 구성 파일
├── handler.py             # API 요청 처리 및 라우팅
├── requirements.txt       # Python 의존성 목록
├── serverless.yml         # 서버리스 설정 파일 (필요시 적용)
```

## API Documentation
FastAPI에서 기본적으로 제공하는 Swagger 페이지를 통해 API 명세를 확인할 수 있습니다.

- [Swagger API Documentation](http://ssafy-2024-backend-mateatgumi.fly.dev/docs)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/mijisuh/mateatgumi-backend.git
cd mateatgumi-backend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
- `.env` 파일 생성 후 아래 변수 추가:
  ```env
  OPENAI_API_KEY='~'
  PINECONE_API_KEY='~'
  UPSTAGE_API_KEY='~'
  ```

### 4. Run the Server
```bash
python app.py
```

## Deployment
### Deploying on Fly.io
1. Fly CLI 설치(Windows):
   ```bash
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. Fly.io 로그인 연동
    ```bash
    flyctl auth login
    ```

3. Fly 프로젝트 초기화:
   ```bash
   flyctl launch
   ```

4. 배포:
   ```bash
   flyctl deploy
   ```

## How It Works

### 1. 데이터 크롤링 및 저장
- `dataset/gumi_restaurants.json`에는 네이버 지도에서 "진평동 맛집", "인동 맛집"으로 검색한 식당들의 리뷰와 메타 정보가 포함되어 있습니다.
- 식당 데이터는 최신순과 추천순으로 약 8:2 비율로 선정되었습니다.

### 2. 임베딩 및 벡터 DB 저장
- `embed.py`는 JSON 데이터를 읽고 리뷰를 Upstage Solar Embedding API를 통해 벡터화한 뒤 Pinecone에 저장합니다.
- 임베딩 모델은 Upstage Solar Embedding API를 활용하여 고품질의 벡터를 생성합니다.

### 3. API 서버
- `app.py`에서 FastAPI를 사용하여 API 요청을 처리합니다.
- 리뷰 검색 및 추천 결과를 반환하는 엔드포인트를 제공합니다.

## 벡터화 및 저장 (embed.py)
`embed.py`는 `dataset/gumi_restaurants.json` 데이터를 읽어 벡터화하고 Pinecone 벡터 DB에 저장하는 데 사용됩니다. 이 작업은 최초 1회만 수행하면 됩니다.

```bash
python embed.py
```

## License
This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
