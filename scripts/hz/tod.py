"""時刻ごとの光(昼下がり → 夕方 → 夕焼け → 日暮れ → 夜)。sky.py の昼と夜の間を作る。リールで使う。

  tod.setup(scene, "golden")       # 空・雲・霞・窓や外観の明かりをその時刻にする
  tod.set_floodlights(on)          # 照明塔と屋根の投光器だけを点ける・消す(日暮れのカットで使う)

数字はすべて試し描きを見て決めた見た目の値(実際の照度ではない)。
"""
import bpy

from . import sky

FLOOD_PREFIX = ("tower_light_", "roof_light_")

# az, el: 太陽の方位と高度(度)。bg, exposure: 空の強さと露出。
# clouds: 雲の色(太陽の側 near と反対側 far)。haze: 霞の色と濃さ、山だけの濃さ。
# lights: 窓・外観のライトアップ・街灯の点き具合(0=昼、1=夜)。floods: 投光器。
TIMES = {
    "late": dict(az=236.0, el=20.0, bg=0.11, exposure=0.1,
                 clouds=dict(near=(1.0, 0.90, 0.78), far=(0.95, 0.95, 0.98), strength=1.5, power=3.0),
                 haze=(0.52, 0.55, 0.62), haze_max=0.90, mountain_haze=0.35, lights=0.0, floods=False),
    "golden": dict(az=236.0, el=5.0, bg=0.12, exposure=0.2,
                   clouds=dict(near=(1.0, 0.70, 0.42), far=(0.85, 0.74, 0.76), strength=1.3, power=3.0),
                   haze=(0.46, 0.42, 0.46), haze_max=0.88, mountain_haze=0.22, lights=0.0, floods=False),
    "sunset": dict(az=243.0, el=0.6, bg=0.16, exposure=0.5,
                   clouds=dict(near=(1.0, 0.45, 0.22), far=(0.42, 0.34, 0.46), strength=0.9, power=2.0),
                   haze=(0.24, 0.17, 0.17), haze_max=0.86, mountain_haze=0.55, lights=0.35, floods=False),
    "blue": dict(az=245.0, el=-3.5, bg=0.55, exposure=0.6,
                 clouds=dict(near=(0.55, 0.22, 0.20), far=(0.07, 0.08, 0.14), strength=0.35, power=2.0),
                 haze=(0.030, 0.036, 0.075), haze_max=0.86, mountain_haze=0.70, lights=0.85, floods=False),
    "night": None,   # sky.setup_night のまま(投光器も点く)
}


def setup(scene, name, **over):
    """over で一部の値(太陽の高さ el など)を変えられる。"""
    t = TIMES[name]
    if t is not None and over:
        t = dict(t, **over)
    if t is None:
        sky.setup_night(scene)
        _ext_lights(1.0)
        set_floodlights(True)
        return
    sky.setup_day(scene, az=t["az"], el=t["el"], bg_strength=t["bg"], exposure=t["exposure"], clouds=t["clouds"])
    _set_dn(t["lights"])
    _emissive(t["lights"])
    _ext_lights(t["lights"])
    _haze(t["haze"], t["haze_max"], t["mountain_haze"])
    set_floodlights(t["floods"])
    if t["lights"] > 0:
        sky._glare(scene, True)


def _set_dn(frac):
    """"dn 昼 夜" の Value ノード(窓・虹色の帯・タイルなど)を昼と夜の間にする。霞は _haze が決める。"""
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == "VALUE" and n.label.startswith("dn "):
                parts = n.label.split()
                if len(parts) > 3 and parts[3].startswith("haze"):
                    continue
                a, b = float(parts[1]), float(parts[2])
                n.outputs[0].default_value = a + (b - a) * frac


def _emissive(frac):
    for m in bpy.data.materials:
        if "emit_day" in m and m.use_nodes and m.name != "lamp_lens":
            b = m.node_tree.nodes.get("Principled BSDF")
            if b:
                b.inputs["Emission Strength"].default_value = m["emit_day"] + (m["emit_night"] - m["emit_day"]) * frac


def _lights():
    c = bpy.data.collections.get("night_lights")
    return (c, list(c.objects)) if c else (None, [])


def _ext_lights(frac):
    """投光器以外の夜の光(外観を照らす光、街灯)。強さを frac 倍にする。"""
    c, obs = _lights()
    if c is None:
        return
    c.hide_render = False
    for ob in obs:
        if ob.type != "LIGHT" or ob.name.startswith(FLOOD_PREFIX):
            continue
        if "e0" not in ob:
            ob["e0"] = ob.data.energy
        ob.data.energy = ob["e0"] * frac
        ob.hide_render = frac <= 0.0


def set_floodlights(on):
    c, obs = _lights()
    if c is not None:
        c.hide_render = False
    for ob in obs:
        if ob.name.startswith(FLOOD_PREFIX):
            ob.hide_render = not on
    m = bpy.data.materials.get("lamp_lens")
    if m:
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Strength"].default_value = m["emit_night"] if on else 0.0


def _haze(color, vmax, mountain_max):
    """霞の色と濃さを決める(materials.add_haze が作ったノードを書き換える)。"""
    for m in bpy.data.materials:
        if not m.get("hazed"):
            continue
        nt = m.node_tree
        for n in nt.nodes:
            if n.type != "VALUE" or not n.label.startswith("dn "):
                continue
            if n.label.endswith("haze_col"):
                n.outputs[0].default_value = 0.0
                for ln in nt.links:
                    if ln.from_node == n and ln.to_node.type == "MIX":
                        ln.to_node.inputs["A"].default_value = tuple(color) + (1.0,)
            elif n.label.endswith("haze_max"):
                n.outputs[0].default_value = mountain_max if m.name == "mountain" else vmax
