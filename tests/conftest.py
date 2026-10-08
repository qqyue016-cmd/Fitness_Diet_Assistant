import pytest

from db import get_connect

TEST_DATE = '1900-01-01'


@pytest.fixture(autouse=True)
def clean_intake():
    """每个用例跑完后，只清理本测试专属日期，绝不触碰真实数据。"""
    yield
    conn = get_connect()
    conn.execute('DELETE FROM intake WHERE date = ?', (TEST_DATE,))
    conn.commit()
    conn.close()