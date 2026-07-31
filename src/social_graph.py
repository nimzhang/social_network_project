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
        # ===================== 新增：黑名单集合（中优3） =====================
        self.blacklist: Set[int] = set()

    # ===================== 黑名单全套接口（扩展A） =====================
    def add_to_blacklist(self, user_id: int) -> bool:
        """将用户加入黑名单"""
        if user_id not in self.user_attrs:
            return False
        self.blacklist.add(user_id)
        return True

    def remove_from_blacklist(self, user_id: int) -> bool:
        """将用户移出黑名单"""
        if user_id in self.blacklist:
            self.blacklist.remove(user_id)
            return True
        return False

    def is_in_blacklist(self, user_id: int) -> bool:
        """判断用户是否在黑名单中"""
        return user_id in self.blacklist

    def clear_blacklist(self) -> None:
        """清空黑名单（pytest测试收尾重置用）"""
        self.blacklist.clear()

    # ===================== 原有基础增删改查（适配黑名单过滤） =====================
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
        """对接直接好友查询模块：自动过滤黑名单用户，返回升序好友ID"""
        if user_id not in self.user_attrs:
            print(f"用户{user_id}不存在")
            return []
        friends = list(self.graph.get(user_id, set()))
        # 过滤黑名单
        friends = [f for f in friends if f not in self.blacklist]
        friends.sort()
        return friends

    def get_direct_friends_with_weight(self, user_id: int) -> List[Tuple[int, int]]:
        """带权重好友查询，适配加权社交距离计算，过滤黑名单"""
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

    # ===================== 高优需求1：带路径二度人脉查询 =====================
    def find_second_degree_with_path(self, user_id: int) -> List[Tuple[int, int, List[int]]]:
        """
        查询目标用户所有二度人脉，附带连接路径
        返回格式：[(二度用户ID, 中间好友ID, 完整路径列表), ...]
        规则：
        1. 排除自己、一度好友、黑名单用户
        2. BFS遍历记录前驱节点回溯路径
        """
        if user_id not in self.user_attrs:
            return []
        # 一度好友集合
        first_degree = set(self.get_direct_friends(user_id))
        visited = set()
        prev_node: Dict[int, Optional[int]] = {}
        q = deque()
        q.append((user_id, 0))  # (当前节点, 当前度数)
        prev_node[user_id] = None
        visited.add(user_id)

        second_degree_res = []

        while q:
            cur_uid, depth = q.popleft()
            # 深度超过2直接终止遍历（性能优化：提前截断）
            if depth > 2:
                continue
            for neighbor in self.graph[cur_uid]:
                # 黑名单、已访问节点直接跳过
                if neighbor in self.blacklist or neighbor in visited:
                    continue
                prev_node[neighbor] = cur_uid
                visited.add(neighbor)
                new_depth = depth + 1
                if new_depth == 1:
                    q.append((neighbor, new_depth))
                # 命中二度人脉，回溯完整路径
                elif new_depth == 2:
                    path = []
                    tmp = neighbor
                    while tmp is not None:
                        path.append(tmp)
                        tmp = prev_node[tmp]
                    path.reverse()
                    mid_friend = path[1]  # 中间一度好友
                    second_degree_res.append((neighbor, mid_friend, path))
        return second_degree_res

    # ===================== 高优需求2：统一N度人脉标准接口（收拢所有BFS人脉逻辑） =====================
    def find_n_degree_friends(self, user_id: int, n: int) -> List[int]:
        """
        通用N度人脉查询统一接口
        :param user_id: 起始用户ID
        :param n: 人脉度数（1=一度好友，2=二度好友）
        :return: 升序N度好友ID列表，自动过滤黑名单
        """
        if user_id not in self.user_attrs or n <= 0:
            return []
        visited = set()
        q = deque()
        q.append((user_id, 0))
        visited.add(user_id)
        degree_result = defaultdict(list)

        while q:
            cur_uid, depth = q.popleft()
            # 超过目标度数提前终止遍历（性能优化）
            if depth >= n:
                continue
            for neighbor in self.graph[cur_uid]:
                if neighbor in visited or neighbor in self.blacklist:
                    continue
                visited.add(neighbor)
                new_depth = depth + 1
                degree_result[new_depth].append(neighbor)
                q.append((neighbor, new_depth))
        target_list = degree_result.get(n, [])
        target_list.sort()
        return target_list

    # ===================== BFS无权最短路径（全程过滤黑名单+性能优化） =====================
    def get_shortest_distance(self, start_uid: int, end_uid: int) -> Tuple[int, List[int]]:
        """
        BFS广度优先遍历：无权图最短社交距离+完整路径回溯
        返回：(距离值, 路径列表)
        无法连通/目标在黑名单：返回 (-1, [])
        """
        # 基础合法性校验
        if start_uid not in self.user_attrs or end_uid not in self.user_attrs:
            return -1, []
        if end_uid in self.blacklist:
            return -1, []
        if start_uid == end_uid:
            return 0, [start_uid]

        prev_node: Dict[int, Optional[int]] = {}
        q = deque([start_uid])
        prev_node[start_uid] = None

        while q:
            cur = q.popleft()
            for neighbor in self.graph[cur]:
                # 跳过黑名单、已访问节点
                if neighbor in self.blacklist or neighbor in prev_node:
                    continue
                prev_node[neighbor] = cur
                q.append(neighbor)
                if neighbor == end_uid:
                    q = deque()  # 清空队列提前退出循环
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

    # ===================== Dijkstra加权最短路径（过滤黑名单） =====================
    def get_weighted_shortest_path(self, start_uid: int, end_uid: int) -> Tuple[int, List[int]]:
        """
        Dijkstra迪杰斯特拉算法：计算带权重好友的最短路径（总权重最小）
        返回：(总权重, 路径列表) 不可达/黑名单返回 (-1, [])
        """
        if start_uid not in self.user_attrs or end_uid not in self.user_attrs:
            return -1, []
        if end_uid in self.blacklist:
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
            # 遍历邻居，跳过黑名单用户
            for neighbor in self.graph[cur_uid]:
                if neighbor in self.blacklist:
                    continue
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

    # ===================== 中优1+2：小顶堆TopK兴趣推荐 + 返回共同兴趣详情 =====================
    def recommend_friends_by_interest(self, user_id: int, top_n: int = 5) -> List[Tuple[int, str, int, List[str]]]:
        """
        基于兴趣重合度推荐陌生的好友：自研小顶堆实现TopK（不全局排序）
        返回结构：[(用户ID, 用户名, 共同兴趣数量, 共同兴趣名称列表)]
        自动排除：自身、好友、黑名单用户
        """
        if user_id not in self.user_attrs:
            return []
        my_info = self.user_attrs[user_id]
        my_interests = set(my_info["interests"])
        if not my_interests:
            return []
        # 已好友 + 黑名单全部排除
        exclude_users = set(self.get_direct_friends(user_id)) | self.blacklist
        exclude_users.add(user_id)

        # key:候选用户ID, value:匹配兴趣列表
        user_match_interests: Dict[int, List[str]] = defaultdict(list)
        for interest in my_interests:
            for candidate_uid in self.interest_index.get(interest, []):
                if candidate_uid not in exclude_users:
                    user_match_interests[candidate_uid].append(interest)

        # ========== 小顶堆实现TopK，替代全局sort（堆结构应用考点） ==========
        heap = []
        for cand_uid, inter_list in user_match_interests.items():
            score = len(inter_list)
            cand_name = self.user_attrs[cand_uid]["name"]
            item = (score, cand_uid, cand_name, inter_list)
            # 堆未满直接入堆
            if len(heap) < top_n:
                heapq.heappush(heap, item)
            else:
                # 堆已满，对比堆顶最小值，更大则替换
                if score > heap[0][0]:
                    heapq.heappop(heap)
                    heapq.heappush(heap, item)

        # 堆内结果升序，反转降序排列
        heap.sort(reverse=True, key=lambda x: (x[0], -x[1]))
        # 组装最终返回结构
        final_res = []
        for scr, uid, name, inters in heap:
            final_res.append((uid, name, scr, inters))
        return final_res

    # ===================== 原有保留算法接口 =====================
    def calc_degree_centrality(self) -> List[Tuple[int, int, str]]:
        """度中心性计算：统计每个用户好友数量，找出社群核心用户"""
        centrality_list = []
        for uid in self.user_attrs.keys():
            # 过滤黑名单后的有效好友数
            valid_friends = [f for f in self.graph[uid] if f not in self.blacklist]
            friend_count = len(valid_friends)
            uname = self.user_attrs[uid]["name"]
            centrality_list.append((uid, friend_count, uname))
        centrality_list.sort(key=lambda x: (-x[1], x[0]))
        return centrality_list

    def find_all_communities(self) -> List[List[int]]:
        """连通分量查找：划分社交网络所有独立社群，跳过黑名单节点"""
        visited = set()
        communities = []
        all_users = [uid for uid in self.user_attrs.keys() if uid not in self.blacklist]

        for uid in all_users:
            if uid not in visited:
                q = deque([uid])
                visited.add(uid)
                one_community = []
                while q:
                    cur = q.popleft()
                    one_community.append(cur)
                    for neighbor in self.graph[cur]:
                        if neighbor not in visited and neighbor not in self.blacklist:
                            visited.add(neighbor)
                            q.append(neighbor)
                one_community.sort()
                communities.append(one_community)
        return communities

    # ===================== 低优扩展预留：加权混合推荐接口（可后续填充） =====================
    def recommend_friends_weight_mix(self, user_id: int, top_n: int = 5) -> List:
        """扩展B：结合好友亲密度权重+共同兴趣混合评分推荐（预留实现入口）"""
        pass