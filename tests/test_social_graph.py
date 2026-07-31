import pytest
import os
import sys

# 修复src导入问题，自动添加项目根目录到系统路径
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.social_graph import SocialGraph

# ===================== 全局配置开关 =====================
# True=读取data文件夹真实文件；False=代码内置生成测试数据（无需csv/txt）
USE_DATA_FILE = False


def build_memory_graph_data() -> SocialGraph:
    """不依赖外部文件，内存直接构造完整测试数据集（和csv/txt数据完全一致）"""
    g = SocialGraph()
    # 用户数据
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

    # 好友关系（无向，默认权重1）
    edges = [
        (1, 2), (1, 3), (1, 6), (2, 3), (2, 5),
        (3, 4), (3, 6), (4, 7), (4, 8), (5, 7),
        (5, 9), (6, 9), (7, 8), (7, 10), (8, 10),
        (9, 10), (2, 9), (3, 8), (5, 10), (6, 7)
    ]
    # 统一正确方法名 add_friendship
    for u, v in edges:
        g.add_friendship(u, v, weight=1)
    print("✅ 已使用内存内置测试数据，无需外部文件")
    return g


def load_file_graph() -> SocialGraph:
    """从项目data文件夹加载csv/txt数据，自动拼接绝对路径"""
    g = SocialGraph()
    user_csv = os.path.join(BASE_DIR, "data", "users.csv")
    rel_txt = os.path.join(BASE_DIR, "data", "relationships.txt")

    print(f"\n📂 用户文件路径: {user_csv}")
    print(f"📂 关系文件路径: {rel_txt}")

    # 校验文件是否存在
    if not os.path.exists(user_csv):
        raise FileNotFoundError(f"用户文件不存在：{user_csv}")
    if not os.path.exists(rel_txt):
        raise FileNotFoundError(f"关系文件不存在：{rel_txt}")

    # 加载数据
    load_user_ok = g.load_users_from_csv(user_csv)
    load_rel_ok = g.load_relationships_from_txt(rel_txt)

    if not load_user_ok:
        raise RuntimeError("users.csv 加载失败，请检查文件格式")
    if not load_rel_ok:
        raise RuntimeError("relationships.txt 加载失败，请检查文件格式")
    print("✅ 外部数据文件加载完成")
    return g


@pytest.fixture(scope="module")
def graph() -> SocialGraph:
    """全局共用图实例，自动切换文件/内存两种数据源
    yield 后置动作：测试全部跑完自动清空黑名单，避免残留污染
    """
    if USE_DATA_FILE:
        g = load_file_graph()
    else:
        g = build_memory_graph_data()
    yield g
    # 测试收尾重置黑名单
    g.clear_blacklist()
    print("\n🧹 测试结束，黑名单已清空")


# ===================== 测试组1：数据加载与基础信息 =====================
def test_all_user_load(graph):
    """校验10个用户全部成功加载"""
    all_uid = list(range(1, 11))
    for uid in all_uid:
        info = graph.get_user_info(uid)
        assert info["name"] != "未知用户", f"用户{uid}缺失"
    assert len(graph.interest_index) > 0, "兴趣索引为空"


def test_user_detail_info(graph):
    """校验用户姓名、兴趣字段准确性"""
    u1 = graph.get_user_info(1)
    assert u1["name"] == "张三"
    assert set(u1["interests"]) == {"编程", "篮球", "摄影"}

    u10 = graph.get_user_info(10)
    assert u10["name"] == "王十二"
    assert set(u10["interests"]) == {"阅读", "绘画", "篮球"}


def test_direct_friend_list(graph):
    """校验一度好友邻接表数据正确（返回列表，转集合对比）"""
    assert set(graph.get_direct_friends(1)) == {2, 3, 6}
    assert set(graph.get_direct_friends(3)) == {1, 2, 4, 6, 8}
    assert set(graph.get_direct_friends(7)) == {4, 5, 6, 8, 10}


def test_interest_invert_index(graph):
    """校验兴趣反向索引匹配正确用户"""
    code_users = sorted(graph.interest_index.get("编程", []))
    assert code_users == [1, 3, 6, 9]

    travel_users = sorted(graph.interest_index.get("旅行", []))
    assert travel_users == [2, 5, 8]


# ===================== 测试组2：五大核心算法 + 新增接口测试 =====================
def test_bfs_unweight_shortest(graph):
    """BFS无权最短路径"""
    dist, path = graph.get_shortest_distance(1, 5)
    assert dist == 2
    assert path == [1, 2, 5]

    dist10, path10 = graph.get_shortest_distance(1, 10)
    assert dist10 == 3

    # 自身到自身
    d_self, p_self = graph.get_shortest_distance(5, 5)
    assert d_self == 0 and p_self == [5]


def test_dijkstra_weight_path(graph):
    """Dijkstra加权最短路径"""
    weight, path = graph.get_weighted_shortest_path(1, 5)
    assert weight == 2  # 每条边权重都是1，总距离固定为2
    assert path[0] == 1 and path[-1] == 5

    w_self, _ = graph.get_weighted_shortest_path(3, 3)
    assert w_self == 0


def test_second_degree_with_path(graph):
    """测试高优先级：二度人脉带路径查询"""
    second_list = graph.find_second_degree_with_path(1)
    # 校验返回元组固定结构 (uid, mid_id, path_list)
    assert len(second_list) > 0
    for item in second_list:
        assert len(item) == 3
        uid, mid, path = item
        assert isinstance(path, list)
        assert path[0] == 1
        assert len(path) == 3  # 二度路径长度固定3个节点


def test_n_degree_unified_api(graph):
    """测试统一N度人脉标准接口"""
    # 一度好友
    one_deg = graph.find_n_degree_friends(1, 1)
    assert len(one_deg) == 3
    assert set(one_deg) == {2, 3, 6}
    # 二度好友
    two_deg = graph.find_n_degree_friends(1, 2)
    assert len(two_deg) > 0


def test_interest_friend_recommend(graph):
    """兴趣相似度好友推荐：适配4元组返回(uid,name,score,共同兴趣列表)，小顶堆TopK"""
    rec = graph.recommend_friends_by_interest(1, top_n=3)
    assert len(rec) <= 3
    # 遍历校验返回结构与规则
    for item in rec:
        uid, name, score, inters = item
        # 不推荐现有一度好友、自己
        assert uid not in {1, 2, 3, 6}
        assert isinstance(inters, list)
        assert score == len(inters)  # 分数=共同兴趣数量


def test_degree_centrality_sort(graph):
    """度中心性降序排序"""
    rank = graph.calc_degree_centrality()
    assert len(rank) == 10
    # 保证降序排列
    prev_count = 999
    for _, cnt, _ in rank:
        assert cnt <= prev_count
        prev_count = cnt
    # 3、7号用户好友数量最多（5个好友）
    top_two_count = [x[1] for x in rank[:2]]
    assert 5 in top_two_count


def test_community_connected(graph):
    """连通分量社群划分：整张图属于同一个社群"""
    comms = graph.find_all_communities()
    assert len(comms) == 1
    assert sorted(comms[0]) == list(range(1, 11))


# ===================== 测试组3：边界异常 + 黑名单全套功能测试 =====================
def test_abnormal_input(graph):
    """非法ID、超大推荐数量容错测试"""
    # 不存在用户：返回未知用户字典
    info_999 = graph.get_user_info(999)
    assert info_999["name"] == "未知用户"
    assert len(info_999["interests"]) == 0

    # 不存在用户好友列表为空列表
    friends_999 = graph.get_direct_friends(999)
    assert friends_999 == []

    # 超过总人数的推荐数，正常返回全部候选
    rec_all = graph.recommend_friends_by_interest(1, top_n=100)
    assert isinstance(rec_all, list)


def test_blacklist_filter(graph):
    """黑名单增删、全链路过滤功能测试（所有算法均屏蔽黑名单用户）"""
    # 1. 将用户5加入黑名单
    graph.add_to_blacklist(5)
    assert graph.is_in_blacklist(5) is True

    # 2. 好友列表自动过滤黑名单用户：李四(2)原本好友包含5，现在查询不到
    assert 5 not in graph.get_direct_friends(2)

    # 3. BFS最短路径无法抵达黑名单用户
    dist, _ = graph.get_shortest_distance(1, 5)
    assert dist == -1

    # 4. Dijkstra加权路径同样不可达
    w, _ = graph.get_weighted_shortest_path(1, 5)
    assert w == -1

    # 5. 二度人脉、N度人脉不会出现黑名单用户
    second_friends = [x[0] for x in graph.find_second_degree_with_path(1)]
    assert 5 not in second_friends

    # 6. 移出黑名单，所有功能恢复正常通路
    graph.remove_from_blacklist(5)
    assert graph.is_in_blacklist(5) is False

    dist2, _ = graph.get_shortest_distance(1, 5)
    assert dist2 == 2