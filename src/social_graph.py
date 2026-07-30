from collections import defaultdict, deque
import csv
import os
import heapq
from typing import Dict, Set, Tuple, List, Optional


class SocialGraph:
    def __init__(self):
        """初始化社交网络图核心数据结构"""
        # 邻接表：用户ID -> 好友ID集合（无向图）
        self.graph: Dict[int, Set[int]] = defaultdict(set)
        # 用户属性：用户ID -> {name: 姓名, interests: 兴趣列表}
        self.user_attrs: Dict[int, Dict] = {}
        # 关系权重：(较小用户ID, 较大用户ID) -> 权重值（避免重复存储）
        self.edge_weights: Dict[Tuple[int, int], int] = {}
        # 兴趣倒排索引，适配智能推荐模块
        self.interest_index: Dict[str, List[int]] = {}

    def add_user(self, user_id: int, name: str, interests: List[str] = None) -> bool:
        """添加用户，校验ID合法性，维护兴趣索引"""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"用户ID必须为正整数，当前输入：{user_id}")
        if user_id in self.user_attrs:
            print(f"警告：用户ID {user_id} 已存在，跳过添加")
            return False
        self.user_attrs[user_id] = {
            'name': name.strip(),
            'interests': interests if interests else []
        }
        self._update_interest_index(user_id, interests)
        return True

    def _update_interest_index(self, user_id: int, interests: List[str]) -> None:
        """私有方法维护兴趣倒排索引，给智能推荐提供数据"""
        if not interests:
            return
        for interest in interests:
            interest = interest.strip()
            if interest not in self.interest_index:
                self.interest_index[interest] = []
            if user_id not in self.interest_index[interest]:
                self.interest_index[interest].append(user_id)

    def add_friendship(self, user1: int, user2: int, weight: int = 1) -> bool:
        """无向图双向添加好友，适配直接好友、社交距离模块"""
        if user1 <= 0 or user2 <= 0:
            raise ValueError(f"用户ID必须为正整数，当前输入：{user1}, {user2}")
        if user1 == user2:
            raise ValueError("用户不能与自身建立好友关系")
        if user1 not in self.user_attrs:
            raise ValueError(f"用户 {user1} 不存在，请先添加用户")
        if user2 not in self.user_attrs:
            raise ValueError(f"用户 {user2} 不存在，请先添加用户")
        self.graph[user1].add(user2)
        self.graph[user2].add(user1)
        edge_key = (min(user1, user2), max(user1, user2))
        self.edge_weights[edge_key] = weight
        return True

    def load_users_from_csv(self, filename: str) -> bool:
        """数据加载服务：读取users.csv用户文件，兼容中文表头与多编码"""
        print(f"正在加载用户数据：{filename}")
        if not os.path.exists(filename):
            print(f"错误：用户文件 {filename} 不存在")
            return False
        encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312"]
        for encode in encodings:
            try:
                with open(filename, "r", encoding=encode) as f:
                    reader = csv.DictReader(f)
                    required_cols = ["用户ID", "姓名", "兴趣标签"]
                    # 修复：判断表头是否为空
                    if reader.fieldnames is None:
                        print("CSV文件为空，无表头字段！")
                        return False
                    if not all(col in reader.fieldnames for col in required_cols):
                        print(f"CSV缺少必填中文列，必须包含：{required_cols}")
                        return False
                    success_count = 0
                    fail = 0
                    for row_idx, row in enumerate(reader, start=2):
                        try:
                            uid = int(row["用户ID"].strip())
                            uname = row["姓名"].strip()
                            interest_raw = row["兴趣标签"].strip()
                            interest_list = [i.strip() for i in interest_raw.split(";") if i.strip()]
                            if self.add_user(uid, uname, interest_list):
                                success_count += 1
                            else:
                                fail += 1
                        except Exception as e:
                            print(f"第{row_idx}行解析失败：{str(e)}")
                            fail += 1
                    print(f"用户加载：成功{success_count}条，失败{fail}条")
                    return success_count > 0
            except UnicodeDecodeError:
                continue
        print("所有编码解析失败，文件编码异常")
        return False

    def load_relationships_from_txt(self, filename: str) -> bool:
        """数据加载服务：读取relationships.txt好友文件，自动跳过表头"""
        if not os.path.exists(filename):
            print(f"错误：关系文件 {filename} 不存在")
            return False
        encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312"]
        for encode in encodings:
            try:
                with open(filename, "r", encoding=encode) as f:
                    suc = 0
                    fail = 0
                    line_num = 0
                    # 修复：捕获空白文件的StopIteration
                    try:
                        next(f)
                    except StopIteration:
                        print("关系TXT文件为空，无任何数据！")
                        return False
                    for line in f:
                        line_num += 1
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = [p.strip() for p in line.split(",") if p.strip()]
                        if len(parts) < 2:
                            print(f"第{line_num}行格式错误")
                            fail += 1
                            continue
                        u1 = int(parts[0])
                        u2 = int(parts[1])
                        w = int(parts[2]) if len(parts) >= 3 else 1
                        try:
                            self.add_friendship(u1, u2, w)
                            suc += 1
                        except Exception as e:
                            print(f"第{line_num}行添加失败：{e}")
                            fail += 1
                    print(f"关系加载：成功{suc}条，失败{fail}条")
                    return suc > 0
            except UnicodeDecodeError:
                continue
        return False

    def get_direct_friends(self, user_id: int) -> List[int]:
        """对接直接好友查询模块，返回升序直接好友ID"""
        if user_id not in self.user_attrs:
            print(f"用户{user_id}不存在")
            return []
        friends = list(self.graph.get(user_id, set()))
        friends.sort()
        return friends

    def get_direct_friends_with_weight(self, user_id: int) -> List[Tuple[int, int]]:
        """带权重好友查询，适配加权社交距离计算"""
        friend_ids = self.get_direct_friends(user_id)
        res = []
        for fid in friend_ids:
            key = (min(user_id, fid), max(user_id, fid))
            w = self.edge_weights.get(key, 1)
            res.append((fid, w))
        res.sort(key=lambda x: (-x[1], x[0]))
        return res

    def get_user_info(self, user_id: int) -> dict:
        """给UI展示区提供用户姓名、兴趣信息"""
        return self.user_attrs.get(user_id, {"name": "未知用户", "interests": []})

    # ===================== 以下为你编写的算法模块 =====================
    def get_shortest_distance(self, start_uid: int, end_uid: int) -> Tuple[int, List[int]]:
        """
        BFS广度优先遍历：无权图最短社交距离+完整路径回溯
        返回：(距离值, 路径列表)
        无法连通：返回 (-1, [])
        """
        if start_uid not in self.user_attrs or end_uid not in self.user_attrs:
            return -1, []
        if start_uid == end_uid:
            return 0, [start_uid]

        prev_node: Dict[int, Optional[int]] = {}
        q = deque([start_uid])
        prev_node[start_uid] = None

        while q:
            cur = q.popleft()
            for neighbor in self.graph[cur]:
                if neighbor not in prev_node:
                    prev_node[neighbor] = cur
                    q.append(neighbor)
                    if neighbor == end_uid:
                        q = deque()
                        break

        if end_uid not in prev_node:
            return -1, []

        # 回溯生成路径
        path = []
        temp = end_uid
        while temp is not None:
            path.append(temp)
            temp = prev_node[temp]
        path.reverse()
        dist = len(path) - 1
        return dist, path

    def get_weighted_shortest_path(self, start_uid: int, end_uid: int) -> Tuple[int, List[int]]:
        """
        Dijkstra迪杰斯特拉算法：计算带权重好友的最短路径（总权重最小）
        返回：(总权重, 路径列表) 不可达返回 (-1, [])
        """
        if start_uid not in self.user_attrs or end_uid not in self.user_attrs:
            return -1, []
        if start_uid == end_uid:
            return 0, [start_uid]

        INF = float('inf')
        dist: Dict[int, int] = {uid: INF for uid in self.user_attrs.keys()}
        prev_node: Dict[int, Optional[int]] = {uid: None for uid in self.user_attrs.keys()}
        dist[start_uid] = 0
        heap = []
        heapq.heappush(heap, (0, start_uid))

        while heap:
            cur_weight, cur_uid = heapq.heappop(heap)
            if cur_uid == end_uid:
                break
            if cur_weight > dist[cur_uid]:
                continue
            # 遍历所有邻居
            for neighbor in self.graph[cur_uid]:
                edge_key = (min(cur_uid, neighbor), max(cur_uid, neighbor))
                w = self.edge_weights[edge_key]
                if dist[neighbor] > dist[cur_uid] + w:
                    dist[neighbor] = dist[cur_uid] + w
                    prev_node[neighbor] = cur_uid
                    heapq.heappush(heap, (dist[neighbor], neighbor))

        if dist[end_uid] == INF:
            return -1, []

        # 回溯路径
        path = []
        tmp = end_uid
        while tmp is not None:
            path.append(tmp)
            tmp = prev_node[tmp]
        path.reverse()
        return dist[end_uid], path

    def recommend_friends_by_interest(self, user_id: int, top_n: int = 5) -> List[Tuple[int, str, int]]:
        """
        基于兴趣重合度推荐陌生好友（核心推荐算法）
        :param user_id: 目标用户ID
        :param top_n: 推荐人数
        :return: [(用户ID, 用户名, 共同兴趣数量)] 按分数降序排列
        """
        if user_id not in self.user_attrs:
            return []
        # 当前用户兴趣列表
        my_interests = set(self.user_attrs[user_id]["interests"])
        if not my_interests:
            return []
        # 已经是好友的用户集合，排除
        my_friends = set(self.graph[user_id])
        score_dict: Dict[int, int] = defaultdict(int)

        # 遍历每一个兴趣，累加匹配分数
        for interest in my_interests:
            for uid in self.interest_index.get(interest, []):
                if uid != user_id and uid not in my_friends:
                    score_dict[uid] += 1

        # 排序：共同兴趣从多到少，同分用户ID升序
        sorted_users = sorted(score_dict.items(), key=lambda x: (-x[1], x[0]))
        res = []
        for uid, score in sorted_users[:top_n]:
            name = self.user_attrs[uid]["name"]
            res.append((uid, name, score))
        return res

    def calc_degree_centrality(self) -> List[Tuple[int, int, str]]:
        """
        度中心性计算：统计每个用户好友数量，找出社群核心用户
        返回：[(用户ID, 好友总数, 用户名)] 好友数降序排列
        """
        centrality_list = []
        for uid in self.user_attrs.keys():
            friend_count = len(self.graph[uid])
            uname = self.user_attrs[uid]["name"]
            centrality_list.append((uid, friend_count, uname))
        # 好友数量从大到小排序
        centrality_list.sort(key=lambda x: (-x[1], x[0]))
        return centrality_list

    def find_all_communities(self) -> List[List[int]]:
        """
        连通分量查找：划分社交网络所有独立社群
        返回：[[社群1所有用户ID], [社群2所有用户ID], ...]
        """
        visited = set()
        communities = []
        all_users = list(self.user_attrs.keys())

        for uid in all_users:
            if uid not in visited:
                # BFS遍历整个连通子图
                q = deque([uid])
                visited.add(uid)
                one_community = []
                while q:
                    cur = q.popleft()
                    one_community.append(cur)
                    for neighbor in self.graph[cur]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            q.append(neighbor)
                one_community.sort()
                communities.append(one_community)
        return communities


