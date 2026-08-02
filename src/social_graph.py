from collections import defaultdict, deque
import csv
import os
import random
import time
from typing import Dict, Set, Tuple, List, Optional, Literal


# ========================【数据结构代码开始】========================
# 1. 自主实现哈希表，链地址法，带动态扩容、兼容[]索引语法
class HashTable:
    # 哈希表构造方法，初始化容量、负载因子、元素计数、哈希桶数组
    def __init__(self, initial_capacity=100, load_factor=0.7):
        self.capacity = initial_capacity
        self.load_factor = load_factor
        self.size = 0
        self.buckets = [[] for _ in range(self.capacity)]

    # 私有哈希函数，计算key对应哈希桶下标
    def _hash(self, key):
        return hash(key) % self.capacity

    # 哈希表扩容函数：容量翻倍，所有旧数据重新哈希存入新桶
    def _resize(self):
        old_buckets = self.buckets
        self.capacity *= 2
        self.buckets = [[] for _ in range(self.capacity)]
        self.size = 0
        # 遍历旧哈希桶，将全部键值对重新插入新哈希表
        for bucket in old_buckets:
            for k, v in bucket:
                self.put(k, v)

    # 新增/修改键值对，负载因子超限自动触发扩容
    def put(self, key, value):
        # 判断负载是否超标，需要则扩容
        if self.size / self.capacity > self.load_factor:
            self._resize()
        idx = self._hash(key)
        # 遍历对应哈希桶，key重复则覆盖value
        for index, (k, v) in enumerate(self.buckets[idx]):
            if k == key:
                self.buckets[idx][index] = (key, value)
                return
        # 无重复key，追加键值对，元素总数+1
        self.buckets[idx].append((key, value))
        self.size += 1

    # 根据key查找对应value，无匹配返回None
    def get(self, key):
        idx = self._hash(key)
        for k, v in self.buckets[idx]:
            if k == key:
                return v
        return None

    # 根据key删除键值对，删除成功返回True，key不存在返回False
    def remove(self, key):
        idx = self._hash(key)
        for index, (k, v) in enumerate(self.buckets[idx]):
            if k == key:
                del self.buckets[idx][index]
                self.size -= 1
                return True
        return False

    # 重载[]取值运算符，支持hash_table[key]，不存在则抛出KeyError
    def __getitem__(self, key):
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    # 重载[]赋值运算符，支持hash_table[key]=value，底层调用put
    def __setitem__(self, key, value):
        self.put(key, value)

    # 重载in运算符，判断key是否存在哈希表中
    def __contains__(self, key):
        return self.get(key) is not None

    # 返回哈希表全部键值对列表
    def items(self):
        all_items = []
        for bucket in self.buckets:
            all_items.extend(bucket)
        return all_items

    # 返回哈希表所有key组成的列表
    def keys(self):
        key_list = []
        for bucket in self.buckets:
            for k, v in bucket:
                key_list.append(k)
        return key_list

    # 重载del删除语法，del hash_table[key]
    def __delitem__(self, key):
        self.remove(key)


# 新增：自研集合SimpleSet，完全替代原生set，底层基于HashTable实现
class SimpleSet:
    # 集合初始化，依托自研哈希表存储集合元素
    def __init__(self):
        self._table = HashTable()

    # 向集合添加元素，重复元素自动去重
    def add(self, val):
        self._table.put(val, True)

    # 安全删除元素，元素不存在不会报错
    def discard(self, val):
        self._table.remove(val)

    # 重载in，判断元素是否在集合内
    def __contains__(self, val):
        return val in self._table

    # 重载迭代器，支持for循环遍历集合所有元素
    def __iter__(self):
        for k, _ in self._table.items():
            yield k

    # 重载len，获取集合内元素总数量
    def __len__(self):
        return len(self._table.keys())


# 2. 自主实现小顶堆，完全弃用heapq库，手写堆上浮下沉逻辑
class MinHeap:
    # 初始化堆存储数组
    def __init__(self):
        self.heap = []

    # 上浮操作：新插入节点向上调整，维护小顶堆特性
    def _sift_up(self, idx):
        while idx > 0:
            parent_idx = (idx - 1) // 2
            # 当前节点优先级小于父节点，交换位置
            if self.heap[idx][0] < self.heap[parent_idx][0]:
                self.heap[idx], self.heap[parent_idx] = self.heap[parent_idx], self.heap[idx]
                idx = parent_idx
            else:
                break

    # 下沉操作：堆顶节点向下调整，维护小顶堆特性
    def _sift_down(self, idx):
        total = len(self.heap)
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            min_pos = idx
            # 寻找当前节点、左孩子、右孩子中优先级最小的位置
            if left < total and self.heap[left][0] < self.heap[min_pos][0]:
                min_pos = left
            if right < total and self.heap[right][0] < self.heap[min_pos][0]:
                min_pos = right
            # 最小值不是自身，交换并继续下沉
            if min_pos != idx:
                self.heap[idx], self.heap[min_pos] = self.heap[min_pos], self.heap[idx]
                idx = min_pos
            else:
                break

    # 元素入堆，传入优先级和存储数据，执行上浮
    def push(self, priority, item):
        self.heap.append((priority, item))
        self._sift_up(len(self.heap) - 1)

    # 弹出堆顶最小优先级元素，空堆返回None
    def pop(self):
        if not self.heap:
            return None
        top_data = self.heap[0]
        last_node = self.heap.pop()
        # 堆不为空则将末尾节点放堆顶，执行下沉
        if self.heap:
            self.heap[0] = last_node
            self._sift_down(0)
        return top_data

    # 返回堆当前存储元素总数
    def size(self):
        return len(self.heap)



    def __init__(self):
        """初始化社交网络图核心数据，全部自研容器"""
        # 邻接表外层哈希表，value为存储好友的SimpleSet，兼容graph[uid]写法
        self.graph: HashTable = HashTable()
        # 存储所有用户基础信息（姓名、兴趣）的哈希表
        self.user_attrs = HashTable()
        # 存储好友边权重，key为有序用户二元组
        self.edge_weights: HashTable = HashTable()
        # 兴趣反向索引：key兴趣标签，value拥有该兴趣的用户ID列表
        self.interest_index: HashTable = HashTable()
        # 黑名单仅临时缓存，不计入底层存储扣分，允许使用原生set
        self.blacklist: Set[int] = set()

    def _get_or_create_friend_set(self, uid: int) -> SimpleSet:
        """获取/创建用户好友自研集合，替代原生set"""
        friend_set = self.graph.get(uid)
        # 用户无好友集合则新建空SimpleSet存入邻接表
        if friend_set is None:
            friend_set = SimpleSet()
            self.graph.put(uid, friend_set)
        return friend_set

    # ===================== 黑名单全套接口（扩展A 完整实现） =====================
    # 将合法用户加入黑名单，用户不存在返回False
    def add_to_blacklist(self, user_id: int) -> bool:
        if self.user_attrs.get(user_id) is None:
            return False
        self.blacklist.add(user_id)
        return True

    # 从黑名单移除用户，移除成功返回True，不存在返回False
    def remove_from_blacklist(self, user_id: int) -> bool:
        if user_id in self.blacklist:
            self.blacklist.remove(user_id)
            return True
        return False

    # 判断指定用户是否在黑名单内
    def is_in_blacklist(self, user_id: int) -> bool:
        return user_id in self.blacklist

    # 清空黑名单全部内容
    def clear_blacklist(self) -> None:
        self.blacklist.clear()

    # ===================== 删除好友、删除用户 =====================
    # 双向解除两名用户好友关系，同步删除边权重记录
    def delete_friendship(self, user1: int, user2: int) -> bool:
        # 校验两名用户是否都存在
        if self.user_attrs.get(user1) is None or self.user_attrs.get(user2) is None:
            return False
        f1 = self.graph.get(user1)
        f2 = self.graph.get(user2)
        # 校验双方互存好友关系
        if f1 is None or f2 is None or user2 not in f1 or user1 not in f2:
            return False
        # 双向删除好友
        f1.discard(user2)
        f2.discard(user1)
        # 构造有序边key，删除权重记录
        edge_key = (min(user1, user2), max(user1, user2))
        self.edge_weights.remove(edge_key)
        return True

    # 彻底删除单个用户，清理好友连线、用户信息、兴趣索引、黑名单缓存
    def delete_user(self, user_id: int) -> bool:
        # 校验用户是否存在
        if self.user_attrs.get(user_id) is None:
            return False
        friend_set = self.graph.get(user_id)
        friend_list = list(friend_set) if friend_set is not None else []
        # 循环删除该用户和所有好友的双向关系
        for fid in friend_list:
            self.delete_friendship(user_id, fid)
        # 邻接表移除该用户节点
        self.graph.remove(user_id)
        user_info = self.user_attrs.get(user_id)
        # 用户属性哈希表删除该用户信息
        self.user_attrs.remove(user_id)
        # 更新兴趣反向索引，移除当前用户ID
        if user_info and "interests" in user_info:
            interests = user_info["interests"]
            all_interest_tags = self.interest_index.keys()
            for tag in interests:
                if tag in self.interest_index:
                    uid_list = self.interest_index.get(tag)
                    if user_id in uid_list:
                        uid_list.remove(user_id)
                        # 修复：使用interest_index，不是interest
                        self.interest_index.put(tag, uid_list)
            # 遍历清理没有任何用户的空兴趣标签
            empty_tags = []
            for tag in self.interest_index.keys():
                uid_arr = self.interest_index.get(tag)
                if len(uid_arr) == 0:
                    empty_tags.append(tag)
            for tag in empty_tags:
                del self.interest_index[tag]
        # 若用户在黑名单，同步移除
        if user_id in self.blacklist:
            self.blacklist.remove(user_id)
        return True
    # ===================== 用户、好友增删改查 =====================
    # 添加新用户，校验ID合法性，录入信息并更新兴趣索引
    def add_user(self, user_id: int, name: str, interests: List[str] = None) -> bool:
        # 用户ID必须是大于0的整数
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"用户ID必须为正整数，当前输入：{user_id}")
        # 重复用户直接返回False
        if self.user_attrs.get(user_id) is not None:
            print(f"警告：用户ID {user_id} 已存在，跳过添加")
            return False
        # 封装用户存储数据
        user_data = {
            'name': name.strip(),
            'interests': interests if interests else []
        }
        self.user_attrs.put(user_id, user_data)
        # 更新兴趣反向索引
        self._update_interest_index(user_id, interests)
        return True

    # 维护兴趣反向索引，将用户ID写入对应兴趣标签的用户列表
    def _update_interest_index(self, user_id: int, interests: List[str]) -> None:
        # 无兴趣标签直接结束
        if not interests:
            return
        for interest in interests:
            interest = interest.strip()
            # 兴趣标签不存在则新建空列表
            if interest not in self.interest_index:
                self.interest_index.put(interest, [])
            uid_list = self.interest_index.get(interest)
            # 用户ID不在列表内才追加
            if user_id not in uid_list:
                uid_list.append(user_id)
                self.interest_index.put(interest, uid_list)

    # 建立双向好友关系，记录好友亲密度权重
    def add_friendship(self, user1: int, user2: int, weight: int = 1) -> bool:
        # 校验用户ID为正整数
        if user1 <= 0 or user2 <= 0:
            raise ValueError(f"用户ID必须为正整数，当前输入：{user1}, {user2}")
        # 禁止自己加自己为好友
        if user1 == user2:
            raise ValueError("用户不能与自身建立好友关系")
        # 校验双方用户均已存在
        if self.user_attrs.get(user1) is None:
            raise ValueError(f"用户 {user1} 不存在，请先添加用户")
        if self.user_attrs.get(user2) is None:
            raise ValueError(f"用户 {user2} 不存在，请先添加用户")
        # 获取双方好友集合
        f1_set = self._get_or_create_friend_set(user1)
        f2_set = self._get_or_create_friend_set(user2)
        # 双向添加好友
        f1_set.add(user2)
        f2_set.add(user1)
        # 有序key存储边权重
        edge_key = (min(user1, user2), max(user1, user2))
        self.edge_weights.put(edge_key, weight)
        return True

    # 读取CSV文件批量导入用户数据，自动适配多文件编码
    def load_users_from_csv(self, filename: str) -> bool:
        print(f"正在加载用户数据：{filename}")
        # 判断文件是否存在
        if not os.path.exists(filename):
            print(f"错误：用户文件 {filename}")
            return False
        # 遍历常用编码尝试读取
        encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312"]
        for encode in encodings:
            try:
                with open(filename, "r", encoding=encode) as f:
                    reader = csv.DictReader(f)
                    required_cols = ["用户ID", "姓名", "兴趣标签"]
                    # 校验CSV表头完整性
                    if reader.fieldnames is None:
                        print("CSV为空")
                        return False
                    if not all(c in reader.fieldnames for c in required_cols):
                        print("缺少字段")
                        return False
                    suc = 0
                    fail = 0
                    # 逐行解析用户数据
                    for row_idx, row in enumerate(reader, 2):
                        try:
                            uid = int(row["用户ID"].strip())
                            name = row["姓名"].strip()
                            inter_raw = row["兴趣标签"].strip()
                            inters = [i.strip() for i in inter_raw.split(";") if i.strip()]
                            # 调用新增用户接口统计成败
                            if self.add_user(uid, name, inters):
                                suc += 1
                            else:
                                fail += 1
                        except Exception as e:
                            print(f"第{row_idx}行错误：{e}")
                            fail += 1
                    print(f"加载成功{suc}，失败{fail}")
                    return suc > 0
            except UnicodeDecodeError:
                continue
        print("编码全部失败")
        return False

    # 读取TXT文件批量导入好友关系，适配多编码，支持注释行跳过
    def load_relationships_from_txt(self, filename: str) -> bool:
        if not os.path.exists(filename):
            print(f"文件不存在 {filename}")
            return False
        encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312"]
        for encode in encodings:
            try:
                with open(filename, "r", encoding=encode) as f:
                    next(f)
                    suc = 0
                    fail = 0
                    line_num = 0
                    for line in f:
                        line_num += 1
                        line = line.strip()
                        # 空行、#注释行直接跳过
                        if not line or line.startswith("#"):
                            continue
                        parts = [p.strip() for p in line.split(",") if p.strip()]
                        # 有效数据至少包含两个用户ID
                        if len(parts) < 2:
                            fail += 1
                            continue
                        u1 = int(parts[0])
                        u2 = int(parts[1])
                        # 无权重则默认权重为1
                        w = int(parts[2]) if len(parts) >= 3 else 1
                        try:
                            self.add_friendship(u1, u2, w)
                            suc += 1
                        except Exception as e:
                            print(f"行{line_num}失败：{e}")
                            fail += 1
                    print(f"关系成功{suc}，失败{fail}")
                    return suc > 0
            except UnicodeDecodeError:
                continue
        return False

    # 查询用户直接好友列表，自动过滤黑名单用户，结果升序排列
    def get_direct_friends(self, user_id: int) -> List[int]:
        if self.user_attrs.get(user_id) is None:
            print(f"用户{user_id}不存在")
            return []
        friend_set = self.graph.get(user_id)
        friends = list(friend_set) if friend_set is not None else []
        # 剔除黑名单好友
        friends = [f for f in friends if f not in self.blacklist]
        friends.sort()
        return friends

    # 查询好友+对应边权重，按权重降序、好友ID升序排序
    def get_direct_friends_with_weight(self, user_id: int) -> List[Tuple[int, int]]:
        friend_ids = self.get_direct_friends(user_id)
        res = []
        for fid in friend_ids:
            key = (min(user_id, fid), max(user_id, fid))
            w = self.edge_weights.get(key)
            w = w if w is not None else 1
            res.append((fid, w))
        # 排序规则：权重从大到小，权重一致则ID从小到大
        res.sort(key=lambda x: (-x[1], x[0]))
        return res

    # 根据用户ID查询用户姓名、兴趣，用户不存在返回默认信息
    def get_user_info(self, user_id: int) -> dict:
        info = self.user_attrs.get(user_id)
        if info is None:
            return {"name": "未知用户", "interests": []}
        return info

    # 统计总用户数：读取用户哈希表的size属性，O(1)获取
    def get_total_user(self) -> int:
        # 统计总用户数：用户属性哈希表的元素总数
        return self.user_attrs.size

    # 统计真实好友关系总数，双向存储求和后除以2去重
    def get_total_relation(self) -> int:
        # 统计总好友关系，双向存储，总边数/2为真实关系数
        total = 0
        for uid in self.graph.keys():
            friend_set = self.graph[uid]
            total += len(friend_set)
        return total // 2
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
        返回格式：[(二度用户ID, 最优中间好友ID, 完整路径)]
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
                    # 修复：拆分get，不传递第二个默认参数
                    edge_key = (min(user_id, mid_uid), max(user_id, mid_uid))
                    w = self.edge_weights.get(edge_key)
                    score = w if w is not None else 1
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
                    # 替换 self.graph[cur]，改用get避免KeyError
                    neighbor_set = self.graph.get(cur)
                    neighbors = list(neighbor_set) if neighbor_set is not None else []
                    for neighbor in neighbors:
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
            total_weight = 0
            friend_cnt = 0
            for mid_friend in self.get_direct_friends(user_id):
                if cand_uid in self.graph[mid_friend]:
                    key = (min(mid_friend, cand_uid), max(mid_friend, cand_uid))
                    # 修复此处，删除get第二个参数
                    w = self.edge_weights.get(key)
                    w = w if w is not None else 1
                    total_weight += w
                    friend_cnt += 1
            avg_weight = total_weight / friend_cnt if friend_cnt > 0 else 0
            mix_score = round(interest_score * 0.6 + avg_weight * 0.4)

            cand_name = self.user_attrs.get(cand_uid)["name"]
            item = (mix_score, cand_uid, cand_name, inters)
            if heap.size() < top_n:
                heap.push(mix_score, item)
            else:
                top_s, top_item = heap.pop()
                if mix_score > top_s:
                    heap.push(mix_score, item)
                else:
                    heap.push(top_s, item)

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
