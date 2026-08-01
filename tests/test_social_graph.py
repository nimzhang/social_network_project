import pytest
import os
import sys
from typing import List, Tuple, Dict, Any

# ===================== 路径导入配置 =====================
# 修复src模块导入，将项目根目录加入环境变量
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 导入自研底层数据结构 + 社交图谱核心类
from src.social_graph import SocialGraph, HashTable, MinHeap

# ===================== 全局常量统一管理 =====================
MAX_TEST_USER_NUM: int = 10
INVALID_UID: int = 999
SELF_UID_ERR: int = 1
MIN_VALID_UID: int = 1
# 数据源切换开关：True读取csv/txt文件，False加载内存内置数据
USE_DATA_FILE: bool = False

# ===================== 通用工具函数 =====================
def print_test_title(title: str) -> None:
    """打印模块分割标题，区分不同测试板块"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

# ===================== 测试数据构造函数 =====================
def build_memory_graph_data() -> SocialGraph:
    """内存离线构造标准社交数据集，与外部文件数据完全一致"""
    g = SocialGraph()
    # 用户信息：(用户ID, 姓名, 兴趣列表)
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

    # 无向好友边，所有边默认权重=1
    edge_list = [
        (1, 2), (1, 3), (1, 6), (2, 3), (2, 5),
        (3, 4), (3, 6), (4, 7), (4, 8), (5, 7),
        (5, 9), (6, 9), (7, 8), (7, 10), (8, 10),
        (9, 10), (2, 9), (3, 8), (5, 10), (6, 7)
    ]
    for u, v in edge_list:
        g.add_friendship(u, v, weight=1)

    print("✅ 初始化完成：内存内置标准数据集加载完毕")
    return g


def load_file_graph() -> SocialGraph:
    """读取data目录下csv、txt文件构建图谱"""
    g = SocialGraph()
    user_csv_path = os.path.join(BASE_DIR, "data", "users.csv")
    rel_txt_path = os.path.join(BASE_DIR, "data", "relationships.txt")

    print(f"\n📂 用户数据文件路径：{user_csv_path}")
    print(f"📂 好友关系文件路径：{rel_txt_path}")

    # 校验文件是否存在
    if not os.path.exists(user_csv_path):
        raise FileNotFoundError(f"用户文件缺失：{user_csv_path}")
    if not os.path.exists(rel_txt_path):
        raise FileNotFoundError(f"好友关系文件缺失：{rel_txt_path}")

    # 解析文件数据
    load_user_ok = g.load_users_from_csv(user_csv_path)
    load_rel_ok = g.load_relationships_from_txt(rel_txt_path)

    if not load_user_ok:
        raise RuntimeError("users.csv解析失败，请检查文件格式、编码")
    if not load_rel_ok:
        raise RuntimeError("relationships.txt解析失败，请检查边数据格式")

    print("✅ 初始化完成：外部文件数据集加载完毕")
    return g

# ===================== Pytest 夹具配置 =====================
@pytest.fixture(scope="module")
def graph() -> SocialGraph:
    """
    模块级夹具：全局共用一张完整社交图谱
    整个测试套件仅初始化1次，所有用例执行结束后清空黑名单，避免数据污染
    """
    print_test_title("开始初始化全局社交图谱实例")
    if USE_DATA_FILE:
        graph_ins = load_file_graph()
    else:
        graph_ins = build_memory_graph_data()

    yield graph_ins

    # 后置清理：重置黑名单，恢复初始环境
    graph_ins.clear_blacklist()
    print("\n🧹 全局收尾：黑名单已清空，测试环境重置完成")


@pytest.fixture(scope="function")
def empty_graph() -> SocialGraph:
    """
    函数级空图谱夹具：每个边界测试用例都会生成全新空白图
    用例之间完全隔离，互不干扰
    """
    return SocialGraph()

# ===================== 测试分组0：自研底层数据结构单元测试 =====================
class TestSelfDataStructure:
    """自研哈希表、小顶堆底层功能校验"""
    def test_hash_table_all_interface(self):
        """哈希表：增、查、改、删、成员判断全套接口测试"""
        ht = HashTable(capacity=20)
        # 插入键值对
        ht.put(1, {"name": "张三"})
        ht.put(5, {"name": "李四"})

        # 取值校验
        assert ht.get(1)["name"] == "张三", "哈希表取值异常"
        assert ht.get(INVALID_UID) is None, "不存在键应返回None"

        # 覆盖更新原有key
        ht.put(1, {"name": "张三三"})
        assert ht.get(1)["name"] == "张三三", "哈希表键覆盖更新失效"

        # in 成员运算符校验
        assert 1 in ht
        assert INVALID_UID not in ht

        # 删除元素校验
        assert ht.remove(5) is True, "存在元素删除应返回True"
        assert ht.get(5) is None
        assert ht.remove(INVALID_UID) is False, "删除不存在元素返回False"
        print("✅ test_hash_table_all_interface：自研哈希表全部接口校验通过")

    def test_min_heap_push_pop_order(self):
        """小顶堆基础出入堆、升序弹出、空堆容错测试"""
        heap = MinHeap()
        heap.push(5, "C")
        heap.push(2, "A")
        heap.push(7, "D")
        heap.push(1, "B")

        # 从小到大依次弹出最小值
        assert heap.pop() == (1, "B")
        assert heap.pop() == (2, "A")
        assert heap.pop() == (5, "C")
        assert heap.pop() == (7, "D")

        # 空堆弹出返回None，堆大小归零
        assert heap.pop() is None
        assert heap.size() == 0
        print("✅ test_min_heap_push_pop_order：基础小顶堆排序、空值容错正常")

    def test_min_heap_duplicate_weight(self):
        """补充：权重重复场景下小顶堆排序稳定性测试"""
        heap = MinHeap()
        heap.push(3, "X")
        heap.push(1, "A")
        heap.push(1, "B")
        heap.push(2, "C")

        assert heap.pop() == (1, "A")
        assert heap.pop() == (1, "B")
        assert heap.pop() == (2, "C")
        assert heap.pop() == (3, "X")
        assert heap.size() == 0
        print("✅ test_min_heap_duplicate_weight：重复权重小顶堆排序逻辑正常")

# ===================== 测试分组1：图谱加载、基础信息、索引校验 =====================
class TestGraphBasicLoadInfo:
    """数据集加载、用户信息、邻接表、兴趣反向索引校验"""
    def test_all_users_loaded_correctly(self, graph):
        """校验10个用户全部加载成功，无缺失"""
        print_test_title("校验全体用户加载完整性")
        uid_range = list(range(MIN_VALID_UID, MAX_TEST_USER_NUM + 1))
        for uid in uid_range:
            user_info = graph.get_user_info(uid)
            assert user_info["name"] != "未知用户", f"用户ID:{uid} 加载缺失"
        assert len(graph.interest_index) > 0, "兴趣反向索引未构建"
        print("✅ test_all_users_loaded_correctly：10位用户加载完整，兴趣索引生效")

    def test_user_detail_attribute(self, graph):
        """精准校验指定用户姓名、兴趣列表内容"""
        user1 = graph.get_user_info(1)
        assert user1["name"] == "张三"
        assert set(user1["interests"]) == {"编程", "篮球", "摄影"}

        user10 = graph.get_user_info(10)
        assert user10["name"] == "王十二"
        assert set(user10["interests"]) == {"阅读", "绘画", "篮球"}
        print("✅ test_user_detail_attribute：用户姓名、兴趣信息匹配无误")

    def test_direct_friend_adjacent_list(self, graph):
        """直连好友邻接表数据校验"""
        assert set(graph.get_direct_friends(1)) == {2, 3, 6}
        assert set(graph.get_direct_friends(3)) == {1, 2, 4, 6, 8}
        assert set(graph.get_direct_friends(7)) == {4, 5, 8, 10, 6}
        print("✅ test_direct_friend_adjacent_list：邻接表直连好友数据校验通过")

    def test_interest_reverse_index(self, graph):
        """兴趣->用户反向索引正确性校验"""
        program_user = sorted(graph.interest_index["编程"])
        assert program_user == [1, 3, 6, 9]

        travel_user = sorted(graph.interest_index["旅行"])
        assert travel_user == [2, 5, 8]
        print("✅ test_interest_reverse_index：兴趣反向索引数据完全正确")

    def test_adjacency_list_storage(self, graph):
        """邻接表存储结构、边权重基础校验"""
        adj_table = graph.graph
        assert 2 in adj_table[1]
        assert 6 in adj_table[1]
        assert 1 in adj_table[2]
        assert INVALID_UID not in adj_table

        edge_key = tuple(sorted([1, 2]))
        assert graph.edge_weights[edge_key] == 1
        print("✅ test_adjacency_list_storage：邻接表存边、权重存储正常")

    def test_undirect_graph_bidirectional_edge(self, graph):
        """新增：全局校验无向图双向边一致性，杜绝单向残边"""
        adj_table = graph.graph
        for u in adj_table:
            for v in adj_table[u]:
                assert u in adj_table[v], f"无向边异常：{u}存有{v}好友，{v}未存有{u}"
        print("✅ test_undirect_graph_bidirectional_edge：整张图谱双向好友关系全部合规")

    def test_user_empty_interests(self, empty_graph):
        """新增：无任何兴趣用户兼容性测试，防止索引、推荐崩溃"""
        empty_graph.add_user(99, "无名氏", [])
        # 空兴趣不会写入任意兴趣索引
        for interest in empty_graph.interest_index:
            assert 99 not in empty_graph.interest_index[interest]
        # 无兴趣用户推荐好友返回空列表
        rec_list = empty_graph.recommend_friends_by_interest(99, 3)
        assert rec_list == []
        print("✅ test_user_empty_interests：零兴趣用户适配无异常")

# ===================== 测试分组2：用户、好友增删改、边权重操作 =====================
class TestUserFriendOperate:
    """用户新增删除、好友添加删除、边权重修改全套操作测试"""
    def test_add_repeat_friend(self, graph):
        """重复添加已存在好友，不会生成冗余边"""
        assert 2 in graph.get_direct_friends(1)
        graph.add_friendship(1, 2, weight=1)
        friend_list = graph.get_direct_friends(1)
        assert friend_list.count(2) == 1
        print("✅ test_add_repeat_friend：重复添加好友无冗余边")

    def test_modify_edge_weight(self, graph):
        """修改边权重后，带权最短路径同步更新生效"""
        graph.add_friendship(1, 2, weight=5)
        total_weight, _ = graph.get_weighted_shortest_path(1, 5)
        # 路径1-2-5：权重5+1=6
        assert total_weight == 6
        print("✅ test_modify_edge_weight：权重修改生效，迪杰斯特拉计算同步更新")

    def test_friendship_weight_default_and_illegal(self, empty_graph):
        """新增：边默认权重赋值 + 负数非法权重拦截"""
        # 不传权重默认等于1
        empty_graph.add_friendship(1, 2)
        key = tuple(sorted([1, 2]))
        assert empty_graph.edge_weights[key] == 1

        # 传入负权重抛出ValueError异常
        with pytest.raises(ValueError):
            empty_graph.add_friendship(2, 3, weight=-5)
        print("✅ test_friendship_weight_default_and_illegal：默认权重、负权重校验正常")

    def test_delete_friendship_bidirectional(self, graph):
        """双向删除好友：两边邻接表、权重字典同步移除边"""
        assert 2 in graph.get_direct_friends(1)
        edge_key = tuple(sorted((1, 2)))
        assert edge_key in graph.edge_weights

        delete_result = graph.delete_friendship(1, 2)
        assert delete_result is True
        assert 2 not in graph.get_direct_friends(1)
        assert 1 not in graph.get_direct_friends(2)
        assert edge_key not in graph.edge_weights

        # 重复删除、无效用户删除均返回False
        assert graph.delete_friendship(1, 2) is False
        assert graph.delete_friendship(INVALID_UID, 1) is False
        print("✅ test_delete_friendship_bidirectional：双向好友删除逻辑完整")

    def test_delete_user_full_clean(self):
        """删除用户：好友关系、兴趣索引、黑名单全方位清理"""
        temp_graph = build_memory_graph_data()
        # 删除用户5
        del_ok = temp_graph.delete_user(5)
        assert del_ok is True

        # 用户数据被移除
        assert temp_graph.user_attrs.get(5) is None
        # 所有人好友列表不再包含5
        assert 5 not in temp_graph.get_direct_friends(2)
        # 兴趣索引移除该用户
        assert 5 not in temp_graph.interest_index["旅行"]

        # 已拉黑用户删除后，黑名单同步清除
        temp_graph.add_to_blacklist(5)
        temp_graph.delete_user(5)
        assert not temp_graph.is_in_blacklist(5)

        # 删除不存在用户返回False
        assert temp_graph.delete_user(INVALID_UID) is False
        print("✅ test_delete_user_full_clean：用户全维度数据清理完毕")

# ===================== 测试分组3：核心算法、好友推荐、社群分析 =====================
class TestCoreAlgorithmAndRecommend:
    """最短路径、N度人脉、两套推荐算法、度中心性、连通分量测试"""
    def test_bfs_unweighted_shortest_path(self, graph):
        """BFS无权最短路径计算校验"""
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == 2
        assert path == [1, 2, 5]

        dist10, _ = graph.get_shortest_distance(1, 10)
        assert dist10 == 3

        # 自身到自身距离为0
        self_dist, self_path = graph.get_shortest_distance(5, 5)
        assert self_dist == 0 and self_path == [5]
        print("✅ test_bfs_unweighted_shortest_path：BFS无权最短路径计算正常")

    def test_dijkstra_weighted_shortest_path(self, graph):
        """迪杰斯特拉带权最短路径校验"""
        weight, path = graph.get_weighted_shortest_path(1, 5)
        assert weight == 2
        assert path[0] == 1 and path[-1] == 5

        self_w, _ = graph.get_weighted_shortest_path(3, 3)
        assert self_w == 0
        print("✅ test_dijkstra_weighted_shortest_path：带权最短路径计算无误")

    def test_second_degree_friend_with_path(self, graph):
        """二度人脉查询：返回路径格式、内容合规"""
        second_friends = graph.find_second_degree_friends(1)
        assert len(second_friends) > 0
        for item in second_friends:
            assert len(item) == 3
            uid, mid_uid, path_arr = item
            assert path_arr[0] == 1
            assert len(path_arr) == 3
        print("✅ test_second_degree_friend_with_path：二度人脉查询格式、内容合规")

    def test_n_degree_unified_api(self, graph):
        """通用N度人脉接口容错校验"""
        one_degree = graph.find_n_degree_friends(1, degree=1)
        assert len(one_degree) == 3
        assert set(one_degree) == {2, 3, 6}

        two_degree = graph.find_n_degree_friends(1, degree=2)
        assert len(two_degree) > 0

        # 度数<=0返回空列表
        assert graph.find_n_degree_friends(1, 0) == []
        assert graph.find_n_degree_friends(1, -3) == []
        print("✅ test_n_degree_unified_api：N度人脉通用接口运行正常")

    def test_interest_recommend_sort(self, graph):
        """兴趣相似度推荐：按分数降序排列、数量限制生效"""
        rec_list = graph.recommend_friends_by_interest(1, top_n=3)
        assert len(rec_list) <= 3
        score_last = 999
        for uid, name, score, interests in rec_list:
            assert uid not in {1, 2, 3, 6}
            assert score <= score_last
            score_last = score
        print("✅ test_interest_recommend_sort：兴趣推荐规则、降序排序校验通过")

    def test_hash_table_interest_index(self, empty_graph):
        """兴趣反向索引哈希表增删查综合校验"""
        index = empty_graph.interest_index
        assert sorted(index["音乐"]) == [2, 5, 9]

        empty_graph.add_user(11, "测试用户", ["徒步", "编程"])
        assert 11 in index["编程"]
        assert index.get("滑雪", []) == []
        print("✅ test_hash_table_interest_index：兴趣哈希表存取、缺省值逻辑正常")

    def test_heap_topk_recommend(self, graph):
        """底层小顶堆实现Top-K推荐校验，排序结果一致"""
        rec_result = graph.recommend_friends_by_interest(1, top_n=4)
        scores = [item[2] for item in rec_result]
        sorted_scores = sorted(scores, reverse=True)
        assert scores == sorted_scores
        assert len(rec_result) <= 4
        print("✅ test_heap_topk_recommend：堆实现TopK降序排序、数量限制有效")

    def test_mix_weight_recommend(self, graph):
        """社交+兴趣混合加权推荐校验"""
        mix_rec = graph.recommend_friends_mix_weight(1, top_n=4)
        assert len(mix_rec) <= 4
        for uid, name, score, interests in mix_rec:
            assert isinstance(score, float)
            assert uid not in {1, 2, 3, 6}
        print("✅ test_mix_weight_recommend：混合加权好友推荐功能正常")

    def test_degree_centrality_sort(self, graph):
        """节点度中心性：好友数量降序排序校验"""
        rank_list = graph.calc_degree_centrality()
        assert len(rank_list) == 10
        prev_degree = 999
        for uid, degree, name in rank_list:
            assert degree <= prev_degree
            prev_degree = degree
        # 3号、7号节点好友数最多，度值=5
        top_two_degree = [item[1] for item in rank_list[:2]]
        assert 5 in top_two_degree
        print("✅ test_degree_centrality_sort：节点度值降序排序正确")

    def test_connected_component_community(self, graph, empty_graph):
        """连通分量社群划分：完整图、空图、孤立节点场景全覆盖"""
        # 完整连通图仅有1个社群
        communities = graph.find_connected_components()
        assert len(communities) == 1
        assert sorted(communities[0]) == list(range(1, 11))

        # 空图谱无社群
        assert empty_graph.find_connected_components() == []

        # 单个孤立用户自成社群
        empty_graph.add_user(100, "独居用户", ["追剧"])
        single_comm = empty_graph.find_connected_components()
        assert len(single_comm) == 1
        assert single_comm[0] == [100]
        print("✅ test_connected_component_community：连通社群划分逻辑正常")

# ===================== 测试分组4：边界异常、黑名单全链路拦截 =====================
class TestBoundaryExceptionBlacklist:
    """非法参数容错、黑名单增删清空、全功能拦截校验"""
    def test_abnormal_input_tolerance(self, graph, empty_graph):
        """各类非法入参捕获，程序无崩溃"""
        # 查询不存在用户
        unknown_user = graph.get_user_info(INVALID_UID)
        assert unknown_user["name"] == "未知用户"
        assert len(unknown_user["interests"]) == 0

        # 无效用户好友列表为空
        assert graph.get_direct_friends(INVALID_UID) == []

        # 推荐数量过大，返回所有可选好友
        all_rec = graph.recommend_friends_by_interest(1, top_n=200)
        assert isinstance(all_rec, list)

        # 自己无法添加自己为好友，抛出异常
        with pytest.raises(ValueError):
            graph.add_friendship(SELF_UID_ERR, SELF_UID_ERR)

        # 负ID创建用户非法
        with pytest.raises(ValueError):
            graph.add_user(-10, "负数ID用户", ["追剧"])

        # 空图谱执行全部算法不会报错崩溃
        empty_graph.get_shortest_distance(1, 2)
        empty_graph.calc_degree_centrality()
        empty_graph.recommend_friends_by_interest(1, 5)
        print("✅ test_abnormal_input_tolerance：异常参数容错完备，无程序崩溃")

    def test_empty_graph_all_algorithm_return(self, empty_graph):
        """新增：空图谱所有算法返回值统一规范"""
        dist, _ = empty_graph.get_shortest_distance(1, 2)
        assert dist == -1

        weight, _ = empty_graph.get_weighted_shortest_path(1, 2)
        assert weight == -1

        rec = empty_graph.recommend_friends_by_interest(1, 5)
        assert rec == []

        central_rank = empty_graph.calc_degree_centrality()
        assert central_rank == []
        print("✅ test_empty_graph_all_algorithm_return：空图算法返回值标准统一")

    def test_blacklist_cannot_add_friend(self, graph):
        """新增：已拉黑用户无法建立好友关系"""
        graph.add_to_blacklist(5)
        add_res = graph.add_friendship(1, 5, 1)
        assert add_res is False
        assert 5 not in graph.get_direct_friends(1)
        print("✅ test_blacklist_cannot_add_friend：黑名单用户禁止建立好友关系")

    def test_blacklist_full_intercept_all_func(self, graph):
        """黑名单：添加、移除、清空；路径/人脉/推荐全方位拦截"""
        # 拉黑不存在用户返回False
        assert graph.add_to_blacklist(INVALID_UID) is False

        # 正常拉黑用户5
        assert graph.add_to_blacklist(5) is True
        assert graph.is_in_blacklist(5) is True
        # 重复拉黑无报错
        assert graph.add_to_blacklist(5) is True

        # 好友列表自动屏蔽拉黑用户
        assert 5 not in graph.get_direct_friends(2)

        # 最短路径无法抵达黑名单节点
        dist_bfs, _ = graph.get_shortest_distance(1, 5)
        assert dist_bfs == -1
        dist_dijk, _ = graph.get_weighted_shortest_path(1, 5)
        assert dist_dijk == -1

        # 二度人脉、N度人脉过滤黑名单用户
        second_list = graph.find_second_degree_friends(1)
        uids = [item[0] for item in second_list]
        assert 5 not in uids

        # 好友推荐不会出现黑名单用户
        rec_data = graph.recommend_friends_by_interest(1, 5)
        rec_uids = [item[0] for item in rec_data]
        assert 5 not in rec_uids

        # 移出黑名单恢复所有访问权限
        assert graph.remove_from_blacklist(5) is True
        assert graph.is_in_blacklist(5) is False
        # 重复移除返回False
        assert graph.remove_from_blacklist(5) is False
        dist_recover, _ = graph.get_shortest_distance(1, 5)
        assert dist_recover == 2

        # 批量拉黑后一键清空黑名单
        graph.add_to_blacklist(3)
        graph.add_to_blacklist(7)
        graph.clear_blacklist()
        assert not graph.is_in_blacklist(3) and not graph.is_in_blacklist(7)
        print("✅ test_blacklist_full_intercept_all_func：黑名单全链路拦截、恢复功能全部校验通过")

# ===================== 测试分组5：文件解析与内存数据一致性校验 =====================
class TestFileLoadParseConsistency:
    """文件读取解析数据 和 内存构造数据 完全一致性比对"""
    def test_file_memory_data_equal(self):
        file_graph = load_file_graph()
        memory_graph = build_memory_graph_data()

        # 逐用户比对姓名、兴趣列表
        for uid in range(1, MAX_TEST_USER_NUM + 1):
            file_info = file_graph.get_user_info(uid)
            mem_info = memory_graph.get_user_info(uid)
            assert file_info["name"] == mem_info["name"]
            assert set(file_info["interests"]) == set(mem_info["interests"])

        # 逐用户比对直连好友列表
        for uid in range(1, MAX_TEST_USER_NUM + 1):
            assert set(file_graph.get_direct_friends(uid)) == set(memory_graph.get_direct_friends(uid))

        print("✅ test_file_memory_data_equal：CSV、TXT文件解析数据与内存数据集完全一致")