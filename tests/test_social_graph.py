import pytest
import os
import sys
from typing import List, Tuple, Dict, Any

# ===================== 路径导入配置 =====================
# 修复src模块导入，将项目根目录加入系统环境变量
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 导入自研数据结构与社交图谱核心类
from src.social_graph import SocialGraph, HashTable, MinHeap

# ===================== 全局可配置开关 =====================
# True：读取data目录csv/txt外部文件；False：内存内置生成测试数据（无需文件）
USE_DATA_FILE: bool = False
# 通用测试常量
MAX_TEST_USER_NUM = 10
INVALID_UID = 999
SELF_UID_ERR = 1

# ===================== 通用工具函数（封装重复逻辑） =====================
def print_test_title(title: str) -> None:
    """打印分段测试标题，控制台区分模块"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

# ===================== 测试数据构造函数 =====================
def build_memory_graph_data() -> SocialGraph:
    """
    内存离线构造社交网络数据集
    完全等价于csv/txt文件数据，无需依赖外部磁盘文件
    """
    g = SocialGraph()
    # 用户元组：(用户ID, 姓名, 兴趣爱好列表)
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

    # 无向好友边，默认边权重统一为1
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
    """从项目data文件夹读取用户、好友关系文本文件初始化图谱"""
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
@pytest.fixture(scope="module")
def graph() -> SocialGraph:
    """
    模块级全局图谱夹具：整个测试套件只初始化1次图谱实例
    测试全部执行完毕后自动清空黑名单，消除测试用例间数据污染
    """
    print_test_title("开始初始化社交图谱全局实例")
    if USE_DATA_FILE:
        graph_ins = load_file_graph()
    else:
        graph_ins = build_memory_graph_data()

    yield graph_ins

    # 后置清理钩子
    graph_ins.clear_blacklist()
    print("\n🧹 全局收尾：黑名单已全部清空，测试环境重置完成")

@pytest.fixture(scope="function")
def empty_graph() -> SocialGraph:
    """函数级空图谱夹具：每个边界测试用例单独生成空白图，互不干扰"""
    return SocialGraph()

# ===================== 测试分组0：自研基础数据结构单元测试（哈希表 + 小顶堆） =====================
class TestSelfDataStructure:
    """分类：自研底层数据结构单元测试"""
    def test_hash_table_all_interface(self):
        """测试链地址法哈希表：增、查、改、删、包含判断全接口"""
        ht = HashTable(capacity=20)
        # 新增键值对
        ht.put(1, {"name": "张三"})
        ht.put(5, {"name": "李四"})

        # 取值校验
        assert ht.get(1)["name"] == "张三", "哈希表取值错误"
        assert ht.get(INVALID_UID) is None, "不存在key应当返回None"

        # key覆盖更新
        ht.put(1, {"name": "张三三"})
        assert ht.get(1)["name"] == "张三三", "哈希表更新覆盖失效"

        # __contains__ 成员运算符校验
        assert 1 in ht
        assert INVALID_UID not in ht

        # 删除操作
        assert ht.remove(5) is True, "存在key删除应当返回True"
        assert ht.get(5) is None
        assert ht.remove(INVALID_UID) is False, "删除不存在key返回False"

    def test_min_heap_push_pop_order(self):
        """测试小顶堆：入堆、堆化上浮下沉、顺序弹出、空堆容错"""
        heap = MinHeap()
        # 乱序插入(权重, 携带数据)
        heap.push(5, "C")
        heap.push(2, "A")
        heap.push(7, "D")
        heap.push(1, "B")

        # 严格从小到大弹出最小值
        assert heap.pop() == (1, "B")
        assert heap.pop() == (2, "A")
        assert heap.pop() == (5, "C")
        assert heap.pop() == (7, "D")

        # 空堆弹出返回None，堆大小归零
        assert heap.pop() is None
        assert heap.size() == 0

# ===================== 测试分组1：数据加载、基础信息、索引校验 =====================
class TestGraphBasicLoadInfo:
    """分类：图谱初始化加载、用户信息、邻接表、兴趣反向索引校验"""
    def test_all_users_loaded_correctly(self, graph):
        """校验10位用户完整导入，无丢失"""
        print_test_title("校验全体用户加载完整性")
        uid_list = list(range(1, MAX_TEST_USER_NUM + 1))
        for uid in uid_list:
            user_info = graph.get_user_info(uid)
            assert user_info["name"] != "未知用户", f"用户ID:{uid} 加载缺失"
        # 兴趣反向索引已构建
        assert len(graph.interest_index) > 0, "兴趣反向索引为空，构建失败"

    def test_user_detail_attribute(self, graph):
        """校验用户姓名、兴趣列表字段精准匹配"""
        user1 = graph.get_user_info(1)
        assert user1["name"] == "张三"
        assert set(user1["interests"]) == {"编程", "篮球", "摄影"}

        user10 = graph.get_user_info(10)
        assert user10["name"] == "王十二"
        assert set(user10["interests"]) == {"阅读", "绘画", "篮球"}

    def test_direct_friend_adjacent_list(self, graph):
        """校验一度好友邻接表无向关系数据准确"""
        assert set(graph.get_direct_friends(1)) == {2, 3, 6}
        assert set(graph.get_direct_friends(3)) == {1, 2, 4, 6, 8}
        assert set(graph.get_direct_friends(7)) == {4, 5, 6, 8, 10}

    def test_interest_reverse_index(self, graph):
        """兴趣反向索引：查询爱好对应的所有用户ID"""
        code_lover = sorted(graph.interest_index["编程"])
        assert code_lover == [1, 3, 6, 9]

        travel_lover = sorted(graph.interest_index["旅行"])
        assert travel_lover == [2, 5, 8]

# ===================== 测试分组2：用户、好友增删改基础接口 =====================
class TestUserFriendOperate:
    """分类：用户新增删除、好友添加解除、边权重管理"""
    def test_add_repeat_friend(self, graph):
        """重复添加同一好友，无冗余边，无报错"""
        # 原本已是好友
        assert 2 in graph.get_direct_friends(1)
        # 重复添加
        res = graph.add_friendship(1, 2, weight=1)
        # 可自定义返回规则：已存在好友返回True/False均可，这里校验边不会重复存储
        friend_list = graph.get_direct_friends(1)
        assert friend_list.count(2) == 1

    def test_modify_edge_weight(self, graph):
        """修改好友之间边的权重，Dijkstra路径权重同步更新"""
        graph.add_friendship(1, 2, weight=5)
        total_w, _ = graph.get_weighted_shortest_path(1, 5)
        # 路径1-2-5 权重总和 5+1=6
        assert total_w == 6

    def test_delete_friendship_bidirectional(self, graph):
        """双向删除好友关系：双方邻接表、边权重字典同步清除"""
        assert 2 in graph.get_direct_friends(1)
        edge_key = tuple(sorted((1, 2)))
        assert edge_key in graph.edge_weights

        # 执行删除
        delete_res = graph.delete_friendship(1, 2)
        assert delete_res is True
        assert 2 not in graph.get_direct_friends(1)
        assert 1 not in graph.get_direct_friends(2)
        assert edge_key not in graph.edge_weights

        # 重复删除、无效用户删除均返回False
        assert graph.delete_friendship(1, 2) is False
        assert graph.delete_friendship(INVALID_UID, 1) is False

    def test_delete_user_full_clean(self):
        """彻底删除用户：好友连线、用户属性、兴趣索引、黑名单全部清理"""
        temp_graph = build_memory_graph_data()
        # 删除用户5
        del_success = temp_graph.delete_user(5)
        assert del_success is True

        # 用户哈希表移除
        assert temp_graph.user_attrs.get(5) is None
        # 所有好友列表不再包含该用户
        assert 5 not in temp_graph.get_direct_friends(2)
        # 兴趣索引剔除用户ID
        assert 5 not in temp_graph.interest_index["旅行"]

        # 黑名单绑定用户一并清除
        temp_graph.add_to_blacklist(5)
        temp_graph.delete_user(5)
        assert not temp_graph.is_in_blacklist(5)

        # 删除不存在用户返回False
        assert temp_graph.delete_user(INVALID_UID) is False

# ===================== 测试分组3：核心算法 + 推荐系统 + 社群分析 =====================
class TestCoreAlgorithmAndRecommend:
    """分类：最短路径、N度人脉、好友推荐、度中心性、连通社群划分"""
    def test_bfs_unweighted_shortest_path(self, graph):
        """BFS无权图最短路径计算"""
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == 2
        assert path == [1, 2, 5]

        dist_10, _ = graph.get_shortest_distance(1, 10)
        assert dist_10 == 3

        # 起点终点为同一人，距离0，路径仅自身
        d_self, p_self = graph.get_shortest_distance(5, 5)
        assert d_self == 0 and p_self == [5]

    def test_dijkstra_weighted_shortest_path(self, graph):
        """Dijkstra算法加权最短路径求解"""
        total_weight, path = graph.get_weighted_shortest_path(1, 5)
        assert total_weight == 2
        assert path[0] == 1 and path[-1] == 5

        w_self, _ = graph.get_weighted_shortest_path(3, 3)
        assert w_self == 0

    def test_second_degree_friend_with_path(self, graph):
        """二度人脉查询，携带完整跳转路径"""
        second_friends = graph.find_second_degree_with_path(1)
        assert len(second_friends) > 0
        for item in second_friends:
            assert len(item) == 3
            uid, mid_uid, path_arr = item
            assert path_arr[0] == 1
            assert len(path_arr) == 3

    def test_n_degree_unified_api(self, graph):
        """通用N度人脉统一接口容错校验"""
        # 一度好友
        one_deg = graph.find_n_degree_friends(1, degree=1)
        assert len(one_deg) == 3
        assert set(one_deg) == {2, 3, 6}

        # 二度好友
        two_deg = graph.find_n_degree_friends(1, degree=2)
        assert len(two_deg) > 0

        # 非法度数 <= 0 返回空列表
        assert graph.find_n_degree_friends(1, 0) == []
        assert graph.find_n_degree_friends(1, -3) == []

    def test_interest_based_recommend_sort(self, graph):
        """基于兴趣相似度好友推荐：按共同兴趣数量降序排列"""
        rec_list = graph.recommend_friends_by_interest(1, top_n=3)
        assert len(rec_list) <= 3
        score_prev = 999
        for uid, name, score, inter_list in rec_list:
            # 过滤自己和现有好友
            assert uid not in {1, 2, 3, 6}
            assert score == len(inter_list)
            # 推荐结果降序排序
            assert score <= score_prev
            score_prev = score

    def test_mix_weight_recommend(self, graph):
        """兴趣+社交亲密度混合加权推荐"""
        mix_rec = graph.recommend_friends_weight_mix(1, top_n=4)
        assert len(mix_rec) <= 4
        for uid, name, score, inters in mix_rec:
            assert isinstance(score, float)
            assert uid not in {1, 2, 3, 6}

    def test_degree_centrality_desc_sort(self, graph):
        """度中心性计算，好友数量降序排序"""
        rank_result = graph.calc_degree_centrality()
        assert len(rank_result) == 10
        prev_num = 999
        for _, friend_cnt, _ in rank_result:
            assert friend_cnt <= prev_num
            prev_num = friend_cnt
        # 好友最多用户为3号、7号，均为5个好友
        top_counts = [item[1] for item in rank_result[:2]]
        assert 5 in top_counts

    def test_connected_component_community(self, graph, empty_graph):
        """连通分量社群划分：完整大图单社群；空图无社群；单点用户独立社群"""
        # 完整整张图连通，仅1个社群
        communities = graph.find_all_communities()
        assert len(communities) == 1
        assert sorted(communities[0]) == list(range(1, 11))

        # 空图谱社群为空
        assert empty_graph.find_all_communities() == []

        # 单个用户自成社群
        empty_graph.add_user(100, "测试用户", [])
        single_comm = empty_graph.find_all_communities()
        assert len(single_comm) == 1
        assert single_comm[0] == [100]

# ===================== 测试分组4：边界异常输入 + 黑名单全链路拦截测试 =====================
class TestBoundaryExceptionBlacklist:
    """分类：非法参数容错、黑名单增删查改+全算法拦截校验"""
    def test_abnormal_input_fault_tolerant(self, graph, empty_graph):
        """各类非法入参异常捕获与容错"""
        # 不存在用户信息查询返回默认未知用户
        unknown_user = graph.get_user_info(INVALID_UID)
        assert unknown_user["name"] == "未知用户"
        assert len(unknown_user["interests"]) == 0

        # 无效用户好友列表为空
        assert graph.get_direct_friends(INVALID_UID) == []

        # 推荐数量超出总用户数，返回全部候选
        all_rec = graph.recommend_friends_by_interest(1, top_n=200)
        assert isinstance(all_rec, list)

        # 自己不能添加自己为好友，抛出ValueError
        with pytest.raises(ValueError):
            graph.add_friendship(SELF_UID_ERR, SELF_UID_ERR)

        # 负ID创建用户非法
        with pytest.raises(ValueError):
            graph.add_user(-10, "负数ID", ["追剧"])

        # 空图谱运行所有算法不崩溃
        empty_graph.get_shortest_distance(1, 2)
        empty_graph.calc_degree_centrality()
        empty_graph.recommend_friends_by_interest(1, 5)

    def test_blacklist_full_intercept_all_func(self, graph):
        """黑名单完整场景：添加、移除、清空；所有算法均拦截黑名单用户"""
        # 1. 拉黑不存在用户返回False
        assert graph.add_to_blacklist(INVALID_UID) is False

        # 2. 正常拉黑有效用户5
        assert graph.add_to_blacklist(5) is True
        assert graph.is_in_blacklist(5) is True
        # 重复添加黑名单允许，返回True
        assert graph.add_to_blacklist(5) is True

        # 3. 好友列表自动屏蔽黑名单用户
        assert 5 not in graph.get_direct_friends(2)

        # 4. BFS最短路径无法抵达黑名单节点，距离返回-1
        dist_bfs, _ = graph.get_shortest_distance(1, 5)
        assert dist_bfs == -1

        # 5. Dijkstra加权路径同样不可达
        dist_dijk, _ = graph.get_weighted_shortest_path(1, 5)
        assert dist_dijk == -1

        # 6. 二度人脉、N度人脉全部过滤黑名单人员
        second_uid_list = [item[0] for item in graph.find_second_degree_with_path(1)]
        assert 5 not in second_uid_list
        n2_friends = graph.find_n_degree_friends(1, 2)
        assert 5 not in n2_friends

        # 7. 推荐好友结果不会出现黑名单用户
        rec_data = graph.recommend_friends_by_interest(1, top_n=5)
        rec_uids = [item[0] for item in rec_data]
        assert 5 not in rec_uids

        # 8. 移出黑名单恢复访问
        assert graph.remove_from_blacklist(5) is True
        assert graph.is_in_blacklist(5) is False
        assert graph.remove_from_blacklist(5) is False

        dist_recover, _ = graph.get_shortest_distance(1, 5)
        assert dist_recover == 2

        # 9. 批量拉黑后一键清空黑名单
        graph.add_to_blacklist(3)
        graph.add_to_blacklist(7)
        graph.clear_blacklist()
        assert len(graph.blacklist) == 0