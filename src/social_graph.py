from collections import defaultdict, deque
import csv
import os
from typing import Dict, Set, Tuple, List, Optional


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
