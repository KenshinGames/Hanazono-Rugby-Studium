"""決まった角度のカメラ。名前 → (位置, 見る先, 焦点距離 mm)。センサー幅は 36 mm。"""
import bpy
from mathutils import Vector

VIEWS = {
    # 仕上げの 5 つ
    "broadcast": ((-1.6, 66.5, 17.6), (0.0, -12.0, 0.0), 21),          # 中継風(メインスタンド上段の中央)
    "behind_goal": ((-84.0, 3.0, 7.5), (30.0, 0.0, 6.0), 26),        # 南のゴール裏から
    "from_seat": ((-22.0, -58.5, 10.9), (30.0, 32.0, 7.0), 20),       # バックスタンドの客席から
    "aerial": ((-150.0, -120.0, 150.0), (-5.0, 5.0, 0.0), 35),       # 空から見下ろす
    "exterior": ((-196.0, -52.0, 1.8), (-112.0, -4.0, 13.0), 22),     # 南の正面広場から外観
    # 確認用
    "ref_back": ((-20.0, 38.0, 1.7), (-5.0, -60.0, 6.0), 22),
    "ref_north": ((15.0, 22.0, 3.0), (84.0, -2.0, 11.0), 26),
    "east_close": ((-30.0, -50.0, 9.5), (-10.0, -56.0, 8.0), 24),
    "ref_main": ((-58.0, -22.0, 1.7), (-5.0, 62.0, 13.0), 24),
    "top": ((0.0, 0.0, 330.0), (0.0, 0.01, 0.0), 50),
    "pitch_oblique": ((-95.0, 60.0, 45.0), (0.0, 0.0, 0.0), 32),
    "goal_close": ((-64.0, 9.0, 2.2), (-45.0, -2.0, 3.0), 28),
    "corner_sw": ((-78.0, 50.0, 7.0), (30.0, -5.0, 6.0), 22),
    "corner_ne": ((80.0, -52.0, 9.0), (-20.0, 20.0, 6.0), 20),
    "corner_nw": ((84.0, 60.0, 30.0), (-10.0, -10.0, 4.0), 24),
    "corner_se": ((-100.0, -75.0, 32.0), (0.0, 0.0, 4.0), 24),
    "main_front": ((0.0, -52.0, 10.0), (0.0, 60.0, 14.0), 20),
    "roof_under": ((14.0, 55.5, 10.5), (-30.0, 66.0, 21.0), 18),
    "back_front": ((0.0, 55.0, 12.0), (0.0, -55.0, 6.0), 18),
    "north_front": ((10.0, 0.0, 6.0), (82.0, 0.0, 12.0), 28),
    "south_front": ((-5.0, 0.0, 8.0), (-95.0, 0.0, 10.0), 22),
    "ext_north": ((170.0, 40.0, 20.0), (80.0, 0.0, 10.0), 28),
    "ext_west": ((10.0, 170.0, 12.0), (0.0, 80.0, 14.0), 22),
    "ext_east": ((0.0, -150.0, 14.0), (0.0, -60.0, 8.0), 24),
    "ext_south_high": ((-190.0, 30.0, 50.0), (-90.0, 0.0, 8.0), 28),
}


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def make(scene, name, loc=None, target=None, lens=None):
    if name == "map":
        # 空中写真(refs/map/stadium_grid10m.png、1 m = 5 画素)と重ねるための真上からの正射影
        import math
        cam = bpy.data.cameras.new(name)
        cam.type = "ORTHO"
        cam.ortho_scale = 1596 / 5.0
        cam.clip_end = 3000.0
        ob = bpy.data.objects.new("cam_map", cam)
        ob.location = (0, 0, 500)
        ob.rotation_euler = (0, 0, -math.pi / 2)
        scene.collection.objects.link(ob)
        return ob
    if loc is None:
        loc, target, lens = VIEWS[name]
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_start = 0.1
    cam.clip_end = 30000.0
    ob = bpy.data.objects.new("cam_" + name, cam)
    ob.location = loc
    scene.collection.objects.link(ob)
    look_at(ob, target)
    return ob
