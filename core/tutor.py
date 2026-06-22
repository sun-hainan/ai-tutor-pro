"""
私教核心业务逻辑：答疑、出题、判分、评审
"""
import json
from core.llm import chat
import re


def parse_result(result: str) -> dict:
    """解析出题结果"""
    result = re.sub(r'', '', result, flags=re.DOTALL)
    # 2. 剥掉 markdown 围栏 ```json ... ```
    result = re.sub(r'```(?:json)?\s*', '', result)
    result = result.replace('```', '').strip()
    # 3. 从剩下的文本里抠出第一个 {...} 块
    match = re.search(r'\{.*\}', result, re.DOTALL)
    if match:
        result = match.group(0)
    return json.loads(result)

# ========== 答疑 ==========

def answer_question(
    question: str,
    system_prompt: str = "",
    history: list = None,
) -> str:
    """
    答疑：基于私教的 system_prompt 回答用户问题
    
    Args:
        question: 用户问题
        system_prompt: 私教的人设
        history: 历史对话 [{"role": "user/assistant", "content": "..."}]
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})
    
    return chat(messages, temperature=0.7)


# ========== 出题 ==========

def generate_quiz(topic: str, difficulty: str = "medium", context: str = "") -> dict:
    """
    出题：生成结构化选择题
    
    Args:
        topic: 题目主题
        difficulty: easy/medium/hard
        context: 可选上下文（比如基于之前的错题）
    """
    difficulty_desc = {
        "easy": "考察基础概念，选项有明显错误",
        "medium": "考察理解和应用，迷惑性适中",
        "hard": "考察深入理解和边界情况，迷惑性强",
    }
    
    prompt = f"""你是一个出题老师，围绕"{topic}"出一道{difficulty}难度的单选题。

            【难度要求】{difficulty_desc.get(difficulty, difficulty_desc["medium"])}

            {f"【参考上下文】{context}" if context else ""}

            【输出要求】
            1. 题干清晰，不要有歧义
            2. 4 个选项，答案唯一
            3. 解释要说明"为什么对"和"为什么其他错"
            4. 严格按 JSON 格式输出

            JSON 格式：
            {{
                "question": "题目内容",
                "options": {{
                    "A": "选项A的内容",
                    "B": "选项B的内容",
                    "C": "选项C的内容",
                    "D": "选项D的内容"
                }},
                "correct_answer": "A",
                "explanation": "详细解析"
            }}"""
    
    result = chat(
        [{"role": "user", "content": prompt}],
        temperature=0.5,
        json_mode=True
    )
    
    try:
        # return json.loads(result)
        return parse_result(result)
    except json.JSONDecodeError:
        # 如果解析失败，尝试提取 JSON
        start = result.find("{")
        end = result.rfind("}") + 1
        if start != -1 and end != -1:
            return json.loads(result[start:end])
        raise


# ========== 判分 ==========

def judge_answer(
    question: str,
    user_answer: str,
    correct_answer: str,
    explanation: str = "",
    level: str = "beginner",
) -> str:
    """判分 + 详细解析"""
    prompt = f"""【题目】{question}

【用户答案】{user_answer}

【正确答案】{correct_answer}

{f"【原解析】{explanation}" if explanation else ""}

请按以下格式回复：
1. 一句话判断对错
2. 详细解释（用户水平：{level}，用对应深度）
3. 如果错了，指出用户可能的误区
4. 推荐下一步学习方向"""
    
    return chat(
        [{"role": "user", "content": prompt}],
        temperature=0.3
    )


# ========== 代码评审 ==========

def review_code(code: str, language: str = "python", level: str = "beginner") -> str:
    """代码评审"""
    prompt = f"""请评审这段 {language} 代码（用户水平：{level}）：

```{language}
{code}
```

【评审维度】

## 🔍 问题诊断
- Bug 和隐患（按严重程度排序）

## 💡 改进建议
- 可读性、性能、最佳实践（3-5 条具体建议）

## ✨ 优化后代码
- 给出优化版本，注释关键改动

## 📚 学习建议
- 针对 {level} 用户的额外学习资源方向"""
    
    return chat(
        [{"role": "user", "content": prompt}],
        temperature=0.3
    )


# ========== 错题分类 ==========

def auto_categorize_mistake(question: str, wrong_answer: str, correct_answer: str = "") -> dict:
    """AI 自动识别错题属于哪个知识点"""
    prompt = f"""用户的错题：
【题目】{question}
【用户答】{wrong_answer}
{f"【正确答案】{correct_answer}" if correct_answer else ""}

请分析：
1. 这个错题属于哪个具体知识点？
2. 这个知识点属于哪个分类？
3. 用户可能的误区是什么？

严格按 JSON 格式：
{{
    "knowledge_point": "具体的知识点名",
    "category": "所属分类",
    "user_misconception": "用户的误区"
}}"""
    
    result = chat(
        [{"role": "user", "content": prompt}],
        temperature=0.3,
        json_mode=True
    )
    print(f"AI 回答：{result}")
    # return json.loads(result)
    return parse_result(result)

# ========== 复习出题 ==========

def generate_review_quiz(mistakes: list) -> dict:
    """
    基于用户错题生成变形题
    mistakes: Mistake 对象列表
    """
    if not mistakes:
        raise ValueError("没有错题可复习")
    
    mistakes_text = "\n".join([
        f"{i+1}. [{m.knowledge_point.name if m.knowledge_point else '未知'}] "
        f"{m.question}\n   用户错答: {m.user_answer}\n   正确答案: {m.correct_answer}"
        for i, m in enumerate(mistakes[:5])
    ])
    
    prompt = f"""用户有以下错题：

{mistakes_text}

请基于这些错题**出一道变形题**帮他巩固（不要原题）。

【要求】
1. 考同一个知识点，但换种问法
2. 比原题稍难（让他真正掌握，不是背答案）
3. 提供 4 个迷惑性强的选项
4. 解释中关联到原错题

JSON 格式：
{{
    "question": "新题目",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct_answer": "X",
    "explanation": "解析 + 与原错题的联系"
}}"""
    
    result = chat(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        json_mode=True
    )
    
    # return json.loads(result)
    return parse_result(result)