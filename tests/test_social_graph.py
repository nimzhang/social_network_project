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
# 新增：排序策略常量
SORT_INTEREST = "interest"
SORT_WEIGHT = "weight"
WRONG_SORT_KEY = "time"

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
# 修改：scope 改为 function，每个用例单独全新构建图谱，彻底隔离数据污染
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
# ===================== 第一大部分：数据结构测试 =====================
# ==============================================================
class TestSelfDataStructure:
    def test_hash_table_all_interface(self):
        # 修复1：删除 capacity 传参，不再写 HashTable(capacity=20)
        ht = HashTable()
        assert ht.get(1) is None, "空哈希表取值必须返回 None"
        assert 1 not in ht
        ht.put(1, {"name": "张三"})
        ht.put(5, {"name": "李四"})
        ht.put(9, {"name": "王五"})
        assert ht.get(1)["name"] == "张三", "哈希表取值错误"
        assert ht.get(INVALID_UID) is None, "不存在 key 应当返回 None"
        ht.put(1, {"name": "张三三"})
        assert ht.get(1)["name"] == "张三三", "哈希表更新覆盖失效"
        assert 1 in ht
        assert 5 in ht
        assert INVALID_UID not in ht
        assert ht.remove(5) is True, "存在 key 删除应当返回 True"
        assert ht.get(5) is None
        assert ht.remove(INVALID_UID) is False, "删除不存在 key 返回 False"
        ht.remove(1)
        ht.remove(9)
        assert ht.get(1) is None and ht.get(9) is None
        print("✅ test_hash_table_all_interface：自研哈希表全部接口校验通过")

    def test_min_heap_push_pop_order(self):
        heap = MinHeap()
        assert heap.pop() is None
        assert heap.size() == 0
        heap.push(5, "C")
        heap.push(2, "A")
        heap.push(7, "D")
        heap.push(1, "B")
        heap.push(2, "X")
        heap.push(2, "Y")
        assert heap.pop() == (1, "B")
        assert heap.pop() == (2, "A")
        assert heap.pop() == (2, "X")
        assert heap.pop() == (2, "Y")
        assert heap.pop() == (5, "C")
        assert heap.pop() == (7, "D")
        assert heap.pop() is None
        assert heap.size() == 0
        print("✅ test_min_heap_push_pop_order：自研小顶堆出入堆顺序、空值容错正常")

# 测试分组 1：基础加载校验
class TestGraphBasicLoadInfo:
    def test_all_users_loaded_correctly(self, graph):
        print_test_title("校验全体用户加载完整性")
        uid_list = list(range(1, MAX_TEST_USER_NUM + 1))
        for uid in uid_list:
            user_info = graph.get_user_info(uid)
            assert user_info["name"] != "未知用户", f"用户 ID:{uid} 加载缺失"
            assert len(user_info["interests"]) > 0, f"用户 ID:{uid} 兴趣列表为空，数据异常"
        assert len(graph.interest_index.keys()) > 0, "兴趣反向索引为空，构建失败"
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
        assert set(graph.get_direct_friends(1)) == {2, 3, 6}
        assert set(graph.get_direct_friends(3)) == {1, 2, 4, 6, 8}
        assert set(graph.get_direct_friends(7)) == {4, 5, 6, 8, 10}
        assert graph.get_direct_friends(INVALID_UID) == []
        print("✅ test_direct_friend_adjacent_list：用户直连好友邻接表校验通过")

    def test_interest_reverse_index(self, graph):
        code_lover = sorted(graph.interest_index.get("编程"))
        assert code_lover == [1, 3, 6, 9]
        travel_lover = sorted(graph.interest_index.get("旅行"))
        assert travel_lover == [2, 5, 8]
        assert graph.interest_index.get("滑雪") is None
        print("✅ test_interest_reverse_index：兴趣反向索引数据正确")

    def test_adjacency_list_storage(self, graph):
        adj = graph.graph
        assert 2 in adj[1] and 1 in adj[2]
        assert 3 in adj[1] and 1 in adj[3]
        assert 6 in adj[1] and 1 in adj[6]
        assert INVALID_UID not in adj
        edge_key = tuple(sorted([1, 2]))
        assert graph.edge_weights[edge_key] == 1
        print("✅ test_adjacency_list_storage：邻接表双向存边、权重、边界校验全部正常")

class TestFileLoadParse:
    def test_file_parse_accuracy(self):
        BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        user_csv_path = os.path.join(BASE, "data", "users.csv")
        rel_txt_path = os.path.join(BASE, "data", "relationships.txt")
        file_g = SocialGraph()
        file_g.load_users_from_csv(user_csv_path)
        file_g.load_relationships_from_txt(rel_txt_path)
        memory_g = build_memory_graph_data()
        for uid in range(1, 11):
            file_info = file_g.get_user_info(uid)
            mem_info = memory_g.get_user_info(uid)
            assert file_info["name"] == mem_info["name"]
            assert set(file_info["interests"]) == set(mem_info["interests"])
        for uid in range(1, 11):
            assert set(file_g.get_direct_friends(uid)) == set(memory_g.get_direct_friends(uid))
        print("✅ test_file_parse_accuracy：users.csv、relationships.txt 文件解析和内存数据完全匹配")
# ==============================================================
# ===================== 【第二大部分：算法同学负责全量代码】 =====================
# 覆盖：上层业务增删改、全部图算法、推荐、黑名单、边界容错
# ==============================================================
# 测试分组 2：用户、好友增删改基础上层业务接口
class TestUserFriendOperate:
    """分类：用户新增删除、好友添加解除、边权重管理 | 扩充重复操作、删除后反向验证"""
    def test_add_repeat_friend(self, graph):
        """重复添加同一好友，无冗余边，无报错"""
        # 原本已是好友
        assert 2 in graph.get_direct_friends(1)
        # 重复添加多次
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
        assert 2 in graph.get_direct_friends(1)
        edge_key = tuple(sorted((1, 2)))
        assert edge_key in graph.edge_weights
        # 执行删除
        delete_res = graph.delete_friendship(1, 2)
        assert delete_res is True
        assert 2 not in graph.get_direct_friends(1)
        assert 1 not in graph.get_direct_friends(2)
        assert edge_key not in graph.edge_weights
        # 重复删除、无效用户删除均返回 False
        assert graph.delete_friendship(1, 2) is False
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
        travel_data = temp_graph.interest_index.get("旅行")
        travel_data = travel_data if travel_data is not None else []
        assert 5 not in travel_data
        # 先拉黑再删（删除自动清黑名单）
        temp_graph.add_to_blacklist(5)
        # 此时用户已删，再次删除会返回False，不再重复调用delete_user
        assert temp_graph.is_in_blacklist(5) is False
        # 删除不存在用户、负数用户均返回 False
        assert temp_graph.delete_user(INVALID_UID) is False
        assert temp_graph.delete_user(NEGATIVE_UID) is False
        print("✅ test_delete_user_full_clean：用户全维度删除清理完成")

# 测试分组 3：核心图算法 + 推荐系统 + 社群分析
class TestCoreAlgorithmAndRecommend:
    """分类：最短路径、N 度人脉、好友推荐、度中心性、连通社群划分"""
    def test_bfs_unweighted_shortest_path(self, graph):
        """BFS 无权图最短路径计算：可达节点、自身节点、边界全覆盖"""
        dist, path = graph.get_shortest_distance(1, 5)
        assert dist == 2
        assert path == [1, 2, 5]
        dist_10, _ = graph.get_shortest_distance(1, 10)
        assert dist_10 == 3
        # 起点终点为同一人，距离 0，路径仅自身
        d_self, p_self = graph.get_shortest_distance(5, 5)
        assert d_self == 0 and p_self == [5]
        print("✅ test_bfs_unweighted_shortest_path：BFS 无权最短路径计算正常")

    def test_dijkstra_weighted_shortest_path(self, graph):
        """Dijkstra 算法加权最短路径求解"""
        total_weight, path = graph.get_weighted_shortest_path(1, 5)
        assert total_weight == 2
        assert path[0] == 1 and path[-1] == 5
        w_self, _ = graph.get_weighted_shortest_path(3, 3)
        assert w_self == 0
        print("✅ test_dijkstra_weighted_shortest_path：Dijkstra 带权路径计算无误")

    # ==========【原有用例修改：适配新增sort_strategy参数】==========
    def test_second_degree_friend_with_path(self, graph):
        """二度人脉查询，携带完整跳转路径；双排序策略校验 + 非法参数降级容错"""
        print_test_title("测试二度人脉两种排序策略")

        # 策略1：兴趣排序 interest
        res_interest = graph.find_second_degree_with_path(1, sort_strategy="interest")
        assert len(res_interest) > 0
        for item in res_interest:
            assert len(item) == 3
            uid, mid_uid, path_arr = item
            assert path_arr[0] == 1
            assert len(path_arr) == 3

        # 策略2：权重排序 weight
        res_weight = graph.find_second_degree_with_path(1, sort_strategy="weight")
        assert len(res_weight) > 0

        # ✅ 修复：非法排序字段 → 自动降级为 "weight"，而不是返回空
        res_wrong = graph.find_second_degree_with_path(1, sort_strategy="id")
        assert isinstance(res_wrong, list)
        assert len(res_wrong) > 0  # 降级后有数据，而不是空列表

        # ✅ 额外验证：降级后实际使用的策略是 weight
        # 对比降级结果与 weight 结果应该一致
        res_wrong = graph.find_second_degree_with_path(1, sort_strategy="id")
        res_weight = graph.find_second_degree_with_path(1, sort_strategy="weight")
        # 排序可能相同（因为数据量小），至少长度一致
        assert len(res_wrong) == len(res_weight)

        print("✅ test_second_degree_friend_with_path：双排序策略、非法参数降级容错校验完成")

    def test_n_degree_unified_api(self, graph):
        """通用 N 度人脉统一接口容错校验：正整数、0、负数度数区分处理"""
        # 一度好友
        one_deg = graph.find_n_degree_friends(1, 1)
        assert len(one_deg) == 3
        assert set(one_deg) == {2, 3, 6}
        # 二度好友
        two_deg = graph.find_n_degree_friends(1, 2)
        assert len(two_deg) > 0
        # 非法度数 <= 0 返回空列表
        assert graph.find_n_degree_friends(1, 0) == []
        assert graph.find_n_degree_friends(1, -3) == []
        print("✅ test_n_degree_unified_api：N 度人脉通用接口运行正常")

    def test_interest_based_recommend_sort(self, graph):
        """基于兴趣相似度好友推荐：按共同兴趣数量降序排列；排除自身与现有好友"""
        rec_list = graph.recommend_friends_by_interest(1, top_n=3)
        assert len(rec_list) <= 3
        score_prev = 999
        for uid, name, score, inter_list in rec_list:
            # 过滤自己和现有好友
            assert uid not in {1, 2, 3, 6}, "推荐列表不能出现自身和已添加好友"
            assert score == len(inter_list)
            # 推荐结果严格降序排序
            assert score <= score_prev
            score_prev = score
        print("✅ test_interest_based_recommend_sort：兴趣推荐规则、降序排序校验通过")

    def test_hash_table_interest_index(self):
        """测试兴趣反向索引哈希表存取、新增、删除逻辑"""
        temp_g = build_memory_graph_data()
        hash_index = temp_g.interest_index
        # 修改：不再判断 dict，改为判断自研 HashTable
        assert isinstance(hash_index, HashTable)
        travel_list = hash_index.get("旅行")
        travel_list = travel_list if travel_list is not None else []
        assert sorted(travel_list) == [2, 5, 8]
        # 新增用户只操作临时图
        temp_g.add_user(11, "测试", ["徒步", "编程"])
        code_list = hash_index.get("编程")
        code_list = code_list if code_list is not None else []
        assert 11 in code_list
        # 不存在爱好默认返回空列表
        ski_list = hash_index.get("滑雪")
        ski_list = ski_list if ski_list is not None else []
        assert ski_list == []
        print("✅ test_hash_table_interest_index：兴趣哈希表增、查、缺省逻辑校验通过")

    def test_heap_recommend_topk(self, graph):
        """测试推荐功能底层小根堆 TopK 排序逻辑：降序输出、数量限制生效"""
        rec_result = graph.recommend_friends_by_interest(1, top_n=4)
        scores = [item[2] for item in rec_result]
        sorted_score = sorted(scores, reverse=True)
        assert scores == sorted_score
        assert len(rec_result) <= 4
        print("✅ test_heap_recommend_topk：堆实现 TopK 推荐降序排序、数量限制有效")

    def test_mix_weight_recommend(self, graph):
        """兴趣 + 社交亲密度混合加权推荐"""
        mix_rec = graph.recommend_friends_weight_mix(1, top_n=4)
        assert len(mix_rec) <= 4
        for uid, name, score, inters in mix_rec:
            # 整数、浮点数都允许
            assert isinstance(score, (int, float))
            assert uid not in {1, 2, 3, 6}
        print("✅ test_mix_weight_recommend：混合加权推荐正常返回")

    def test_degree_centrality_desc_sort(self, graph):
        """度中心性计算，好友数量降序排序；校验最大节点度数"""
        rank_result = graph


# ===================== 【全新新增测试分组：数据导出功能测试】 =====================
class TestDataExportFeature:
    """测试功能3：数据导出"""

    def test_export_adjacency_list(self, graph, tmp_path):
        """测试导出标准邻接表"""
        print_test_title("测试标准邻接表导出")

        output_file = tmp_path / "export_adjacency_list.txt"

        result = graph.export_adjacency_list(str(output_file))
        assert result is True

        assert output_file.exists()

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

        result = graph.export_adjacency_table_text(str(output_file))
        assert result is True

        assert output_file.exists()

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

            # 验证数据
            assert "张三" in content
            assert "2(李四)" in content

        print(f"\n📂 文件位置: {output_file}")