from collections import defaultdict, deque
import csv
import os
from typing import Dict, Set, Tuple, List, Optional


# ========================【数据结构代码开始】========================
# 1. 自主实现哈希表，链地址法，适配任意可哈希key（int/字符串等），替代原生dict存储user_attrs、interest_index
class HashTable:
    def __init__(self, capacity=100):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]

    def _hash(self, key):
        # 支持int、字符串等所有可哈希类型，不再限制仅整数取模
        return hash(key) % self.capacity

    def put(self, key, value):
        idx = self._hash(key)
        for index, (k, v) in enumerate(self.buckets[idx]):
            if k == key:
                self.buckets[idx][index] = (key, value)
                return
        self.buckets[idx].append((key, value))

    def get(self, key):
        idx = self._hash(key)
        for k, v in self.buckets[idx]:
            if k == key:
                return v
        return None

    def remove(self, key):
        idx = self._hash(key)
        for index, (k, v) in enumerate(self.buckets[idx]):
            if k == key:
                del self.buckets[idx][index]
                return True
        return False

    # 新增方法，适配GUI的 in 判断，无需改动GUI
    def __contains__(self, key):
        return self.get(key) is not None

    # 新增遍历全部键值对，适配遍历需求（遍历兴趣索引、遍历全部用户）
    def items(self):
        all_items = []
        for bucket in self.buckets:
            all_items.extend(bucket)
        return all_items

    # 新增获取所有key，适配循环遍历场景
    def keys(self):
        key_list = []
        for bucket in self.buckets:
            for k, v in bucket:
                key_list.append(k)
        return key_list

    # 新增删除指定key，适配del语法兼容
    def __delitem__(self, key):
        self.remove(key)


# 2. 自主实现小顶堆，完全弃用heapq
class MinHeap:
    def __init__(self):
        self.heap = []

    def _sift_up(self, idx):
        while idx > 0:
            parent_idx = (idx - 1) // 2
            if self.heap[idx][0] < self.heap[parent_idx][0]:
                self.heap[idx], self.heap[parent_idx] = self.heap[parent_idx], self.heap[idx]
                idx = parent_idx
            else:
                break

    def _sift_down(self, idx):
        total = len(self.heap)
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            min_pos = idx
            if left < total and self.heap[left][0] < self.heap[min_pos][0]:
                min_pos = left
            if right < total and self.heap[right][0] < self.heap[min_pos][0]:
                min_pos = right
            if min_pos != idx:
                self.heap[idx], self.heap[min_pos] = self.heap[min_pos], self.heap[idx]
                idx = min_pos
            else:
                break

    def push(self, priority, item):
        self.heap.append((priority, item))
        self._sift_up(len(self.heap) - 1)

    def pop(self):
        if not self.heap:
            return None
        top_data = self.heap[0]
        last_node = self.heap.pop()
        if self.heap:
            self.heap[0] = last_node
            self._sift_down(0)
        return top_data

    def size(self):
        return len(self.heap)


class SocialGraph:
    def __init__(self):
        """初始化社交网络图核心数据结构"""
        # 邻接表：用户ID -> 好友ID集合（无向图）
        self.graph: Dict[int, Set[int]] = defaultdict(set)
        # 【修改】替换原生字典为自研哈希表
        self.user_attrs = HashTable()
        # 关系权重：(较小用户ID, 较大用户ID) -> 权重值（避免重复存储）
        self.edge_weights: Dict[Tuple[int, int], int] = {}
        # 【改造】兴趣倒排索引彻底替换为自研HashTable，不再使用原生dict
        self.interest_index: HashTable = HashTable()
        # ===================== 新增：黑名单集合（中优3 扩展A） =====================
        self.blacklist: Set[int] = set()

    # ===================== 黑名单全套接口（扩展A 完整实现） =====================
    def add_to_blacklist(self, user_id: int) -> bool:
        """将用户加入黑名单，不存在用户返回false"""
        if self.user_attrs.get(user_id) is None:
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
        """清空黑名单（测试用例重置环境）"""
        self.blacklist.clear()

    # ===================== 完善：删除好友、删除用户两个核心方法（加固边界逻辑） =====================
    def delete_friendship(self, user1: int, user2: int) -> bool:
        """
        双向删除好友关系，同步清理边权重
        返回值：True=删除成功，False=用户不存在/并非好友/重复删除
        """
        # 校验两个用户都存在
        if self.user_attrs.get(user1) is None or self.user_attrs.get(user2) is None:
            return False
        # 校验二者互为好友
        if user2 not in self.graph[user1] or user1 not in self.graph[user2]:
            return False
        # 双向移除邻接表好友
        self.graph[user1].discard(user2)
        self.graph[user2].discard(user1)
        # 删除权重记录
        edge_key = (min(user1, user2), max(user1, user2))
        self.edge_weights.pop(edge_key, None)
        return True

    def delete_user(self, user_id: int) -> bool:
        """
        删除用户节点全链路清理：
        1. 断开所有双向好友关系 2. 删除邻接表记录 3. 哈希表销毁用户数据
        4. 兴趣索引剔除该用户 5. 黑名单移除该用户
        返回：True删除成功 / False用户不存在
        """
        if self.user_attrs.get(user_id) is None:
            return False

        # 拷贝好友列表遍历，避免遍历中集合变动报错
        friend_list = list(self.graph.get(user_id, set()))
        for fid in friend_list:
            self.delete_friendship(user_id, fid)

        # 删除邻接表该用户条目
        self.graph.pop(user_id, None)
        # 取出用户兴趣数据后删除哈希表内用户
        user_info = self.user_attrs.get(user_id)
        self.user_attrs.remove(user_id)

        # 遍历兴趣倒排索引，移除当前用户ID（适配自研HashTable）
        if user_info and "interests" in user_info:
            interests = user_info["interests"]
            all_interest_tags = self.interest_index.keys()
            for tag in interests:
                if tag in self.interest_index:
                    uid_list = self.interest_index.get(tag)
                    if user_id in uid_list:
                        uid_list.remove(user_id)
                        self.interest_index.put(tag, uid_list)
            # 清理空兴趣分类（无用户的兴趣删掉）
            empty_tags = []
            for tag in self.interest_index.keys():
                uid_arr = self.interest_index.get(tag)
                if len(uid_arr) == 0:
                    empty_tags.append(tag)
            for tag in empty_tags:
                del self.interest_index[tag]

        # 黑名单同步移除
        if user_id in self.blacklist:
            self.blacklist.remove(user_id)
        return True

    # ===================== 原有基础增删改查（适配哈希表+全局黑名单过滤） =====================
    def add_user(self, user_id: int, name: str, interests: List[str] = None) -> bool:
        """添加用户，校验ID合法性，维护兴趣索引"""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"用户ID必须为正整数，当前输入：{user_id}")
        if self.user_attrs.get(user_id) is not None:
            print(f"警告：用户ID {user_id} 已存在，跳过添加")
            return False
        user_data = {
            'name': name.strip(),
            'interests': interests if interests else []
        }
        self.user_attrs.put(user_id, user_data)
        self._update_interest_index(user_id, interests)
        return True

    def _update_interest_index(self, user_id: int, interests: List[str]) -> None:
        """私有方法维护兴趣倒排索引，给智能推荐提供数据（适配自研HashTable）"""
        if not interests:
            return
        for interest in interests:
            interest = interest.strip()
            if interest not in self.interest_index:
                self.interest_index.put(interest, [])
            uid_list = self.interest_index.get(interest)
            if user_id not in uid_list:
                uid_list.append(user_id)
                self.interest_index.put(interest, uid_list)

    def add_friendship(self, user1: int, user2: int, weight: int = 1) -> bool:
        """
        统一方法名：全程使用 add_friendship
        无向图双向添加好友，适配直接好友、社交距离模块
        """
        if user1 <= 0 or user2 <= 0:
            raise ValueError(f"用户ID必须为正整数，当前输入：{user1}, {user2}")
        if user1 == user2:
            raise ValueError("用户不能与自身建立好友关系")
        if self.user_attrs.get(user1) is None:
            raise ValueError(f"用户 {user1} 不存在，请先添加用户")
        if self.user_attrs.get(user2) is None:
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
        if self.user_attrs.get(user_id) is None:
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
        info = self.user_attrs.get(user_id)
        if info is None:
            return {"name": "未知用户", "interests": []}
        return info
# ========================【数据结构代码结束】========================

# ========================【算法代码开始】========================
    # ===================== 【重点修复】带路径二度人脉查询（去重+严格过滤黑名单+固定路径长度3） =====================
    def find_second_degree_with_path(self, user_id: int) -> List[Tuple[int, int, List[int]]]:
        """
        查询目标用户所有二度人脉，附带连接路径
        返回格式：[(二度用户ID, 中间好友ID, 完整路径列表)]
        约束规则（完全适配pytest断言）：
        1. 排除自己、所有一度好友、黑名单用户
        2. 同一个二度用户只保留1条路径（去重）
        3. 路径固定长度=3：[起点,中间人,二度好友]
        4. 自动屏蔽黑名单节点
        """
        if self.user_attrs.get(user_id) is None:
            return []

        # 获取过滤黑名单后的一度好友集合
        first_friends = set(self.get_direct_friends(user_id))
        visited_second = set()  # 记录已经加入结果的二度用户，去重
        result = []

        # 遍历每一个中间一级好友
        for mid_uid in first_friends:
            # 获取中间人过滤黑名单后的好友列表
            mid_all_friends = self.get_direct_friends(mid_uid)
            for sec_uid in mid_all_friends:
                # 多重筛选条件
                if (sec_uid == user_id  # 排除自己
                        or sec_uid in first_friends  # 排除一度好友
                        or sec_uid in visited_second  # 去重二度节点
                        or sec_uid in self.blacklist):  # 排除黑名单
                    continue

                visited_second.add(sec_uid)
                path = [user_id, mid_uid, sec_uid]
                result.append((sec_uid, mid_uid, path))

        return result

    # ===================== 高优需求2：统一N度人脉标准接口（收拢所有人脉BFS逻辑） =====================
    def find_n_degree_friends(self, user_id: int, n: int) -> List[int]:
        """
        【核心收拢接口】通用N度人脉查询统一标准方法
        :param user_id: 起始用户ID
        :param n: 人脉度数（1=一度好友，2=二度好友）
        :return: 升序N度好友ID列表，自动过滤黑名单
        ✅ 所有GUI层一度、二度、多度人脉查询全部调用本接口
        ✅ GUI不再手写任何BFS遍历逻辑，严格遵循MVC分层
        """
        if self.user_attrs.get(user_id) is None or n <= 0:
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
        if self.user_attrs.get(start_uid) is None or self.user_attrs.get(end_uid) is None:
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
                    q = deque()  # 清空队列提前退出循环，减少无效遍历
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
        if self.user_attrs.get(start_uid) is None or self.user_attrs.get(end_uid) is None:
            return -1, []
        if end_uid in self.blacklist:
            return -1, []
        if start_uid == end_uid:
            return 0, [start_uid]

        INF = float('inf')
        # 遍历哈希表取出全部用户ID
        all_uids = []
        for bucket in self.user_attrs.buckets:
            for k, v in bucket:
                all_uids.append(k)
        dist: Dict[int, int] = {uid: INF for uid in all_uids}
        prev_node: Dict[int, Optional[int]] = {uid: None for uid in all_uids}
        dist[start_uid] = 0
        heap = MinHeap()
        heap.push(0, start_uid)

        while heap.size() > 0:
            cur_weight, cur_uid = heap.pop()
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
                    heap.push(dist[neighbor], neighbor)

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

    # ===================== 中优1+2：自研小顶堆TopK兴趣推荐 + 推荐理由详情 =====================
    def recommend_friends_by_interest(self, user_id: int, top_n: int = 5) -> List[Tuple[int, str, int, List[str]]]:
        """
        基于兴趣重合度推荐陌生好友：自研小顶堆实现TopK（不全局排序全量用户）
        返回结构：[(用户ID, 用户名, 共同兴趣数量, 共同兴趣名称列表)]
        ✅ 补齐推荐理由：直接返回具体共同兴趣清单，满足任务书扩展C要求
        自动排除：自身、好友、黑名单用户
        """
        user_info = self.user_attrs.get(user_id)
        if user_info is None:
            return []
        my_interests = set(user_info["interests"])
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

        # ========== 完全替换为自研MinHeap，删除heapq依赖，TopK渐进筛选 ==========
        heap = MinHeap()
        for cand_uid, inter_list in user_match_interests.items():
            score = len(inter_list)
            cand_name = self.user_attrs.get(cand_uid)["name"]
            item = (score, cand_uid, cand_name, inter_list)
            if heap.size() < top_n:
                heap.push(score, item)
            else:
                top_score, top_item = heap.pop()
                if score > top_score:
                    heap.push(score, item)
                else:
                    heap.push(top_score, top_item)

        # 取出堆内所有元素，降序排列（兴趣多的在前）
        temp_list = []
        while heap.size() > 0:
            s, data = heap.pop()
            temp_list.append(data)
        temp_list.sort(reverse=True, key=lambda x: (x[0], -x[1]))

        final_res = []
        for scr, uid, name, inters in temp_list:
            final_res.append((uid, name, scr, inters))
        return final_res

    # ===================== 原有保留算法接口（全部兼容黑名单过滤） =====================
    def calc_degree_centrality(self) -> List[Tuple[int, int, str]]:
        """度中心性计算：统计每个用户好友数量，找出社群核心用户"""
        centrality_list = []
        # 遍历哈希表全部用户
        all_uids = []
        for bucket in self.user_attrs.buckets:
            for k, v in bucket:
                all_uids.append(k)
        for uid in all_uids:
            # 过滤黑名单后的有效好友数
            valid_friends = [f for f in self.graph[uid] if f not in self.blacklist]
            friend_count = len(valid_friends)
            uname = self.user_attrs.get(uid)["name"]
            centrality_list.append((uid, friend_count, uname))
        centrality_list.sort(key=lambda x: (-x[1], x[0]))
        return centrality_list

    def find_all_communities(self) -> List[List[int]]:
        """连通分量查找：划分社交网络所有独立社群，跳过黑名单节点"""
        visited = set()
        communities = []
        all_uids = []
        for bucket in self.user_attrs.buckets:
            for k, v in bucket:
                all_uids.append(k)
        all_users = [uid for uid in all_uids if uid not in self.blacklist]

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

    # ===================== 低优扩展B：加权混合推荐完整预留框架 =====================
    def recommend_friends_weight_mix(self, user_id: int, top_n: int = 5) -> List[Tuple[int, str, float, List[str]]]:
        """
        扩展B：结合好友亲密度权重+共同兴趣混合评分推荐
        混合公式示例：综合得分 = 共同兴趣数 * 0.6 + 好友亲密度均值 * 0.4
        返回：[(用户ID, 姓名, 综合得分, 共同兴趣列表)]
        """
        user_info = self.user_attrs.get(user_id)
        if not user_info:
            return []
        my_interests = set(user_info["interests"])
        exclude = set(self.get_direct_friends(user_id)) | self.blacklist | {user_id}

        # 1. 获取兴趣匹配用户
        match_dict: Dict[int, List[str]] = defaultdict(list)
        for inter in my_interests:
            for uid in self.interest_index.get(inter, []):
                if uid not in exclude:
                    match_dict[uid].append(inter)

        # 2. 遍历候选，计算混合分数
        heap = MinHeap()
        for cand_uid, inters in match_dict.items():
            interest_score = len(inters)
            # 计算候选用户与我方圈子亲密度均值
            total_weight = 0
            friend_cnt = 0
            for mid_friend in self.get_direct_friends(user_id):
                if cand_uid in self.graph[mid_friend]:
                    key = (min(mid_friend, cand_uid), max(mid_friend, cand_uid))
                    total_weight += self.edge_weights.get(key, 1)
                    friend_cnt += 1
            avg_weight = total_weight / friend_cnt if friend_cnt > 0 else 0
            mix_score = round(interest_score * 0.6 + avg_weight * 0.4, 2)

            cand_name = self.user_attrs.get(cand_uid)["name"]
            item = (mix_score, cand_uid, cand_name, inters)
            if heap.size() < top_n:
                heap.push(mix_score, item)
            else:
                top_s, top_item = heap.pop()
                if mix_score > top_s:
                    heap.push(mix_score, item)
                else:
                    heap.push(top_s, top_item)

        # 结果降序输出
        res = []
        while heap.size():
            s, data = heap.pop()
            res.append((data[1], data[2], s, data[3]))
        res.sort(reverse=True, key=lambda x: x[2])
        return res
# ========================【算法代码结束】========================