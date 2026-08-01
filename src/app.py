import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu
from tkinter.scrolledtext import ScrolledText
from src.social_graph import SocialGraph
import os, webbrowser, datetime
from typing import Tuple
from pyvis.network import Network


class SocialNetworkGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("社交网络图谱分析及智能推荐系统")
        self.root.geometry("1080x700")
        self.root.minsize(900, 600)

        # 核心模型
        self.graph = SocialGraph()
        base = os.path.dirname(os.path.abspath(__file__))
        self.user_csv = os.path.join(os.path.dirname(base), "data", "users.csv")
        self.rel_txt = os.path.join(os.path.dirname(base), "data", "relationships.txt")

        # 全局变量
        self.uid_var = tk.StringVar()
        self.end_uid_var = tk.StringVar()
        self.n_degree_var = tk.StringVar(value="3")
        self.topk_var = tk.StringVar(value="5")
        self.weight_flag = tk.BooleanVar(value=False)
        self.new_uid_var = tk.StringVar()
        self.new_name_var = tk.StringVar()
        self.new_interest_var = tk.StringVar()
        self.target_uid_var = tk.StringVar()
        self.weight_var = tk.StringVar(value="1")
        self.black_uid_var = tk.StringVar()

        self._init_style()
        self._create_menu()
        self._build_layout()
        self._auto_load()

    # -------------------------- 样式配置 --------------------------
    def _init_style(self):
        style = ttk.Style()
        self.root.option_add("*Font", ("微软雅黑", 10))
        style.configure("TLabel", foreground="#333333")

    def _create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="加载用户CSV", command=self._load_user)
        file_menu.add_command(label="加载关系TXT", command=self._load_rel)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件操作", menu=file_menu)

        stat_menu = Menu(menubar, tearoff=0)
        stat_menu.add_command(label="全网社群划分", command=self._show_communities)
        stat_menu.add_command(label="用户度中心性排行", command=self._show_centrality)
        stat_menu.add_separator()
        stat_menu.add_command(label="清空输出", command=self._clear_output)
        menubar.add_cascade(label="分析工具", menu=stat_menu)

        vis_menu = Menu(menubar, tearoff=0)
        vis_menu.add_command(label="生成全局网络图", command=self._generate_graph)
        menubar.add_cascade(label="可视化", menu=vis_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="关于系统", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

    # -------------------------- 主布局（左侧固定，无滚动） --------------------------
    def _build_layout(self):
        # 左侧固定面板：宽度350px，锁定尺寸不随内容变化
        left_frame = ttk.Frame(self.root, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)
        left_frame.pack_propagate(False)

        # 右侧结果区
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_user_panel(left_frame)
        self._build_distance_panel(left_frame)
        self._build_manage_panel(left_frame)
        self._build_blacklist_panel(left_frame)
        self._build_delete_panel(left_frame)
        self._build_output(right_frame)

    # -------------------------- 功能面板（统一右侧安全边距） --------------------------
    def _build_user_panel(self, parent):
        frame = ttk.LabelFrame(parent, text=" 当前查询用户 ", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 2))

        ttk.Label(frame, text="用户ID:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.uid_var, width=12).grid(row=0, column=1, padx=4)
        ttk.Button(frame, text="确认", command=self._confirm_user, width=6).grid(row=0, column=2, padx=(0, 2))

        self.user_info = ttk.Label(frame, text="未选中用户", foreground="#888")
        self.user_info.grid(row=1, column=0, columnspan=3, sticky="w", pady=6)

        # 人脉查询按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=2)
        ttk.Button(btn_frame, text="一度人脉", command=self._query_1degree).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                                 padx=(0, 1))
        ttk.Button(btn_frame, text="二度人脉", command=self._query_2degree).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                                 padx=1)
        ttk.Button(btn_frame, text="多度人脉", command=self._query_ndegree).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                                 padx=(1, 2))

        row2 = ttk.Frame(frame)
        row2.grid(row=3, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Label(row2, text="度数:").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.n_degree_var, width=5).pack(side=tk.LEFT, padx=4)
        ttk.Label(row2, text="推荐Top:", foreground="#666").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Entry(row2, textvariable=self.topk_var, width=5).pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="兴趣推荐", command=self._recommend).pack(side=tk.LEFT, padx=(4, 2))

    def _build_distance_panel(self, parent):
        frame = ttk.LabelFrame(parent, text=" 社交距离计算 ", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 2))

        ttk.Label(frame, text="起点:").grid(row=0, column=0, sticky="w")
        self.start_label = ttk.Label(frame, text="未选中", foreground="#888")
        self.start_label.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Checkbutton(frame, text="加权模式", variable=self.weight_flag).grid(row=0, column=2, sticky="w",
                                                                                padx=(0, 2))

        ttk.Label(frame, text="终点ID:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.end_uid_var, width=12).grid(row=1, column=1, padx=4)
        ttk.Button(frame, text="计算", command=self._calc_distance, width=6).grid(row=1, column=2, padx=(0, 2))

    def _build_manage_panel(self, parent):
        frame = ttk.LabelFrame(parent, text=" 用户与好友管理 ", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 2))

        # 新增用户
        ttk.Label(frame, text="新增ID:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.new_uid_var, width=8).grid(row=0, column=1, padx=2)
        ttk.Label(frame, text="姓名:").grid(row=0, column=2, sticky="w")
        ttk.Entry(frame, textvariable=self.new_name_var, width=8).grid(row=0, column=3, padx=2)
        ttk.Button(frame, text="添加用户", command=self._add_user).grid(row=0, column=4, padx=(4, 2))

        ttk.Label(frame, text="兴趣标签:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.new_interest_var, width=20).grid(row=1, column=1, columnspan=3, sticky="w",
                                                                            padx=2)

        ttk.Separator(frame, orient="horizontal").grid(row=2, column=0, columnspan=5, sticky="ew", pady=6)

        # 好友操作
        ttk.Label(frame, text="对方ID:").grid(row=3, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.target_uid_var, width=8).grid(row=3, column=1, padx=2)
        ttk.Label(frame, text="权重:").grid(row=3, column=2, sticky="w")
        ttk.Entry(frame, textvariable=self.weight_var, width=5).grid(row=3, column=3, padx=2)

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=0, columnspan=5, sticky="ew", pady=6)
        ttk.Button(btn_row, text="添加好友", command=self._add_friend).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                            padx=(0, 3))
        ttk.Button(btn_row, text="解除好友", command=self._del_friend).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                            padx=(3, 2))

    def _build_blacklist_panel(self, parent):
        frame = ttk.LabelFrame(parent, text=" 黑名单管理 ", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 2))

        ttk.Label(frame, text="用户ID:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.black_uid_var, width=12).grid(row=0, column=1, padx=4)
        ttk.Button(frame, text="查看", command=self._show_blacklist, width=6).grid(row=0, column=2, padx=(0, 2))

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=6)
        ttk.Button(btn_row, text="加入", command=self._add_black).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                       padx=(0, 2))
        ttk.Button(btn_row, text="移出", command=self._remove_black).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(btn_row, text="清空", command=self._clear_black).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                         padx=(2, 2))

    def _build_delete_panel(self, parent):
        # 修复删除按钮右边裁切：容器加右侧边距
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10), padx=(0, 2))
        ttk.Button(frame, text="删除当前用户", command=self._del_user).pack(fill=tk.X)

    def _build_output(self, parent):
        self.output = ScrolledText(parent, wrap=tk.WORD, bg="#fafafa", relief="flat", padx=10, pady=10)
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.config(state=tk.DISABLED)

        # 标签样式
        self.output.tag_config("title", foreground="#553399", font=("微软雅黑", 11, "bold"))
        self.output.tag_config("info", foreground="#0066cc")
        self.output.tag_config("success", foreground="#008822")
        self.output.tag_config("warning", foreground="#cc8800")
        self.output.tag_config("error", foreground="#cc2222")
        self.output.tag_config("detail", foreground="#555")

    # -------------------------- 通用工具方法 --------------------------
    def _print(self, text: str, tag: str = "normal"):
        self.output.config(state=tk.NORMAL)
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.output.insert(tk.END, f"[{time_str}] {text}\n", tag)
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    def _clear_output(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete(1.0, tk.END)
        self.output.config(state=tk.DISABLED)
        self._print("输出区已清空", "info")

    def _valid_uid(self, uid_str: str) -> Tuple[bool, int]:
        raw = uid_str.strip()
        if not raw:
            messagebox.showwarning("提示", "用户ID不能为空")
            return False, -1
        try:
            uid = int(raw)
        except ValueError:
            messagebox.showerror("错误", "请输入合法数字ID")
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

    # -------------------------- 核心交互逻辑 --------------------------
    def _confirm_user(self):
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        info = self.graph.get_user_info(uid)
        interests = "、".join(info["interests"]) if info["interests"] else "无"
        self.user_info.config(text=f"{uid} {info['name']} | 兴趣: {interests}", foreground="#222")
        self.start_label.config(text=f"{uid} {info['name']}", foreground="#222")
        self._print(f"已切换查询目标: {self._name(uid)}", "info")

    def _auto_load(self):
        self._print("正在加载默认数据...", "info")
        u_ok = os.path.exists(self.user_csv) and self.graph.load_users_from_csv(self.user_csv)
        r_ok = os.path.exists(self.rel_txt) and self.graph.load_relationships_from_txt(self.rel_txt)
        if u_ok and r_ok:
            self._print("✅ 用户与关系数据加载完成", "success")
        else:
            self._print("⚠️ 部分数据加载失败，请手动加载", "warning")

    def _load_user(self):
        path = filedialog.askopenfilename(filetypes=[("CSV文件", "*.csv")])
        if path and self.graph.load_users_from_csv(path):
            self.user_csv = path
            self._print(f"✅ 用户文件加载: {os.path.basename(path)}", "success")

    def _load_rel(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if path and self.graph.load_relationships_from_txt(path):
            self.rel_txt = path
            self._print(f"✅ 关系文件加载: {os.path.basename(path)}", "success")

    # ---------- 人脉查询（带人数统计） ----------
    def _query_1degree(self):
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        friends = self.graph.get_direct_friends_with_weight(uid)
        count = len(friends)

        self._print(f"═══ {self._name(uid)} 一度人脉 ═══", "title")
        self._print(f"  共有 {count} 位直接好友，按亲密度降序排列", "info")

        if count == 0:
            self._print("  暂无好友数据", "warning")
            self._print("", "normal")
            return

        for idx, (fid, w) in enumerate(friends, 1):
            finfo = self.graph.get_user_info(fid)
            finterests = "、".join(finfo["interests"]) if finfo["interests"] else "无"
            self._print(f"  {idx}. ID：{fid}  姓名：{finfo['name']}  亲密度：{w}  兴趣：{finterests}", "detail")
        self._print("", "normal")

    def _query_2degree(self):
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        res = self.graph.find_second_degree_with_path(uid)
        count = len(res)

        self._print(f"═══ {self._name(uid)} 二度人脉 ═══", "title")
        self._print(f"  共有 {count} 位二度人脉", "info")

        if count == 0:
            self._print("  暂无二度人脉数据", "warning")
            self._print("", "normal")
            return

        for idx, (sec_uid, mid_uid, path) in enumerate(res, 1):
            sinfo = self.graph.get_user_info(sec_uid)
            sinterests = "、".join(sinfo["interests"]) if sinfo["interests"] else "无"
            path_str = " → ".join([self._name(p) for p in path])
            self._print(f"  {idx}. ID：{sec_uid}  姓名：{sinfo['name']}", "success")
            self._print(f"      连通路径：{path_str}", "detail")
            self._print(f"      兴趣：{sinterests}", "detail")
        self._print("", "normal")

    def _query_ndegree(self):
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        try:
            n = int(self.n_degree_var.get())
            if n < 3:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "度数必须≥3的整数")
            return

        res = self.graph.find_n_degree_friends(uid, n)
        count = len(res)

        self._print(f"═══ {self._name(uid)} {n}度人脉 ═══", "title")
        self._print(f"  共有 {count} 位{n}度人脉", "info")

        if count == 0:
            self._print("  无匹配的人脉数据", "warning")
            self._print("", "normal")
            return

        for idx, rid in enumerate(res, 1):
            rinfo = self.graph.get_user_info(rid)
            rinterests = "、".join(rinfo["interests"]) if rinfo["interests"] else "无"
            self._print(f"  {idx}. ID：{rid}  姓名：{rinfo['name']}  兴趣：{rinterests}", "detail")
        self._print("", "normal")

    # ---------- 社交距离计算 ----------
    def _calc_distance(self):
        s_ok, start = self._valid_uid(self.uid_var.get())
        e_ok, end = self._valid_uid(self.end_uid_var.get())
        if not (s_ok and e_ok):
            return

        if self.weight_flag.get():
            dist, path = self.graph.get_weighted_shortest_path(start, end)
            mode = "加权社交距离"
            desc = f"总权重：{dist}"
        else:
            dist, path = self.graph.get_shortest_distance(start, end)
            mode = "无权社交距离"
            desc = f"最短跳数：{dist}"

        self._print(f"═══ {self._name(start)} → {self._name(end)} ═══", "title")
        if dist == -1:
            self._print("  两用户无连通路径", "warning")
            return
        path_str = " → ".join([self._name(p) for p in path])
        self._print(f"  {mode}：{desc}", "info")
        self._print(f"  完整路径：{path_str}", "success")
        self._print("", "normal")

    # ---------- 兴趣推荐 ----------
    def _recommend(self):
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
        count = len(rec_list)

        self._print(f"═══ {self._name(uid)} 兴趣推荐 Top{topk} ═══", "title")
        self._print(f"  匹配到 {count} 位推荐用户", "info")

        if count == 0:
            self._print("  暂无匹配的推荐结果", "warning")
            self._print("", "normal")
            return

        for idx, (rid, rname, cnt, inters) in enumerate(rec_list, 1):
            inter_str = "、".join(inters)
            self._print(f"  {idx}. ID：{rid}  姓名：{rname}  共同兴趣 {cnt}个", "success")
            self._print(f"      重合兴趣：{inter_str}", "detail")
        self._print("", "normal")

    # ---------- 用户/好友管理 ----------
    def _add_user(self):
        try:
            uid = int(self.new_uid_var.get().strip())
            name = self.new_name_var.get().strip()
            if uid <= 0 or not name:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "ID为正整数且姓名不能为空")
            return
        interests = [i.strip() for i in self.new_interest_var.get().split(";") if i.strip()]
        if self.graph.add_user(uid, name, interests):
            self._print(f"✅ 新增用户: {self._name(uid)}", "success")
            self.new_uid_var.set("")
            self.new_name_var.set("")
            self.new_interest_var.set("")
        else:
            self._print(f"⚠️ 用户 {uid} 已存在", "warning")

    def _add_friend(self):
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
        self._print(f"✅ 建立好友: {self._name(u1)} ↔ {self._name(u2)} (权重{w})", "success")
        self.target_uid_var.set("")

    def _del_friend(self):
        s_ok, u1 = self._valid_uid(self.uid_var.get())
        t_ok, u2 = self._valid_uid(self.target_uid_var.get())
        if not (s_ok and t_ok):
            return
        if self.graph.delete_friendship(u1, u2):
            self._print(f"✅ 解除好友: {self._name(u1)} ↔ {self._name(u2)}", "success")
        else:
            self._print("⚠️ 两人并非好友", "warning")
        self.target_uid_var.set("")

    def _del_user(self):
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
        else:
            self._print("删除失败", "error")

    # ---------- 黑名单管理 ----------
    def _add_black(self):
        ok, uid = self._valid_uid(self.black_uid_var.get())
        if not ok:
            return
        if self.graph.add_to_blacklist(uid):
            self._print(f"✅ 已拉黑: {self._name(uid)}", "success")
            self.black_uid_var.set("")

    def _remove_black(self):
        ok, uid = self._valid_uid(self.black_uid_var.get())
        if not ok:
            return
        if self.graph.remove_from_blacklist(uid):
            self._print(f"✅ 已移出黑名单: {self._name(uid)}", "success")
        else:
            self._print("⚠️ 该用户不在黑名单中", "warning")
        self.black_uid_var.set("")

    def _show_blacklist(self):
        bl = sorted(self.graph.blacklist)
        self._print("═══ 黑名单列表 ═══", "title")
        self._print(f"  共 {len(bl)} 位拉黑用户", "info")
        if not bl:
            self._print("  黑名单为空", "info")
        else:
            self._print("  " + "、".join([self._name(u) for u in bl]), "detail")
        self._print("", "normal")

    def _clear_black(self):
        if messagebox.askyesno("确认", "确定清空全部黑名单？"):
            self.graph.clear_blacklist()
            self._print("✅ 黑名单已清空", "success")

    # ---------- 统计分析 ----------
    def _show_communities(self):
        comms = self.graph.find_all_communities()
        self._print(f"═══ 全网社群划分结果 ═══", "title")
        self._print(f"  全网共划分出 {len(comms)} 个独立社群", "info")
        for idx, group in enumerate(comms, 1):
            names = "、".join([self._name(u) for u in group])
            self._print(f"  社群{idx}（{len(group)}人）：{names}", "detail")
        self._print("", "normal")

    def _show_centrality(self):
        rank = self.graph.calc_degree_centrality()
        self._print("═══ 用户度中心性排行 ═══", "title")
        self._print(f"  共统计 {len(rank)} 位用户", "info")
        for idx, (uid, cnt, name) in enumerate(rank, 1):
            self._print(f"  第{idx}名：{uid} {name} | 好友数：{cnt}", "success")
        self._print("", "normal")

    # ---------- 可视化 ----------
    def _generate_graph(self):
        user_count = sum(len(b) for b in self.graph.user_attrs.buckets)
        if user_count == 0:
            messagebox.showwarning("提示", "请先加载数据")
            return
        try:
            net = Network(notebook=False, width="100%", height="800px", directed=False)
            net.set_options("""
            {
              "nodes": {"font": {"size": 14}, "shape": "dot", "shadow": true},
              "edges": {"smooth": {"type": "continuous"}, "color": {"inherit": false}},
              "physics": {"barnesHut": {"gravitationalConstant": -8000, "springLength": 200}},
              "interaction": {"hover": true, "zoomView": true, "dragView": true}
            }
            """)
            colors = ["#42a5f5", "#66bb6a", "#ffa726", "#ab47bc", "#ef5350", "#26c6da"]
            idx = 0
            for bucket in self.graph.user_attrs.buckets:
                for uid, attr in bucket:
                    cnt = len(self.graph.graph.get(uid, set()))
                    size = 20 + min(cnt * 3, 25)
                    title = f"ID:{uid}\n姓名:{attr['name']}\n好友数:{cnt}\n兴趣:{'、'.join(attr['interests'])}"
                    net.add_node(uid, label=f"{uid}-{attr['name']}", size=size, color=colors[idx % len(colors)],
                                 title=title)
                    idx += 1

            added = set()
            for (u1, u2), w in self.graph.edge_weights.items():
                if (u2, u1) not in added:
                    net.add_edge(u1, u2, width=w * 0.8, title=f"亲密度:{w}", color="#90a4ae")
                    added.add((u1, u2))

            save_path = "social_network_graph.html"
            net.write_html(save_path)
            webbrowser.open(os.path.abspath(save_path))
            self._print("✅ 网络图已生成并打开", "success")
        except Exception as e:
            messagebox.showerror("生成失败", str(e))

    # ---------- 帮助与关于 ----------
    def _show_help(self):
        messagebox.showinfo("使用说明",
                            """1. 输入用户ID并点击「确认」作为全局查询目标
                            2. 点击对应按钮查询人脉、计算社交距离
                            3. 支持增删用户/好友、黑名单管理
                            4. 顶部菜单可进行社群分析、可视化生成""")

    def _show_about(self):
        messagebox.showinfo("关于系统",
                            """社交网络图谱分析及智能推荐系统
                            数据结构课程设计作品
                            核心技术：邻接表 + 哈希表 + BFS + Dijkstra
                            扩展功能：多度人脉 / 黑名单 / 兴趣推荐 / 可视化""")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        SocialNetworkGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("启动失败", str(e))