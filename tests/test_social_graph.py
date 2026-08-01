import pytest
import os
import sys
from typing import List, Tuple, Dict, Any

# ===================== 路径导入配置 =====================
# 修复 src 模块导入，将项目根目录加入系统环境变量
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 导入自研数据结构与社交图谱核心类
from src.social_graph import SocialGraph, HashTable, MinHeap

# ===================== 全局可配置开关 =====================
# True：读取 data 目录 csv/txt 外部文件；False：内存内置生成测试数据（无需文件）
USE_DATA_FILE: bool = False

# 通用测试常量统一管理
MAX_TEST_USER_NUM = 10
INVALID_UID = 999
SELF_UID_ERR = 1
NEGATIVE_UID = -6  # 负数非法用户 ID
TOP_N_OVER_MAX = 200  # 超过总用户数的推荐参数

# ===================== 通用工具函数（封装重复逻辑） =====================
def print_test_title(title: str) -> None:
    """打印分段测试标题，控制台区分模块，统一排版样式"""
    print(f"\n {'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

# ===================== 测试数据构造函数 =====================
def build_memory_graph_data() -> SocialGraph:
    """
    内存离线构造社交网络数据集
    完全等价于 csv/txt 文件数据，无需依赖外部磁盘文件
    """
    g = SocialGraph()
    # 用户元组：(用户 ID, 姓名，兴趣爱好列表)
    user_list = [
        (1, "张三", ["编程", "篮球", "摄影"]),
        (2, "李四", ["阅读", "音乐", "旅行"]),
        (3, "王五", ["编程", "跑步", "电影"]),
        (4, "赵六", ["游戏", "美食", "动漫"]),
        (5, "钱七", ["音乐", "绘画", "旅行"]),
        (6, "孙八", ["编程", "篮球", "阅读"]),
        (7, "周九", ["电影", "美食", "摄影"]),
        (8, "吴十", ["旅行", "动漫", "游戏"]),
        (9, "郑十一", ["编程", "音乐", "电影"]),
        (10, "王十二", ["阅读", "绘画", "篮球"]),
    ]
    for uid, name, interests in user_list:
        g.add_user(uid, name, interests)

    # 无向好友边，默认边权重统一为 1
    edges = [
        (1, 2), (1, 3), (1, 6), (2, 3), (2, 5),
        (3, 4), (3, 6), (4, 7), (4, 8), (5, 7),
        (5, 9), (6, 9), (7, 8), (7, 10), (8, 10),
        (9, 10), (2, 9), (3, 8), (5, 10), (6, 7)
    ]
    for u, v in edges:
        g.add_friendship(u, v, weight=1)

    print("✅ 初始化完成：内存内置测试数据集已加载")
    return g
