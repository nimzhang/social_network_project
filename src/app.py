import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu
from tkinter.scrolledtext import ScrolledText
from src.social_graph import SocialGraph
import os
import webbrowser
from pyvis.network import Network
from typing import Tuple


class SocialNetworkGUI:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("社交网络图谱分析及智能推荐系统")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        self.graph_model = SocialGraph()

        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        self.user_csv_path = os.path.join(project_root, "data", "users.csv")
        self.rel_txt_path = os.path.join(project_root, "data", "relationships.txt")

        # 核心变量
        self.current_uid_var = tk.StringVar()
        self.end_uid_var = tk.StringVar()
        self.n_degree_var = tk.StringVar(value="3")
        self.top_k_var = tk.StringVar(value="5")
        self.use_weight_flag = tk.BooleanVar(value=False)

        # 管理模块变量
        self.new_uid_var = tk.StringVar()
        self.new_name_var = tk.StringVar()
        self.new_interest_var = tk.StringVar()
        self.friend_target_var = tk.StringVar()
        self.friend_weight_var = tk.StringVar(value="1")
        self.blacklist_uid_var = tk.StringVar()

        self._create_menu_bar()
        self._build_main_layout()
        self._auto_load_default_data()

    # ===================== 顶部菜单栏（新增统计工具菜单） =====================
    def _create_menu_bar(self):
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)

        # 文件菜单
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="手动加载用户CSV", command=self._load_user_file_dialog)
        file_menu.add_command(label="手动加载关系TXT", command=self._load_rel_file_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="退出程序", command=self.root.quit)
        menu_bar.add_cascade(label="文件操作", menu=file_menu)

        # 统计工具菜单（原左侧辅助统计移到这里）
        stat_menu = Menu(menu_bar, tearoff=0)
        stat_menu.add_command(label="全网社群划分", command=self._show_communities)
        stat_menu.add_command(label="用户度中心性排行", command=self._show_centrality)
        stat_menu.add_separator()
        stat_menu.add_command(label="清空结果输出区", command=self._clear_output)
        menu_bar.add_cascade(label="统计工具", menu=stat_menu)

        # 可视化菜单
        vis_menu = Menu(menu_bar, tearoff=0)
        vis_menu.add_command(label="生成全局社交网络图", command=self._generate_network_html)
        menu_bar.add_cascade(label="可视化", menu=vis_menu)

        # 帮助菜单
        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="功能操作说明", command=self._show_help_msg)
        help_menu.add_command(label="关于系统", command=self._show_about_msg)
        menu_bar.add_cascade(label="帮助", menu=help_menu)

    # ===================== 主界面布局 =====================
    def _build_main_layout(self):
        left_canvas = tk.Canvas(self.root, width=320)
        left_scroll = ttk.Scrollbar(self.root, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_canvas.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        left_scroll.pack(side=tk.LEFT, fill=tk.Y)

        left_panel = ttk.Frame(left_canvas)
        left_canvas.create_window((0, 0), window=left_panel, anchor="nw")
        left_panel.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))

        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 左侧模块（已移除辅助统计工具）
        self._build_current_user_panel(left_panel)
        self._build_distance_widget(left_panel)
        self._build_manage_widget(left_panel)
        self._build_blacklist_widget(left_panel)

        self._build_result_area(right_panel)

    # ===================== 当前查询用户面板 =====================
    def _build_current_user_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="当 前 查 询 用 户", padding=12)
        frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(frame, text="用户ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.current_uid_var, width=14).grid(row=0, column=1, padx=6)
        ttk.Button(frame, text="确认/切换用户", command=self._confirm_current_user).grid(row=0, column=2)

        self.user_info_label = ttk.Label(frame, text="未选中用户", foreground="#888888")
        self.user_info_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 10))

        ttk.Separator(frame, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=6)

        ttk.Button(frame, text="一度人脉", width=10, command=self._query_direct).grid(row=3, column=0, padx=2, pady=3)
        ttk.Button(frame, text="二度人脉", width=10, command=self._query_second).grid(row=3, column=1, padx=2, pady=3)
        ttk.Button(frame, text="多度人脉", width=10, command=self._query_n_degree).grid(row=3, column=2, padx=2, pady=3)

        ttk.Label(frame, text="多度度数：").grid(row=4, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(frame, textvariable=self.n_degree_var, width=8).grid(row=4, column=1, sticky="w", padx=6, pady=(4, 0))
        ttk.Label(frame, text="(≥3)", foreground="#888888").grid(row=4, column=2, sticky="w", pady=(4, 0))

        ttk.Separator(frame, orient="horizontal").grid(row=5, column=0, columnspan=3, sticky="ew", pady=8)

        ttk.Label(frame, text="推荐数量：").grid(row=6, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.top_k_var, width=8).grid(row=6, column=1, sticky="w", padx=6)
        ttk.Button(frame, text="兴趣智能推荐", command=self._interest_recommend).grid(row=6, column=2, padx=2)

    # ===================== 社交距离计算 =====================
    def _build_distance_widget(self, parent):
        frame = ttk.LabelFrame(parent, text="社 交 距 离 计 算", padding=10)
        frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(frame, text="起点(当前用户)：").grid(row=0, column=0, sticky="w")
        self.distance_start_label = ttk.Label(frame, text="未选中", foreground="#888888")
        self.distance_start_label.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(frame, text="终点ID：").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.end_uid_var, width=14).grid(row=1, column=1, padx=6)

        ttk.Checkbutton(frame, text="加权路径", variable=self.use_weight_flag).grid(row=0, column=2, rowspan=2)
        ttk.Button(frame, text="计算最短路径", command=self._calc_distance).grid(row=2, column=1, pady=4)

    # ===================== 用户/好友管理 =====================
    def _build_manage_widget(self, parent):
        frame = ttk.LabelFrame(parent, text="用 户 / 好 友 管 理", padding=10)
        frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(frame, text="新增用户ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.new_uid_var, width=10).grid(row=0, column=1, padx=3)
        ttk.Label(frame, text="姓名：").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.new_name_var, width=10).grid(row=1, column=1, padx=3)
        ttk.Label(frame, text="兴趣(分号分隔)：").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.new_interest_var, width=10).grid(row=2, column=1, padx=3)
        ttk.Button(frame, text="添加用户", command=self._add_new_user).grid(row=0, column=2, rowspan=3, padx=5)

        ttk.Separator(frame, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=6)

        ttk.Label(frame, text="发起方(当前用户)：").grid(row=4, column=0, sticky="w")
        self.add_friend_from_label = ttk.Label(frame, text="未选中", foreground="#888888")
        self.add_friend_from_label.grid(row=4, column=1, sticky="w", padx=3)
        ttk.Label(frame, text="对方用户ID：").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.friend_target_var, width=10).grid(row=5, column=1, padx=3)
        ttk.Label(frame, text="亲密度权重：").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.friend_weight_var, width=10).grid(row=6, column=1, padx=3)
        ttk.Button(frame, text="添加好友", command=self._add_new_friend).grid(row=4, column=2, rowspan=3, padx=5)

        ttk.Separator(frame, orient="horizontal").grid(row=7, column=0, columnspan=3, sticky="ew", pady=6)

        ttk.Button(frame, text="删除当前用户", command=self._delete_user).grid(row=8, column=0, padx=2, pady=2)
        ttk.Button(frame, text="解除好友关系", command=self._delete_friendship).grid(row=8, column=1, padx=2, pady=2)

    # ===================== 黑名单管理 =====================
    def _build_blacklist_widget(self, parent):
        frame = ttk.LabelFrame(parent, text="黑 名 单 管 理（扩展A）", padding=10)
        frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(frame, text="用户ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.blacklist_uid_var, width=14).grid(row=0, column=1, padx=6)
        ttk.Button(frame, text="加入黑名单", command=self._add_blacklist).grid(row=0, column=2)
        ttk.Button(frame, text="移出黑名单", command=self._remove_blacklist).grid(row=1, column=0, pady=4)
        ttk.Button(frame, text="查看黑名单", command=self._show_blacklist).grid(row=1, column=1, pady=4)
        ttk.Button(frame, text="清空黑名单", command=self._clear_blacklist).grid(row=1, column=2, pady=4)

    # ===================== 结果展示区 =====================
    def _build_result_area(self, parent):
        self.output = ScrolledText(parent, wrap=tk.WORD, font=("微软雅黑", 10))
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.config(state=tk.DISABLED)

        self.output.tag_config("info", foreground="#0066cc")
        self.output.tag_config("success", foreground="#008822")
        self.output.tag_config("error", foreground="#dd2222")
        self.output.tag_config("title", foreground="#6622bb", font=("微软雅黑", 11, "bold"))
        self.output.tag_config("warning", foreground="#cc8800")
        self.output.tag_config("detail", foreground="#333333")

        self._print_msg("=== 社交网络图谱分析及智能推荐系统 启动完成 ===", tag="title")
        self._print_msg("请在左侧输入用户ID并确认，即可查询各类人脉信息\n", tag="info")

    # ===================== 通用工具方法 =====================
    def _print_msg(self, text: str, tag="normal"):
        self.output.config(state=tk.NORMAL)
        import datetime
        time_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.output.insert(tk.END, f"[{time_stamp}] {text}\n", tag)
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    def _clear_output(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete(1.0, tk.END)
        self.output.config(state=tk.DISABLED)
        self._print_msg("输出区已清空", tag="info")

    def _check_uid_valid(self, input_str: str) -> Tuple[bool, int]:
        raw = input_str.strip()
        if not raw:
            messagebox.showerror("输入错误", "用户ID不能为空！")
            return False, -1
        try:
            uid = int(raw)
        except ValueError:
            messagebox.showerror("输入错误", f"「{raw}」不是合法数字，请输入正整数ID")
            return False, -1
        if uid <= 0:
            messagebox.showerror("输入错误", "用户ID必须大于0！")
            return False, -1
        if self.graph_model.get_user_info(uid)["name"] == "未知用户":
            messagebox.showerror("用户不存在", f"用户ID {uid} 未在系统中注册")
            return False, -1
        return True, uid

    def _format_user_name(self, uid: int) -> str:
        info = self.graph_model.get_user_info(uid)
        return f"{uid}({info['name']})"

    # ===================== 确认当前用户 =====================
    def _confirm_current_user(self):
        valid, uid = self._check_uid_valid(self.current_uid_var.get())
        if not valid:
            return
        info = self.graph_model.get_user_info(uid)
        interests = "、".join(info["interests"]) if info["interests"] else "无"

        self.user_info_label.config(
            text=f"当前用户：{uid} {info['name']}\n兴趣：{interests}",
            foreground="#000000"
        )
        self.distance_start_label.config(text=f"{uid} {info['name']}", foreground="#000000")
        self.add_friend_from_label.config(text=f"{uid} {info['name']}", foreground="#000000")

        self._print_msg(f"已切换查询目标：{self._format_user_name(uid)}", tag="info")

    # ===================== 文件加载 =====================
    def _auto_load_default_data(self):
        self._print_msg("开始自动加载默认数据文件...", tag="info")
        user_ok = self.graph_model.load_users_from_csv(self.user_csv_path) if os.path.exists(
            self.user_csv_path) else False
        rel_ok = self.graph_model.load_relationships_from_txt(self.rel_txt_path) if os.path.exists(
            self.rel_txt_path) else False

        if user_ok and rel_ok:
            self._print_msg("✅ 用户数据、好友关系全部加载成功！", tag="success")
        elif user_ok or rel_ok:
            self._print_msg("⚠ 部分数据加载成功，功能可能受限", tag="warning")
        else:
            self._print_msg("❌ 默认数据加载失败，请通过【文件操作】菜单手动选择文件", tag="error")

    def _load_user_file_dialog(self):
        path = filedialog.askopenfilename(title="选择用户数据CSV文件",
                                          filetypes=[("CSV表格", "*.csv"), ("全部文件", "*.*")])
        if not path:
            return
        self.user_csv_path = path
        if self.graph_model.load_users_from_csv(path):
            self._print_msg(f"✅ 用户文件加载成功：{os.path.basename(path)}", tag="success")
        else:
            self._print_msg("❌ 用户文件解析失败", tag="error")

    def _load_rel_file_dialog(self):
        path = filedialog.askopenfilename(title="选择好友关系TXT文件",
                                          filetypes=[("文本文件", "*.txt"), ("全部文件", "*.*")])
        if not path:
            return
        self.rel_txt_path = path
        if self.graph_model.load_relationships_from_txt(path):
            self._print_msg(f"✅ 关系文件加载成功：{os.path.basename(path)}", tag="success")
        else:
            self._print_msg("❌ 关系文件解析失败", tag="error")

    # ===================== 人脉查询 =====================
    def _query_direct(self):
        valid, uid = self._check_uid_valid(self.current_uid_var.get())
        if not valid:
            return
        friends_with_weight = self.graph_model.get_direct_friends_with_weight(uid)
        user_name = self.graph_model.get_user_info(uid)["name"]

        self._print_msg(f"======== 用户{uid}({user_name}) 一度人脉 ========", tag="title")
        if not friends_with_weight:
            self._print_msg("该用户暂无直接好友", tag="info")
            return

        self._print_msg(f"共 {len(friends_with_weight)} 位直接好友，按亲密度降序：\n", tag="info")
        for idx, (fid, weight) in enumerate(friends_with_weight, 1):
            finfo = self.graph_model.get_user_info(fid)
            finterests = "、".join(finfo["interests"]) if finfo["interests"] else "无"
            self._print_msg(f"  【{idx}】ID：{fid}  姓名：{finfo['name']}", tag="success")
            self._print_msg(f"      亲密度：{weight}  兴趣：{finterests}\n", tag="detail")

    def _query_second(self):
        valid, uid = self._check_uid_valid(self.current_uid_var.get())
        if not valid:
            return
        second_list = self.graph_model.find_second_degree_with_path(uid)
        user_name = self.graph_model.get_user_info(uid)["name"]

        self._print_msg(f"======== 用户{uid}({user_name}) 二度人脉 ========", tag="title")
        if not second_list:
            self._print_msg("该用户无二度人脉", tag="info")
            return

        self._print_msg(f"总计：{len(second_list)} 位二度人脉\n", tag="info")
        for idx, (sec_uid, mid_uid, path) in enumerate(second_list, 1):
            sinfo = self.graph_model.get_user_info(sec_uid)
            sinterests = "、".join(sinfo["interests"]) if sinfo["interests"] else "无"
            path_str = " → ".join([self._format_user_name(p) for p in path])
            self._print_msg(f"【{idx}】ID：{sec_uid}  姓名：{sinfo['name']}", tag="success")
            self._print_msg(f"      兴趣：{sinterests}", tag="detail")
            self._print_msg(f"      连通路径：{path_str}\n", tag="detail")

    def _query_n_degree(self):
        valid_uid, uid = self._check_uid_valid(self.current_uid_var.get())
        if not valid_uid:
            return
        n_raw = self.n_degree_var.get().strip()
        try:
            n = int(n_raw)
            if n < 3:
                messagebox.showerror("参数错误", "多度查询度数必须≥3")
                return
        except ValueError:
            messagebox.showerror("参数错误", "请输入有效的数字度数")
            return

        res_list = self.graph_model.find_n_degree_friends(uid, n)
        user_name = self.graph_model.get_user_info(uid)["name"]
        self._print_msg(f"======== 用户{uid}({user_name}) {n}度人脉 ========", tag="title")

        if not res_list:
            self._print_msg(f"未找到{n}度人脉", tag="info")
            return

        self._print_msg(f"总计：{len(res_list)} 位{n}度人脉\n", tag="info")
        for idx, rid in enumerate(res_list, 1):
            rinfo = self.graph_model.get_user_info(rid)
            rinterests = "、".join(rinfo["interests"]) if rinfo["interests"] else "无"
            self._print_msg(f"【{idx}】ID：{rid}  姓名：{rinfo['name']}  兴趣：{rinterests}", tag="success")

    # ===================== 社交距离计算 =====================
    def _calc_distance(self):
        s_ok, start = self._check_uid_valid(self.current_uid_var.get())
        if not s_ok:
            messagebox.showerror("操作失败", "请先确认当前查询用户")
            return
        e_ok, end = self._check_uid_valid(self.end_uid_var.get())
        if not e_ok:
            return

        use_weight = self.use_weight_flag.get()
        if use_weight:
            total_w, path = self.graph_model.get_weighted_shortest_path(start, end)
            desc = f"加权最短路径 | 路径总权重：{total_w}"
        else:
            dist, path = self.graph_model.get_shortest_distance(start, end)
            total_w = dist
            desc = f"无权社交距离 | 跳数：{dist}"

        self._print_msg(f"======== {self._format_user_name(start)} ➜ {self._format_user_name(end)} ========",
                        tag="title")
        if total_w == -1:
            self._print_msg("两个用户之间不存在连通路径", tag="warning")
            return

        self._print_msg(desc, tag="info")
        path_str = " → ".join([self._format_user_name(p) for p in path])
        self._print_msg(f"完整路径：{path_str}\n", tag="success")

    # ===================== 兴趣推荐 =====================
    def _interest_recommend(self):
        valid, uid = self._check_uid_valid(self.current_uid_var.get())
        if not valid:
            return
        try:
            top_n = int(self.top_k_var.get().strip())
            if top_n <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("参数错误", "推荐数量必须为正整数")
            return

        rec_list = self.graph_model.recommend_friends_by_interest(uid, top_n)
        user_info = self.graph_model.get_user_info(uid)
        interests = "、".join(user_info["interests"]) if user_info["interests"] else "无"

        self._print_msg(f"======== 用户{uid}({user_info['name']}) 兴趣推荐 Top{top_n} ========", tag="title")
        self._print_msg(f"本人兴趣：{interests}\n", tag="info")

        if not rec_list:
            self._print_msg("暂无匹配的陌生好友可供推荐", tag="warning")
            return

        for idx, (rid, rname, same_cnt, same_interests) in enumerate(rec_list, 1):
            inter_str = "、".join(same_interests) if same_interests else "无"
            self._print_msg(f"【{idx}】推荐用户：{self._format_user_name(rid)}", tag="success")
            self._print_msg(f"      共同兴趣数量：{same_cnt} ｜重合兴趣：{inter_str}\n", tag="detail")

    # ===================== 用户/好友管理 =====================
    def _add_new_user(self):
        uid_str = self.new_uid_var.get().strip()
        name = self.new_name_var.get().strip()
        interest_str = self.new_interest_var.get().strip()

        try:
            uid = int(uid_str)
            if uid <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "用户ID必须为正整数")
            return
        if not name:
            messagebox.showerror("输入错误", "用户姓名不能为空")
            return

        interests = [i.strip() for i in interest_str.split(";") if i.strip()]
        if self.graph_model.add_user(uid, name, interests):
            self._print_msg(f"✅ 成功添加用户：{self._format_user_name(uid)}", tag="success")
            self.new_uid_var.set("")
            self.new_name_var.set("")
            self.new_interest_var.set("")
        else:
            self._print_msg(f"⚠ 用户ID {uid} 已存在", tag="warning")

    def _add_new_friend(self):
        valid1, u1 = self._check_uid_valid(self.current_uid_var.get())
        if not valid1:
            messagebox.showerror("操作失败", "请先确认当前查询用户")
            return
        valid2, u2 = self._check_uid_valid(self.friend_target_var.get())
        if not valid2:
            return
        try:
            weight = int(self.friend_weight_var.get().strip())
            if weight <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "权重必须为正整数")
            return

        self.graph_model.add_friendship(u1, u2, weight)
        self._print_msg(f"✅ 成功建立好友关系：{self._format_user_name(u1)} ↔ {self._format_user_name(u2)}（权重{weight}）",
                        tag="success")
        self.friend_target_var.set("")

    def _delete_user(self):
        valid, uid = self._check_uid_valid(self.current_uid_var.get())
        if not valid:
            return
        if not messagebox.askyesno("确认删除", f"确定删除当前用户 {uid} 吗？\n删除后无法恢复"):
            return
        if self.graph_model.delete_user(uid):
            self._print_msg(f"✅ 已彻底删除用户：{uid}", tag="success")
            self.user_info_label.config(text="未选中用户", foreground="#888888")
            self.distance_start_label.config(text="未选中", foreground="#888888")
            self.add_friend_from_label.config(text="未选中", foreground="#888888")
            self.current_uid_var.set("")
        else:
            self._print_msg("删除失败", tag="error")

    def _delete_friendship(self):
        valid1, u1 = self._check_uid_valid(self.current_uid_var.get())
        if not valid1:
            messagebox.showerror("操作失败", "请先确认当前查询用户")
            return
        valid2, u2 = self._check_uid_valid(self.friend_target_var.get())
        if not valid2:
            return

        if self.graph_model.delete_friendship(u1, u2):
            self._print_msg(f"✅ 已解除好友关系：{self._format_user_name(u1)} ↔ {self._format_user_name(u2)}",
                            tag="success")
            self.friend_target_var.set("")
        else:
            self._print_msg("⚠ 两位用户并非好友", tag="warning")

    # ===================== 黑名单管理 =====================
    def _add_blacklist(self):
        valid, uid = self._check_uid_valid(self.blacklist_uid_var.get())
        if not valid:
            return
        if self.graph_model.add_to_blacklist(uid):
            self._print_msg(f"✅ 已将 {self._format_user_name(uid)} 加入黑名单", tag="success")
        else:
            self._print_msg("添加失败", tag="error")

    def _remove_blacklist(self):
        valid, uid = self._check_uid_valid(self.blacklist_uid_var.get())
        if not valid:
            return
        if self.graph_model.remove_from_blacklist(uid):
            self._print_msg(f"✅ 已将 {self._format_user_name(uid)} 移出黑名单", tag="success")
        else:
            self._print_msg("⚠ 该用户不在黑名单中", tag="warning")

    def _show_blacklist(self):
        black_list = list(self.graph_model.blacklist)
        self._print_msg("======== 当前黑名单列表 ========", tag="title")
        if not black_list:
            self._print_msg("黑名单为空", tag="info")
            return
        self._print_msg(f"黑名单总人数：{len(black_list)}\n", tag="info")
        show = [self._format_user_name(uid) for uid in sorted(black_list)]
        self._print_msg("拉黑用户：" + "、".join(show), tag="detail")

    def _clear_blacklist(self):
        if not messagebox.askyesno("确认清空", "确定清空全部黑名单吗？"):
            return
        self.graph_model.clear_blacklist()
        self._print_msg("✅ 黑名单已全部清空", tag="success")

    # ===================== 统计功能 =====================
    def _show_communities(self):
        comms = self.graph_model.find_all_communities()
        self._print_msg("======== 全网连通社群划分结果 ========", tag="title")
        self._print_msg(f"全网一共划分出 {len(comms)} 个独立连通社群\n", tag="info")
        for idx, group in enumerate(comms, 1):
            name_list = [self._format_user_name(uid) for uid in group]
            self._print_msg(f"【社群{idx}】人数：{len(group)}", tag="success")
            self._print_msg(f"成员列表：{'、'.join(name_list)}\n", tag="detail")

    def _show_centrality(self):
        cen_list = self.graph_model.calc_degree_centrality()
        self._print_msg("======== 用户度中心性排行（好友数量） ========", tag="title")
        self._print_msg(f"统计人数：{len(cen_list)} 位用户\n", tag="info")
        for idx, (uid, cnt, name) in enumerate(cen_list, 1):
            self._print_msg(f"【第{idx}名】{uid} {name} ｜直接好友数量：{cnt}", tag="success")

    # ===================== 可视化 =====================
    def _generate_network_html(self):
        if len(self.graph_model.user_attrs.buckets) == 0:
            messagebox.showwarning("数据为空", "请先加载数据")
            return
        try:
            net = Network(notebook=False, width="100%", height="900px", directed=False)
            net.set_options("""
            {
              "nodes": {
                "font": { "size": 14, "strokeWidth": 3, "strokeColor": "#ffffff" },
                "shape": "dot", "shadow": true
              },
              "edges": { "smooth": { "type": "continuous" }, "color": { "inherit": false } },
              "physics": {
                "barnesHut": {
                  "gravitationalConstant": -8000, "centralGravity": 0.3,
                  "springLength": 200, "springConstant": 0.04, "damping": 0.09
                },
                "maxVelocity": 50, "minVelocity": 0.1, "timestep": 0.5
              },
              "interaction": { "hover": true, "tooltipDelay": 100, "zoomView": true, "dragView": true }
            }
            """)

            all_users = []
            for bucket in self.graph_model.user_attrs.buckets:
                for uid, attr in bucket:
                    all_users.append((uid, attr))

            colors = ["#42a5f5", "#66bb6a", "#ffa726", "#ab47bc", "#ef5350", "#26c6da"]
            for idx, (uid, attr) in enumerate(all_users):
                label = f"{uid}-{attr['name']}"
                friend_count = len(self.graph_model.graph.get(uid, set()))
                size = 20 + min(friend_count * 3, 25)
                title = f"ID：{uid}\n姓名：{attr['name']}\n好友数：{friend_count}\n兴趣：{'、'.join(attr['interests'])}"
                net.add_node(uid, label=label, size=size, color=colors[idx % len(colors)], title=title)

            added_edges = set()
            for (u1, u2), w in self.graph_model.edge_weights.items():
                if (u2, u1) not in added_edges:
                    net.add_edge(u1, u2, width=w * 0.8, title=f"亲密度：{w}", color="#90a4ae")
                    added_edges.add((u1, u2))

            save_path = "social_network_graph.html"
            net.write_html(save_path)
            webbrowser.open(os.path.abspath(save_path))
            self._print_msg("✅ 社交网络图已生成，已在浏览器打开", tag="success")
        except Exception as e:
            messagebox.showerror("生成失败", str(e))

    # ===================== 帮助与关于 =====================
    def _show_help_msg(self):
        help_text = """
【操作说明】
1. 输入用户ID并确认，作为全局查询目标
2. 一键查询一度/二度/多度人脉、兴趣推荐
3. 社交距离起点自动复用当前用户
4. 添加/解除好友默认以当前用户为发起方
5. 顶部「统计工具」菜单可查看社群、中心性排行
6. 可视化菜单可生成交互式网络图
"""
        messagebox.showinfo("功能帮助", help_text)

    def _show_about_msg(self):
        about = """
社交网络图谱分析及智能推荐系统
数据结构课程设计作品
核心技术：邻接表、哈希表、BFS、Dijkstra
扩展：多度人脉、黑名单、兴趣推荐、可视化
"""
        messagebox.showinfo("关于系统", about)


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = SocialNetworkGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("启动失败", str(e))