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

def load_file_graph() -> SocialGraph:
    """从项目 data 文件夹读取用户、好友关系文本文件初始化图谱"""
    g = SocialGraph()
    user_csv_path = os.path.join(BASE_DIR, "data", "users.csv")
    rel_txt_path = os.path.join(BASE_DIR, "data", "relationships.txt")
    print(f"\n📂 用户数据文件：{user_csv_path}")
    print(f"📂 好友关系文件：{rel_txt_path}")

    # 文件存在性校验
    if not os.path.exists(user_csv_path):
        raise FileNotFoundError(f"用户文件缺失：{user_csv_path}")
    if not os.path.exists(rel_txt_path):
        raise FileNotFoundError(f"好友关系文件缺失：{rel_txt_path}")

    # 加载数据并校验返回状态
    load_user_success = g.load_users_from_csv(user_csv_path)
    load_rel_success = g.load_relationships_from_txt(rel_txt_path)
    if not load_user_success:
        raise RuntimeError("users.csv 解析加载失败，请检查文件格式、编码、字段排列")
    if not load_rel_success:
        raise RuntimeError("relationships.txt 解析加载失败，请检查每行边数据格式")

    print("✅ 初始化完成：外部磁盘数据文件加载完毕")
    return g

# ===================== pytest 夹具配置 =====================
# 修改：scope改为function，每个用例单独全新构建图谱，彻底隔离数据污染
@pytest.fixture(scope="function")
def graph() -> SocialGraph:
    """
    函数级图谱夹具：每一条测试用例都会重新初始化全新图谱
    用例执行完毕后清空黑名单，保证每条用例环境干净独立
    """
    print_test_title("开始初始化社交图谱全局实例")
    if USE_DATA_FILE:
        graph_ins = load_file_graph()
    else:
        graph_ins = build_memory_graph_data()
    yield graph_ins
    # 后置清理钩子：重置黑名单
    graph_ins.clear_blacklist()
    print("\n🧹 全局收尾：黑名单已全部清空，测试环境重置完成")

@pytest.fixture(scope="function")
def empty_graph() -> SocialGraph:
    """函数级空图谱夹具：每个边界测试用例单独生成空白图，用例之间完全隔离互不干扰"""
    return SocialGraph()


# ==============================================================
# ===================== 【第一大部分：数据结构部分】 =====================
# 覆盖：自研HashTable/MinHeap单元测试、邻接表底层、兴趣索引、文件IO全部测试用例
# ==============================================================

# 测试分组 0：自研基础数据结构单元测试（哈希表 + 小顶堆）
class TestSelfDataStructure:
    """分类：自研底层数据结构单元测试 | 扩充：空哈希表、重复插入、堆相同权重场景"""
    def test_hash_table_all_interface(self):
        """测试链地址法哈希表：增、查、改、删、包含判断、空表、重复键全套接口"""
        ht = HashTable(capacity=20)
        # 空哈希表校验
        assert ht.get(1) is None, "空哈希表取值必须返回 None"
        assert 1 not in ht

        # 新增键值对
        ht.put(1, {"name": "张三"})
        ht.put(5, {"name": "李四"})
        ht.put(9, {"name": "王五"})

        # 取值校验
        assert ht.get(1)["name"] == "张三", "哈希表取值错误"
        assert ht.get(INVALID_UID) is None, "不存在 key 应当返回 None"

        # key 覆盖更新（重复插入同一个键）
        ht.put(1, {"name": "张三三"})
        assert ht.get(1)["name"] == "张三三", "哈希表更新覆盖失效"

        # contains 成员运算符校验
        assert 1 in ht
        assert 5 in ht
        assert INVALID_UID not in ht

        # 删除操作
        assert ht.remove(5) is True, "存在 key 删除应当返回 True"
        assert ht.get(5) is None
        assert ht.remove(INVALID_UID) is False, "删除不存在 key 返回 False"

        # 清空所有元素后校验
        ht.remove(1)
        ht.remove(9)
        assert ht.get(1) is None and ht.get(9) is None
        print("✅ test_hash_table_all_interface：自研哈希表全部接口校验通过")

    def test_min_heap_push_pop_order(self):
        """测试小顶堆：入堆、堆化上浮下沉、顺序弹出、空堆、同等权重容错"""
        heap = MinHeap()
        # 空堆校验
        assert heap.pop() is None
        assert heap.size() == 0

        # 乱序插入 (权重，携带数据)
        heap.push(5, "C")
        heap.push(2, "A")
        heap.push(7, "D")
        heap.push(1, "B")
        # 插入相同权重元素
        heap.push(2, "X")
        heap.push(2, "Y")

        # 严格从小到大弹出最小值
        assert heap.pop() == (1, "B")
        assert heap.pop() == (2, "A")
        assert heap.pop() == (2, "X")
        assert heap.pop() == (2, "Y")
        assert heap.pop() == (5, "C")
        assert heap.pop() == (7, "D")

        # 空堆弹出返回 None，堆大小归零
        assert heap.pop() is None
        assert heap.size() == 0
        print("✅ test_min_heap_push_pop_order：自研小顶堆出入堆顺序、空值容错正常")

# 测试分组 1：数据加载、基础信息、索引校验（邻接表、反向索引底层存储）
class TestGraphBasicLoadInfo:
    """分类：图谱初始化加载、用户信息、邻接表、兴趣反向索引校验"""
    def test_all_users_loaded_correctly(self, graph):
        """校验 10 位用户完整导入，无丢失、无信息空缺"""
        print_test_title("校验全体用户加载完整性")
        uid_list = list(range(1, MAX_TEST_USER_NUM + 1))
        for uid in uid_list:
            user_info = graph.get_user_info(uid)
            assert user_info["name"] != "未知用户", f"用户 ID:{uid} 加载缺失"
            assert len(user_info["interests"]) > 0, f"用户 ID:{uid} 兴趣列表为空，数据异常"
        # 兴趣反向索引已构建
        assert len(graph.interest_index) > 0, "兴趣反向索引为空，构建失败"
        print("✅ test_all_users_loaded_correctly：全部 10 个用户加载正常，兴趣索引有效")

    def test_user_detail_attribute(self, graph):
        """校验用户姓名、兴趣列表字段精准匹配；非法用户返回默认空数据"""
        user1 = graph.get_user_info(1)
        assert user1["name"] == "张三"
        assert set(user1["interests"]) == {"编程", "篮球", "摄影"}
        user10 = graph.get_user_info(10)
        assert user10["name"] == "王十二"
        assert set(user10["interests"]) == {"阅读", "绘画", "篮球"}
        # 查询不存在用户
        unknown = graph.get_user_info(INVALID_UID)
        assert unknown["name"] == "未知用户"
        assert len(unknown["interests"]) == 0
        print("✅ test_user_detail_attribute：用户姓名、兴趣信息匹配无误")

    def test_direct_friend_adjacent_list(self, graph):
        """校验一度好友邻接表无向关系数据准确；非法 ID 好友列表为空"""
        assert set(graph.get_direct_friends(1)) == {2, 3, 6}
        assert set(graph.get_direct_friends(3)) == {1, 2, 4, 6, 8}
        assert set(graph.get_direct_friends(7)) == {4, 5, 6, 8, 10}
        # 非法用户无好友
        assert graph.get_direct_friends(INVALID_UID) == []
        print("✅ test_direct_friend_adjacent_list：用户直连好友邻接表校验通过")

    def test_interest_reverse_index(self, graph):
        """兴趣反向索引：查询爱好对应的所有用户 ID；不存在爱好返回空列表"""
        code_lover = sorted(graph.interest_index["编程"])
        assert code_lover == [1, 3, 6, 9]
        travel_lover = sorted(graph.interest_index["旅行"])
        assert travel_lover == [2, 5, 8]
        # 无该爱好返回空
        assert graph.interest_index.get("滑雪", []) == []
        print("✅ test_interest_reverse_index：兴趣反向索引数据正确")

    # 新增专项测试 1：邻接表专项校验（已适配源码 graph.graph）
    def test_adjacency_list_storage(self, graph):
        adj = graph.graph
        # 无向图双向存边校验
        assert 2 in adj[1] and 1 in adj[2]
        assert 3 in adj[1] and 1 in adj[3]
        assert 6 in adj[1] and 1 in adj[6]
        # 非法节点不在邻接表内
        assert INVALID_UID not in adj
        # 边权重统一存储校验
        edge_key = tuple(sorted([1, 2]))
        assert graph.edge_weights[edge_key] == 1
        print("✅ test_adjacency_list_storage：邻接表双向存边、权重、边界校验全部正常")

# 新增专项测试 2：文件读取解析专项测试（文件IO模块测试）
class TestFileLoadParse:
    def test_file_parse_accuracy(self):
        """独立读取文件，校验 csv、txt 解析内容和内存数据完全一致"""
        BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        user_csv_path = os.path.join(BASE, "data", "users.csv")
        rel_txt_path = os.path.join(BASE, "data", "relationships.txt")
        file_g = SocialGraph()
        file_g.load_users_from_csv(user_csv_path)
        file_g.load_relationships_from_txt(rel_txt_path)
        memory_g = build_memory_graph_data()
        # 逐用户比对个人信息
        for uid in range(1, 11):
            file_info = file_g.get_user_info(uid)
            mem_info = memory_g.get_user_info(uid)
            assert file_info["name"] == mem_info["name"]
            assert set(file_info["interests"]) == set(mem_info["interests"])
        # 逐用户比对好友邻接关系
        for uid in range(1, 11):
            assert set(file_g.get_direct_friends(uid)) == set(memory_g.get_direct_friends(uid))
        print("✅ test_file_parse_accuracy：users.csv、relationships.txt 文件解析和内存数据完全匹配")

