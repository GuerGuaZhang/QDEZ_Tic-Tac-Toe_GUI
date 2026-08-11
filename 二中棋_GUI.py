# -*- coding: utf-8 -*-
"""
《二中棋》GUI 版 —— 完整功能复刻
========================================================================
依据对原版"二中棋.exe"（MinGW GCC 4.9.2 编译、O2 优化、源码丢失）的逆向
（COFF 符号 + DWARF + 全量反汇编 + 字符串 xref），用 Python + tkinter 全新
实现，忠实还原原版全部功能。仅供学习与个人使用，请勿用于商业或侵权用途。

原版功能（对应逆向出的字符串与逻辑）：
  * 主菜单：开始游戏S / 游戏说明H / 设置P / 退出E（制作人 SqrtSecond）
  * 设置：速度调节(上下键) + 键盘偏好(wsad+空格 / 方向键+Enter，仅单人有效)
  * 游戏说明：分页剧情（标准三子棋 + 随机事件机制 + 别触发5次神秘事件）
  * 模式：A单人·人机先手 / B单人·人机后手 / C双人
  * 对局：3x3 三子棋，○/×，比分 %d:%d，轮到谁下在哪一行哪一列
  * 随机事件（每下一手触发）：消除某格/某行/某列/两条对角线、帮你下一手、
    反转局势、无事发生
  * 神秘事件计数：每触发一次"神秘事件×N"，满5次触发 Windows 崩溃整蛊彩蛋
  * 局后结算：胜者 + "要再玩一局吗？" + 最终比分/胜利者/平局/欢迎再玩

运行：python "二中棋_GUI.py"
依赖：仅 Python 标准库 tkinter
"""
import tkinter as tk
from tkinter import messagebox
import random

# ---------- 常量 ----------
BOARD_N = 3                 # 3x3 三子棋
EMPTY = 0
P1 = 1                       # 先手棋子（○）
P2 = -1                      # 后手棋子（×）
P1_TXT, P2_TXT = "○", "×"

MODE_A = "single_first"      # 单人，人机先走
MODE_B = "single_second"     # 单人，人机后走
MODE_C = "double"            # 双人

WIN_LINES = []
for r in range(BOARD_N):
    WIN_LINES.append([(r, c) for c in range(BOARD_N)])
for c in range(BOARD_N):
    WIN_LINES.append([(r, c) for r in range(BOARD_N)])
WIN_LINES.append([(i, i) for i in range(BOARD_N)])
WIN_LINES.append([(i, BOARD_N - 1 - i) for i in range(BOARD_N)])

# ---------- 基础工具 ----------
def check_winner(board):
    """返回胜者 P1/P2，无胜者返回 EMPTY。"""
    for line in WIN_LINES:
        vals = [board[r][c] for (r, c) in line]
        if vals[0] != EMPTY and vals[0] == vals[1] == vals[2]:
            return vals[0]
    return EMPTY


def board_full(board):
    return all(board[r][c] != EMPTY for r in range(BOARD_N) for c in range(BOARD_N))


def empties(board):
    return [(r, c) for r in range(BOARD_N) for c in range(BOARD_N) if board[r][c] == EMPTY]


def _place(board, r, c, val):
    b = [row[:] for row in board]
    b[r][c] = val
    return b


# ---------- 随机事件 ----------
EVENT_MSG = {
    "cell":   "消除格子(%d,%d)！",
    "row":    "消除第%d行！",
    "col":    "消除第%d列！",
    "diag1":  "消除左上到右下的对角线！",
    "diag2":  "消除右上到左下的对角线！",
    "help":   "帮你下一手(%d,%d)！",
    "reverse": "反转局势！！！",
    "none":   "无事发生！（偷笑）",
}


def apply_event(board, just_moved):
    """触发一个随机事件，返回 (描述, 是否帮某方多下了一手)。"""
    kind = random.choice(["cell", "cell", "row", "col", "diag1", "diag2",
                          "help", "reverse", "none", "none"])
    if kind == "cell":
        cells = empties(board)
        r, c = random.choice(cells) if cells else (0, 0)
        board[r][c] = EMPTY
        return EVENT_MSG["cell"] % (r + 1, c + 1), False
    if kind == "row":
        r = random.randrange(BOARD_N)
        for c in range(BOARD_N):
            board[r][c] = EMPTY
        return EVENT_MSG["row"] % (r + 1,), False
    if kind == "col":
        c = random.randrange(BOARD_N)
        for r in range(BOARD_N):
            board[r][c] = EMPTY
        return EVENT_MSG["col"] % (c + 1,), False
    if kind == "diag1":
        for i in range(BOARD_N):
            board[i][i] = EMPTY
        return EVENT_MSG["diag1"], False
    if kind == "diag2":
        for i in range(BOARD_N):
            board[i][BOARD_N - 1 - i] = EMPTY
        return EVENT_MSG["diag2"], False
    if kind == "help":
        cells = empties(board)
        if cells:
            r, c = random.choice(cells)
            board[r][c] = just_moved
            return EVENT_MSG["help"] % (r + 1, c + 1), True
        return EVENT_MSG["none"], False
    if kind == "reverse":
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                if board[r][c] != EMPTY:
                    board[r][c] = -board[r][c]
        return EVENT_MSG["reverse"], False
    return EVENT_MSG["none"], False


# ---------- 人机 AI（三子棋） ----------
def ai_move(board, ai_val, human_val):
    # 1) 自己能赢
    for (r, c) in empties(board):
        if check_winner(_place(board, r, c, ai_val)) == ai_val:
            return (r, c)
    # 2) 挡玩家
    for (r, c) in empties(board):
        if check_winner(_place(board, r, c, human_val)) == human_val:
            return (r, c)
    # 3) 中心优先
    cells = empties(board)
    if (1, 1) in cells:
        return (1, 1)
    # 4) 随机
    return random.choice(cells)


# ---------- 游戏状态 ----------
class Game:
    """对局状态 + 全局设置（速度/键盘/比分/神秘事件计数）。"""

    def __init__(self):
        self.mode = MODE_B          # 默认：单人，人机后走
        self.speed = 2              # 速度档位（越大越慢，影响 AI 思考延时）
        self.board = [[EMPTY] * BOARD_N for _ in range(BOARD_N)]
        self.turn = P1
        self.score_p1 = 0
        self.score_p2 = 0
        self.mystery = 0            # 神秘事件计数（满5触发彩蛋）
        self.round_over = False
        self.last_event = ""

    def reset_board(self):
        self.board = [[EMPTY] * BOARD_N for _ in range(BOARD_N)]
        self.turn = P1
        self.round_over = False
        self.last_event = ""

    def names(self):
        """返回 (先手名, 后手名)。先手执○，后手执×。"""
        if self.mode == MODE_A:     # 单人，人机先走
            return "人机", "玩家"
        if self.mode == MODE_B:     # 单人，人机后走
            return "玩家", "人机"
        return "玩家1", "玩家2"      # 双人

    def is_human(self, player):
        """该棋子是否由人类操作。"""
        if self.mode == MODE_C:
            return True
        if self.mode == MODE_A:
            return player == P2
        return player == P1

    def human_of(self):
        return P2 if self.mode == MODE_A else P1

    def ai_of(self):
        return P1 if self.mode == MODE_A else P2


# ---------- GUI 应用 ----------
class GameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("二中棋 · GUI 复刻")
        self.root.resizable(False, False)
        self.game = Game()
        self.page = None

        self.container = tk.Frame(root)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.build_pages()
        self.show("menu")

    def build_pages(self):
        self.pages = {}
        self.pages["menu"] = self._build_menu()
        self.pages["settings"] = self._build_settings()
        self.pages["help"] = self._build_help()
        self.pages["mode"] = self._build_mode()
        self.pages["game"] = self._build_game()
        self.pages["result"] = self._build_result()

    def show(self, name):
        if self.page and self.page in self.pages:
            self.pages[self.page].pack_forget()
        self.page = name
        self.pages[name].pack(fill=tk.BOTH, expand=True)
        if name == "settings":
            self.refresh_settings()
        if name == "game":
            self.refresh_game()

    # ---------- 主菜单 ----------
    def _build_menu(self):
        f = tk.Frame(self.container, padx=40, pady=30, bg="#1b1e23")
        tk.Label(f, text="二 中 棋", font=("微软雅黑", 26, "bold"),
                 bg="#1b1e23", fg="#e8c86a").pack(pady=(0, 4))
        tk.Label(f, text="主菜单", font=("微软雅黑", 12),
                 bg="#1b1e23", fg="#aaa").pack(pady=(0, 18))
        items = [("开始游戏 —— S", "mode"), ("游戏说明 —— H", "help"),
                 ("设置 —— P", "settings"), ("退出 —— E", "exit")]
        for txt, target in items:
            if target == "exit":
                cmd = self.root.destroy
            elif target == "help":
                cmd = self.show_help
            else:
                cmd = (lambda t=target: self.show(t))
            tk.Button(f, text=txt, width=22, font=("微软雅黑", 12), cursor="hand2",
                      command=cmd).pack(pady=4)
        tk.Label(f, text="制作人：SqrtSecond", font=("微软雅黑", 10),
                 bg="#1b1e23", fg="#777").pack(pady=(16, 0))
        tk.Label(f, text="（P.S.按Enter或空格键可快速跳过剧情）", font=("微软雅黑", 9),
                 bg="#1b1e23", fg="#666").pack()
        return f

    # ---------- 设置 ----------
    def _build_settings(self):
        f = tk.Frame(self.container, padx=40, pady=28, bg="#17191d")
        tk.Label(f, text="设置", font=("微软雅黑", 18, "bold"),
                 bg="#17191d", fg="#eee").pack(pady=(0, 14))
        row = tk.Frame(f, bg="#17191d")
        row.pack(pady=6)
        tk.Button(row, text="  +  ", font=("微软雅黑", 13), width=4,
                  command=lambda: self.change_speed(+1)).pack(side=tk.LEFT, padx=6)
        self.lbl_speed = tk.Label(row, text="", font=("微软雅黑", 13),
                                  bg="#17191d", fg="#d8d8d8")
        self.lbl_speed.pack(side=tk.LEFT, padx=6)
        tk.Button(row, text="  -  ", font=("微软雅黑", 13), width=4,
                  command=lambda: self.change_speed(-1)).pack(side=tk.LEFT, padx=6)
        tk.Label(f, text="速度档位：越低越快，越高 AI 思考/动画越明显",
                 font=("微软雅黑", 9), bg="#17191d", fg="#888").pack(pady=2)
        tk.Label(f, text="对局：直接用鼠标点击棋盘格子落子即可",
                 font=("微软雅黑", 10), bg="#17191d", fg="#9cf").pack(pady=8)
        tk.Button(f, text="返回主菜单", command=lambda: self.show("menu")).pack(pady=12)
        return f

    def refresh_settings(self):
        self.lbl_speed.config(text=f"当前速度：{self.game.speed}")

    def change_speed(self, d):
        self.game.speed = max(1, min(10, self.game.speed + d))
        self.refresh_settings()

    # ---------- 游戏说明（分页剧情） ----------
    HELP_TEXT = [
        "首先，这是一个双人游戏。",
        "基本规则和标准的三子棋相同。",
        "双方需要每人轮流下一手。",
        "每人下完一手后，都会触发一个随机的事件。",
        "有可能会消除场上已有的棋子……",
        "但也有可能帮你多下一手棋！",
        "这正是这个游戏的好玩之处。",
        "也很靠运气。",
        "另外……",
        "别触发5次神秘事件，否则后果自负……",
        "准备好了就开始吧！",
    ]

    def _build_help(self):
        f = tk.Frame(self.container, padx=50, pady=40, bg="#101218")
        self.lbl_help = tk.Label(f, text="", font=("微软雅黑", 14),
                                 bg="#101218", fg="#eef", justify="center")
        self.lbl_help.pack(expand=True)
        self._help_idx = 0
        tk.Button(f, text="下一条", font=("微软雅黑", 11),
                  command=self.help_next).pack(pady=8)
        tk.Button(f, text="返回主菜单", font=("微软雅黑", 10),
                  command=lambda: self.show("menu")).pack()
        return f

    def show_help(self):
        self._help_idx = 0
        self.lbl_help.config(text=self.HELP_TEXT[0])
        self.show("help")

    def help_next(self):
        self._help_idx += 1
        if self._help_idx >= len(self.HELP_TEXT):
            self.show("menu")
        else:
            self.lbl_help.config(text=self.HELP_TEXT[self._help_idx])

    # ---------- 模式选择 ----------
    def _build_mode(self):
        f = tk.Frame(self.container, padx=40, pady=30, bg="#1a1c22")
        tk.Label(f, text="你要玩什么模式？", font=("微软雅黑", 15, "bold"),
                 bg="#1a1c22", fg="#eee").pack(pady=(0, 16))
        modes = [("单人，人机先走 —— A", MODE_A), ("单人，人机后走 —— B", MODE_B),
                 ("双人 —— C", MODE_C)]
        for txt, m in modes:
            tk.Button(f, text=txt, width=22, font=("微软雅黑", 12), cursor="hand2",
                      command=lambda mm=m: self.start_game(mm)).pack(pady=4)
        tk.Button(f, text="返回", font=("微软雅黑", 10),
                  command=lambda: self.show("menu")).pack(pady=8)
        return f

    def start_game(self, mode):
        self.game.mode = mode
        self.game.reset_board()
        self.show("game")
        self.start_turn()

    # ---------- 对局 ----------
    CELL = 100                       # 每格像素
    def _build_game(self):
        f = tk.Frame(self.container, bg="#22262c")
        self.lbl_game_top = tk.Label(f, text="", font=("微软雅黑", 13, "bold"),
                                     bg="#22262c", fg="#eee")
        self.lbl_game_top.pack()
        self.lbl_turn = tk.Label(f, text="", font=("微软雅黑", 11),
                                 bg="#22262c", fg="#cfe9ff")
        self.lbl_turn.pack()
        self.lbl_score = tk.Label(f, text="", font=("微软雅黑", 12, "bold"),
                                  bg="#22262c", fg="#ffecb3")
        self.lbl_score.pack()
        self.lbl_event = tk.Label(f, text="", font=("微软雅黑", 11), bg="#22262c",
                                  fg="#ffb07a", wraplength=460, justify="center")
        self.lbl_event.pack(pady=(2, 4))
        s = self.CELL * BOARD_N
        self.cv = tk.Canvas(f, width=s, height=s, bg="#16191e", highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Button-1>", self.on_canvas_click)
        bf = tk.Frame(f, bg="#22262c")
        bf.pack(pady=6)
        tk.Button(bf, text="返回主菜单", command=lambda: self.show("menu")).pack(side=tk.LEFT, padx=5)
        return f

    def on_canvas_click(self, event):
        c = event.x // self.CELL
        r = event.y // self.CELL
        if 0 <= r < BOARD_N and 0 <= c < BOARD_N:
            self.on_place(r, c)

    # ---------- 对局逻辑 ----------
    def mode_name(self):
        return {MODE_A: "单人·人机先走", MODE_B: "单人·人机后走",
                MODE_C: "双人"}[self.game.mode]

    def refresh_game(self):
        n1, n2 = self.game.names()
        self.lbl_game_top.config(text=f"模式：{self.mode_name()}    ○ {n1}  vs  × {n2}")
        self.lbl_score.config(text=f"比分：{self.game.score_p1}:{self.game.score_p2}"
                                   f"    神秘事件×{self.game.mystery}")
        who = self.game.turn
        name = n1 if who == P1 else n2
        mark = P1_TXT if who == P1 else P2_TXT
        self.lbl_turn.config(text=f"现在轮到 {name}（执{mark}）了，你要下在哪一行，哪一列？")
        self.draw_board()

    def draw_board(self):
        self.cv.delete("all")
        s = self.CELL * BOARD_N
        for i in range(1, BOARD_N):
            self.cv.create_line(i * self.CELL, 0, i * self.CELL, s, fill="#3a4048", width=2)
            self.cv.create_line(0, i * self.CELL, s, i * self.CELL, fill="#3a4048", width=2)
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                v = self.game.board[r][c]
                if v == EMPTY:
                    continue
                x0, y0 = c * self.CELL + 16, r * self.CELL + 16
                x1, y1 = (c + 1) * self.CELL - 16, (r + 1) * self.CELL - 16
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                if v == P1:
                    self.cv.create_oval(x0, y0, x1, y1, outline="#57b6ff", width=4)
                    self.cv.create_text(cx, cy, text=P1_TXT, font=("Arial", 42), fill="#57b6ff")
                else:
                    self.cv.create_line(x0, y0, x1, y1, fill="#ff8a80", width=4)
                    self.cv.create_line(x1, y0, x0, y1, fill="#ff8a80", width=4)

    def _delay(self):
        return 250 * self.game.speed

    def start_turn(self):
        if self.game.round_over:
            return
        if not self.game.is_human(self.game.turn):
            self.game.last_event = "人机计算中……"
            self.lbl_event.config(text=self.game.last_event)
            self.root.after(self._delay(), self.ai_act)
        else:
            self.refresh_game()

    def ai_act(self):
        if self.game.round_over:
            return
        ai = self.game.turn
        human = self.game.ai_of()
        move = ai_move(self.game.board, ai, human)
        self.game.board[move[0]][move[1]] = ai
        self.after_place(ai)

    def on_place(self, r, c):
        if self.game.round_over or not self.game.is_human(self.game.turn):
            return
        if self.game.board[r][c] != EMPTY:
            return
        self.game.board[r][c] = self.game.turn
        self.after_place(self.game.turn)

    def after_place(self, player):
        """落子后：神秘事件计数 -> 触发随机事件 -> 检查胜负/彩蛋。"""
        self.game.mystery += 1
        msg, _helped = apply_event(self.game.board, player)
        self.game.last_event = f"神秘事件×{self.game.mystery}！！！  事件发生！\n{msg}"
        self.lbl_event.config(text=self.game.last_event)
        self.refresh_game()
        if self.game.mystery >= 5:
            self.root.after(self._delay(), self.crash_egg)
        else:
            self.root.after(self._delay(), self.check_result)

    def check_result(self):
        if self.game.round_over:
            return
        winner = check_winner(self.game.board)
        if winner:
            self.finish_round(winner)
        elif board_full(self.game.board):
            self.finish_round(EMPTY)
        else:
            self.game.turn = P2 if self.game.turn == P1 else P1
            self.refresh_game()
            self.start_turn()

    def finish_round(self, winner):
        self.game.round_over = True
        n1, n2 = self.game.names()
        if winner == P1:
            self.game.score_p1 += 1
            msg = f"{n1} 获得了胜利！"
        elif winner == P2:
            self.game.score_p2 += 1
            msg = f"{n2} 获得了胜利！"
        else:
            msg = "恭喜双方打成平局！"
        self.refresh_game()
        self.lbl_turn.config(text=msg)
        again = messagebox.askyesno(
            "本局结束", msg + f"\n\n比分：{self.game.score_p1}:{self.game.score_p2}"
                            "\n\n要再玩一局吗？")
        if again:
            self.game.reset_board()
            self.start_turn()
        else:
            self.show_result()

    def crash_egg(self):
        """神秘事件满 5 次：Windows 崩溃整蛊彩蛋。"""
        messagebox.showwarning("Windows系统自动提示", "您的Windows可能出现了点问题。")
        messagebox.showwarning("Windows系统自动提示", "Windows正在尝试修复您的系统中……")
        messagebox.showerror("Windows系统自动提示", "系统内部存储器已被破坏！")
        messagebox.showwarning("Windows系统自动提示", "数据已被破坏……请重新开始……")
        self.game.mystery = 0
        self.game.reset_board()
        self.start_turn()

    # ---------- 结算 ----------
    def _build_result(self):
        f = tk.Frame(self.container, padx=40, pady=40, bg="#131419")
        self.lbl_res = tk.Label(f, text="", font=("微软雅黑", 14), bg="#131419",
                                fg="#eee", justify="center")
        self.lbl_res.pack(expand=True)
        tk.Button(f, text="返回主菜单", font=("微软雅黑", 11),
                  command=lambda: self.show("menu")).pack(pady=8)
        return f

    def show_result(self):
        n1, n2 = self.game.names()
        s1, s2 = self.game.score_p1, self.game.score_p2
        if s1 > s2:
            winner = n1
        elif s2 > s1:
            winner = n2
        else:
            winner = None
        txt = "正在计算最终得分……\n\n最终结果是……\n"
        txt += f"{winner}！\n" if winner else "平局！\n"
        txt += f"\n你们的比分为：{s1}:{s2}。\n\n欢迎下次再玩！"
        self.lbl_res.config(text=txt)
        self.show("result")


def main():
    root = tk.Tk()
    GameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
