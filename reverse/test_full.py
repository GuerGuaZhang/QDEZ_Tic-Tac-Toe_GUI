# -*- coding: utf-8 -*-
"""完整功能版本《二中棋》引擎 + GUI 冒烟测试。"""
import importlib.util, random, io, contextlib, tkinter as tk

path = r"c:\Users\13335\Saved Games\二中棋\二中棋_GUI.py"
spec = importlib.util.spec_from_file_location("game_gui2", path)
mod = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mod)

EMPTY, P1, P2 = mod.EMPTY, mod.P1, mod.P2
fail = 0
def ok(cond, msg):
    global fail
    if cond: print("  PASS:", msg)
    else:    print("  FAIL:", msg); fail += 1

def b(*cells):
    board = [[EMPTY]*mod.BOARD_N for _ in range(mod.BOARD_N)]
    for (r, c, v) in cells:
        board[r][c] = v
    return board

print("== check_winner (3x3) ==")
ok(mod.check_winner(b((0,0,P1),(0,1,P1),(0,2,P1))) == P1, "行三连P1")
ok(mod.check_winner(b((0,0,P2),(1,0,P2),(2,0,P2))) == P2, "列三连P2")
ok(mod.check_winner(b((0,0,P1),(1,1,P1),(2,2,P1))) == P1, "主对角")
ok(mod.check_winner(b((0,2,P2),(1,1,P2),(2,0,P2))) == P2, "副对角")
ok(mod.check_winner(b()) == EMPTY, "空盘")
ok(mod.board_full(b((0,0,P1),(0,1,P1),(0,2,P1),(1,0,P2),(1,1,P1),(1,2,P2),
                    (2,0,P2),(2,1,P1),(2,2,P2))) == True, "满盘")

print("== apply_event 随机事件 ==")
kinds = {}
for _ in range(2000):
    board = b()
    board[0][0] = P1
    msg, helped = mod.apply_event(board, P1)
    # 事件后棋盘仍合法（值∈{0,1,-1}），且不越界
    ok2 = all(board[r][c] in (0,1,-1) for r in range(3) for c in range(3))
    if not ok2:
        print("  事件后非法棋盘:", board); fail += 1; break
    kinds.setdefault(msg[:4], 0)
    kinds[msg[:4]] += 1
print("  事件分布示例:", {k: v for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:8]})
ok(len(kinds) >= 6, f"随机事件种类丰富（观测到 {len(kinds)} 类）")

print("== ai_move ==")
board = b((0,0,P2),(0,1,P2))
ok(mod.ai_move(board, P2, P1) == (0,2), "AI 自己可赢时秒杀")
board = b((0,0,P1),(0,1,P1))
ok(mod.ai_move(board, P2, P1) == (0,2), "AI 挡玩家三连")

print("== 引擎整局模拟（含事件+AI，200 局）==")
from collections import Counter
res = Counter()
for _ in range(200):
    board = b()
    turn = P1
    while True:
        w = mod.check_winner(board)
        if w:
            res[w if w in (1,-1) else 0] += 1; break
        if mod.board_full(board):
            res[0] += 1; break
        if turn == P1:
            cells = mod.empties(board)
            r, c = random.choice(cells); board[r][c] = P1
        else:
            r, c = mod.ai_move(board, P2, P1); board[r][c] = P2
        mod.apply_event(board, turn)     # 每手触发随机事件
        turn = -turn
print("  玩家胜/电脑胜/平局 =", dict(res), " 总对局 =", sum(res.values()))
ok(sum(res.values()) == 200, "200 局全部正常结束")

print("== GUI 冒烟 ==")
try:
    root = tk.Tk(); root.withdraw()
    app = mod.GameApp(root); root.update()
    ok(app.page == "menu", "初始在主菜单")
    app.start_game(mod.MODE_B); root.update()
    ok(app.page == "game" and app.game.turn == P1, "单人·人机后走：玩家先手")
    app.on_place(0, 0); root.update()
    ok(app.game.board[0][0] == P1, "玩家落子生效")
    ok(app.game.mystery == 1, "落子后触发神秘事件计数+1")
    ok("事件" in app.game.last_event, "事件消息已显示")
    # 键盘冒烟
    from types import SimpleNamespace
    app.game_key(SimpleNamespace(keysym="d", char="d")); root.update()
    ok(app._focus_rc != (1,1), "键盘移动光标生效")
    app.show("menu"); root.destroy()
except Exception as e:
    import traceback; traceback.print_exc()
    ok(False, "GUI 冒烟: " + repr(e))

print("\n结果:", "全部通过 ✔" if fail == 0 else f"{fail} 项失败 ✘")