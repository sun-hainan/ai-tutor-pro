"""
间隔重复算法（SM-2）
"""
from datetime import datetime, timedelta
from core.database import Mistake, KnowledgePoint
from sqlalchemy import func


def update_after_review(mistake: Mistake, is_correct: bool, quality: int = None) -> Mistake:
    """
    复习后更新错题状态
    
    Args:
        mistake: Mistake 对象
        is_correct: 是否答对
        quality: 0-5 评分（None 时根据 is_correct 自动定）
            0=完全不会, 1=错且很生疏, 2=错但记得一点
            3=对但很犹豫, 4=对且稍犹豫, 5=完美
    """
    if quality is None:
        quality = 5 if is_correct else 2
    
    # 1. 更新 repetitions 和 interval
    if quality < 3:
        mistake.repetitions = 0
        mistake.interval = 1
    else:
        if mistake.repetitions == 0:
            mistake.interval = 1
        elif mistake.repetitions == 1:
            mistake.interval = 6
        else:
            mistake.interval = int(mistake.interval * mistake.ease_factor)
        mistake.repetitions += 1
    
    # 2. 更新 ease_factor（SM-2 公式）
    ef_delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    mistake.ease_factor = max(1.3, mistake.ease_factor + ef_delta)
    
    # 3. 更新时间戳
    mistake.last_reviewed = datetime.now()
    mistake.next_review = datetime.now() + timedelta(days=mistake.interval)
    
    return mistake


def get_due_mistakes(db, tutor_id: int) -> list:
    """获取今天该复习的错题（next_review <= now）"""
    now = datetime.now()
    return db.query(Mistake).filter(
        Mistake.tutor_id == tutor_id,
        Mistake.next_review <= now
    ).all()


def get_weak_points(db, tutor_id: int, top_n: int = 5) -> list:
    """
    获取薄弱知识点（按错题数排序）
    """
    results = db.query(
        KnowledgePoint.name,
        func.count(Mistake.id).label('mistake_count')
    ).join(Mistake).filter(
        Mistake.tutor_id == tutor_id
    ).group_by(KnowledgePoint.name).order_by(
        func.count(Mistake.id).desc()
    ).limit(top_n).all()
    
    return [{"knowledge_point": r[0], "mistake_count": r[1]} for r in results]


def get_review_stats(db, tutor_id: int) -> dict:
    """获取复习统计"""
    total = db.query(Mistake).filter_by(tutor_id=tutor_id).count()
    due = len(get_due_mistakes(db, tutor_id))
    
    # 已掌握：复习过 2 次以上
    mastered = db.query(Mistake).filter(
        Mistake.tutor_id == tutor_id,
        Mistake.repetitions >= 2
    ).count()
    
    mastery_rate = (mastered / total * 100) if total > 0 else 0
    
    return {
        "total_mistakes": total,
        "due_today": due,
        "mastered": mastered,
        "mastery_rate": mastery_rate,
    }