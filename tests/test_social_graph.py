import pytest
import os
import sys
from typing import List, Tuple, Dict, Any

# ===================== 路径导入配置 =====================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 仅导入主图谱类（底层容器由数据结构同学负责测试）
from src.social_graph import SocialGraph

# ===================== 全局常量 =====================
MAX_TEST_USER_NUM = 10
INVALID_UID = 999
SELF_UID_ERR = 1
NEGATIVE_UID = -6
TOP_N_OVER_MAX = 200
USE_DATA_FILE: bool = False

# ===================== 通用工具函数 =====================
def print_test_title(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

# ===================== 测试数据构造 =====================
def build_memory_graph_data() -> SocialGraph:
    g = SocialGraph()
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
    g = SocialGraph()
    user_csv_path = os.path.join(BASE_DIR, "data", "users.csv")
    rel_txt_path = os.path.join(BASE_DIR, "data", "relationships.txt")
    print(f"\n📂 用户数据文件：{user_csv_path}")
    print(f"📂 好友关系文件：{rel_txt_path}")
    if not os.path.exists(user_csv_path):
        raise FileNotFoundError(f"用户文件缺失：{user_csv_path}")
    if not os.path.exists(rel_txt_path):
        raise FileNotFoundError(f"好友关系文件缺失：{rel_txt_path}")
    load_user_success = g.load_users_from_csv(user_csv_path)
    load_rel_success = g.load_relationships_from_txt(rel_txt_path)
    if not load_user_success:
        raise RuntimeError("users.csv 解析加载失败，请检查文件格式、编码、字段排列")
    if not load_rel_success:
        raise RuntimeError("relationships.txt 解析加载失败，请检查每行边数据格式")
    print("✅ 初始化完成：外部磁盘数据文件加载完毕")
    return g

# ===================== Pytest 夹具 =====================
@pytest.fixture(scope="module")
def graph() -> SocialGraph:
    print_test_title("开始初始化算法测试全局图谱实例")
    if USE_DATA_FILE:
        graph_ins = load_file_graph()
    else:
        graph_ins = build_memory_graph_data()
    yield graph_ins
    graph_ins.clear_blacklist()
    print("\n🧹 算法测试环境重置完成")

@pytest.fixture(scope="function")
def empty_graph() -> SocialGraph:
    return SocialGraph()

# ===================== 分组1：图谱上层基础信息（业务接口，不含底层存储） =====================
class TestGraphBasicLoadInfo:
    def test_all_users_loaded_correctly(self, graph):
        print_test_title("校验全体用户加载完整性")
        uid_list = list(range(1, MAX_TEST_USER_NUM + 1))
        for uid in uid_list:
            user_info = graph.get_user_info(uid)
            assert user_info["name"] != "未知用户", f"用户 ID:{uid} 加载缺失"
            assert len(user_info["interests"]) > 0
        assert len(graph.interest_index) > 0
        print("✅ test_all_users_loaded_correctly：全部 10 个用户加载正常，兴趣索引有效")

    def test_user_detail_attribute(self, graph):
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
        """上层接口获取好友（底层邻接表由数据结构同学测试）"""
        assert set(graph.get_direct_friends(1)) == {2, 3, 6}
        assert set(graph.get_direct_friends(3)) == {1, 2, 4, 6, 8}
        assert set(graph.get_direct_friends(7)) == {4, 5, 6, 8, 10}
        assert graph.get_direct_friends(INVALID_UID) == []
        print("✅ test_direct_friend_adjacent_list：用户直好友上层接口校验通过")

    def test_interest_reverse_index(self, graph):
        code_lover = sorted(graph.interest_index["编程"])
        assert code_lover == [1, 3, 9, 6]
        travel_lover = sorted(graph.interest_index["旅行"])
        assert travel_lover == [2, 5, 8]
        assert graph.interest_index.get("滑雪", []) == []
        print("✅ test_interest_reverse_index：兴趣反向索引上层查询正确")

# ===================== 分组2：用户、好友业务操作 =====================
class TestUserFriendOperate:
    def test_add_repeat_friend(self, graph):
        assert 2 in graph.get_direct_friends(1)
        for _ in range(3):
            graph.add_friendship(1, 2, weight=1)
        friend_list = graph.get_direct_friends(1)
        assert friend_list.count(2) == 1
        print("✅ test_add_repeat_friend：重复添加好友不会产生冗余边")

    def test_modify_edge_weight(self, graph):
        graph.add_friendship(1, 2, weight=5)
        total_w, _ = graph.get_weighted_shortest_path(1, 5)
        assert total_w == 6
        graph.add_friendship(1, 2, weight=1)
        w_recover, _ = graph.get_weighted_shortest_path(1, 5)
        assert w_recover == 2
        print("✅ test_modify_edge_weight：边权重修改生效，带权路径同步更新")

    def test_delete_friendship_bidirectional(self, graph):
        assert 2 in graph.get_direct_friends(1)
        edge_key = tuple(sorted((1, 2)))
        delete_res = graph.delete_friendship(1, 2)
        assert delete_res is True
        assert 2 not in graph.get_direct_friends(1)
        assert 1 not in graph.get_direct_friends(2)
        assert graph.delete_friendship(1, 2) is False
        assert graph.delete_friendship(INVALID_UID, 1) is False
        assert graph.delete_friendship(NEGATIVE_UID, 2) is False
        print("✅ test_delete_friendship_bidirectional：双向好友删除逻辑完整")

    def test_delete_user_full_clean(self):
        temp_graph = build_memory_graph_data()
        del_success = temp_graph.delete_user(5)
        assert del_success is True
        assert temp_graph.user_attrs.get(5) is None
        assert 5 not in temp_graph.get_direct_friends(2)
        assert 5 not in temp_graph.interest_index["旅行"]
        temp_graph.add_to_blacklist(5)
        temp_graph.delete_user(5)
        assert not temp_graph.is_in_blacklist(5)
        assert temp_graph.delete_user(INVALID_UID) is False
        assert temp_graph.delete_user(NEGATIVE_UID) is False
        print("✅ test_delete_user_full_clean：用户全维度删除清理完成")

# ===================== 分组3：核心图算法、好友推荐（算法同学核心任务） =====================
class TestCoreAlgorithmAndRecommend:
    def test_bfs_unweighted_shortest_path(self, graph):
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == 2
        assert path == [1, 2, 5]
        dist_10, _ = graph.get_shortest_distance(1, 10)
        assert dist_10 == 3
        d_self, p_self = graph.get_shortest_distance(5, 5)
        assert d_self == 0 and p_self == [5]
        print("✅ test_bfs_unweighted_shortest_path：BFS 无权最短路径计算正常")

    def test_dijkstra_weighted_shortest_path(self, graph):
        total_weight, path = graph.get_weighted_shortest_path(1, 5)
        assert total_weight == 2
        assert path[0] == 1 and path[-1] == 5
        w_self, _ = graph.get_weighted_shortest_path(3, 3)
        assert w_self == 0
        print("✅ test_dijkstra_weighted_shortest_path：Dijkstra 带权路径计算无误")

    def test_second_degree_friend_with_path(self, graph):
        second_friends = graph.find_second_degree_with_path(1)
        assert len(second_friends) > 0
        for item in second_friends:
            assert len(item) == 3
            uid, mid_uid, path_arr = item
            assert path_arr[0] == 1
            assert len(path_arr) == 3
        print("✅ test_second_degree_friend_with_path：二度人脉查询格式、内容合规")

    def test_n_degree_unified_api(self, graph):
        one_deg = graph.find_n_degree_friends(1, 1)
        assert len(one_deg) == 3
        assert set(one_deg) == {2, 3, 6}
        two_deg = graph.find_n_degree_friends(1, 2)
        assert len(two_deg) > 0
        assert graph.find_n_degree_friends(1, 0) == []
        assert graph.find_n_degree_friends(1, -3) == []
        print("✅ test_n_degree_unified_api：N 度人脉通用接口运行正常")

    def test_interest_based_recommend_sort(self, graph):
        rec_list = graph.recommend_friends_by_interest(1, top_n=3)
        assert len(rec_list) <= 3
        score_prev = 999
        for uid, name, score, inter_list in rec_list:
            assert uid not in {1, 2, 3, 6}
            assert score == len(inter_list)
            assert score <= score_prev
            score_prev = score
        print("✅ test_interest_based_recommend_sort：兴趣推荐规则、降序排序校验通过")

    def test_heap_recommend_topk(self, graph):
        """算法层：堆在推荐业务落地测试（底层堆由数据结构同学单元测试）"""
        rec_result = graph.recommend_friends_by_interest(1, top_n=4)
        scores = [item[2] for item in rec_result]
        sorted_score = sorted(scores, reverse=True)
        assert scores == sorted_score
        assert len(rec_result) <= 4
        print("✅ test_heap_recommend_topk：堆实现 TopK 推荐降序排序、数量限制有效")

    def test_mix_weight_recommend(self, graph):
        mix_rec = graph.recommend_friends_weight_mix(1, top_n=4)
        assert len(mix_rec) <= 4
        for uid, name, score, inters in mix_rec:
            assert isinstance(score, float)
            assert uid not in {1, 2, 3, 6}
        print("✅ test_mix_weight_recommend：混合加权推荐正常返回")

    def test_degree_centrality_desc_sort(self, graph):
        rank_result = graph.calc_degree_centrality()
        assert len(rank_result) == 10
        prev_num = 999
        for _, friend_cnt, _ in rank_result:
            assert friend_cnt <= prev_num
            prev_num = friend_cnt
        top_counts = [item[1] for item in rank_result[:2]]
        assert 5 in top_counts
        print("✅ test_degree_centrality_desc_sort：节点度值降序排序正确")

    def test_connected_component_community(self, graph, empty_graph):
        communities = graph.find_all_communities()
        assert len(communities) == 1
        assert sorted(communities[0]) == list(range(1, 11))
        assert empty_graph.find_all_communities() == []
        empty_graph.add_user(100, "测试用户", [])
        single_comm = empty_graph.find_all_communities()
        assert len(single_comm) == 1
        assert single_comm[0] == [100]
        print("✅ test_connected_component_community：连通社群划分逻辑正常")

# ===================== 分组4：边界异常 + 黑名单全链路拦截 =====================
class TestBoundaryExceptionBlacklist:
    def test_abnormal_input_fault_tolerant(self, graph, empty_graph):
        unknown_user = graph.get_user_info(INVALID_UID)
        assert unknown["name"] == "未知用户"
        assert len(unknown["interests"]) == 0
        assert graph.get_direct_friends(INVALID_UID) == []
        assert graph.get_direct_friends(NEGATIVE_UID) == []
        all_rec = graph.recommend_friends_by_interest(1, top_n=TOP_N_OVER_MAX)
        assert isinstance(all_rec, list)
        with pytest.raises(ValueError):
            graph.add_friendship(SELF_UID_ERR, SELF_UID_ERR)
        with pytest.raises(ValueError):
            graph.add_user(NEGATIVE_UID, "负数 ID", ["追剧"])
        empty_graph.get_shortest_distance(1, 2)
        empty_graph.calc_degree_centrality()
        empty_graph.recommend_friends_by_interest(1, 5)
        empty_graph.find_all_communities()
        print("✅ test_abnormal_input_fault_tolerant：各类异常参数容错无崩溃")

    def test_blacklist_full_intercept_all_func(self, graph):
        assert graph.add_to_blacklist(INVALID_UID) is False
        assert graph.add_to_blacklist(5) is True
        assert graph.is_in_blacklist(5) is True
        assert graph.add_to_blacklist(5) is True
        assert 5 not in graph.get_direct_friends(2)
        dist_bfs, _ = graph.get_shortest_distance(1, 5)
        assert dist_bfs == -1
        dist_dijk, _ = graph.get_weighted_shortest_path(1, 5)
        assert dist_dijk == -1
        second_uid_list = [item[0] for item in graph.find_second_degree_with_path(1)]
        assert 5 not in second_uid_list
        n2_friends = graph.find_n_degree_friends(1, 2)
        assert 5 not in n2_friends
        rec_data = graph.recommend_friends_by_interest(1, top_n=5)
        rec_uids = [item[0] for item in rec_data]
        assert 5 not in rec_uids
        assert graph.remove_from_blacklist(5) is True
        assert graph.is_in_blacklist(5) is False
        assert graph.remove_from_blacklist(5) is False
        dist_recover, _ = graph.get_shortest_distance(1, 5)
        assert dist_recover == 2
        graph.add_to_blacklist(3)
        graph.add_to_blacklist(7)
        graph.clear_blacklist()
        assert len(graph.blacklist) == 0
        print("✅ test_blacklist_full_intercept_all_func：黑名单全功能拦截、恢复校验全部通过")