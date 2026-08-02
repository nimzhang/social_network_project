from collections import defaultdict, deque
import csv
import os
import random
import time
from typing import Dict, Set, Tuple, List, Optional, Literal


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


# ========================【算法代码开始】========================
        # ======================== 新增功能1：人脉层级计算（可视化配色专用） ========================
    def get_user_degree_layer(self, center_user_id: int) -> Dict[int, int]:
        """
        以中心用户为原点，计算全网所有节点人脉层级，用于可视化颜色区分
        返回字典：{用户ID: 层级数值}
        层级定义：
            0: 中心用户自己
            1: 一度人脉（直接好友）→ 红色
            2: 二度人脉 → 橙色
            3及以上: 其余所有节点 → 灰色
        自动跳过黑名单节点（不纳入遍历）
        """
        if self.user_attrs.get(center_user_id) is None:
            return {}

        layer_map = defaultdict(int)
        visited = set()
        q = deque()
        q.append((center_user_id, 0))
        visited.add(center_user_id)
        layer_map[center_user_id] = 0

        while q:
            cur_uid, depth = q.popleft()
            # 超过2度不再深入遍历，统一归为灰色
            if depth >= 2:
                continue
            for neighbor in self.graph[cur_uid]:
                if neighbor in visited or neighbor in self.blacklist:
                    continue
                visited.add(neighbor)
                new_depth = depth + 1
                layer_map[neighbor] = new_depth
                q.append((neighbor, new_depth))

        # 剩余未遍历到的节点统一标记为3（其他人脉，灰色）
        all_uid_list = self.user_attrs.keys()
        for uid in all_uid_list:
            if uid not in layer_map and uid not in self.blacklist:
                layer_map[uid] = 3

        return dict(layer_map)

    # ===================== 【重构优化2：二度人脉择优路径，支持两种排序策略】 =====================
    def find_second_degree_with_path(
            self,
            user_id: int,
            sort_strategy: Literal["weight", "interest"] = "weight"
    ) -> List[Tuple[int, int, List[int]]]:
        """
        查询目标用户所有二度人脉，附带最优连接路径（不再取遍历第一条）
        :param user_id: 起始中心用户
        :param sort_strategy: 择优策略
            "weight": 按中间人好友总权重降序（亲密度最高中间人优先）
            "interest": 按中间人共同兴趣数量降序（兴趣契合优先）
        返回格式：[(二度用户ID, 最优中间好友ID, 完整路径列表)]
        约束规则：
        1. 排除自己、所有一度好友、黑名单用户
        2. 同一个二度用户仅保留最优1条路径
        3. 路径固定长度=3：[起点,中间人,二度好友]
        """
        if self.user_attrs.get(user_id) is None:
            return []

        first_friends = set(self.get_direct_friends(user_id))
        second_candidates = defaultdict(list)  # key:二度好友ID, value: [(中间人ID,路径)]

        # 第一步：收集所有可达二度人脉+全部可达中间人路径
        for mid_uid in first_friends:
            mid_friends = self.get_direct_friends(mid_uid)
            for sec_uid in mid_friends:
                # 过滤条件
                if sec_uid == user_id or sec_uid in first_friends or sec_uid in self.blacklist:
                    continue
                path = [user_id, mid_uid, sec_uid]
                second_candidates[sec_uid].append((mid_uid, path))

        # 第二步：对每个二度好友，按照策略选出最优中间人路径
        final_result = []
        user_base_interests = set(self.get_user_info(user_id)["interests"])

        for sec_uid, mid_path_list in second_candidates.items():
            score_list = []
            for mid_uid, path in mid_path_list:
                if sort_strategy == "weight":
                    # 策略1：中间人权重得分 = 用户与中间人之间的好友权重
                    edge_key = (min(user_id, mid_uid), max(user_id, mid_uid))
                    score = self.edge_weights.get(edge_key, 1)
                else:
                    # 策略2：中间人得分 = 和中心用户共同兴趣数量
                    mid_interests = set(self.get_user_info(mid_uid)["interests"])
                    score = len(user_base_interests & mid_interests)
                score_list.append((score, mid_uid, path))

            # 得分降序排序，取最高分第一条最优路径
            score_list.sort(key=lambda x: -x[0])
            best_score, best_mid, best_path = score_list[0]
            final_result.append((sec_uid, best_mid, best_path))

        return final_result

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

    # ===================== 优化3：Dijkstra懒加载实现，移除全节点预初始化 =====================
    def get_weighted_shortest_path(self, start_uid: int, end_uid: int) -> Tuple[int, List[int]]:
        """
        Dijkstra迪杰斯特拉算法：惰性更新实现，无需预先遍历所有用户初始化距离字典
        大数据量节点下内存占用更低、初始化耗时大幅缩短
        返回：(总权重, 路径列表) 不可达/黑名单返回 (-1, [])
        """
        if self.user_attrs.get(start_uid) is None or self.user_attrs.get(end_uid) is None:
            return -1, []
        if end_uid in self.blacklist:
            return -1, []
        if start_uid == end_uid:
            return 0, [start_uid]

        INF = float('inf')
        dist: Dict[int, int] = dict()       # 惰性创建：仅存入遍历到的节点
        prev_node: Dict[int, Optional[int]] = dict()
        dist[start_uid] = 0
        prev_node[start_uid] = None

        heap = MinHeap()
        heap.push(0, start_uid)

        while heap.size() > 0:
            cur_weight, cur_uid = heap.pop()
            if cur_uid == end_uid:
                break
            # 堆内存在过期旧记录，直接跳过
            if cur_weight > dist.get(cur_uid, INF):
                continue

            # 遍历邻接好友
            for neighbor in self.graph[cur_uid]:
                if neighbor in self.blacklist:
                    continue
                edge_key = (min(cur_uid, neighbor), max(cur_uid, neighbor))
                w = self.edge_weights[edge_key]
                new_dist = cur_weight + w

                # 节点未访问过 / 找到更短路径时更新
                if new_dist < dist.get(neighbor, INF):
                    dist[neighbor] = new_dist
                    prev_node[neighbor] = cur_uid
                    heap.push(new_dist, neighbor)

        if dist.get(end_uid, INF) == INF:
            return -1, []

        # 回溯生成路径
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
            uid_list = self.interest_index.get(interest)
            uid_list = uid_list if uid_list is not None else []
            for candidate_uid in uid_list:
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
        all_uids = self.user_attrs.keys()
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
        all_uids = self.user_attrs.keys()
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
            uid_list = self.interest_index.get(inter)
            uid_list = uid_list if uid_list is not None else []
            for uid in uid_list:
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

    # ======================== 新增功能4：大数据量生成 + 性能测试工具（1000用户/5000边） ========================
    def generate_big_test_data(self, user_num: int = 1000, edge_num: int = 5000):
        """
        随机生成大规模社交网络数据集
        :param user_num: 用户总数 默认1000
        :param edge_num: 好友边总数 默认5000
        """
        # 清空原有数据
        self.__init__()
        interest_pool = ["游戏", "阅读", "篮球", "电影", "音乐", "旅行", "美食", "编程", "摄影", "健身"]

        # 批量创建用户
        for uid in range(1, user_num + 1):
            name = f"用户{uid}"
            # 随机分配2~4个兴趣标签
            rand_interests = random.sample(interest_pool, k=random.randint(2, 4))
            self.add_user(uid, name, rand_interests)

        # 随机生成无向好友边，不重复、不自环
        created_edges = set()
        while len(created_edges) < edge_num:
            u = random.randint(1, user_num)
            v = random.randint(1, user_num)
            if u == v:
                continue
            edge_key = (min(u, v), max(u, v))
            if edge_key not in created_edges:
                weight = random.randint(1, 10)
                self.add_friendship(u, v, weight)
                created_edges.add(edge_key)
        print(f"✅ 大数据测试集生成完成：用户数={user_num}，好友边数={edge_num}")

    def run_performance_test(self, test_center_id: int = 1):
        """
        执行全套性能测试，打印各算法耗时
        测试项：N度人脉查询、BFS最短路径、Dijkstra加权路径、二度人脉择优查询
        """
        print("\n========== 大数据性能测试报告 ==========")
        # 1. 一度、二度人脉查询耗时
        start = time.perf_counter()
        self.find_n_degree_friends(test_center_id, 1)
        self.find_n_degree_friends(test_center_id, 2)
        t1 = time.perf_counter() - start
        print(f"1. 一度+二度人脉BFS查询耗时: {t1:.4f} s")

        # 2. BFS无权最短路径
        start = time.perf_counter()
        self.get_shortest_distance(test_center_id, random.randint(2, 1000))
        t2 = time.perf_counter() - start
        print(f"2. BFS无权最短路径查询耗时: {t2:.4f} s")

        # 3. Dijkstra加权最短路径（懒加载优化后）
        start = time.perf_counter()
        self.get_weighted_shortest_path(test_center_id, random.randint(2, 1000))
        t3 = time.perf_counter() - start
        print(f"3. Dijkstra加权路径(惰性更新)耗时: {t3:.4f} s")

        # 4. 择优二度人脉遍历
        start = time.perf_counter()
        self.find_second_degree_with_path(test_center_id, sort_strategy="weight")
        t4 = time.perf_counter() - start
        print(f"4. 择优二度人脉遍历耗时: {t4:.4f} s")

        # 5. 人脉层级计算（可视化配色）
        start = time.perf_counter()
        self.get_user_degree_layer(test_center_id)
        t5 = time.perf_counter() - start
        print(f"5. 全网人脉层级计算(可视化用)耗时: {t5:.4f} s")
        print("========================================\n")
# ========================【算法代码结束】========================

# 1. 定义顶层main函数
def main():
    """程序主入口函数，性能演示/整体运行入口"""
    # 这里放你原本要执行的所有主逻辑代码
    pass

# 2. 脚本直接运行时调用main
if __name__ == "__main__":
    main()
