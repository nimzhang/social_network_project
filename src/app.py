import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu
from tkinter.scrolledtext import ScrolledText
from src.social_graph import SocialGraph
import os
import webbrowser
from pyvis.network import Network
from collections import deque
from typing import Tuple


class SocialNetworkGUI:
    def __init__(self, root_window):
        # 主窗口基础配置
        self.root = root_window
        self.root.title("社交网络图谱分析及智能推荐系统")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)  # 最小窗口尺寸，防止界面挤压

        # 绑定后端图实例
        self.graph_model = SocialGraph()

        # 全局文件路径变量
        # 获取app.py所在文件夹(src)
        src_dir = os.path.dirname(os.path.abspath(__file__))
        # src向上一层就是项目根目录
        project_root = os.path.dirname(src_dir)

        self.user_csv_path = os.path.join(project_root, "data", "users.csv")
        self.rel_txt_path = os.path.join(project_root, "data", "relationships.txt")

        # 界面输入绑定变量
        self.input_uid = tk.StringVar()          # 单用户ID（一度/二度/多度查询）
        self.start_uid_var = tk.StringVar()      # 距离计算起点
        self.end_uid_var = tk.StringVar()        # 距离计算终点
        self.n_degree_var = tk.StringVar(value="3")  # 多度人脉度数
        self.top_k_var = tk.StringVar(value="5")  # 推荐TopN数量
        self.use_weight_flag = tk.BooleanVar(value=False)  # 是否启用加权路径

        # 初始化UI布局、菜单栏、事件绑定
        self._create_menu_bar()
        self._build_main_layout()
        # 程序启动自动加载默认数据
        self._auto_load_default_data()

    # ===================== 顶部菜单栏 =====================
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

        # 可视化扩展菜单（扩展E）
        vis_menu = Menu(menu_bar, tearoff=0)
        vis_menu.add_command(label="生成社交网络图", command=self._generate_network_html)
        menu_bar.add_cascade(label="可视化", menu=vis_menu)

        # 帮助菜单
        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="功能操作说明", command=self._show_help_msg)
        help_menu.add_command(label="关于系统", command=self._show_about_msg)
        menu_bar.add_cascade(label="帮助", menu=help_menu)

    # ===================== 主界面左右分栏布局 =====================
    def _build_main_layout(self):
        # 左侧功能操作面板
        left_panel = ttk.Frame(self.root)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        left_panel.config(width=320)
        left_panel.pack_propagate(False)

        # 右侧结果展示面板
        right_panel = ttk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 构建左侧所有功能模块
        self._build_left_widgets(left_panel)
        # 构建右侧滚动结果框
        self._build_result_area(right_panel)

    # ===================== 左侧功能分区组件 =====================
    def _build_left_widgets(self, parent_frame):
        # 1. 一度人脉模块
        frame1 = ttk.LabelFrame(parent_frame, text="一 度 人 脉 查 询", padding=10)
        frame1.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(frame1, text="用户ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame1, textvariable=self.input_uid, width=12).grid(row=0, column=1, padx=6)
        ttk.Button(frame1, text="查询", command=self._query_direct).grid(row=0, column=2)

        # 2. 二度人脉模块（基础必做）
        frame2 = ttk.LabelFrame(parent_frame, text="二 度 人 脉 查 询", padding=10)
        frame2.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(frame2, text="用户ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame2, textvariable=self.input_uid, width=12).grid(row=0, column=1, padx=6)
        ttk.Button(frame2, text="查询", command=self._query_second).grid(row=0, column=2)

        # 3. 多度人脉（扩展A）
        frame3 = ttk.LabelFrame(parent_frame, text="多 度 人 脉（扩展A）", padding=10)
        frame3.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(frame3, text="用户ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame3, textvariable=self.input_uid, width=12).grid(row=0, column=1, padx=6)
        ttk.Label(frame3, text="度数N：").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame3, textvariable=self.n_degree_var, width=12).grid(row=1, column=1, padx=6)
        ttk.Button(frame3, text="查询", command=self._query_n_degree).grid(row=1, column=2)

        # 4. 社交距离计算（BFS无权 / Dijkstra加权）
        frame4 = ttk.LabelFrame(parent_frame, text="社 交 距 离 计 算", padding=10)
        frame4.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(frame4, text="起点ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame4, textvariable=self.start_uid_var, width=12).grid(row=0, column=1, padx=6)
        ttk.Label(frame4, text="终点ID：").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame4, textvariable=self.end_uid_var, width=12).grid(row=1, column=1, padx=6)
        ttk.Checkbutton(frame4, text="加权路径", variable=self.use_weight_flag).grid(row=0, column=2, rowspan=2)
        ttk.Button(frame4, text="计算最短路径", command=self._calc_distance).grid(row=2, column=1, pady=4)

        # 5. 兴趣智能推荐（扩展C）
        frame5 = ttk.LabelFrame(parent_frame, text="兴 趣 推 荐（扩展C）", padding=10)
        frame5.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(frame5, text="用户ID：").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame5, textvariable=self.input_uid, width=12).grid(row=0, column=1, padx=6)
        ttk.Label(frame5, text="推荐数：").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame5, textvariable=self.top_k_var, width=12).grid(row=1, column=1, padx=6)
        ttk.Button(frame5, text="生成推荐", command=self._interest_recommend).grid(row=1, column=2)

        # 6. 社群/核心用户快捷工具
        frame6 = ttk.LabelFrame(parent_frame, text="辅 助 统 计", padding=10)
        frame6.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(frame6, text="查看所有社群", command=self._show_communities).grid(row=0, column=0, padx=2, pady=3)
        ttk.Button(frame6, text="度中心性排行", command=self._show_centrality).grid(row=0, column=1, padx=2, pady=3)

        # 底部清空按钮
        clear_btn = ttk.Button(parent_frame, text="清空结果输出区", command=self._clear_output)
        clear_btn.pack(fill=tk.X, pady=15)

    # ===================== 右侧结果滚动文本框 =====================
    def _build_result_area(self, parent_frame):
        # 滚动文本框，只读展示输出
        self.output = ScrolledText(parent_frame, wrap=tk.WORD, font=("微软雅黑", 10))
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.config(state=tk.DISABLED)
        # 定义文字颜色标签
        self.output.tag_config("info", foreground="#0066cc")
        self.output.tag_config("success", foreground="#008822")
        self.output.tag_config("error", foreground="#dd2222")
        self.output.tag_config("title", foreground="#6622bb", font=("微软雅黑", 11, "bold"))
        # 欢迎文字
        self._print_msg("=== 社交网络系统启动完成 ===", tag="title")
        self._print_msg("已自动加载data目录下users.csv、relationships.txt\n", tag="info")

    # ===================== 输出区工具函数 =====================
    def _print_msg(self, text: str, tag="normal"):
        """统一格式化输出到右侧文本框"""
        self.output.config(state=tk.NORMAL)
        import datetime
        time_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.output.insert(tk.END, f"[{time_stamp}] {text}\n", tag)
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    def _clear_output(self):
        """清空右侧所有内容"""
        self.output.config(state=tk.NORMAL)
        self.output.delete(1.0, tk.END)
        self.output.config(state=tk.DISABLED)
        self._print_msg("输出区已清空", tag="info")

    # ===================== 输入校验通用工具 =====================
    def _check_uid_input(self, input_str: str) -> Tuple[bool, int]:
        """校验输入是否为合法正整数用户ID"""
        raw = input_str.strip()
        if not raw:
            messagebox.showerror("输入校验失败", "用户ID不能为空！")
            return False, -1
        try:
            uid = int(raw)
        except ValueError:
            messagebox.showerror("输入校验失败", f"「{raw}」不是合法数字，请输入正整数ID")
            return False, -1
        if uid <= 0:
            messagebox.showerror("输入校验失败", "用户ID必须大于0！")
            return False, -1
        if uid not in self.graph_model.user_attrs:
            messagebox.showerror("用户不存在", f"用户ID {uid} 未在数据中注册")
            return False, -1
        return True, uid

    # ===================== 文件加载相关 =====================
    def _auto_load_default_data(self):
        """程序启动自动加载data下默认文件"""
        self._print_msg("开始自动加载默认数据文件...", tag="info")
        user_ok = False
        rel_ok = False
        if os.path.exists(self.user_csv_path):
            user_ok = self.graph_model.load_users_from_csv(self.user_csv_path)
        else:
            self._print_msg(f"警告：{self.user_csv_path} 文件不存在", tag="error")

        if os.path.exists(self.rel_txt_path):
            rel_ok = self.graph_model.load_relationships_from_txt(self.rel_txt_path)
        else:
            self._print_msg(f"警告：{self.rel_txt_path} 文件不存在", tag="error")

        if user_ok and rel_ok:
            self._print_msg("✅ 用户、关系数据全部加载成功！", tag="success")
        elif user_ok or rel_ok:
            self._print_msg("⚠ 部分数据加载成功，缺失文件会影响功能", tag="info")
        else:
            self._print_msg("❌ 默认文件加载失败，请通过【文件操作】手动选择文件", tag="error")

    def _load_user_file_dialog(self):
        """弹窗选择用户CSV文件"""
        path = filedialog.askopenfilename(
            title="选择用户数据CSV",
            filetypes=[("CSV表格", "*.csv"), ("全部文件", "*.*")]
        )
        if not path:
            return
        self.user_csv_path = path
        res = self.graph_model.load_users_from_csv(path)
        if res:
            self._print_msg(f"✅ 用户文件 {os.path.basename(path)} 加载完成", tag="success")
        else:
            self._print_msg(f"❌ 用户文件 {os.path.basename(path)} 解析失败", tag="error")

    def _load_rel_file_dialog(self):
        """弹窗选择关系TXT文件"""
        path = filedialog.askopenfilename(
            title="选择好友关系TXT",
            filetypes=[("文本文件", "*.txt"), ("全部文件", "*.*")]
        )
        if not path:
            return
        self.rel_txt_path = path
        res = self.graph_model.load_relationships_from_txt(path)
        if res:
            self._print_msg(f"✅ 关系文件 {os.path.basename(path)} 加载完成", tag="success")
        else:
            self._print_msg(f"❌ 关系文件 {os.path.basename(path)} 解析失败", tag="error")

    # ===================== 核心功能绑定（基础7项） =====================
    def _query_direct(self):
        """一度人脉查询按钮事件"""
        valid, uid = self._check_uid_input(self.input_uid.get())
        if not valid:
            return
        friend_ids = self.graph_model.get_direct_friends(uid)
        user_info = self.graph_model.get_user_info(uid)
        name = user_info["name"]
        self._print_msg(f"======== 用户{uid}({name}) 一度人脉 ========", tag="title")
        if not friend_ids:
            self._print_msg("该用户暂无任何好友", tag="info")
            return
        show_list = []
        for fid in friend_ids:
            fn = self.graph_model.get_user_info(fid)["name"]
            show_list.append(f"{fid}({fn})")
        self._print_msg("、".join(show_list), tag="success")

    def _query_second(self):
        """二度人脉查询（BFS深度2）"""
        valid, uid = self._check_uid_input(self.input_uid.get())
        if not valid:
            return
        # 手动实现二度逻辑：深度2，排除自身和一度
        visited = {uid}
        direct = set(self.graph_model.get_direct_friends(uid))
        visited.update(direct)
        second_set = set()
        for f in direct:
            for ff in self.graph_model.graph[f]:
                if ff not in visited:
                    second_set.add(ff)
        second_list = sorted(list(second_set))
        user_info = self.graph_model.get_user_info(uid)
        self._print_msg(f"======== 用户{uid}({user_info['name']}) 二度人脉 ========", tag="title")
        if not second_list:
            self._print_msg("该用户无二度人脉", tag="info")
            return
        show = []
        for sid in second_list:
            sname = self.graph_model.get_user_info(sid)["name"]
            show.append(f"{sid}({sname})")
        self._print_msg("、".join(show), tag="success")

    def _query_n_degree(self):
        """扩展A：N度人脉自定义查询"""
        valid_uid, uid = self._check_uid_input(self.input_uid.get())
        if not valid_uid:
            return
        # 校验度数
        n_raw = self.n_degree_var.get().strip()
        try:
            n = int(n_raw)
            if n < 3:
                messagebox.showerror("度数错误", "多度查询N必须≥3，二度请使用上方二度按钮")
                return
        except ValueError:
            messagebox.showerror("度数错误", "请输入数字度数（3/4/5）")
            return
        # BFS遍历分层
        depth_map = {uid: 0}
        q = deque([uid])
        target_n_set = set()
        while q:
            cur = q.popleft()
            cur_dep = depth_map[cur]
            if cur_dep >= n:
                continue
            for neighbor in self.graph_model.graph[cur]:
                if neighbor not in depth_map:
                    depth_map[neighbor] = cur_dep + 1
                    q.append(neighbor)
                    if depth_map[neighbor] == n:
                        target_n_set.add(neighbor)
        res_list = sorted(list(target_n_set))
        uname = self.graph_model.get_user_info(uid)["name"]
        self._print_msg(f"======== 用户{uid}({uname}) {n}度人脉 ========", tag="title")
        if not res_list:
            self._print_msg(f"不存在{n}度人脉", tag="info")
            return
        show = [f"{x}({self.graph_model.get_user_info(x)['name']})" for x in res_list]
        self._print_msg("、".join(show), tag="success")

    def _calc_distance(self):
        """社交距离计算，切换BFS/Dijkstra"""
        s_raw = self.start_uid_var.get().strip()
        e_raw = self.end_uid_var.get().strip()
        ok1, start = self._check_uid_input(s_raw)
        ok2, end = self._check_uid_input(e_raw)
        if not (ok1 and ok2):
            return
        use_weight = self.use_weight_flag.get()
        if use_weight:
            total_w, path = self.graph_model.get_weighted_shortest_path(start, end)
            title = f"【加权最短路径 总权重：{total_w}】"
        else:
            dist, path = self.graph_model.get_shortest_distance(start, end)
            total_w = dist
            title = f"【无权最短社交距离：{dist}】"
        self._print_msg(f"======== {start} → {end} {title} ========", tag="title")
        if total_w == -1:
            self._print_msg("两个用户不存在连通的社交路径", tag="error")
            return
        # 拼接带姓名路径
        path_str = []
        for p_id in path:
            p_name = self.graph_model.get_user_info(p_id)["name"]
            path_str.append(f"{p_id}({p_name})")
        self._print_msg("最短路径：" + " → ".join(path_str), tag="success")

    def _interest_recommend(self):
        """扩展C：兴趣智能推荐"""
        valid, uid = self._check_uid_input(self.input_uid.get())
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
        self._print_msg(f"======== 用户{uid}({user_info['name']}) 兴趣推荐Top{top_n} ========", tag="title")
        self._print_msg(f"用户自身兴趣：{interests}", tag="info")
        if not rec_list:
            self._print_msg("无匹配陌生好友可供推荐", tag="info")
            return
        for (rid, rname, same_cnt) in rec_list:
            self._print_msg(f"推荐用户{rid} {rname} | 共同兴趣数：{same_cnt}", tag="success")

    # ===================== 辅助统计功能 =====================
    def _show_communities(self):
        """展示所有连通社群"""
        comms = self.graph_model.find_all_communities()
        self._print_msg("======== 全网连通社群划分 ========", tag="title")
        for idx, group in enumerate(comms, 1):
            name_list = [f"{uid}({self.graph_model.get_user_info(uid)['name']})" for uid in group]
            self._print_msg(f"社群{idx}（共{len(group)}人）：" + "、".join(name_list), tag="info")

    def _show_centrality(self):
        """度中心性排行"""
        cen_list = self.graph_model.calc_degree_centrality()
        self._print_msg("======== 用户好友数量排行（度中心性） ========", tag="title")
        for idx, (uid, cnt, name) in enumerate(cen_list, 1):
            self._print_msg(f"第{idx}名：{uid} {name} | 好友总数：{cnt}", tag="success")

    # ===================== 扩展E：PyVis网络图可视化 =====================
    def _generate_network_html(self):
        """生成交互式社交网络图HTML并自动打开"""
        if len(self.graph_model.user_attrs) == 0:
            messagebox.showwarning("数据为空", "请先加载用户和好友数据再生成可视化图")
            return
        net = Network(notebook=False, width="100%", height="850px", directed=False)
        # 全局设置节点字体大小14
        net.set_options("""
        {
          "nodes": {
            "font": {
              "size": 14
            }
          }
        }
        """)
        # 添加所有用户节点
        for uid, attr in self.graph_model.user_attrs.items():
            label = f"{uid}-{attr['name']}"
            net.add_node(uid, label=label, size=16)
        # 添加无向边，去重
        added_edges = set()
        for (u1, u2), w in self.graph_model.edge_weights.items():
            if (u2, u1) not in added_edges:
                net.add_edge(u1, u2, width=w, title=f"亲密度权重：{w}")
                added_edges.add((u1, u2))
        # 保存文件
        save_path = "social_network_graph.html"
        net.write_html(save_path)
        webbrowser.open(os.path.abspath(save_path))
        self._print_msg(f"✅ 社交网络图已生成，自动打开文件：{save_path}", tag="success")

    # ===================== 帮助弹窗 =====================
    def _show_help_msg(self):
        help_text = """
【系统功能说明】
基础必做7项功能：
1. 图建模：自主邻接表存储用户与好友关系
2. 数据持久化：加载CSV用户、TXT好友文件
3. 一度人脉：直接好友查询
4. 二度人脉：BFS深度2筛选好友的好友
5. 社交距离：BFS无权 / Dijkstra加权最短路径
6. 哈希表缓存用户信息
7. 完整Tkinter图形界面

本次实现扩展功能ACE：
A 多度人脉：自定义3度及以上人脉遍历
C 兴趣智能推荐：基于兴趣倒排索引匹配陌生好友
E 可视化图谱：PyVis生成交互式网络图

操作提示：
1. data目录放置users.csv、relationships.txt可自动加载
2. 所有ID必须为正整数，不存在用户会弹窗报错
3. 加权勾选后使用Dijkstra计算权重最短路径
4. 可视化菜单可生成网页关系图，支持拖拽缩放
"""
        messagebox.showinfo("功能帮助", help_text)

    def _show_about_msg(self):
        about = """
社交网络图谱分析及智能推荐系统
数据结构课程设计 | ACE扩展实现
开发语言：Python3 + Tkinter
核心数据结构：邻接表、哈希表、堆
核心算法：BFS、Dijkstra、倒排索引推荐
扩展：多度人脉、兴趣推荐、网络图可视化
"""
        messagebox.showinfo("关于本系统", about)


# 程序入口启动
if __name__ == "__main__":
    root = tk.Tk()
    app = SocialNetworkGUI(root)
    root.mainloop()