"""
RAG（检索增强生成）
让 AI 基于用户的私有资料回答问题
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import requests
import json
import chromadb
from pypdf import PdfReader

load_dotenv()
_client = OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY"),
    base_url=os.getenv("MINIMAX_BASE_URL")
)

# 向量库存储目录
CHROMA_DIR = "./data/chroma"
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)


# ========== Embedding ==========

def get_embedding(text: str) -> list:
    """文本转向量"""
    # response = _client.embeddings.create(
    #     model=os.getenv("MINIMAX_EMBEDDING_MODEL", "text-embedding-v2"),
    #     input=text,
    # )
    # return response.data[0].embedding
    url = f"https://api.minimax.chat/v1/embeddings?GroupId={os.getenv("MINIMAX_EMBEDDING_GROUPID")}"
    headers = {
        "Authorization": f"Bearer {os.getenv("MINIMAX_API_KEY")}",
        "Content-Type": "application/json"
    }

    data = {
        "texts": [
            text
        ],
        "model": "embo-01",
        "type": "db"
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    res = json.loads(response.text)['vectors'][0]
    return res


# ========== 文档处理 ==========

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    把长文本切成小块
    chunk_size: 每块字符数
    overlap: 块之间重叠字符数
    """
    chunks = []
    start = 0
    text = text.strip()
    
    if not text:
        return chunks
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    
    return chunks


def parse_pdf(pdf_path: str) -> str:
    """解析 PDF 为文本"""
    reader = PdfReader(pdf_path)
    full_text = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
            if text:
                full_text.append(text)
        except Exception as e:
            print(f"  警告：第 {i+1} 页解析失败：{e}")
    return "\n".join(full_text)


# ========== 存入向量库 ==========

def ingest_pdf(pdf_path: str, collection_name: str) -> int:
    """把 PDF 喂进指定私教的向量库"""
    print(f"  解析 PDF: {pdf_path}")
    text = parse_pdf(pdf_path)
    print(f"  文本长度：{len(text)} 字符")
    
    return ingest_text(text, source_name=os.path.basename(pdf_path), collection_name=collection_name)


def ingest_text(text: str, source_name: str, collection_name: str) -> int:
    """把文本喂进指定私教的向量库"""
    chunks = chunk_text(text)
    print(f"  切出 {len(chunks)} 块")
    
    if not chunks:
        return 0
    
    collection = chroma_client.get_or_create_collection(collection_name)
    
    # 批量处理（每批 50 块，避免单次请求过大）
    batch_size = 50
    total_added = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        embeddings = [get_embedding(chunk) for chunk in batch]
        ids = [f"{source_name}_{i+j}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}" 
               for j in range(len(batch))]
        
        collection.add(
            embeddings=embeddings,
            documents=batch,
            ids=ids,
        )
        total_added += len(batch)
    
    return total_added


# ========== 检索 ==========

def search(query: str, collection_name: str, top_k: int = 3) -> list:
    """在指定私教资料库中检索相关文档块"""
    collection = chroma_client.get_or_create_collection(collection_name)
    query_embedding = get_embedding(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
    
    documents = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0] if results["distances"] else []
    
    return list(zip(documents, distances))


# ========== RAG 问答 ==========

def rag_answer(question: str, collection_name: str, tutor_name: str = "私教") -> str:
    """基于检索内容回答"""
    results = search(question, collection_name, top_k=3)
    
    if not results:
        return "抱歉，没有找到相关资料。请先上传一些教程或文档。"
    
    context = "\n\n---\n\n".join([doc for doc, _ in results])
    
    prompt = f"""你是{tutor_name}，需要基于以下参考资料回答用户问题。

【严格要求】
1. 优先使用参考资料中的内容
2. 如果参考资料里有答案，明确引用（"根据资料..."）
3. 如果参考资料里没有答案，明确说"我手头的资料里没找到，建议你查官方文档"
4. 不要编造资料里没有的内容
5. 简洁准确，重点突出

【参考资料】
{context}

【用户问题】
{question}

【你的回答】"""
    
    response = _client.chat.completions.create(
        model=os.getenv("MINIMAX_MODEL", "MiniMax-M3"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    ),
    
    return response.choices[0].message.content


# ========== 辅助函数 ==========

def get_collection_stats(collection_name: str) -> dict:
    """获取资料库统计"""
    try:
        collection = chroma_client.get_collection(collection_name)
        return {"doc_count": collection.count(), "exists": True}
    except Exception:
        return {"doc_count": 0, "exists": False}


def list_collections() -> list:
    """列出所有资料库"""
    return [c.name for c in chroma_client.list_collections()]