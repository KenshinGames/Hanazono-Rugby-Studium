"""config/dimensions.json を読む。Blender の外の Python からも使える。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "config", "dimensions.json")

_cache = None


def load():
    global _cache
    if _cache is None:
        with open(PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def field_lines():
    """ラインの位置をまとめて返す(試合を足すスクリプト向け)。"""
    f = load()["field"]
    hl = f["length"] / 2
    hw = f["width"] / 2
    return {
        "touch_y": hw,
        "goal_x": hl,
        "dead_ball_x": hl + f["in_goal_depth"],
        "line_22_x": hl - f["line_22m_from_goal"],
        "line_10_x": f["line_10m_from_halfway"],
        "line_5_y": hw - f["line_5m_from_touch"],
        "line_15_y": hw - f["line_15m_from_touch"],
    }
