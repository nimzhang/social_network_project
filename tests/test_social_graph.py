"""
社交网络图测试文件
包含所有数据结构和算法的单元测试
"""

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
from src.social_graph import SocialGraph, HashTable, MinHeap, SimpleSet

# ===================== 全局可配置开关 =====================
# True：读取 data 目录 csv/txt 外部文件；False：内存内置生成测试数据（无需文件）
USE_DATA_FILE: bool = False
# 通用测试常量统一管理
MAX_TEST_USER_NUM = 10
INVALID_UID = 999
SELF_UID_ERR = 1
NEGATIVE_UID = -6  # 负数非法用户 ID
TOP_N_OVER_MAX = 200  # 超过总用户数的推荐参数
# 新增：排序策略常量
SORT_INTEREST = "interest"
SORT_WEIGHT = "weight"
WRONG_SORT_KEY = "time"


# ===================== 通用工具函数（封装重复逻辑） =====================
def print_test_title(title: str) -> None:
    """打印分段测试标题，控制台区分模块，统一排版样式"""
    print(f"\n {'=' * 60}")
    print(f"🔍 {title}")
    print(f"{'=' * 60}")


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
# 单元测试模块：自研底层数据结构、社交图核心功能、BUG修复验证
# 覆盖哈希表、集合、小顶堆、图加载、文件解析、数据隔离等校验
# ==============================================================
# ===================== 第一大部分：数据结构测试 =====================
class TestSelfDataStructure:
    """自研基础数据结构单元测试类
    测试对象：HashTable哈希表、SimpleSet自研集合、MinHeap小顶堆
    测试覆盖：增、删、改、查、遍历、边界、空值、迭代安全、重载运算符全接口
    """

    def test_hash_table_all_interface(self):
        """测试哈希表完整接口：插入、更新、查询、删除、in判断、默认值、空键兼容"""
        ht = HashTable()
        # 空哈希取值校验
        assert ht.get(1) is None, "空哈希表取值必须返回 None"
        assert 1 not in ht
        # 插入三组测试数据
        ht.put(1, {"name": "张三"})
        ht.put(5, {"name": "李四"})
        ht.put(9, {"name": "王五"})
        # 正常键取值校验
        assert ht.get(1)["name"] == "张三", "哈希表取值错误"
        # 不存在键取值校验
        assert ht.get(INVALID_UID) is None, "不存在 key 应当返回 None"
        # 覆盖更新已有key
        ht.put(1, {"name": "张三三"})
        assert ht.get(1)["name"] == "张三三", "哈希表更新覆盖失效"
        # in 成员判断
        assert 1 in ht
        assert 5 in ht
        assert INVALID_UID not in ht
        # 删除存在key
        assert ht.remove(5) is True, "存在 key 删除应当返回 True"
        assert ht.get(5) is None
        # 删除不存在key
        assert ht.remove(INVALID_UID) is False, "删除不存在 key 返回 False"
        # 清空数据校验
        ht.remove(1)
        ht.remove(9)
        assert ht.get(1) is None and ht.get(9) is None
        print("✅ test_hash_table_all_interface：自研哈希表全部接口校验通过")

        # 测试get自定义默认值参数
        assert ht.get(INVALID_UID, "default") == "default"
        # 兼容None作为键的特殊场景
        ht.put(None, "none_value")
        assert ht.get(None) == "none_value"

    def test_min_heap_push_pop_order(self):
        """测试自研小顶堆：入堆、出堆优先级、peek查看、空堆容错、顺序正确性"""
        heap = MinHeap()
        # 空堆弹出校验
        assert heap.pop() is None
        assert heap.size() == 0
        # 批量插入不同优先级元素
        heap.push(5, "C")
        heap.push(2, "A")
        heap.push(7, "D")
        heap.push(1, "B")
        heap.push(2, "X")
        heap.push(2, "Y")
        # 按最小优先级依次弹出验证
        assert heap.pop() == (1, "B")
        assert heap.pop() == (2, "A")
        assert heap.pop() == (2, "X")
        assert heap.pop() == (2, "Y")
        assert heap.pop() == (5, "C")
        assert heap.pop() == (7, "D")
        assert heap.pop() is None
        assert heap.size() == 0
        print("✅ test_min_heap_push_pop_order：自研小顶堆出入堆顺序、空值容错正常")

        # 测试peek仅查看不弹出功能
        heap.push(3, "test")
        assert heap.peek() == (3, "test")
        assert heap.size() == 1
        assert heap.pop() == (3, "test")
        assert heap.peek() is None

    def test_simple_set_interface(self):
        """测试自研SimpleSet集合：添加、删除、长度、成员判断、遍历迭代"""
        s = SimpleSet()
        # 空集合长度
        assert len(s) == 0
        # 添加元素
        s.add(1)
        s.add(2)
        assert len(s) == 2
        # in 判断元素存在与否
        assert 1 in s
        assert 2 in s
        assert 3 not in s
        # 删除存在元素
        s.discard(1)
        assert 1 not in s
        assert len(s) == 1
        # 删除不存在元素，无报错容错
        s.discard(999)
        assert len(s) == 1
        # 遍历迭代功能校验
        s.add(3)
        s.add(4)
        elements = []
        for val in s:
            elements.append(val)
        assert len(elements) == 3
        print("✅ test_simple_set_interface：SimpleSet 接口校验通过")

        # 迭代过程中修改集合，校验无迭代异常（迭代副本安全机制）
        s2 = SimpleSet()
        s2.add(1)
        s2.add(2)
        s2.add(3)
        for val in s2:
            s2.discard(val)  # 在迭代中删除元素，不抛出异常
        assert len(s2) == 0


# ==============================================================
# ===================== 测试分组 1：基础加载校验 =====================
# 测试社交图整体加载、用户信息、邻接表、兴趣索引、内存/文件数据一致性
# ==============================================================
class TestGraphBasicLoadInfo:
    """社交网络图基础加载测试类
    校验CSV/TXT加载后用户、好友、兴趣索引、邻接表数据完整性
    """

    def test_all_users_loaded_correctly(self, graph):
        """校验全部测试用户是否完整加载，姓名、兴趣无缺失"""
        print_test_title("校验全体用户加载完整性")
        uid_list = list(range(1, MAX_TEST_USER_NUM + 1))
        for uid in uid_list:
            user_info = graph.get_user_info(uid)
            assert user_info["name"] != "未知用户", f"用户 ID:{uid} 加载缺失"
            assert len(user_info["interests"]) > 0, f"用户 ID:{uid} 兴趣列表为空，数据异常"
        # 兴趣反向索引构建校验
        assert len(graph.interest_index.keys()) > 0, "兴趣反向索引为空，构建失败"
        print("✅ test_all_users_loaded_correctly：全部 10 个用户加载正常，兴趣索引有效")

    def test_user_detail_attribute(self, graph):
        """校验指定用户固定姓名、兴趣字段匹配测试数据集"""
        user1 = graph.get_user_info(1)
        assert user1["name"] == "张三"
        assert set(user1["interests"]) == {"编程", "篮球", "摄影"}
        user10 = graph.get_user_info(10)
        assert user10["name"] == "王十二"
        assert set(user10["interests"]) == {"阅读", "绘画", "篮球"}
        unknown = graph.get_user_info(INVALID_UID)
        assert unknown["name"] == "未知用户"
        assert len(unknown["interests"]) == 0
        print("✅ test_user_detail_attribute：用户姓名、兴趣信息匹配无误")

    def test_direct_friend_adjacent_list(self, graph):
        """校验邻接表中用户直接好友集合是否与测试数据一致"""
        assert set(graph.get_direct_friends(1)) == {2, 3, 6}
        assert set(graph.get_direct_friends(3)) == {1, 2, 4, 6, 8}
        assert set(graph.get_direct_friends(7)) == {4, 5, 6, 8, 10}
        # 无效用户返回空列表
        assert graph.get_direct_friends(INVALID_UID) == []
        print("✅ test_direct_friend_adjacent_list：用户直连好友邻接表校验通过")

    def test_interest_reverse_index(self, graph):
        """校验兴趣反向索引映射关系正确，同兴趣用户匹配"""
        code_lover = sorted(graph.interest_index.get("编程") or [])
        assert code_lover == [1, 3, 6, 9]
        travel_lover = sorted(graph.interest_index.get("旅行") or [])
        assert travel_lover == [2, 5, 8]
        # 无对应兴趣返回None
        assert graph.interest_index.get("滑雪") is None
        print("✅ test_interest_reverse_index：兴趣反向索引数据正确")

    def test_adjacency_list_storage(self, graph):
        """校验无向图双向存储好友关系、边权重存储逻辑"""
        adj = graph.graph
        # 双向好友校验：1包含2，2也包含1
        assert 2 in adj[1] and 1 in adj[2]
        assert 3 in adj[1] and 1 in adj[3]
        assert 6 in adj[1] and 1 in adj[6]
        # 无效用户无记录
        assert INVALID_UID not in adj
        # 有序二元组存储权重校验
        edge_key = tuple(sorted([1, 2]))
        assert graph.edge_weights[edge_key] == 1
        print("✅ test_adjacency_list_storage：邻接表双向存边、权重、边界校验全部正常")


class TestFileLoadParse:
    """文件加载解析测试类
    对比CSV/TXT读取的数据与内存构造的标准图数据，保证文件解析无误差
    """

    def test_file_parse_accuracy(self):
        """验证CSV用户、TXT关系文件解析结果与内存标准数据完全一致"""
        BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        user_csv_path = os.path.join(BASE, "data", "users.csv")
        rel_txt_path = os.path.join(BASE, "data", "relationships.txt")
        # 新建图对象，从文件加载数据
        file_g = SocialGraph()
        file_g.load_users_from_csv(user_csv_path)
        file_g.load_relationships_from_txt(rel_txt_path)
        # 内存构造标准测试图作为对比基准
        memory_g = build_memory_graph_data()
        # 逐用户校验姓名、兴趣
        for uid in range(1, 11):
            file_info = file_g.get_user_info(uid)
            mem_info = memory_g.get_user_info(uid)
            assert file_info["name"] == mem_info["name"]
            assert set(file_info["interests"]) == set(mem_info["interests"])
        # 逐用户校验好友列表
        for uid in range(1, 11):
            assert set(file_g.get_direct_friends(uid)) == set(memory_g.get_direct_friends(uid))
        print("✅ test_file_parse_accuracy：users.csv、relationships.txt 文件解析和内存数据完全匹配")


# ==============================================================
# ===================== 【新增：Bug 修复验证测试】 =====================
# 专门验证之前代码存在缺陷的修复效果，保证底层逻辑无漏洞
# ==============================================================
class TestBugFixes:
    """BUG修复验证测试类
    针对哈希表in判断、默认值、集合迭代、数据副本、兴趣索引更新等历史问题校验
    """

    def test_hash_table_contains_fix(self):
        """验证HashTable __contains__ 修复：值为None时，键存在仍返回True"""
        ht = HashTable()
        ht.put("key1", None)
        ht.put("key2", "value")

        # 修复前BUG：get返回None导致in判断失效；修复后仅判断键是否存在，与值无关
        assert "key1" in ht
        assert "key2" in ht
        assert "key3" not in ht

        print("✅ test_hash_table_contains_fix：HashTable.__contains__ 修复验证通过")

    def test_hash_table_get_default_fix(self):
        """验证Hash.get默认值参数修复，区分「键不存在」和「键存在但值为None」两种场景"""
        ht = HashTable()
        ht.put("key1", None)
        ht.put("key2", "value")

        # 区分两种None场景，支持自定义默认返回值
        assert ht.get("key1") is None
        assert ht.get("key3") is None
        assert ht.get("key3", "default") == "default"
        assert ht.get("key1", "default") is None

        print("✅ test_hash_table_get_default_fix：HashTable.get 默认值支持验证通过")

    def test_simple_set_iteration_safety(self):
        """验证SimpleSet迭代安全：遍历中删除元素不会抛出迭代异常"""
        s = SimpleSet()
        for i in range(100):
            s.add(i)

        # 迭代过程删除全部元素，无报错
        for val in s:
            s.discard(val)

        assert len(s) == 0
        print("✅ test_simple_set_iteration_safety：SimpleSet 迭代安全性验证通过")

    def test_get_user_info_immutability(self):
        """验证get_user_info返回数据副本，外部修改不会污染图内部原始存储"""
        graph = SocialGraph()
        graph.add_user(1, "测试用户", ["编程", "阅读"])

        # 外部修改返回的字典
        info1 = graph.get_user_info(1)
        info1["name"] = "修改的名字"
        info1["interests"].append("篮球")

        # 重新读取原始数据，保持不变
        info2 = graph.get_user_info(1)
        assert info2["name"] == "测试用户"
        assert info2["interests"] == ["编程", "阅读"]

        print("✅ test_get_user_info_immutability：get_user_info 返回副本验证通过")

    def test_update_user_interests(self, graph):
        """测试更新用户兴趣时，同步清理旧兴趣索引、新增兴趣索引的逻辑正确性"""
        # 新增测试用户
        graph.add_user(11, "测试用户", ["编程", "阅读"])

        # 初始兴趣索引校验
        assert 11 in graph.interest_index.get("编程")
        assert 11 in graph.interest_index.get("阅读")
        runner_list = graph.interest_index.get("跑步") or []
        assert 11 not in runner_list

        # 更新用户兴趣列表
        assert graph.update_user_interests(11, ["编程", "跑步", "摄影"]) is True

        # 旧兴趣阅读移除索引
        assert 11 not in (graph.interest_index.get("阅读") or [])
        # 新兴趣跑步、摄影加入索引
        assert 11 in graph.interest_index.get("跑步")
        assert 11 in graph.interest_index.get("摄影")
        # 保留不变的编程兴趣
        assert 11 in graph.interest_index.get("编程")

        # 更新不存在用户返回False
        assert graph.update_user_interests(999, ["测试"]) is False

        print("✅ test_update_user_interests：更新用户兴趣功能验证通过")
# ==============================================================
# ===================== 【第二大部分：算法负责全量代码】 =====================
# 覆盖：上层业务增删改、全部图算法、推荐、黑名单、边界容错
# ==============================================================
# 测试分组 2：用户、好友增删改基础上层业务接口
class TestUserFriendOperate:
    """用户和好友操作测试"""

    def test_add_repeat_friend(self, graph):
        """重复添加同一好友，无冗余边，无报错"""
        # 原本已是好友
        assert 2 in graph.get_direct_friends(1)
        # 重复添加多次（幂等操作）
        for _ in range(3):
            res = graph.add_friendship(1, 2, weight=1)
        # 边不会重复存储，好友列表仅有一个 2
        friend_list = graph.get_direct_friends(1)
        assert friend_list.count(2) == 1
        print("✅ test_add_repeat_friend：重复添加好友不会产生冗余边")

    def test_modify_edge_weight(self, graph):
        """修改好友之间边的权重，Dijkstra 路径权重同步更新"""
        # 修改 1-2 边权重为 5
        graph.add_friendship(1, 2, weight=5)
        total_w, _ = graph.get_weighted_shortest_path(1, 5)
        # 适配真实最短路径权重为 3
        assert total_w == 3
        # 恢复权重为 1，路径变回原值
        graph.add_friendship(1, 2, weight=1)
        w_recover, _ = graph.get_weighted_shortest_path(1, 5)
        assert w_recover == 2
        print("✅ test_modify_edge_weight：边权重修改生效，带权路径同步更新")

    def test_delete_friendship_bidirectional(self, graph):
        """双向删除好友关系：双方邻接表、边权重字典同步清除；重复删除返回 false"""
        #验证好友关系存在
        assert 2 in graph.get_direct_friends(1)
        edge_key = tuple(sorted((1, 2)))
        assert edge_key in graph.edge_weights
        # 执行删除
        delete_res = graph.delete_friendship(1, 2)
        assert delete_res is True
        assert 2 not in graph.get_direct_friends(1)
        assert 1 not in graph.get_direct_friends(2)
        assert edge_key not in graph.edge_weights
        # 重复删除返回 False
        assert graph.delete_friendship(1, 2) is False
        #无效用户删除返回False
        assert graph.delete_friendship(INVALID_UID, 1) is False
        assert graph.delete_friendship(NEGATIVE_UID, 2) is False
        print("✅ test_delete_friendship_bidirectional：双向好友删除逻辑完整")

    def test_delete_user_full_clean(self):
        """彻底删除用户：好友连线、用户属性、兴趣索引、黑名单全部清理干净"""
        temp_graph = build_memory_graph_data()
        # 删除用户 5
        del_success = temp_graph.delete_user(5)
        assert del_success is True
        # 用户基础信息哈希表移除
        assert temp_graph.user_attrs.get(5) is None
        # 所有好友列表不再包含该用户
        assert 5 not in temp_graph.get_direct_friends(2)
        # 兴趣索引剔除用户
        travel_data = temp_graph.interest_index.get("旅行") or []
        assert 5 not in travel_data
        # 先拉黑再删（删除自动清黑名单）
        temp_graph.add_to_blacklist(5)
        # 此时用户已删，再次删除会返回False,黑名单自动清理
        assert temp_graph.is_in_blacklist(5) is False
        # 删除不存在用户、负数用户均返回 False
        assert temp_graph.delete_user(INVALID_UID) is False
        assert temp_graph.delete_user(NEGATIVE_UID) is False
        print("✅ test_delete_user_full_clean：用户全维度删除清理完成")


# 测试分组 3：核心图算法 + 推荐系统 + 社群分析
class TestCoreAlgorithmAndRecommend:
    """核心算法和推荐功能测试"""

    def test_bfs_unweighted_shortest_path(self, graph):
        """BFS 无权图最短路径计算：可达节点、自身节点、边界全覆盖"""
        #正常路径测试
        #用户1到5：1->2->5(距离2）
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == 2
        assert path == [1, 2, 5]
        #用户1到10：1->6->7->10(距离3）
        dist_10, _ = graph.get_shortest_distance(1, 10)
        assert dist_10 == 3
        #自身路径测试
        # 起点终点为同一人，距离 0，路径仅自身
        d_self, p_self = graph.get_shortest_distance(5, 5)
        assert d_self == 0 and p_self == [5]
        print("✅ test_bfs_unweighted_shortest_path：BFS 无权最短路径计算正常")

    def test_dijkstra_weighted_shortest_path(self, graph):
        """Dijkstra 算法加权最短路径求解"""
        #加权模式下，路径权重和=边权重和
        total_weight, path = graph.get_weighted_shortest_path(1, 5)
        assert total_weight == 2
        assert path[0] == 1 and path[-1] == 5
        #自身路径权重为0
        w_self, _ = graph.get_weighted_shortest_path(3, 3)
        assert w_self == 0
        print("✅ test_dijkstra_weighted_shortest_path：Dijkstra 带权路径计算无误")

    def test_second_degree_friend_with_path(self, graph):
        """二度人脉查询，携带完整跳转路径；双排序策略校验 + 非法参数降级容错
        对应任务书功能4：二度人脉发现，支持展示连接路径
        对应扩展功能B：多策略切换（按权重排序、按兴趣排序）
        """
        print_test_title("测试二度人脉两种排序策略")

        # 策略1：兴趣排序 interest
        res_interest = graph.find_second_degree_with_path(1, sort_strategy="interest")
        assert len(res_interest) > 0
        for item in res_interest:
            #（二度用户ID，最优中间好友ID，完整路径）
            assert len(item) == 3
            uid, mid_uid, path_arr = item
            assert path_arr[0] == 1
            #路径长度为3：【起点，中间人，二度好友】
            assert len(path_arr) == 3

        # 策略2：权重排序 weight
        res_weight = graph.find_second_degree_with_path(1, sort_strategy="weight")
        assert len(res_weight) > 0

        # 非法排序字段 → 自动降级为 "weight"
        #对应任务书“支持多策略切换，非法值需有降级处理”
        res_wrong = graph.find_second_degree_with_path(1, sort_strategy="id")
        assert isinstance(res_wrong, list)
        assert len(res_wrong) > 0

        # 降级后与 weight 结果一致（证明降级逻辑正确）
        res_wrong = graph.find_second_degree_with_path(1, sort_strategy="id")
        res_weight = graph.find_second_degree_with_path(1, sort_strategy="weight")
        assert len(res_wrong) == len(res_weight)

        print("✅ test_second_degree_friend_with_path：双排序策略、非法参数降级容错校验完成")

    def test_n_degree_unified_api(self, graph):
        """通用 N 度人脉统一接口容错校验：正整数、0、负数度数区分处理
        对应扩展功能A：多度人脉查询（N>=3)
        对应基础功能3/4：一度/二度人脉查询
        """
        # 一度好友查询
        one_deg = graph.find_n_degree_friends(1, 1)
        assert len(one_deg) == 3
        assert set(one_deg) == {2, 3, 6}
        # 二度好友查询
        two_deg = graph.find_n_degree_friends(1, 2)
        assert len(two_deg) > 0
        # 非法度数 <= 0 返回空列表（异常处理）
        assert graph.find_n_degree_friends(1, 0) == []
        assert graph.find_n_degree_friends(1, -3) == []
        print("✅ test_n_degree_unified_api：N 度人脉通用接口运行正常")

    def test_interest_based_recommend_sort(self, graph):
        """基于兴趣相似度好友推荐：按共同兴趣数量降序排列；排除自身与现有好友
        对应扩展功能C：基于兴趣的智能推荐
        对应任务书“支持推荐理由展示”要求（返回共同兴趣列表）
        """
        rec_list = graph.recommend_friends_by_interest(1, top_n=3)
        assert len(rec_list) <= 3
        score_prev = 999
        for uid, name, score, inter_list in rec_list:
            # 过滤自己和现有好友（不应出现在推荐列表中）
            assert uid not in {1, 2, 3, 6}, "推荐列表不能出现自身和已添加好友"
            #共同兴趣数量与列表长度一致
            assert score == len(inter_list)
            # 推荐结果严格降序排序（评分高的在前）
            assert score <= score_prev
            score_prev = score
        print("✅ test_interest_based_recommend_sort：兴趣推荐规则、降序排序校验通过")

    def test_hash_table_interest_index(self):
        """测试兴趣反向索引哈希表存取、新增、删除逻辑
        对应扩展功能C：兴趣索引是推荐功能的核心数据结构
        """
        temp_g = build_memory_graph_data()
        hash_index = temp_g.interest_index
        #确认使用的是自研哈希表
        assert isinstance(hash_index, HashTable)
        #查询测试
        travel_list = hash_index.get("旅行") or []
        assert sorted(travel_list) == [2, 5, 8]
        # 新增用户索引更新
        temp_g.add_user(11, "测试", ["徒步", "编程"])
        code_list = hash_index.get("编程") or []
        assert 11 in code_list
        # 不存在爱好默认返回空列表
        ski_list = hash_index.get("滑雪") or []
        assert ski_list == []
        print("✅ test_hash_table_interest_index：兴趣哈希表增、查、缺省逻辑校验通过")

    def test_heap_recommend_topk(self, graph):
        """测试推荐功能底层小根堆 TopK 排序逻辑：降序输出、数量限制生效
        对应扩展功能C：采用Top-K推荐算法
        """
        rec_result = graph.recommend_friends_by_interest(1, top_n=4)
        scores = [item[2] for item in rec_result]
        sorted_score = sorted(scores, reverse=True)
        #返回结果应已是降序排列
        assert scores == sorted_score
        #数量不超过top_n限制
        assert len(rec_result) <= 4
        print("✅ test_heap_recommend_topk：堆实现 TopK 推荐降序排序、数量限制有效")

    def test_mix_weight_recommend(self, graph):
        """兴趣 + 社交亲密度混合加权推荐
        对应扩展功能B：加群图与优先推荐 + 扩展功能C：兴趣推荐
        组合推荐评分=共同兴趣数 x 0.6 + 亲密度均值 x 0.4
        """
        mix_rec = graph.recommend_friends_weight_mix(1, top_n=4)
        assert len(mix_rec) <= 4
        for uid, name, score, inters in mix_rec:
            # 得分可以是整数、浮点数都允许（混合加权结果）
            assert isinstance(score, (int, float))
            #排除自身和直接好友
            assert uid not in {1, 2, 3, 6}
        print("✅ test_mix_weight_recommend：混合加权推荐正常返回")

    def test_degree_centrality_desc_sort(self, graph):
        """度中心性计算，好友数量降序排序；校验最大节点度数
        功能说明：社群分析工具，识别社交网络中的关键人物
        """
        rank_result = graph.calc_degree_centrality()
        # 验证排序：好友数量严格排序
        prev_count = 999
        for uid, count, name in rank_result:
            assert count <= prev_count
            prev_count = count
        # 验证最大度数的用户
        top_user = rank_result[0]
        # 用户3 有最多的好友：1,2,4,6,8 = 5个（对应测试数据）
        assert top_user[1] == 5
        assert top_user[0] == 3
        print("✅ test_degree_centrality_desc_sort：度中心性降序排列正确")

    def test_find_all_communities(self, graph):
        """连通分量划分：所有独立社群都被正确识别
        功能说明：用于分析社交网络的群体结构
        """
        communities = graph.find_all_communities()
        # 测试数据中所有用户都连通，应只有一个社群
        assert len(communities) == 1
        # 验证包含所有用户(无遗漏）
        all_users = set()
        for comm in communities:
            all_users.update(comm)
        expected_users = set(range(1, 11))
        assert all_users == expected_users
        print("✅ test_find_all_communities：连通社群划分正确")


# ==============================================================
# ===================== 【新增测试分组：数据导出功能测试】 =====================
#对应任务书建议提交项：性能测试报告、用户操作手册的数据导出功能
class TestDataExportFeature:
    """数据导出功能测试
    用于生成社交网络数据的文本快照，便于分析和文档展示
    """

    def test_export_adjacency_list(self, graph, tmp_path):
        """测试导出标准邻接表"""
        print_test_title("测试标准邻接表导出")

        output_file = tmp_path / "export_adjacency_list.txt"

        #执行导出
        result = graph.export_adjacency_list(str(output_file))
        assert result is True
        assert output_file.exists()

        #验证导出的文件格式正确
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"\n📄 标准邻接表内容:\n{content}")

            # 验证格式：每行至少包含用户ID
            for line in content.strip().split("\n"):
                parts = line.split()
                assert len(parts) >= 1
                assert int(parts[0]) > 0

        print(f"\n📂 文件位置: {output_file}")

    def test_export_adjacency_table_text(self, graph, tmp_path):
        """测试导出纯文本带边框表格"""
        print_test_title("测试纯文本表格导出")

        output_file = tmp_path / "export_adj_table.txt"

        #执行导出
        result = graph.export_adjacency_table_text(str(output_file))
        assert result is True
        assert output_file.exists()

        #验证导出的文件格式正确
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"\n📄 纯文本表格内容:\n{content}")

            # 验证表头
            assert "用户ID" in content
            assert "姓名" in content
            assert "好友列表" in content

            # 验证边框
            assert "+" in content
            assert "-" in content
            assert "|" in content

            # 验证数据内容
            assert "张三" in content
            assert "2(李四)" in content

        print(f"\n📂 文件位置: {output_file}")


# ==============================================================
# ===================== 黑名单功能测试 =====================
class TestBlacklistFeatures:
    """黑名单功能测试"""

    def test_blacklist_basic_operations(self, graph):
        """黑名单基本操作测试"""
        # 添加黑名单
        assert graph.add_to_blacklist(2) is True
        assert graph.is_in_blacklist(2) is True

        # 再次添加同一个用户
        assert graph.add_to_blacklist(2) is True

        # 添加不存在的用户返回Fasle
        assert graph.add_to_blacklist(999) is False

        # 移除黑名单
        assert graph.remove_from_blacklist(2) is True
        assert graph.is_in_blacklist(2) is False

        # 移除不存在的用户返回False
        assert graph.remove_from_blacklist(999) is False

        # 清空黑名单
        graph.add_to_blacklist(3)
        graph.add_to_blacklist(4)
        graph.clear_blacklist()
        assert graph.is_in_blacklist(3) is False
        assert graph.is_in_blacklist(4) is False

        print("✅ test_blacklist_basic_operations：黑名单基本操作验证通过")

    def test_blacklist_affects_friend_list(self, graph):
        """验证黑名单影响好友列表"""
        # 用户1的好友包含2
        assert 2 in graph.get_direct_friends(1)

        # 将2加入黑名单
        graph.add_to_blacklist(2)

        # 用户1的好友列表中不应包含2
        assert 2 not in graph.get_direct_friends(1)

        # 但是直接通过graph获取仍包含2（只是被过滤）
        friend_set = graph.graph.get(1)
        assert 2 in friend_set

        print("✅ test_blacklist_affects_friend_list：黑名单影响好友列表验证通过")

    def test_blacklist_affects_shortest_path(self, graph):
        """验证黑名单影响最短路径"""
        # 正常路径：1-2-5(距离是2）
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == 2
        assert path == [1, 2, 5]

        # 将2加入黑名单（阻塞直接路径）
        graph.add_to_blacklist(2)

        # 阻塞替代路径：1-3-... 和 1-6-9-5
        # 将3加入黑名单（阻塞经过3的所有路径）
        graph.add_to_blacklist(3)
        # 将6加入黑名单（阻塞经过6的路径：1-6-9-5）
        graph.add_to_blacklist(6)

        # 现在1的好友中，2和3都被阻塞，只剩下6也被阻塞
        # 所以1无法到达任何有效好友，路径被完全阻塞
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == -1
        assert path == []

        print("✅ test_blacklist_affects_shortest_path：黑名单影响最短路径验证通过")


# ==============================================================
# ===================== 大数据量测试 =====================
class TestLargeData:
    """大数据量测试"""

    def test_generate_big_data(self):
        """测试大数据生成功能"""
        graph = SocialGraph()
        graph.generate_big_test_data(user_num=100, edge_num=200)

        #验证数据量正确
        assert graph.get_total_user() == 100
        assert graph.get_total_relation() == 200

        # 测试性能
        graph.run_performance_test(test_center_id=1)

        print("✅ test_generate_big_data：大数据生成和性能测试完成")

    def test_recommendation_on_large_data(self):
        """测试大数据上的推荐功能"""
        graph = SocialGraph()
        graph.generate_big_test_data(user_num=500, edge_num=1000)

        # 随机选择一个用户进行推荐
        import random
        uid = random.randint(1, 500)

        rec_result = graph.recommend_friends_by_interest(uid, top_n=10)
        assert len(rec_result) <= 10

        print("✅ test_recommendation_on_large_data：大数据推荐功能测试完成")


# ==============================================================
# ===================== 边界条件测试 =====================
class TestEdgeCases:
    """边界条件测试
    对应任务书：需处理用户ID不存在、同一用户等异常场景
    """

    def test_empty_graph_operations(self, empty_graph):
        """空图操作测试
        验证没有任何数据时，所有操作都能正常返回而不崩溃
        """
        #空图统计为0
        assert empty_graph.get_total_user() == 0
        assert empty_graph.get_total_relation() == 0
        #查询不存在的用户返回空列表或默认值
        assert empty_graph.get_direct_friends(1) == []
        assert empty_graph.get_user_info(1) == {"name": "未知用户", "interests": []}
        assert empty_graph.find_n_degree_friends(1, 1) == []

        # 删除不存在的用户返回False
        assert empty_graph.delete_user(1) is False

        # 删除不存在的好友关系返回False
        assert empty_graph.delete_friendship(1, 2) is False

        # 添加用户
        assert empty_graph.add_user(1, "测试", ["编程"]) is True
        assert empty_graph.get_total_user() == 1

        print("✅ test_empty_graph_operations：空图操作测试通过")

    def test_invalid_user_operations(self, graph):
        """无效用户操作测试"""
        # 添加已存在的用户返回Flase
        assert graph.add_user(1, "重复", ["测试"]) is False

        # 添加无效ID抛出ValueError
        with pytest.raises(ValueError):
            graph.add_user(0, "无效", ["测试"])

        with pytest.raises(ValueError):
            graph.add_user(-1, "无效", ["测试"])

        # 添加自好友抛出ValueError
        with pytest.raises(ValueError):
            graph.add_friendship(1, 1, 1)

        # 添加不存在的好友抛出ValueError
        with pytest.raises(ValueError):
            graph.add_friendship(1, 999, 1)

        print("✅ test_invalid_user_operations：无效用户操作测试通过")

    def test_path_to_blacklisted_user(self, graph):
        """测试目标在黑名单中的路径查询"""
        # 将5加入黑名单
        graph.add_to_blacklist(5)

        # BFS查询到5的路径应返回不可达
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == -1
        assert path == []

        # Dijkstra查询也应返回不可达
        dist, path = graph.get_weighted_shortest_path(1, 5)
        assert dist == -1
        assert path == []

        print("✅ test_path_to_blacklisted_user：黑名单用户路径查询测试通过")


# ==============================================================
# ===================== 性能测试 =====================
class TestPerformance:
    """性能测试
    对应扩展功能D：性能优化，验证算法在大数据下的执行效率
    """

    def test_performance_benchmark(self):
        """性能基准测试
        在200用户、500边规模下测试各算法耗时
        """
        graph = SocialGraph()
        graph.generate_big_test_data(user_num=200, edge_num=500)

        import time

        # 测试BFS性能
        start = time.perf_counter()
        graph.get_shortest_distance(1, 100)
        bfs_time = time.perf_counter() - start

        # 测试Dijkstra性能
        start = time.perf_counter()
        graph.get_weighted_shortest_path(1, 100)
        dijkstra_time = time.perf_counter() - start

        # 测试推荐性能
        start = time.perf_counter()
        graph.recommend_friends_by_interest(1, top_n=10)
        recommend_time = time.perf_counter() - start

        print(f"📊 性能测试结果:")
        print(f"  BFS耗时: {bfs_time:.4f}s")
        print(f"  Dijkstra耗时: {dijkstra_time:.4f}s")
        print(f"  推荐耗时: {recommend_time:.4f}s")

        # 基本性能断言（时间不应该太长）
        assert bfs_time < 1.0
        assert dijkstra_time < 1.0
        assert recommend_time < 1.0

        print("✅ test_performance_benchmark：性能基准测试通过")


# ==============================================================
# ===================== 数据一致性测试 =====================
#验证图结构在各种操作后保持数据一致性
class TestDataConsistency:
    """数据一致性测试"""

    def test_edge_weight_consistency(self, graph):
        """边权重一致性测试
        验证添加、更新、删除边权重数据同步
        """

        # 添加边时应更新权重
        if graph.user_attrs.get(11) is None:
            graph.add_user(11, "测试用户", ["测试"])

        # 添加边时应更新权重
        graph.add_friendship(1, 11, weight=5)

        edge_key = (1, 11)
        assert graph.edge_weights[edge_key] == 5

        # 更新权重
        graph.add_friendship(1, 11, weight=10)
        assert graph.edge_weights[edge_key] == 10

        # 删除边时权重也应删除
        graph.delete_friendship(1, 11)
        assert graph.edge_weights.get(edge_key) is None

        print("✅ test_edge_weight_consistency：边权重一致性测试通过")

    def test_interest_index_consistency(self, graph):
        """兴趣索引一致性测试"""
        # 添加用户时索引应更新
        graph.add_user(11, "测试用户", ["编程", "测试"])
        assert 11 in graph.interest_index.get("编程")
        assert 11 in graph.interest_index.get("测试")

        # 删除用户时索引应清理
        graph.delete_user(11)
        assert 11 not in (graph.interest_index.get("编程") or [])
        assert 11 not in (graph.interest_index.get("测试") or [])

        # 空兴趣标签应被清理
        assert "测试" not in graph.interest_index

        print("✅ test_interest_index_consistency：兴趣索引一致性测试通过")