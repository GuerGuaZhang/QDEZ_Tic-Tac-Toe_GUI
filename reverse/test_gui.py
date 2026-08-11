# -*- coding: utf-8 -*-
"""无界面验证《二中棋》引擎：胜利判定、AI、整局流程。"""
import importlib.util, random, sys, io, contextlib

path = r"c:\Users\13335\Saved Games\二中棋\二中棋_GUI.py"
spec = importlib.util.spec_from_file_location("game_gui", path)
mod = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mod)

EMP = mod.EMPTY; P = mod.PLAYER; A = mod.AI

def line_board(*cells_val):
    b = [[EMP]*4 for _ in range(4)]
    for (r, c, v) in cells_val:
        b[r][c] = v
    return b

fail = 0
def ok(cond, msg):
    global fail
    if cond: print("  PASS:", msg)
    else:    print("  FAIL:", msg); fail += 1

print("== 胜利判定 check_win ==")
ok(mod.check_win(line_board((0,0,P),(0,1,P),(0,2,P))) == P, "行三连(玩家)")
ok(mod.check_win(line_board((0,1,P),(1,1,P),(2,1,P))) == P, "列三连")
ok(mod.check_win(line_board((0,0,A),(1,1,A),(2,2,A))) == A, "主对角三连(电脑)")
ok(mod.check_win(line_board((1,2,A),(2,1,A),(3,0,A))) == A, "副对角三连")
ok(mod.check_win([[EMP]*4 for _ in range(4)]) == EMP, "空盘无胜")
ok(mod.check_win(line_board((0,0,P),(0,1,P),(0,2,P),(0,3,P))) == P, "整行四连亦判胜")

print("== AI 行为 ==")
b = line_board((0,0,A),(0,1,A)); 
ok(mod.ai_move(b) == (0,2), "AI 优先自己连三取胜")
b = line_board((0,0,P),(0,1,P));
# AI 应堵 (0,2) 或 (0,3)？三连判定只查 (0,0)(0,1)(0,2)，堵 (0,2)
ok(mod.ai_move(b) == (0,2), "AI 堵玩家三连")
b = [[EMP]*4 for _ in range(4)]
mv = mod.ai_move(b)
ok(mv in mod.empties(b), "空盘 AI 走合法空位")

print("== 整局模拟（玩家随机 vs AI，跑 400 局）==")
from collections import Counter
res = Counter()
for _ in range(400):
    board = [[EMP]*4 for _ in range(4)]
    turn = P
    while True:
        w = mod.check_win(board)
        if w: res[w] += 1; break
        if mod.board_full(board): res[0] += 1; break
        if turn == P:
            r, c = random.choice(mod.empties(board)); board[r][c] = P
        else:
            r, c = mod.ai_move(board); board[r][c] = A
        turn = -turn
print("  玩家胜/电脑胜/平局 =", dict(res), "   总对局 =", sum(res.values()))
ok(sum(res.values()) == 400, "400 局全部正常结束（无死循环）")

print("\n结果:", "全部通过 ✔" if fail == 0 else f"{fail} 项失败 ✘")
