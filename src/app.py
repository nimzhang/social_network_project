# pyright: reportGeneralTypeIssues=false
# type: ignore
"""
src/app.py：系统GUI界面控制模块
采用Tkinter开发桌面交互，MVC视图+控制器层，对接自主实现的邻接表、哈希表、BFS/Dijkstra底层
本模块由小组GUI负责人完成
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu
from tkinter.scrolledtext import ScrolledText
import os, webbrowser, datetime, threading
# 导入自主编写的底层图数据结构核心类
from src.social_graph import SocialGraph

# ===================== 全局UI常量配置 =====================
WIN_TITLE = "社交网络图谱分析系统"  # 程序主窗口标题
WIN_SIZE = "1000x650"             # 窗口初始宽高
FONT = ("微软雅黑", 10)            # 全局统一文字字体
# 日志输出文字颜色分类，区分提示/成功/警告/错误
TAG_COLORS = {
    "title": "#553399",    # 模块标题：紫色
    "info": "#0066cc",     # 普通提示：蓝色
    "success": "#008822",  # 操作成功：绿色
    "warning": "#cc8800",  # 警告信息：橙黄
    "error": "#cc2222",    # 错误提示：红色
    "detail": "#555555"    # 明细文本：灰色
}
SORT_OPTIONS = ["按ID升序", "按亲密度降序", "按共同兴趣降序"]  # 人脉排序下拉选项
DEFAULT_SORT = "按亲密度降序"                                 # 默认排序策略


class SocialNetworkGUI:
    """
    MVC视图+控制器主类：负责全部GUI交互、按钮事件、数据联动
    核心职责：
    1. 窗口、菜单栏、左右功能面板布局搭建
    2. 输入校验、按钮绑定、快捷键注册
    3. 调用SocialGraph底层数据结构与算法接口
    4. 表格、日志渲染，文件导入导出
    5. 全部基础功能+扩展功能可视化交互
    依赖：tkinter、threading、pyvis(可视化扩展)、src.social_graph
    """
    def __init__(self, root):
        """
        窗口初始化构造方法
        :param root: tk.Tk 根窗口实例
        执行流程：窗口配置→实例化图模型→绑定变量→搭建UI→异步加载测试数据
        """
        # 基础窗口配置
        self.root = root
        root.title(WIN_TITLE)
        root.geometry(WIN_SIZE)
        root.minsize(800, 550)
        root.option_add("*Font", FONT)

        # MVC Model层实例：自主实现社交图数据结构
        self.graph = SocialGraph()
        self.current_uid = None  # 全局缓存当前操作用户

        # 计算项目data文件夹绝对路径，解决相对路径加载失败问题
        base = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(os.path.dirname(base), "data")

        # ---------------------- 界面绑定变量（输入框/复选框/下拉框） ----------------------
        # 核心查询相关变量
        self.uid_var = tk.StringVar()
        self.end_uid_var = tk.StringVar()
        self.degree_var = tk.StringVar(value="3")
        self.top_k_var = tk.StringVar(value="5")
        self.weight_mode = tk.BooleanVar(value=False)
        self.sort_var = tk.StringVar(value=DEFAULT_SORT)

        # 用户/好友新增编辑变量
        self.new_uid_var = tk.StringVar()
        self.new_name_var = tk.StringVar()
        self.new_inter_var = tk.StringVar()
        self.target_uid_var = tk.StringVar()
        self.weight_var = tk.StringVar(value="1")

        # 黑名单、可视化筛选变量
        self.black_uid_var = tk.StringVar()
        self.hide_black = tk.BooleanVar(value=False)
        self.only_subgraph = tk.BooleanVar(value=False)

        # 界面控件缓存，方便全局调用
        self.uid_entry = None
        self.user_info = None
        self.end_entry = None
        self.start_label = None
        self.tree = None
        self.log = None

        # 依次构建菜单栏、布局、快捷键
        self._create_menu()
        self._build_layout()
        self._bind_shortcuts()

        # ========== 恢复自动加载默认数据功能 ==========
        self._async_load_default()

    def _create_menu(self):
        """私有方法：创建窗口顶部全局菜单栏，分为四大功能菜单"""
        bar = Menu(self.root)
        # 文件菜单：数据导入、导出、退出
        f = Menu(bar, tearoff=0)
        for label, cmd in [("加载用户CSV", self._load_user_file), ("加载关系TXT", self._load_rel_file)]:
            f.add_command(label=label, command=cmd)
        f.add_separator()
        f.add_command(label="导出邻接表（TXT）", command=self._export_adj_list)
        f.add_command(label="导出纯文本表格（TXT）", command=self._export_adj_table)
        f.add_separator()
        f.add_command(label="退出", command=self.root.quit)
        bar.add_cascade(label="文件", menu=f)

        # 分析工具：社群划分、度中心性、清空输出
        s = Menu(bar, tearoff=0)
        s.add_command(label="社群划分", command=self._show_communities)
        s.add_command(label="度中心性排行", command=self._show_centrality)
        s.add_separator()
        s.add_command(label="清空输出", command=self._clear_all, accelerator="Ctrl+L")
        bar.add_cascade(label="分析工具", menu=s)

        # 可视化菜单：黑名单过滤、子图筛选、生成网络图
        v = Menu(bar, tearoff=0)
        v.add_checkbutton(label="隐藏黑名单用户", variable=self.hide_black)
        v.add_checkbutton(label="仅显示当前用户子网络", variable=self.only_subgraph)
        v.add_separator()
        v.add_command(label="生成网络图", command=self._generate_graph)
        bar.add_cascade(label="可视化", menu=v)

        # 帮助菜单：操作说明、关于弹窗
        h = Menu(bar, tearoff=0)
        h.add_command(label="使用说明", command=lambda: messagebox.showinfo("说明",
            "1. 输入ID点确认设为查询目标\n2. 点击按钮查询人脉/距离\n3. 支持增删用户、好友、黑名单\n4. 快捷键：回车确认，Ctrl+L清空"))
        h.add_command(label="关于", command=lambda: messagebox.showinfo("关于",
            "社交网络图谱分析系统\n数据结构课程设计\n邻接表 + 哈希表 + BFS/Dijkstra"))
        bar.add_cascade(label="帮助", menu=h)
        self.root.config(menu=bar)

    def _build_layout(self):
        """私有方法：搭建窗口左右分栏布局，左侧滚动操作面板，右侧结果展示"""
        # 主容器：grid布局划分左右比例
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)  # 左侧占1份宽度
        main_frame.grid_columnconfigure(1, weight=3)  # 右侧占3份宽度
        main_frame.grid_rowconfigure(0, weight=1)

        # ---------- 左侧滚动面板容器 ----------
        left_container = ttk.Frame(main_frame)
        left_container.grid(row=0, column=0, sticky="nsew")
        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        # 画布：实现垂直滚动功能
        left_canvas = tk.Canvas(left_container, highlightthickness=0)
        left_canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        left_canvas.configure(yscrollcommand=v_scrollbar)

        # 内部承载所有控件的Frame
        left = ttk.Frame(left_canvas)
        window_id = left_canvas.create_window((0, 0), window=left, anchor="nw")

        # 画布尺寸变化回调：同步内部容器宽度
        def _on_canvas_resize(event):
            left_canvas.itemconfig(window_id, width=event.width)

        # 内部内容高度变化：更新滚动区域范围
        def _on_left_configure(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))

        # 鼠标滚轮滚动事件回调
        def _on_mousewheel(event):
            if event.num == 4:
                left_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                left_canvas.yview_scroll(1, "units")
            else:
                delta = -1 if event.delta < 0 else 1
                left_canvas.yview_scroll(delta, "units")

        # 绑定画布各类事件
        left_canvas.bind("<Configure>", _on_canvas_resize)
        left.bind("<Configure>", _on_left_configure)
        left_canvas.bind("<Enter>", lambda e: left_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        left_canvas.bind("<Leave>", lambda e: left_canvas.unbind_all("<MouseWheel>"))
        left_canvas.bind("<Button-4>", _on_mousewheel)
        left_canvas.bind("<Button-5>", _on_mousewheel)

        # ================= 左侧所有控件 =================
        # 面板1：用户查询与人脉
        p = ttk.LabelFrame(left, text=" 用户查询与人脉 ", padding=8)
        p.pack(fill="x", pady=(0, 8))
        row1 = ttk.Frame(p)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="用户ID:").pack(side="left")
        self.uid_entry = ttk.Entry(row1, textvariable=self.uid_var, width=10)
        self.uid_entry.pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(row1, text="确认", command=self._confirm_user, width=6).pack(side="left", padx=(4, 0))
        self.user_info = ttk.Label(p, text="未选中用户", foreground="#888")
        self.user_info.pack(anchor="w", pady=4)

        row_sort = ttk.Frame(p)
        row_sort.pack(fill="x", pady=2)
        ttk.Label(row_sort, text="排序:", foreground="#666").pack(side="left")
        ttk.Combobox(row_sort, textvariable=self.sort_var, values=SORT_OPTIONS,
                     state="readonly", width=14).pack(side="left", padx=4, fill="x", expand=True)

        btn_row = ttk.Frame(p)
        btn_row.pack(fill="x", pady=4)
        for text, cmd in [("一度", self._query_1), ("二度", self._query_2), ("多度", self._query_n)]:
            ttk.Button(btn_row, text=text, command=cmd).pack(side="left", expand=True, fill="x", padx=1)

        row3 = ttk.Frame(p)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="度数:", foreground="#666").pack(side="left")
        ttk.Entry(row3, textvariable=self.degree_var, width=4).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Label(row3, text="TopK:", foreground="#666").pack(side="left", padx=(8, 0))
        ttk.Entry(row3, textvariable=self.top_k_var, width=4).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(row3, text="兴趣推荐", command=self._recommend).pack(side="left", padx=4)

        # 面板2：社交距离计算
        p = ttk.LabelFrame(left, text=" 社交距离计算 ", padding=8)
        p.pack(fill="x", pady=(0, 8))
        row1 = ttk.Frame(p)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="起点:").pack(side="left")
        self.start_label = ttk.Label(row1, text="未选中", foreground="#888")
        self.start_label.pack(side="left", padx=4)
        ttk.Checkbutton(row1, text="加权模式", variable=self.weight_mode).pack(side="left", padx=8)
        row2 = ttk.Frame(p)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="终点ID:").pack(side="left")
        self.end_entry = ttk.Entry(row2, textvariable=self.end_uid_var, width=10)
        self.end_entry.pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(row2, text="计算", command=self._calc_dist, width=6).pack(side="left", padx=(4, 0))

        # 面板3：用户与好友管理
        p = ttk.LabelFrame(left, text=" 用户与好友管理 ", padding=8)
        p.pack(fill="x", pady=(0, 8))
        r1 = ttk.Frame(p)
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="ID:").pack(side="left")
        ttk.Entry(r1, textvariable=self.new_uid_var, width=6).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Label(r1, text="姓名:").pack(side="left")
        ttk.Entry(r1, textvariable=self.new_name_var, width=8).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(r1, text="添加用户", command=self._add_user).pack(side="left", padx=4)
        r2 = ttk.Frame(p)
        r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="兴趣(、分隔):").pack(side="left")
        ttk.Entry(r2, textvariable=self.new_inter_var, width=18).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Separator(p, orient="horizontal").pack(fill="x", pady=6)
        r3 = ttk.Frame(p)
        r3.pack(fill="x", pady=2)
        ttk.Label(r3, text="对方ID:").pack(side="left")
        ttk.Entry(r3, textvariable=self.target_uid_var, width=6).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Label(r3, text="权重:").pack(side="left")
        ttk.Entry(r3, textvariable=self.weight_var, width=4).pack(side="left", padx=2, fill="x", expand=True)
        r4 = ttk.Frame(p)
        r4.pack(fill="x", pady=4)
        ttk.Button(r4, text="添加好友", command=self._add_friend).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(r4, text="解除好友", command=self._del_friend).pack(side="left", expand=True, fill="x", padx=2)

        # 面板4：黑名单管理
        p = ttk.LabelFrame(left, text=" 黑名单管理 ", padding=8)
        p.pack(fill="x", pady=(0, 8))
        r1 = ttk.Frame(p)
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="用户ID:").pack(side="left")
        ttk.Entry(r1, textvariable=self.black_uid_var, width=10).pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(r1, text="查看列表", command=self._show_black).pack(side="left", padx=(4, 0))
        r2 = ttk.Frame(p)
        r2.pack(fill="x", pady=4)
        for t, c in [("加入", self._add_black), ("移出", self._remove_black), ("清空", self._clear_black)]:
            ttk.Button(r2, text=t, command=c).pack(side="left", expand=True, fill="x", padx=2)

        # 弹性空白区域，将底部按钮挤到窗口下方
        spacer = ttk.Frame(left, height=0)
        spacer.pack(fill="both", expand=True)

        ttk.Button(left, text="删除当前用户", command=self._del_user).pack(fill="x", pady=(8, 0))

        # ---------- 右侧结果展示区域 ----------
        right = ttk.Frame(main_frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # 表格展示区
        table_frame = ttk.LabelFrame(right, text=" 结果展示 ")
        table_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        cols = ("c1", "c2", "c3", "c4")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=6)
        for c, w in zip(cols, [80, 100, 150, 250]):
            self.tree.column(c, width=w, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        # 操作日志滚动文本框
        log_frame = ttk.LabelFrame(right, text=" 操作日志 ")
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self.log = ScrolledText(log_frame, wrap=tk.WORD, bg="#fafafa", relief="flat", padx=8, pady=8)
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.config(state=tk.DISABLED)
        # 注册日志文字样式
        for tag, color in TAG_COLORS.items():
            self.log.tag_config(tag, foreground=color)
        self.log.tag_config("title", font=("微软雅黑", 11, "bold"))

    def _bind_shortcuts(self):
        """私有方法：绑定全局键盘快捷键"""
        self.uid_entry.bind("<Return>", lambda _: self._confirm_user())
        self.end_entry.bind("<Return>", lambda _: self._calc_dist())
        self.root.bind("<Control-l>", lambda _: self._clear_all())

    def _print(self, text, tag="normal"):
        """
        日志打印封装方法
        :param text: 输出文本内容
        :param tag: 文字颜色标签，对应TAG_COLORS
        """
        if not self.log:
            return
        self.log.config(state=tk.NORMAL)
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{t}] {text}\n", tag)
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _clear_all(self):
        """清空表格与全部日志内容"""
        if self.tree:
            for item in self.tree.get_children():
                self.tree.delete(item)
        if self.log:
            self.log.config(state=tk.NORMAL)
            self.log.delete(1.0, tk.END)
            self.log.config(state=tk.DISABLED)
        self._print("已清空所有输出", "info")

    def _update_table(self, headers, rows):
        """
        刷新表格数据
        :param headers: 表头列表，最多4列
        :param rows: 表格行数据二维列表
        """
        if not self.tree:
            return
        # 清空原有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        # 设置表头
        for col, h in zip(("c1", "c2", "c3", "c4"), headers):
            self.tree.heading(col, text=h)
        # 插入每一行数据
        for r in rows:
            self.tree.insert("", tk.END, values=r)

    def _valid_uid(self, uid_str):
        """
        用户ID统一校验工具函数
        :param uid_str: 输入框原始字符串
        :return (布尔是否合法, 转换后数字ID)
        """
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
        # 调用底层哈希表查询用户，不存在则报错
        if self.graph.get_user_info(uid)["name"] == "未知用户":
            messagebox.showerror("错误", f"用户 {uid} 不存在")
            return False, -1
        return True, uid

    def _name(self, uid):
        """
        格式化用户展示文本：ID(姓名)
        :param uid: 用户数字ID
        :return: 拼接完成的可读字符串
        """
        return f"{uid}({self.graph.get_user_info(uid)['name']})"

    # ---------------------- 数据加载异步工具 ----------------------
    def _async_load_default(self):
        """开启子线程异步加载默认data文件夹数据，防止GUI主线程阻塞卡死"""
        self._print("正在加载默认数据...", "info")
        self.root.config(cursor="wait")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        """子线程执行数据加载逻辑，不占用UI渲染线程"""
        user_path = os.path.join(self.data_dir, "users.csv")
        rel_path = os.path.join(self.data_dir, "relationships.txt")
        ok_u = self.graph.load_users_from_csv(user_path)
        ok_r = self.graph.load_relationships_from_txt(rel_path)
        # 切回主线程更新界面提示
        self.root.after(0, self._on_load_done, ok_u, ok_r)

    def _on_load_done(self, ok_u, ok_r):
        """数据加载完成后的UI回调提示"""
        self.root.config(cursor="")
        if ok_u and ok_r:
            self._print("✅ 默认数据加载完成", "success")
        else:
            self._print("⚠️ 部分数据加载失败，请手动加载", "warning")

    def _load_user_file(self):
        """手动弹窗选择CSV用户文件并加载"""
        path = filedialog.askopenfilename(filetypes=[("CSV文件", "*.csv")])
        if not path:
            return
        if self.graph.load_users_from_csv(path):
            self._print(f"✅ 用户文件加载: {os.path.basename(path)}", "success")
        else:
            self._print("❌ 用户文件加载失败", "error")
            messagebox.showerror("失败", "文件格式错误或编码不支持")

    def _load_rel_file(self):
        """手动弹窗选择TXT好友关系文件并加载"""
        path = filedialog.askopenfilename(filetypes=[("TXT文件", "*.txt")])
        if not path:
            return
        if self.graph.load_relationships_from_txt(path):
            self._print(f"✅ 关系文件加载: {os.path.basename(path)}", "success")
        else:
            self._print("❌ 关系文件加载失败", "error")
            messagebox.showerror("失败", "文件格式错误或编码不支持")

    # ---------------------- 导出文件功能 ----------------------
    def _export_adj_list(self):
        """导出标准邻接表文本文件"""
        if self.graph.user_attrs.size == 0:
            messagebox.showwarning("提示", "当前没有用户数据可导出")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本文件", "*.txt")], title="导出标准邻接表")
        if not path:
            return
        if self.graph.export_adjacency_list(path):
            self._print(f"✅ 标准邻接表已导出: {os.path.basename(path)}", "success")
            messagebox.showinfo("成功", f"标准邻接表导出成功！\n{path}")
        else:
            self._print("❌ 标准邻接表导出失败", "error")
            messagebox.showerror("失败", "导出失败，请检查路径权限")

    def _export_adj_table(self):
        """导出纯文本表格格式邻接关系"""
        if self.graph.user_attrs.size == 0:
            messagebox.showwarning("提示", "当前没有用户数据可导出")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本文件", "*.txt")], title="导出纯文本表格")
        if not path:
            return
        if self.graph.export_adjacency_table_text(path):
            self._print(f"✅ 纯文本表格已导出: {os.path.basename(path)}", "success")
            messagebox.showinfo("成功", f"纯文本表格导出成功！\n{path}")
        else:
            self._print("❌ 纯文本表格导出失败", "error")
            messagebox.showerror("失败", "导出失败，请检查路径权限")

    # ---------------------- 核心查询功能绑定方法 ----------------------
    def _confirm_user(self):
        """确认选中当前操作用户，刷新界面展示用户基础信息"""
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        info = self.graph.get_user_info(uid)
        inter = "、".join(info["interests"]) if info["interests"] else "无"
        self.user_info.config(text=f"{uid} {info['name']} | 兴趣: {inter}", foreground="#222")
        self.start_label.config(text=f"{uid} {info['name']}", foreground="#222")
        self.current_uid = uid
        self._print(f"已切换查询目标: {self._name(uid)}", "info")

    def _get_sort_key(self):
        """转换下拉框排序文本为底层算法识别标识"""
        mapping = {"按ID升序": "id", "按亲密度降序": "weight", "按共同兴趣降序": "interest"}
        return mapping.get(self.sort_var.get(), "id")

    def _query_1(self):
        """查询一度人脉（用户直接好友）"""
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        friends = self.graph.get_direct_friends_with_weight(uid)
        sort_key = self._get_sort_key()
        my_interests = set(self.graph.get_user_info(uid)["interests"])
        # 根据选中规则排序好友列表
        if sort_key == "id":
            friends.sort(key=lambda x: x[0])
        elif sort_key == "interest":
            def common(item):
                fid, _ = item
                return len(my_interests & set(self.graph.get_user_info(fid)["interests"]))
            friends.sort(key=lambda x: (-common(x), x[0]))
        # 组装表格展示数据
        self._print(f"═══ {self._name(uid)} 一度人脉（共{len(friends)}人）═══", "title")
        rows = []
        for fid, w in friends:
            info = self.graph.get_user_info(fid)
            common_cnt = len(my_interests & set(info["interests"]))
            col3 = f"共同兴趣: {common_cnt}个" if sort_key == "interest" else f"亲密度: {w}"
            rows.append((fid, info["name"], col3, "、".join(info["interests"])))
        self._update_table(["用户ID", "姓名", "匹配维度", "兴趣标签"], rows)

    def _query_2(self):
        """基于BFS算法查询二度人脉（好友的好友）"""
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        res = self.graph.find_second_degree_with_path(uid, sort_strategy=self._get_sort_key())
        self._print(f"═══ {self._name(uid)} 二度人脉（共{len(res)}人）═══", "title")
        rows = []
        for sec_uid, mid_uid, path in res:
            info = self.graph.get_user_info(sec_uid)
            path_str = " → ".join([self._name(p) for p in path])
            rows.append((sec_uid, info["name"], f"中间人: {self._name(mid_uid)}", path_str))
        self._update_table(["用户ID", "姓名", "中间人", "连通路径"], rows)

    def _query_n(self):
        """自定义N度人脉查询（扩展功能A）"""
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        try:
            n = int(self.degree_var.get())
            if n < 1:
                raise ValueError
        except:
            messagebox.showerror("错误", "度数必须为正整数")
            return
        uids = self.graph.find_n_degree_friends(uid, n)
        rows = [(fid, self.graph.get_user_info(fid)["name"], f"{n}度人脉", "、".join(self.graph.get_user_info(fid)["interests"])) for fid in uids]
        self._print(f"═══ {self._name(uid)} {n}度人脉（共{len(uids)}人）═══", "title")
        self._update_table(["用户ID", "姓名", "人脉度数", "兴趣标签"], rows)

    def _calc_dist(self):
        """计算两用户最短社交距离，切换BFS无权 / Dijkstra加权两种模式"""
        s_ok, start = self._valid_uid(self.uid_var.get())
        e_ok, end = self._valid_uid(self.end_uid_var.get())
        if not (s_ok and e_ok):
            return
        # 判断是否启用加权模式
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

    def _recommend(self):
        """基于用户兴趣标签智能好友推荐（扩展功能C）"""
        ok, uid = self._valid_uid(self.uid_var.get())
        if not ok:
            return
        try:
            topk = int(self.top_k_var.get())
            if topk <= 0:
                raise ValueError
        except:
            messagebox.showerror("错误", "推荐数量必须为正整数")
            return
        rec_list = self.graph.recommend_friends_by_interest(uid, topk)
        self._print(f"═══ {self._name(uid)} 兴趣推荐 Top{topk} ═══", "title")
        rows = [(rid, rname, f"共同兴趣: {cnt}个", "、".join(inters)) for rid, rname, cnt, inters in rec_list]
        self._update_table(["用户ID", "姓名", "匹配度", "共同兴趣"], rows)

    # ---------------------- 用户/好友管理 ----------------------
    def _add_user(self):
        """手动新增用户并录入兴趣标签到图结构"""
        try:
            uid = int(self.new_uid_var.get().strip())
            name = self.new_name_var.get().strip()
            if uid <= 0 or not name:
                raise ValueError
        except:
            messagebox.showerror("错误", "ID为正整数且姓名不能为空")
            return
        raw = self.new_inter_var.get().strip()
        # 校验禁止使用英文/中文逗号分号，统一中文顿号
        wrong_seps = ["：", "；", ":", ";", "，", ","]
        for sep in wrong_seps:
            if sep in raw:
                messagebox.showerror("格式错误", "兴趣请使用中文顿号“、”分隔，例如：编程、篮球、摄影")
                return
        inters = [i.strip() for i in raw.split("、") if i.strip()]
        if not inters:
            messagebox.showerror("格式错误", "请至少输入一个兴趣标签，用“、”分隔")
            return
        if self.graph.add_user(uid, name, inters):
            self._print(f"✅ 新增用户: {self._name(uid)}", "success")
            # 清空输入框
            self.new_uid_var.set("")
            self.new_name_var.set("")
            self.new_inter_var.set("")
        else:
            self._print(f"⚠️ 用户 {uid} 已存在", "warning")
            messagebox.showwarning("提示", "该用户ID已存在")

    def _add_friend(self):
        """建立双向无向好友关系，设置亲密度权重"""
        s_ok, u1 = self._valid_uid(self.uid_var.get())
        t_ok, u2 = self._valid_uid(self.target_uid_var.get())
        if not (s_ok and t_ok):
            return
        try:
            w = int(self.weight_var.get())
            if w <= 0:
                raise ValueError
        except:
            messagebox.showerror("错误", "权重必须为正整数")
            return
        self.graph.add_friendship(u1, u2, w)
        self._print(f"✅ 建立好友: {self._name(u1)} ↔ {self._name(u2)} (权重:{w})", "success")
        self.target_uid_var.set("")

    def _del_friend(self):
        """解除双向好友关系"""
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
        """彻底删除指定用户，同步清除所有关联好友边"""
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

    # ---------------------- 黑名单功能 ----------------------
    def _add_black(self):
        """将用户加入黑名单，查询、可视化时自动过滤"""
        ok, uid = self._valid_uid(self.black_uid_var.get())
        if not ok:
            return
        if self.graph.add_to_blacklist(uid):
            self._print(f"✅ 已拉黑: {self._name(uid)}", "success")
            self.black_uid_var.set("")

    def _remove_black(self):
        """将用户移出黑名单，恢复展示"""
        ok, uid = self._valid_uid(self.black_uid_var.get())
        if not ok:
            return
        if self.graph.remove_from_blacklist(uid):
            self._print(f"✅ 已移出黑名单: {self._name(uid)}", "success")
        else:
            self._print("⚠️ 该用户不在黑名单中", "warning")
        self.black_uid_var.set("")

    def _show_black(self):
        """查看全部黑名单用户列表"""
        bl = sorted(self.graph.blacklist)
        self._print(f"═══ 黑名单列表（共{len(bl)}人）═══", "title")
        rows = [(uid, self.graph.get_user_info(uid)["name"], "", "") for uid in bl]
        self._update_table(["用户ID", "姓名", "", ""], rows)

    def _clear_black(self):
        """一键清空全部黑名单数据"""
        if not messagebox.askyesno("确认", "确定清空全部黑名单？"):
            return
        self.graph.clear_blacklist()
        self._print("✅ 黑名单已清空", "success")

    # ---------------------- 图统计分析功能 ----------------------
    def _show_communities(self):
        """连通社群划分，输出所有独立社交社群"""
        comms = self.graph.find_all_communities()
        self._print("========================================", "title")
        self._print(f"            全网社群划分 共{len(comms)}个", "title")
        self._print("========================================", "title")
        for i, group in enumerate(comms, 1):
            names = [self._name(u) for u in group]
            chunks = [names[i:i + 5] for i in range(0, len(names), 5)]
            self._print(f"【社群{i}】总人数：{len(group)}人", "info")
            for chunk in chunks:
                self._print("    " + "、".join(chunk), "detail")

    def _show_centrality(self):
        """度中心性排行，按好友数量从高到低排序展示"""
        rank = self.graph.calc_degree_centrality()
        self._print("═══ 用户度中心性排行 ═══", "title")
        rows = [(i, uid, name, f"好友数: {cnt}") for i, (uid, cnt, name) in enumerate(rank, 1)]
        self._update_table(["排名", "用户ID", "姓名", "好友数量"], rows)

    # ---------------------- 交互式网络图可视化（扩展E） ----------------------
    def _generate_graph(self):
        """调用PyVis生成HTML交互式社交网络图，支持缩放拖拽"""
        if self.graph.user_attrs.size == 0:
            messagebox.showwarning("提示", "请先加载数据")
            return
        try:
            from pyvis.network import Network
        except ImportError:
            self._print("❌ 请安装 pyvis: pip install pyvis", "error")
            messagebox.showerror("错误", "请安装 pyvis 库：pip install pyvis")
            return
        try:
            net = Network(notebook=False, width="100%", height="750px", directed=False)
            net.set_options("""{"nodes":{"font":{"size":14},"shape":"dot"},"edges":{"smooth":{"type":"continuous"}},"physics":{"barnesHut":{"gravitationalConstant":-8000,"springLength":200}},"interaction":{"hover":true,"zoomView":true,"dragView":true}}""")
            layer_map = {}
            if self.current_uid:
                layer_map = self.graph.get_user_degree_layer(self.current_uid)
            color_map = {0: "#ff4444", 1: "#4285f4", 2: "#34a853", 3: "#90a4ae"}
            visible = set()
            if self.only_subgraph.get() and self.current_uid:
                visible.add(self.current_uid)
                for u, d in layer_map.items():
                    if d <= 2:
                        visible.add(u)
            # 循环绘制所有用户节点
            for uid, attr in self.graph.user_attrs.items():
                # 黑名单过滤逻辑
                if self.hide_black.get() and uid in self.graph.blacklist:
                    continue
                # 子网络筛选
                if self.only_subgraph.get() and visible and uid not in visible:
                    continue
                friend_set = self.graph.graph.get(uid)
                cnt = len(friend_set) if friend_set else 0
                size = 20 + min(cnt * 3, 25)
                color = color_map.get(layer_map.get(uid, 3), "#90a4ae")
                title = f"ID:{uid}\n姓名:{attr['name']}\n好友数:{cnt}\n兴趣:{'、'.join(attr['interests'])}"
                net.add_node(uid, label=f"{uid}-{attr['name']}", size=size, color=color, title=title)
            added = set()
            # 循环绘制好友边
            for (u1, u2), w in self.graph.edge_weights.items():
                if self.hide_black.get() and (u1 in self.graph.blacklist or u2 in self.graph.blacklist):
                    continue
                if self.only_subgraph.get() and visible and (u1 not in visible or u2 not in visible):
                    continue
                if (u2, u1) not in added:
                    net.add_edge(u1, u2, width=w * 0.8, title=f"亲密度:{w}", color="#90a4ae")
                    added.add((u1, u2))
            # 保存HTML并自动打开
            save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "social_network_graph.html")
            net.write_html(save_path)
            webbrowser.open(os.path.abspath(save_path))
            self._print("✅ 网络图已生成并打开", "success")
        except Exception as e:
            self._print(f"❌ 生成失败: {str(e)}", "error")
            messagebox.showerror("失败", str(e))

# 程序入口启动函数
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = SocialNetworkGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("启动失败", str(e))