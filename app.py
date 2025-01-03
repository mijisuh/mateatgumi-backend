import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain.chains import RetrievalQA
from langchain_pinecone import PineconeVectorStore
from langchain_upstage import ChatUpstage
from langchain_upstage import UpstageEmbeddings
from pinecone import Pinecone, ServerlessSpec
from pydantic import BaseModel
from collections import defaultdict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

import openai
from openai import AsyncOpenAI

load_dotenv()

openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# upstage models
chat_upstage = ChatUpstage()
embedding_upstage = UpstageEmbeddings(model="embedding-query")

pinecone_api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key=pinecone_api_key)
index_name = "gumi-restaurants"

pinecone_vectorstore = PineconeVectorStore(index=pc.Index(index_name), embedding=embedding_upstage)

pinecone_retriever = pinecone_vectorstore.as_retriever(
    search_type='mmr',  # default : similarity(유사도) / mmr 알고리즘
    search_kwargs={"k": 3}  # 쿼리와 관련된 chunk를 3개 검색하기 (default : 4)
)

app = FastAPI(
    title="맛있구미(MatEatGumi) API",
    description="맛있구미 서비스에 대한 API 명세입니다.",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class AssistantRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]  # Entire conversation for naive mode

class MessageRequest(BaseModel):
    message: str

# Thread별 최근 응답을 저장하는 딕셔너리
recent_replies = defaultdict(str)

@app.post("/assistant", summary="답변 생성", response_description="사용자 질문에 대한 답변을 생성하여 응답으로 전송합니다.")
async def assistant_endpoint(req: AssistantRequest):
    """
    사용자 질문을 받아 OpenAI Assistants API를 호출하여 답변을 생성하는 엔드포인트입니다.
    - **message**: 사용자 질문 텍스트
    - **thread_id**: 스레드를 식별하는 id 값(최초 질문 시 빈 값)
    """

    # Pinecone 검색 수행
    result_docs = pinecone_retriever.invoke(req.message)
    
    # thread_id가 없는 초기 대화인 경우
    if not req.thread_id:
        initial_prompt = f"""너는 인공지능 챗봇으로, 주어진 문서를 정확하게 이해해서 답변을 해야 해.
        문서에 있는 내용을 바탕으로 답변해줘. **, #, ` 등 Markdown 문법을 사용하지 말고 답변해줘.
        
        참고할 정보:
        {result_docs}
        
        User: {req.message}"""
        
        thread = await openai.beta.threads.create(
            messages=[{
                "role": "user", 
                "content": initial_prompt
            }]
        )
        thread_id = thread.id

    # Thread id가 있는 경우
    else:
        recent_reply = recent_replies[req.thread_id]

        context_prompt = f"""이전 대화를 이어서 답변해주되, 가장 최근의 답변을 우선적으로 고려해줘. 아래 문서의 내용도 참고해서 답변해줘.
        
        참고할 정보:
        {result_docs}

        최근 답변:
        {recent_reply}
        
        User: {req.message}"""
        
        # 기존 대화 이어가기 - 새로운 컨텍스트 포함
        await openai.beta.threads.messages.create(
            thread_id=req.thread_id, 
            role="user", 
            content=context_prompt
        )
        thread_id = req.thread_id

    # Assistant 실행
    assistant = await openai.beta.assistants.retrieve(os.environ.get("OPENAI_ASSISTANTS_API_ID"))
    await openai.beta.threads.runs.create_and_poll(
        thread_id=thread_id, 
        assistant_id=assistant.id
    )

    # 응답 가져오기
    all_messages = [
        m async for m in openai.beta.threads.messages.list(thread_id=thread_id)
    ]
    assistant_reply = all_messages[0].content[0].text.value

    # Thread별 최근 응답 업데이트
    recent_replies[thread_id] = assistant_reply

    return {"reply": assistant_reply, "thread_id": thread_id}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
