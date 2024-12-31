import os

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from langchain_upstage import UpstageDocumentParseLoader
from langchain_upstage import UpstageEmbeddings
from pinecone import Pinecone, ServerlessSpec

import json
from langchain.docstore.document import Document

load_dotenv()

# upstage models
embedding_upstage = UpstageEmbeddings(model="embedding-query")

pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)
index_name = "gumi-restaurants"
json_path = "./dataset/gumi_restaurants.json"

# create new index
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=4096,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

print(">> start")

# JSON 데이터 읽기
with open(json_path, "r", encoding="utf-8") as file:
    json_data = json.load(file)

# JSON 데이터를 LangChain Document 객체로 변환
docs = []

for store_name, store_data in json_data.items():
    reviews_data = store_data.get("reviews", {})
    recommend_reviews = reviews_data.get("recommend", {})
    recent_reviews = reviews_data.get("recent", {})
    
    # 공통 메타데이터
    metadata = {
        "store": store_name,
        "category": store_data.get("category"),
        "tel": store_data.get("tel"),
        "feature": store_data.get("feature"),
        "location": store_data.get("location"),
    }
    
    # 추천 리뷰 처리
    for review_id, review_text in recommend_reviews.items():
        doc = Document(
            page_content=review_text.strip(),
            metadata={**metadata, "review_type": "recommend", "review_id": review_id}
        )
        docs.append(doc)
    
    # 최근 리뷰 처리
    for review_id, review_text in recent_reviews.items():
        doc = Document(
            page_content=review_text.strip(),
            metadata={**metadata, "review_type": "recent", "review_id": review_id}
        )
        docs.append(doc)

# 변환 결과 확인
print(f"총 Document 객체 수: {len(docs)}")
print(f"첫 번째 Document: {docs[0]}")

# Split the document into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50
)

# Embed the splits
splits = text_splitter.split_documents(docs)

PineconeVectorStore.from_documents(
    splits, embedding_upstage, index_name=index_name
)

print(">> end")
