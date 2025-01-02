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

# create new index
# if index_name not in pc.list_indexes().names():
#     pc.create_index(
#         name=index_name,
#         dimension=4096,
#         metric="cosine",
#         spec=ServerlessSpec(cloud="aws", region="us-east-1"),
#     )

pinecone_vectorstore = PineconeVectorStore(index=pc.Index(index_name), embedding=embedding_upstage)

pinecone_retriever = pinecone_vectorstore.as_retriever(
    search_type='mmr',  # default : similarity(유사도) / mmr 알고리즘
    search_kwargs={"k": 3}  # 쿼리와 관련된 chunk를 3개 검색하기 (default : 4)
)

app = FastAPI()

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


@app.post("/chat")
async def chat_endpoint(req: MessageRequest):
    # qa = RetrievalQA.from_chain_type(llm=chat_upstage,
    #                                  chain_type="stuff",
    #                                  retriever=pinecone_retriever,
    #                                  return_source_documents=True)

    # result = qa(req.message)
    # return {"reply": result['result']}

    result_docs = pinecone_retriever.invoke(req.message)

    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 인공지는 챗봇으로, 주어진 문서를 정확하게 이해해서 답변을 해야 해.
            문서에 있는 내용으로만 답변하고 내용이 없다면, 잘 모르겠다고 답변 해.
            ---
            CONTEXT:
            {context}
            """,
        ),
        ("human", "{input}"),
    ]
    )

    chain = prompt | chat_upstage | StrOutputParser()
    result = chain.invoke({"context": result_docs, "input": req.message})
    return {"reply": result}


@app.post("/assistant")
async def assistant_endpoint(req: AssistantRequest):

    # thread_id 가 없는 초기 대화화
    if not req.thread_id:
        # 새로운 대화 시작 - context 포함
        result_docs = pinecone_retriever.invoke(req.message)
        initial_prompt = f"""너는 인공지능 챗봇으로, 주어진 문서를 정확하게 이해해서 답변을 해야 해.
        문서에 있는 내용을 바탕으로 답변하고, 문서에 없는 내용은 '해당 정보는 찾을 수 없습니다'라고 답변해줘.
        
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

    # Thread id가 있다면
    else:
        # 기존 대화 이어가기 - 이전 맥락 유지
        await openai.beta.threads.messages.create(
            thread_id=req.thread_id, 
            role="user", 
            content=req.message
        )
        thread_id = req.thread_id

    # Assistant 실행
    assistant = await openai.beta.assistants.retrieve("asst_VlpG1oOKqa3PACzjWg898WMw")
    await openai.beta.threads.runs.create_and_poll(
        thread_id=thread_id, 
        assistant_id=assistant.id
    )

    # 응답 가져오기
    all_messages = [
        m async for m in openai.beta.threads.messages.list(thread_id=thread_id)
    ]
    assistant_reply = all_messages[0].content[0].text.value

    return {"reply": assistant_reply, "thread_id": thread_id}


@app.get("/health")
@app.get("/")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
