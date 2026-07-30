from src.social_graph import SocialGraph

def test_add_user():
    """测试添加用户"""
    g = SocialGraph()
    ok = g.add_user(1, "张三", ["篮球","编程"])
    assert ok is True
    # 重复添加同一个用户返回False
    ok2 = g.add_user(1, "张三", [])
    assert ok2 is False

def test_add_friendship():
    """测试添加好友关系"""
    g = SocialGraph()
    g.add_user(1,"A",[])
    g.add_user(2,"B",[])
    g.add_friendship(1, 2, weight=2)
    friends = g.get_direct_friends(1)
    assert friends == [2]

def test_bfs_shortest():
    """BFS无权最短路径"""
    g = SocialGraph()
    g.add_user(1,"U1",[])
    g.add_user(2,"U2",[])
    g.add_user(3,"U3",[])
    g.add_friendship(1,2)
    g.add_friendship(2,3)
    dist,path = g.get_shortest_distance(1,3)
    assert dist == 2
    assert path == [1,2,3]

def test_dijkstra_weight():
    """Dijkstra加权最短路径"""
    g = SocialGraph()
    g.add_user(1,"U1",[])
    g.add_user(2,"U2",[])
    g.add_user(3,"U3",[])
    g.add_friendship(1,2,weight=10)
    g.add_friendship(1,3,weight=1)
    g.add_friendship(3,2,weight=1)
    w,path = g.get_weighted_shortest_path(1,2)
    assert w == 2

def test_recommend_friend():
    """兴趣好友推荐"""
    g = SocialGraph()
    g.add_user(1,"A",["游戏","音乐"])
    g.add_user(2,"B",["游戏"])
    g.add_user(3,"C",["音乐"])
    g.add_user(4,"D",["运动"])
    rec = g.recommend_friends_by_interest(1,top_n=5)
    ids = [x[0] for x in rec]
    assert 2 in ids
    assert 3 in ids

def test_community():
    """连通分量社群划分"""
    g = SocialGraph()
    g.add_user(1,"",[])
    g.add_user(2,"",[])
    g.add_user(10,"",[])
    g.add_friendship(1,2)
    comm = g.find_all_communities()
    assert len(comm) == 2

if __name__ == "__main__":
    graph = SocialGraph()
    user_file = "../data/users.csv"
    rel_file = "../data/relationships.txt"
    print("=====加载用户数据====")
    load_user_ok = graph.load_users_from_csv(user_file)
    print("用户文件加载结果：", load_user_ok)
    print("\n=====加载好友关系数据====")
    load_friend_ok = graph.load_relationships_from_txt(rel_file)
    print("好友文件加载结果：", load_friend_ok)
    print("\n=====基础数据测试=====")
    print("【1】用户1的一度好友ID：", graph.get_direct_friends(1))
    print("【2】用户1个人信息：", graph.get_user_info(1))