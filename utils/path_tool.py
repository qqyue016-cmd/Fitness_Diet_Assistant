'''
为整个项目提供统一绝对路径的工具
'''

import os


def get_project_root() -> str:
    """
    获取项目根目录的绝对路径

    Returns:
        str: 项目根目录的绝对路径
    """
    # 先获取当前文件的路径
    current_path = os.path.abspath(__file__)
    # 再获取当前文件所处文件夹路径
    current_dir = os.path.dirname(current_path)
    # 获取项目根目录路径
    project_root = os.path.dirname(current_dir)

    return project_root

def get_abs_path(relative_path) -> str:
    """
    获取相对路径的绝对路径

    Args:
        relative_path (str): 相对路径

    Returns:
        str: 绝对路径
    """
    project_root = get_project_root()
    return os.path.join(project_root,relative_path)

if __name__ == '__main__':
    print(get_abs_path('scripts/init_db'))