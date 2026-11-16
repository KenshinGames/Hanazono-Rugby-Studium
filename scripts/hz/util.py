"""メッシュを組み立てる共通の道具。"""
import math

import bpy
from mathutils import Matrix, Vector


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return scene


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def stand_xf(side, wall):
    """スタンドの局所座標 (u=左右, d=グラウンドから外へ, z) を世界座標に直す行列。
    side: 'W','E','N','S'。wall は前の壁の位置(W/E は Y、N/S は X の値)。
    回転だけなので面の向きは保たれる。"""
    if side == "W":      # d=+Y, u=+X
        return Matrix.Translation((0, wall, 0))
    if side == "E":      # d=-Y, u=-X
        return Matrix.Translation((0, wall, 0)) @ Matrix.Rotation(math.pi, 4, "Z")
    if side == "N":      # d=+X, u=-Y
        return Matrix.Translation((wall, 0, 0)) @ Matrix.Rotation(-math.pi / 2, 4, "Z")
    if side == "S":      # d=-X, u=+Y
        return Matrix.Translation((wall, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Z")
    raise ValueError(side)


class MB:
    """面をためて、最後に 1 つのメッシュにする。"""

    def __init__(self, xf=None):
        self.v = []
        self.f = []
        self.fm = []
        self.mats = []
        self.xf = xf

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _p(self, p):
        if self.xf is not None:
            p = self.xf @ Vector(p)
        return (p[0], p[1], p[2])

    def face(self, pts, mat):
        n = len(self.v)
        self.v.extend(self._p(p) for p in pts)
        self.f.append(tuple(range(n, n + len(pts))))
        self.fm.append(self._mi(mat))

    def box(self, x0, x1, y0, y1, z0, z1, mat, bottom=True):
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        if z0 > z1:
            z0, z1 = z1, z0
        a, b, c, d = (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)
        e, f, g, h = (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)
        self.face((e, f, g, h), mat)
        if bottom:
            self.face((d, c, b, a), mat)
        self.face((a, b, f, e), mat)
        self.face((b, c, g, f), mat)
        self.face((c, d, h, g), mat)
        self.face((d, a, e, h), mat)

    def rect(self, x0, x1, y0, y1, z, mat):
        """上向きの水平な四角。"""
        self.face(((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)), mat)

    def prism(self, poly, z0, z1, mat, caps=True, side_mat=None):
        """XY 平面の多角形(反時計回り)を Z 方向に押し出す。"""
        n = len(poly)
        sm = side_mat or mat
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]
            self.face(((p[0], p[1], z0), (q[0], q[1], z0), (q[0], q[1], z1), (p[0], p[1], z1)), sm)
        if caps:
            self.face([(p[0], p[1], z1) for p in poly], mat)
            self.face([(p[0], p[1], z0) for p in reversed(poly)], mat)

    def sweep_u(self, profile, u0, u1, mat, caps=True, closed=True):
        """(d, z) の断面を u 方向(局所 X)に押し出す。profile は d-z 平面で反時計回り。"""
        n = len(profile)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            p, q = profile[i], profile[(i + 1) % n]
            self.face(((u1, p[0], p[1]), (u0, p[0], p[1]), (u0, q[0], q[1]), (u1, q[0], q[1])), mat)
        if caps and closed:
            self.face([(u1, p[0], p[1]) for p in profile], mat)
            self.face([(u0, p[0], p[1]) for p in reversed(profile)], mat)

    def cyl(self, p0, p1, r0, mat, n=8, r1=None, caps=False):
        """p0 から p1 への丸棒。"""
        r1 = r0 if r1 is None else r1
        p0 = Vector(p0)
        p1 = Vector(p1)
        ax = p1 - p0
        if ax.length < 1e-9:
            return
        ax.normalize()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.99 else Vector((1, 0, 0))
        e1 = ax.cross(ref).normalized()
        e2 = ax.cross(e1)
        ring0 = []
        ring1 = []
        for i in range(n):
            a = 2 * math.pi * i / n
            o = e1 * math.cos(a) + e2 * math.sin(a)
            ring0.append(p0 + o * r0)
            ring1.append(p1 + o * r1)
        base = len(self.v)
        self.v.extend(self._p(p) for p in ring0)
        self.v.extend(self._p(p) for p in ring1)
        mi = self._mi(mat)
        for i in range(n):
            j = (i + 1) % n
            self.f.append((base + i, base + j, base + n + j, base + n + i))
            self.fm.append(mi)
        if caps:
            self.f.append(tuple(base + i for i in reversed(range(n))))
            self.fm.append(mi)
            self.f.append(tuple(base + n + i for i in range(n)))
            self.fm.append(mi)

    def bar(self, p0, p1, w, h, mat):
        """p0 から p1 への角材(幅 w は水平、h は鉛直に近い向き)。"""
        p0 = Vector(p0)
        p1 = Vector(p1)
        ax = (p1 - p0)
        if ax.length < 1e-9:
            return
        ax.normalize()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.99 else Vector((1, 0, 0))
        e1 = ax.cross(ref).normalized() * (w / 2)
        e2 = e1.cross(ax).normalized() * (h / 2)
        c0 = [p0 - e1 - e2, p0 + e1 - e2, p0 + e1 + e2, p0 - e1 + e2]
        c1 = [p1 - e1 - e2, p1 + e1 - e2, p1 + e1 + e2, p1 - e1 + e2]
        for i in range(4):
            j = (i + 1) % 4
            self.face((c0[i], c0[j], c1[j], c1[i]), mat)
        self.face(list(reversed(c0)), mat)
        self.face(c1, mat)

    def empty(self):
        return not self.f

    def build(self, name, collection, smooth=False, auto_smooth_angle=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        if len(self.mats) > 1:
            me.polygons.foreach_set("material_index", self.fm)
        if smooth:
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.update()
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        return ob


def merge_by_distance(ob, dist=0.0005):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(ob.data)
    bm.free()


def arc_pts(cx, cy, r, a0, a1, n):
    """中心 (cx,cy)、半径 r の弧の点列(角度は度)。"""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


JP_FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
_fonts = {}


def _font(path):
    if path not in _fonts:
        try:
            _fonts[path] = bpy.data.fonts.load(path)
        except Exception as e:
            print("[text] フォントを読めません:", path, e)
            _fonts[path] = None
    return _fonts[path]


def text_obj(name, body, height, mat, collection, origin, normal, align="CENTER", jp=False, extrude=0.0,
             max_width=None, up=(0, 0, 1)):
    """壁に貼る文字。origin は文字の基準点(左右は align、上下は中央)、normal は文字の面が向く向き。
    height は大文字の高さ(m)。メッシュに直して返す。"""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = extrude
    if jp:
        f = _font(JP_FONT)
        if f:
            cu.font = f
    cu.size = height / 0.72
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    bpy.context.scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.name = name
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    n = Vector(normal).normalized()
    u = Vector(up)
    x = u.cross(n).normalized()
    y = n.cross(x).normalized()
    m = Matrix.Identity(4)
    for i, col in enumerate((x, y, n)):
        m[0][i], m[1][i], m[2][i] = col
    sx = 1.0
    if max_width and me.vertices:
        xs = [v.co.x for v in me.vertices]
        w = max(xs) - min(xs)
        if w > max_width:
            sx = max_width / w
    ob.matrix_world = Matrix.Translation(Vector(origin)) @ m @ Matrix.Diagonal((sx, 1, 1, 1))
    collection.objects.link(ob)
    return ob


def frame_xf(origin, normal, up=(0, 0, 1)):
    """局所の x=右、y=上、z=normal とする行列(MB の xf に使う)。"""
    n = Vector(normal).normalized()
    x = Vector(up).cross(n).normalized()
    y = n.cross(x).normalized()
    m = Matrix.Identity(4)
    for i, col in enumerate((x, y, n)):
        m[0][i], m[1][i], m[2][i] = col
    return Matrix.Translation(Vector(origin)) @ m
