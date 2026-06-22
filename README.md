# 🎓 多私教 AI 学习系统

一个用 Python 构建的 AI 学习助手，支持多个独立私教（Python/SQL/ML/算法等），每个私教有独立的人设、错题本、资料库。

## ✨ 功能

- 🎓 **多私教系统**：每个学习目标独立私教，互不干扰
- 💬 **智能答疑**：基于人设的个性化回答，多轮对话持久化
- 📝 **AI 出题**：按主题/难度自动出选择题
- 🔍 **代码评审**：贴代码获得专业反馈
- ❌ **错题复习**：艾宾浩斯 SM-2 算法自动安排复习
- 📖 **资料问答**：上传 PDF/MD 教程，AI 按资料回答
- 📊 **学习画像**：可视化薄弱知识点和错题趋势

## 🚀 本地运行

### 1. 克隆仓库
```bash
git clone https://github.com/你的用户名/ai-tutor-pro.git
cd ai-tutor-pro
```

### 2. 申请 DeepSeek API Key
访问 [platform.deepseek.com](https://platform.deepseek.com) 注册并申请 API Key。

### 3. 配置环境变量
```bash
# 复制模板
cp .env.example .env

# 编辑 .env，填入你的 API Key
# DEEPSEEK_API_KEY=sk-你的真实key
```

### 4. 安装依赖
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或 .\venv\Scripts\Activate.ps1  # Windows

pip install -r requirements.txt
```

### 5. 运行
```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501

## 🛠️ 技术栈

- **LLM**: DeepSeek-V3
- **Web**: Streamlit
- **数据库**: SQLite + SQLAlchemy
- **向量库**: ChromaDB
- **Embedding**: DeepSeek text-embedding-v2
- **部署**: Streamlit Community Cloud

## 📁 项目结构

```
ai-tutor-pro/
├── core/                  # 核心业务逻辑
│   ├── llm.py             # LLM 封装
│   ├── database.py        # 数据库定义
│   ├── tutor_service.py   # 私教管理
│   ├── tutor.py           # 答疑/出题
│   ├── spaced_repetition.py  # 错题算法
│   └── rag.py             # 资料问答
├── app.py                 # Web 入口
├── data/                  # 数据存储
├── uploads/               # 用户上传
└── docs/                  # 教程文档
```

## 📚 完整教程

本项目有完整的 5 天教程：

- [Day 1: 环境与基础架构](./docs/Day1-环境与基础架构.md)
- [Day 2: 私教管理](./docs/Day2-私教管理.md)
- [Day 3: 核心功能](./docs/Day3-核心功能.md)
- [Day 4: Web 界面](./docs/Day4-Web界面.md)
- [Day 5: 部署上线](./docs/Day5-部署上线.md)

## 🤝 贡献

欢迎提 Issue 和 PR！

## 📄 许可

MIT License