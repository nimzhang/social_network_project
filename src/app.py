import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu
from tkinter.scrolledtext import ScrolledText
import os, webbrowser, datetime, threading
from typing import List, Tuple
from src.social_graph import SocialGraph

# ===================== 全局配置 =====================
WIN_TITLE = "社交网络图谱分析系统"
WIN_SIZE = "1000x650"
FONT = ("微软雅黑", 10)
TAG_COLORS = {
    "title":   "#553399",
    "info":    "#0066cc",
    "success": "#008822",
    "warning": "#cc8800",
    "error":   "#cc2222",
    "detail":  "#555555"
}
# 统一排序策略
SORT_OPTIONS = ["按ID升序", "按亲密度降序", "按共同兴趣降序"]
DEFAULT_SORT = "按亲密度降序"


class SocialNetworkGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(WIN_TITLE)
        self.root.geometry(WIN_SIZE)
        self.root.minsize(800, 550)
        self.root.option_add("*Font", FONT)

        # 核心模型与状态
        self.graph = SocialGraph()
        self.current_uid = None
        self.is_loading = False
        base = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(os.path.dirname(base), "data")

        # 输入变量
        self.uid_var = tk.StringVar()
        self.end_uid_var = tk.StringVar()
        self.degree_var = tk.StringVar(value="3")
        self.topk_var = tk.StringVar(value="5")
        self.weight_mode = tk.BooleanVar(value=False)
        self.sort_var = tk.StringVar(value=DEFAULT_SORT)

        # 新增/管理变量
        self.new_uid_var = tk.StringVar()
        self.new_name_var = tk.StringVar()
        self.new_inter_var = tk.StringVar()
        self.target_uid_var = tk.StringVar()
        self.weight_var = tk.StringVar(value="1")
        self.black_uid_var = tk.StringVar()

        # 可视化选项
        self.hide_black = tk.BooleanVar(value=False)
        self.only_subgraph = tk.BooleanVar(value=False)

        # 构建界面
        self._create_menu()
        self._build_layout()
        self._bind_shortcuts()

        # 自动加载默认数据
        self._async_load_default()

    # ===================== 菜单栏 =====================
    def _create_menu(self) -> None:
        bar = Menu(self.root)
        # 文件
        f = Menu(bar, tearoff=0)
        f.add_command(label="加载用户CSV", command=self._load_user_file)
        f.add_command(label="加载关系TXT", command=self._load_rel_file)
        f.add_separator()
        f.add_command(label="退出", command=self.root.quit)
        bar.add_cascade(label="文件", menu=f)
        # 分析
        s = Menu(bar, tearoff=0)
        s.add_command(label="社群划分", command=self._show_communities)
        s.add_command(label="度中心性排行", command=self._show_centrality)
        s.add_separator()
        s.add_command(label="清空输出", command=self._clear_all, accelerator="Ctrl+L")
        bar.add_cascade(label="分析工具", menu=s)
        # 可视化
        v = Menu(bar, tearoff=0)
        v.add_checkbutton(label="隐藏黑名单用户", variable=self.hide_black)
        v.add_checkbutton(label="仅显示当前用户子网络", variable=self.only_subgraph)
        v.add_separator()
        v.add_command(label="生成网络图", command=self._generate_graph)
        bar.add_cascade(label="可视化", menu=v)
        # 帮助
        h = Menu(bar, tearoff=0)
        h.add_command(label="使用说明", command=lambda: messagebox.showinfo("说明",
            "1. 输入ID点确认设为查询目标\n2. 点击按钮查询人脉/距离\n3. 支持增删用户、好友、黑名单\n4. 快捷键：回车确认，Ctrl+L清空"))
        h.add_command(label="关于", command=lambda: messagebox.showinfo("关于",
            "社交网络图谱分析系统\n数据结构课程设计\n邻接表 + 哈希表 + BFS/Dijkstra"))
        bar.add_cascade(label="帮助", menu=h)
        self.root.config(menu=bar)

    # ===================== 主布局 =====================
    def _build_layout(self) -> None:
        # 左侧功能面板
        left = ttk.Frame(self.root, width=320)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left.pack_propagate(False)

        self._build_user_panel(left)
        self._build_distance_panel(left)
        self._build_manage_panel(left)
        self._build_black_panel(left)

        # 右侧结果区
        right = ttk.Frame(self.root)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 结果表格
        table_frame = ttk.LabelFrame(right, text=" 结果展示 ")
        table_frame.pack(fill=tk.X, pady=(0, 8))
        cols = ("c1", "c2", "c3", "c4")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        for c, w in zip(cols, [80, 100, 150, 250]):
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview).pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=lambda f, l: None)

        # 日志区
        log_frame = ttk.LabelFrame(right, text=" 操作日志 ")
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log = ScrolledText(log_frame, wrap=tk.WORD, bg="#fafafa", relief="flat", padx=8, pady=8)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.config(state=tk.DISABLED)
        for tag, color in TAG_COLORS.items():
            self.log.tag_config(tag, foreground=color)
        self.log.tag_config("title", font=("微软雅黑", 11, "bold"))

    # ---------- 用户与人脉查询面板 ----------
    def _build_user_panel(self, parent) -> None:
        f = ttk.LabelFrame(parent, text=" 用户查询与人脉 ", padding=8)
        f.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(f)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="用户ID:").pack(side=tk.LEFT)
        self.uid_entry = ttk.Entry(row1, textvariable=self.uid_var, width=10)
        self.uid_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(row1, text="确认", command=self._confirm_user, width=6).pack(side=tk.LEFT)

        self.user_info = ttk.Label(f, text="未选中用户", foreground="#888")
        self.user_info.pack(anchor="w", pady=4)

        # 排序方式
        row_sort = ttk.Frame(f)
        row_sort.pack(fill=tk.X, pady=2)
        ttk.Label(row_sort, text="排序:", foreground="#666").pack(side=tk.LEFT)
        ttk.Combobox(row_sort, textvariable=self.sort_var, values=SORT_OPTIONS,
                     state="readonly", width=14).pack(side=tk.LEFT, padx=4)

        # 人脉按钮
        btn_row = ttk.Frame(f)
        btn_row.pack(fill=tk.X, pady=4)
        for text, cmd in [("一度", self._query_1), ("二度", self._query_2), ("多度", self._query_n)]:
            ttk.Button(btn_row, text=text, command=cmd).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 度数 & 推荐
        row3 = ttk.Frame(f)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="度数:", foreground="#666").pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.degree_var, width=4).pack(side=tk.LEFT, padx=2)
        ttk.Label(row3, text="TopK:", foreground="#666").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Entry(row3, textvariable=self.topk_var, width=4).pack(side=tk.LEFT, padx=2)
        ttk.Button(row3, text="兴趣推荐", command=self._recommend).pack(side=tk.LEFT, padx=4)

    # ---------- 社交距离面板 ----------
    def _build_distance_panel(self, parent) -> None:
        f = ttk.LabelFrame(parent, text=" 社交距离计算 ", padding=8)
        f.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(f)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="起点:").pack(side=tk.LEFT)
        self.start_label = ttk.Label(row1, text="未选中", foreground="#888")
        self.start_label.pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(row1, text="加权模式", variable=self.weight_mode).pack(side=tk.LEFT, padx=8)

        row2 = ttk.Frame(f)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="终点ID:").pack(side=tk.LEFT)
        self.end_entry = ttk.Entry(row2, textvariable=self.end_uid_var, width=10)
        self.end_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="计算", command=self._calc_dist, width=6).pack(side=tk.LEFT)

    # ---------- 用户与好友管理 ----------
    def _build_manage_panel(self, parent) -> None:
        f = ttk.LabelFrame(parent, text=" 用户与好友管理 ", padding=8)
        f.pack(fill=tk.X, pady=(0, 8))

        # 新增用户
        r1 = ttk.Frame(f)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="ID:").pack(side=tk.LEFT)
        ttk.Entry(r1, textvariable=self.new_uid_var, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(r1, text="姓名:").pack(side=tk.LEFT)
        ttk.Entry(r1, textvariable=self.new_name_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(r1, text="添加用户", command=self._add_user).pack(side=tk.LEFT, padx=4)

        r2 = ttk.Frame(f)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="兴趣(;分隔):").pack(side=tk.LEFT)
        ttk.Entry(r2, textvariable=self.new_inter_var, width=18).pack(side=tk.LEFT, padx=2)

        ttk.Separator(f, orient="horizontal").pack(fill=tk.X, pady=6)

        # 好友操作
        r3 = ttk.Frame(f)
        r3.pack(fill=tk.X, pady=2)
        ttk.Label(r3, text="对方ID:").pack(side=tk.LEFT)
        ttk.Entry(r3, textvariable=self.target_uid_var, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(r3, text="权重:").pack(side=tk.LEFT)
        ttk.Entry(r3, textvariable=self.weight_var, width=4).pack(side=tk.LEFT, padx=2)

        r4 = ttk.Frame(f)
        r4.pack(fill=tk.X, pady=4)
        ttk.Button(r4, text="添加好友", command=self._add_friend).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(r4, text="解除好友", command=self._del_friend).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    # ---------- 黑名单面板 ----------
    def _build_black_panel(self, parent) -> None:
        f = ttk.LabelFrame(parent, text=" 黑名单管理 ", padding=8)
        f.pack(fill=tk.X, pady=(0, 8))

        r1 = ttk.Frame(f)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="用户ID:").pack(side=tk.LEFT)
        ttk.Entry(r1, textvariable=self.black_uid_var, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Button(r1, text="查看列表", command=self._show_black).pack(side=tk.LEFT)

        r2 = ttk.Frame(f)
        r2.pack(fill=tk.X, pady=4)
        for t, c in [("加入", self._add_black), ("移出", self._remove_black), ("清空", self._clear_black)]:
            ttk.Button(r2, text=t, command=c).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        ttk.Button(parent, text="删除当前用户", command=self._del_user).pack(fill=tk.X)

    # ===================== 快捷键 =====================
    def _bind_shortcuts(self) -> None:
        self.uid_entry.bind("<Return>", lambda e: self._confirm_user())
        self.end_entry.bind("<Return>", lambda e: self._calc_dist())
        self.root.bind("<Control-l>", lambda e: self._clear_all())

    # ===================== 通用工具 =====================
    def _print(self, text: str, tag: str = "normal") -> None:
        self.log.config(state=tk.NORMAL)
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{t}] {text}\n", tag)
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _clear_all(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.log.config(state=tk.NORMAL)
        self.log.delete(1.0, tk.END)
        self.log.config(state=tk.DISABLED)
        self._print("已清空所有输出", "info")

    def _update_table(self, headers: List[str], rows: List[tuple]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for col, h in zip(("c1", "c2", "c3", "c4"), headers):
            self.tree.heading(col, text=h)
        for r in rows:
            self.tree.insert("", tk.END, values=r)

    def _valid_uid(self, uid_str: str) -> Tuple[bool, int]:
        raw = uid_str.strip()
        if not raw:
            messagebox.showwarning("提示", "用户ID不能为空")
            return False, -1
        try:
            uid = int(raw)
        except ValueError:
            messagebox.showerror("错误", "请输入数字ID")
            return False, -1
        if uid <= 0:
            messagebox.showerror("错误", "ID必须为正整数")
            return False, -1
        if self.graph.get_user_info(uid)["name"] == "未知用户":
            messagebox.showerror("错误", f"用户 {uid} 不存在")
            return False, -1
        return True, uid

    def _name(self, uid: int) -> str:
        return f"{uid}({self.graph.get_user_info(uid)['name']})"

    def _set_load_state(self, loading: bool) -> None:
        self.is_loading = loading
        self.root.config(cursor="wait" if loading else "")

    # ===================== 异步加载数据 =====================
    def _async_load_default(self) -> None:
        self._print("正在加载默认数据...", "info")
        self._set_load_state(True)
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        ok_u = self.graph.load_users_from_csv(os.path.join(self.data_dir, "users.csv"))
        ok_r = self.graph.load_relationships_from_txt(os.path.join(self.data_dir, "relationships.txt"))
        self.root.after(0, self._on_load_done, ok_u, ok_r)

    def _on_load_done(self, ok_u: bool, ok_r: bool) -> None:
        self._set_load_state(False)
        if ok_u and ok_r:
            self._print("✅ 默认数据加载完成", "success")
        else:
            self._print("⚠️ 部分数据加载失败，请手动加载", "warning")

    def _load_user_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV文件", "*.csv")])
        if not path:
            return
        if self.graph.load_users_from_csv(path):
            self._print(f"✅ 用户文件加载: {os.path.basename(path)}", "success")
        else:
            self._print("❌ 用户文件加载失败", "error")
            messagebox.showerror("失败", "文件格式错误或编码不支持")

    def _load_rel_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("TXT文件", "*.txt")])
        if not path:
            return
        if self.graph.load_relationships_from_txt(path):
            self._print(f"✅ 关系文件加载: {os.path.basename(path)}", "success")
        else:
            self._print("❌ 关系文件加载失败", "error")
            messagebox.showerror("失败", "文件格式错误或编码不支持")

    # ===================== 核心交互 =====================
    def _confirm_user(self) -> None:
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        info = self.graph.get_user_info(uid)
        inter = "、".join(info["interests"]) if info["interests"] else "无"
        self.user_info.config(text=f"{uid} {info['name']} | 兴趣: {inter}", foreground="#222")
        self.start_label.config(text=f"{uid} {info['name']}", foreground="#222")
        self.current_uid = uid
        self._print(f"已切换查询目标: {self._name(uid)}", "info")

    # ---------- 人脉查询 ----------
    def _get_sort_key(self) -> str:
        """统一转换排序策略为后端参数"""
        mapping = {
            "按ID升序": "id",
            "按亲密度降序": "weight",
            "按共同兴趣降序": "interest"
        }
        return mapping.get(self.sort_var.get(), "id")

    def _query_1(self) -> None:
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        # 带权重返回，再按策略排序
        friends = self.graph.get_direct_friends_with_weight(uid)
        sort_key = self._get_sort_key()

        # 获取当前用户的兴趣集合，用于共同兴趣排序
        my_interests = set(self.graph.get_user_info(uid)["interests"])

        if sort_key == "id":
            friends.sort(key=lambda x: x[0])
        elif sort_key == "interest":
            # 按共同兴趣数降序，数量相同则按ID升序
            def get_common_count(item):
                fid, _ = item
                friend_interests = set(self.graph.get_user_info(fid)["interests"])
                return len(my_interests & friend_interests)

            friends.sort(key=lambda x: (-get_common_count(x), x[0]))
        # weight模式：后端返回已经是权重降序，无需额外排序

        self._print(f"═══ {self._name(uid)} 一度人脉（共{len(friends)}人）═══", "title")
        rows = []
        for fid, w in friends:
            info = self.graph.get_user_info(fid)
            common = len(my_interests & set(info["interests"]))
            # 第三列根据排序策略显示对应维度
            if sort_key == "interest":
                col3 = f"共同兴趣: {common}个"
            else:
                col3 = f"亲密度: {w}"
            rows.append((fid, info["name"], col3, "、".join(info["interests"])))
        self._update_table(["用户ID", "姓名", "匹配维度", "兴趣标签"], rows)

    def _query_2(self) -> None:
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        strategy = self._get_sort_key()
        res = self.graph.find_second_degree_with_path(uid, sort_strategy=strategy)

        self._print(f"═══ {self._name(uid)} 二度人脉（共{len(res)}人）═══", "title")
        rows = []
        for sec_uid, mid_uid, path in res:
            info = self.graph.get_user_info(sec_uid)
            path_str = " → ".join([self._name(p) for p in path])
            rows.append((sec_uid, info["name"], f"中间人: {self._name(mid_uid)}", path_str))
        self._update_table(["用户ID", "姓名", "中间人", "连通路径"], rows)

    def _query_n(self) -> None:
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        try:
            n = int(self.degree_var.get())
            if n < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "度数必须为正整数")
            return

        uids = self.graph.find_n_degree_friends(uid, n)
        sort_key = self._get_sort_key()

        # 补充亲密度信息（取路径上最小权重）
        rows = []
        for fid in uids:
            info = self.graph.get_user_info(fid)
            # 多度简化处理：显示ID、姓名、兴趣
            rows.append((fid, info["name"], f"{n}度人脉", "、".join(info["interests"])))

        if sort_key == "id":
            pass  # 后端已按ID升序
        else:
            # 多度按亲密度排序：取最短路径权重和（这里简化，保留ID排序）
            pass

        self._print(f"═══ {self._name(uid)} {n}度人脉（共{len(uids)}人）═══", "title")
        self._update_table(["用户ID", "姓名", "人脉度数", "兴趣标签"], rows)

    # ---------- 社交距离 ----------
    def _calc_dist(self) -> None:
        s_ok, start = self._valid_uid(self.uid_var.get())
        e_ok, end = self._valid_uid(self.end_uid_var.get())
        if not (s_ok and e_ok):
            return

        if self.weight_mode.get():
            dist, path = self.graph.get_weighted_shortest_path(start, end)
            mode = "加权模式"
        else:
            dist, path = self.graph.get_shortest_distance(start, end)
            mode = "无权模式"

        self._print(f"═══ {self._name(start)} → {self._name(end)} ═══", "title")
        if dist == -1:
            self._print("两用户无连通路径", "warning")
            self._update_table([], [])
            return

        desc = f"总权重: {dist}" if self.weight_mode.get() else f"最短跳数: {dist}"
        self._print(f"{mode} | {desc}", "info")
        self._print(f"路径: {' → '.join([self._name(p) for p in path])}", "success")

        rows = [(i + 1, self._name(p), "", "") for i, p in enumerate(path)]
        self._update_table(["序号", "途经节点", "", ""], rows)

    # ---------- 兴趣推荐 ----------
    def _recommend(self) -> None:
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        try:
            topk = int(self.topk_var.get())
            if topk <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "推荐数量必须为正整数")
            return

        rec_list = self.graph.recommend_friends_by_interest(uid, topk)
        self._print(f"═══ {self._name(uid)} 兴趣推荐 Top{topk} ═══", "title")
        rows = []
        for rid, rname, cnt, inters in rec_list:
            rows.append((rid, rname, f"共同兴趣: {cnt}个", "、".join(inters)))
        self._update_table(["用户ID", "姓名", "匹配度", "共同兴趣"], rows)

    # ---------- 用户/好友管理 ----------
    def _add_user(self) -> None:
        try:
            uid = int(self.new_uid_var.get().strip())
            name = self.new_name_var.get().strip()
            if uid <= 0 or not name:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "ID为正整数且姓名不能为空")
            return

        inters = [i.strip() for i in self.new_inter_var.get().split(";") if i.strip()]
        if self.graph.add_user(uid, name, inters):
            self._print(f"✅ 新增用户: {self._name(uid)}", "success")
            self.new_uid_var.set("")
            self.new_name_var.set("")
            self.new_inter_var.set("")
        else:
            self._print(f"⚠️ 用户 {uid} 已存在", "warning")
            messagebox.showwarning("提示", "该用户ID已存在")

    def _add_friend(self) -> None:
        s_ok, u1 = self._valid_uid(self.uid_var.get())
        t_ok, u2 = self._valid_uid(self.target_uid_var.get())
        if not (s_ok and t_ok):
            return
        try:
            w = int(self.weight_var.get())
            if w <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "权重必须为正整数")
            return

        self.graph.add_friendship(u1, u2, w)
        self._print(f"✅ 建立好友: {self._name(u1)} ↔ {self._name(u2)} (权重:{w})", "success")
        self.target_uid_var.set("")

    def _del_friend(self) -> None:
        s_ok, u1 = self._valid_uid(self.uid_var.get())
        t_ok, u2 = self._valid_uid(self.target_uid_var.get())
        if not (s_ok and t_ok):
            return
        if self.graph.delete_friendship(u1, u2):
            self._print(f"✅ 解除好友: {self._name(u1)} ↔ {self._name(u2)}", "success")
        else:
            self._print("⚠️ 两人并非好友", "warning")
        self.target_uid_var.set("")

    def _del_user(self) -> None:
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        if not messagebox.askyesno("确认", f"确定删除用户 {uid} 吗？删除后不可恢复"):
            return
        if self.graph.delete_user(uid):
            self._print(f"✅ 已删除用户: {uid}", "success")
            self.user_info.config(text="未选中用户", foreground="#888")
            self.start_label.config(text="未选中", foreground="#888")
            self.uid_var.set("")
            self.current_uid = None
        else:
            self._print("删除失败", "error")

    # ---------- 黑名单 ----------
    def _add_black(self) -> None:
        ok, uid = self._valid_uid(self.black_uid_var.get())
        if not ok:
            return
        if self.graph.add_to_blacklist(uid):
            self._print(f"✅ 已拉黑: {self._name(uid)}", "success")
            self.black_uid_var.set("")

    def _remove_black(self) -> None:
        ok, uid = self._valid_uid(self.black_uid_var.get())
        if not ok:
            return
        if self.graph.remove_from_blacklist(uid):
            self._print(f"✅ 已移出黑名单: {self._name(uid)}", "success")
        else:
            self._print("⚠️ 该用户不在黑名单中", "warning")
        self.black_uid_var.set("")

    def _show_black(self) -> None:
        bl = sorted(self.graph.blacklist)
        self._print(f"═══ 黑名单列表（共{len(bl)}人）═══", "title")
        rows = [(uid, self.graph.get_user_info(uid)["name"], "", "") for uid in bl]
        self._update_table(["用户ID", "姓名", "", ""], rows)

    def _clear_black(self) -> None:
        if not messagebox.askyesno("确认", "确定清空全部黑名单？"):
            return
        self.graph.clear_blacklist()
        self._print("✅ 黑名单已清空", "success")

    # ---------- 统计分析 ----------
    def _show_communities(self) -> None:
        comms = self.graph.find_all_communities()
        self._print("========================================", "title")
        self._print(f"            全网社群划分 共{len(comms)}个", "title")
        self._print("========================================", "title")
        for i, group in enumerate(comms, 1):
            name_list = [self._name(u) for u in group]
            # 每5人一行拆分，避免单行过长挤在一起
            chunks = [name_list[idx:idx + 5] for idx in range(0, len(name_list), 5)]
            self._print(f"【社群{i}】总人数：{len(group)}人", "info")
            for piece in chunks:
                self._print("    " + "、".join(piece), "detail")

    def _show_centrality(self) -> None:
        rank = self.graph.calc_degree_centrality()
        self._print("═══ 用户度中心性排行 ═══", "title")
        rows = [(i, uid, name, f"好友数: {cnt}") for i, (uid, cnt, name) in enumerate(rank, 1)]
        self._update_table(["排名", "用户ID", "姓名", "好友数量"], rows)

    # ---------- 可视化 ----------
    def _generate_graph(self) -> None:
        user_count = sum(len(b) for b in self.graph.user_attrs.buckets)
        if user_count == 0:
            messagebox.showwarning("提示", "请先加载数据")
            return
        try:
            from pyvis.network import Network
            net = Network(notebook=False, width="100%", height="750px", directed=False)
            net.set_options("""{
                "nodes": {"font": {"size": 14}, "shape": "dot"},
                "edges": {"smooth": {"type": "continuous"}},
                "physics": {"barnesHut": {"gravitationalConstant": -8000, "springLength": 200}},
                "interaction": {"hover": true, "zoomView": true, "dragView": true}
            }""")

            # 层级配色
            layer_map = {}
            if self.current_uid:
                layer_map = self.graph.get_user_degree_layer(self.current_uid)
            color_map = {0: "#ff4444", 1: "#4285f4", 2: "#34a853", 3: "#90a4ae"}

            # 子网络过滤
            visible = set()
            if self.only_subgraph.get() and self.current_uid:
                visible.add(self.current_uid)
                for u, d in layer_map.items():
                    if d <= 2:
                        visible.add(u)

            # 添加节点
            for bucket in self.graph.user_attrs.buckets:
                for uid, attr in bucket:
                    if self.hide_black.get() and uid in self.graph.blacklist:
                        continue
                    if self.only_subgraph.get() and visible and uid not in visible:
                        continue
                    cnt = len(self.graph.graph.get(uid, set()))
                    size = 20 + min(cnt * 3, 25)
                    color = color_map.get(layer_map.get(uid, 3), "#90a4ae")
                    title = f"ID:{uid}\n姓名:{attr['name']}\n好友数:{cnt}\n兴趣:{'、'.join(attr['interests'])}"
                    net.add_node(uid, label=f"{uid}-{attr['name']}", size=size, color=color, title=title)

            # 添加边
            added = set()
            for (u1, u2), w in self.graph.edge_weights.items():
                if self.hide_black.get() and (u1 in self.graph.blacklist or u2 in self.graph.blacklist):
                    continue
                if self.only_subgraph.get() and visible and (u1 not in visible or u2 not in visible):
                    continue
                if (u2, u1) not in added:
                    net.add_edge(u1, u2, width=w * 0.8, title=f"亲密度:{w}", color="#90a4ae")
                    added.add((u1, u2))

            save_path = "social_network_graph.html"
            net.write_html(save_path)
            webbrowser.open(os.path.abspath(save_path))
            self._print("✅ 网络图已生成并打开", "success")
        except Exception as e:
            self._print(f"❌ 生成失败: {str(e)}", "error")
            messagebox.showerror("失败", str(e))


if __name__ == "__main__":
    try:
        root = tk.Tk()
        SocialNetworkGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("启动失败", str(e))