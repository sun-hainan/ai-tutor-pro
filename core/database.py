"""
数据库定义
6 张表：User / Tutor / Mistake / KnowledgePoint / ChatSession / ChatMessage
"""
from datetime import datetime
from pathlib import Path
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Text, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# ========== 数据库路径（绝对路径，不依赖 CWD） ==========
# 解析逻辑：这个 .py 文件在 <项目根>/core/database.py
# 数据库应该放在 <项目根>/data/ai_tutor.db
# 无论你在哪个目录跑 python test_db.py，都能找到正确位置
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # core 的父目录 = 项目根
DB_DIR = PROJECT_ROOT / "data"
DB_DIR.mkdir(exist_ok=True)  # 目录不存在就自动创建（无需手动 mkdir）

DATABASE_URL = f"sqlite:///{DB_DIR / 'ai_tutor.db'}"
# 范例：Windows 下解析为 sqlite:///F:/02_Development/projects/ai-tutor-pro/data/ai_tutor.db
#       Linux/Mac 下解析为 sqlite:////home/user/projects/ai-tutor-pro/data/ai_tutor.db

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 多线程支持
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ========== 表定义 ==========

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    default_level = Column(String, default="beginner")
    created_at = Column(DateTime, default=datetime.now)
    
    # 一个用户多个私教
    tutors = relationship("Tutor", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Tutor(Base):
    """
    私教表
    一个私教 = 一个学习目标
    """
    __tablename__ = "tutors"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 基本信息
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text)
    
    # 人设
    system_prompt = Column(Text, nullable=False)
    level = Column(String, default="beginner")
    style = Column(String, default="patient")
    icon = Column(String, default="🤖")
    
    # RAG 资源
    rag_collection = Column(String, nullable=False, unique=True)
    
    # 时间
    created_at = Column(DateTime, default=datetime.now)
    last_used = Column(DateTime, default=datetime.now)
    
    # 关系
    user = relationship("User", back_populates="tutors")
    mistakes = relationship("Mistake", back_populates="tutor", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="tutor", cascade="all, delete-orphan")


class KnowledgePoint(Base):
    """知识点表"""
    __tablename__ = "knowledge_points"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    category = Column(String, index=True)
    description = Column(Text)


class Mistake(Base):
    """
    错题表
    挂在 Tutor 下，不挂 User（不同私教的错题隔离）
    """
    __tablename__ = "mistakes"
    
    id = Column(Integer, primary_key=True)
    tutor_id = Column(Integer, ForeignKey("tutors.id"), nullable=False, index=True)
    kp_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False)
    
    # 题目内容
    question = Column(Text, nullable=False)
    user_answer = Column(Text)
    correct_answer = Column(Text)
    explanation = Column(Text)
    
    # SM-2 算法字段
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime, default=datetime.now)
    
    # 时间
    created_at = Column(DateTime, default=datetime.now)
    last_reviewed = Column(DateTime, nullable=True)
    
    # 关系
    tutor = relationship("Tutor", back_populates="mistakes")
    knowledge_point = relationship("KnowledgePoint")


class ChatSession(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True)
    tutor_id = Column(Integer, ForeignKey("tutors.id"), nullable=False, index=True)
    title = Column(String)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    tutor = relationship("Tutor", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """对话消息表"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("ChatSession", back_populates="messages")


# ========== 辅助函数 ==========

def init_db():
    """创建所有表（如果不存在）"""
    Base.metadata.create_all(bind=engine)


def get_session():
    """获取数据库 session（每次用完记得 close）"""
    return SessionLocal()