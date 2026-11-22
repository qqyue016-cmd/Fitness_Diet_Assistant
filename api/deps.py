import datetime

from fastapi import Query


def get_date(date: datetime.date | None = Query(None, description='日期，缺省为今天')) -> str:
    """返回 ISO 字符串，可直接传给 db 层（db 只接受 YYYY-MM-DD 字符串）。"""
    return (date or datetime.date.today()).isoformat()
