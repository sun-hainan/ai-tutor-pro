import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import json
#加载环境变量
load_dotenv()

#创建全局客户端(单例模式)
_client = OpenAI(
    api_key = os.getenv("MINIMAX_API_KEY"),
    base_url = os.getenv("MINIMAX_BASE_URL")
)

#模型配置
DEFAULT_CHAT_MODEL = os.getenv("MINIMAX_MODEL", 
"MiniMax-M3")
DEFAULT_EMBEDDING_MODEL = os.getenv("MINIMAX_EMBEDDING_MODEL", 
"embo-01")

def chat(
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
    """
    统一聊天接口

    Args:
        messages (list):消息列表，格式[{"role": "user", "content": "问题"}]
        model (str, optional):模型名称，默认使用环境变量配置的模型
        temperature (float, optional):温度参数，默认0.7
        json_mode (bool, optional):是否开启JSON模式，默认False

    Returns:
        str:模型回复
    """
    if model is None:
        model = DEFAULT_CHAT_MODEL
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = _client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

def get_embedding(text: str, model: str = None) -> list:
    """
    将文本变成向量（一串数字）
    用于RAG语义搜索
    """
    # if model is None:
    #     model = DEFAULT_EMBEDDING_MODEL

    # response = _client.embeddings.create(
    #     model = model,
    #     input = text,
    # )
    # resp = client.embeddings.create(

    #     model="embo-01",

    #     input="Rust是一门编程语言",     # OpenAI 标准的 input 字段

    # )

    # print(resp.data[0].embedding[:5])
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
    # return response.data[0].embedding

