from collections import defaultdict, deque
import csv
import os
from typing import Dict, Set, Tuple, List, Optional


# ========================【数据结构代码开始】========================
# 1. 自主实现哈希表，链地址法，替代原生dict存储user_attrs
class HashTable:
    def __init__(self, capacity=100):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]

    def _hash(self, key):
        return key % self.capacity

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
        # 兴趣倒排索引，适配智能推荐模块
        self.interest_index: Dict[str, List[int]] = {}
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

        # 遍历兴趣倒排索引，移除当前用户ID
        if user_info and "interests" in user_info:
            interests = user_info["interests"]
            for tag in interests:
                if tag in self.interest_index and user_id in self.interest_index[tag]:
                    self.interest_index[tag].remove(user_id)
            # 清理空兴趣分类（无用户的兴趣删掉）
            empty_tags = [k for k, v in self.interest_index.items() if len(v) == 0]
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