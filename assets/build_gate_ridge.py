# 西门屋顶脊饰真网格：正脊三层脊身+浮雕、两端鸱吻（吞脊龙头+内卷鱼尾鳍）、
# 四条垂脊带走兽队列与翘角套兽。尺寸匹配 buildRoof(36,13,5,1.3)。
# 运行：blender --background --python build_gate_ridge.py
import bpy, bmesh, math, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gate_ridge.glb')
W, D, H, LIFT = 36.0, 13.0, 5.0, 1.3
RH = max(W * 0.16, W / 2 - D * 0.42)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.materials):
    for b in list(block):
        if b.users == 0:
            block.remove(b)

V, F = [], []


def box(cx, cy, cz, sx, sy, sz, rz=0.0, ry=0.0):
    i0 = len(V)
    ca, sa = math.cos(rz), math.sin(rz)
    cb, sb = math.cos(ry), math.sin(ry)
    for dx in (-sx, sx):
        for dy in (-sy, sy):
            for dz in (-sz, sz):
                x, y = dx * ca - dy * sa, dx * sa + dy * ca
                X, Z = x * cb + dz * sb, -x * sb + dz * cb
                V.append((cx + X, cz + Z, cy + y))
    # 顶点序: dx,dy,dz 三重循环 -> 索引 bit: dx=4,dy=2,dz=1
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for a, b, c, d in q:
        F.append((i0 + a, i0 + b, i0 + c, i0 + d))


def sphere(cx, cy, cz, r, n=8):
    i0 = len(V)
    for j in range(n + 1):
        ph = math.pi * j / n
        for k in range(n):
            th = 2 * math.pi * k / n
            V.append((cx + r * math.sin(ph) * math.cos(th),
                      cz + r * math.sin(ph) * math.sin(th),
                      cy + r * math.cos(ph)))
    for j in range(n):
        for k in range(n):
            k2 = (k + 1) % n
            a = i0 + j * n + k
            b = i0 + j * n + k2
            c = i0 + (j + 1) * n + k2
            d = i0 + (j + 1) * n + k
            if j == 0:
                F.append((a, c, d))
            elif j == n - 1:
                F.append((a, b, d))
            else:
                F.append((a, b, c, d))


def tube(samples, ringfn):
    i0 = len(V)
    rings = [ringfn(c) for c in samples]
    for r in rings:
        V += r
    m = len(rings)
    for j in range(m - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            F.append((i0 + j * 4 + k, i0 + j * 4 + k2, i0 + (j + 1) * 4 + k2, i0 + (j + 1) * 4 + k))
    F.append(tuple(i0 + k for k in (0, 3, 2, 1)))
    F.append(tuple(i0 + (m - 1) * 4 + k for k in (0, 1, 2, 3)))


def ysurf(t):
    return H * (1 - t) ** 1.45 + LIFT * t ** 3


# ---------- 正脊：脊座 + 脊身 + 浮雕菱花 + 脊盖 ----------
L = 2 * RH + 1.0
box(0, H + 0.12, 0, L / 2, 0.25, 0.375)
box(0, H + 0.55, 0, L / 2 - 0.3, 0.25, 0.30)
x = -RH + 0.6
while x <= RH - 0.6:
    for s in (-1, 1):
        box(x, H + 0.55, s * 0.31, 0.13, 0.13, 0.05, rz=math.pi / 4)
    x += 1.0
box(0, H + 0.88, 0, L / 2 + 0.15, 0.10, 0.425)

# ---------- 鸱吻：吞脊龙头 + 内卷鱼尾鳍 + 背侧小兽 ----------
for s in (-1, 1):
    ox = s * (RH + 0.35)
    ix = -s  #  inward 方向

    def P(u, y):
        return (ox + ix * u, y, 0)

    box(ox + ix * 0.45, H + 0.90, 0, 0.75, 0.175, 0.40)          # 基座
    box(ox + ix * 1.00, H + 1.30, 0, 0.25, 0.20, 0.25)          # 龙头
    box(ox + ix * 1.35, H + 1.25, 0, 0.175, 0.10, 0.15)         # 上吻
    box(ox + ix * 1.30, H + 1.00, 0, 0.20, 0.075, 0.15)         # 下 jaw
    box(ox + ix * 0.30, H + 1.65, 0, 0.15, 0.15, 0.175)         # 背侧小兽
    for sz in (-1, 1):
        sphere(ox + ix * 1.05, H + 1.45, sz * 0.26, 0.06)       # 眼
    # 鱼尾鳍：XY 平面内卷曲线扫掠
    cl = [(0.5, 0.15), (0.55, 0.9), (0.6, 1.4), (0.65, 1.7), (0.8, 1.95),
          (1.1, 2.1), (1.4, 2.05), (1.55, 1.85), (1.5, 1.6)]
    samples = []
    for j, (u, y) in enumerate(cl):
        u2, y2 = cl[min(j + 1, len(cl) - 1)]
        u0, y0 = cl[max(j - 1, 0)]
        dx, dy = u2 - u0, y2 - y0
        n = math.hypot(dx, dy) or 1
        px, py = -dy / n, dx / n
        w = 0.45 - 0.23 * j / (len(cl) - 1)
        cx, cy = ox + ix * u, H + 0.75 + y
        samples.append((cx, cy, px * ix, py))
    i0 = len(V)
    rings = []
    for j, (cx, cy, px, py) in enumerate(samples):
        w = 0.45 - 0.23 * j / (len(samples) - 1)
        rings.append([(cx + px * w, -0.26, cy + py * w), (cx - px * w, -0.26, cy - py * w),
                      (cx - px * w, 0.26, cy - py * w), (cx + px * w, 0.26, cy + py * w)])
    for r in rings:
        V += r
    for j in range(len(rings) - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            F.append((i0 + j * 4 + k, i0 + j * 4 + k2, i0 + (j + 1) * 4 + k2, i0 + (j + 1) * 4 + k))
    F.append(tuple(i0 + k for k in (0, 3, 2, 1)))
    F.append(tuple(i0 + (len(rings) - 1) * 4 + k for k in (0, 1, 2, 3)))
    # 鳍面鳞纹浮雕
    for j in range(2, 8):
        cx, cy, px, py = samples[j]
        for sz in (-1, 1):
            box(cx, cy, sz * 0.27, 0.09, 0.09, 0.04, rz=math.pi / 4)

# ---------- 垂脊 ×4：方脊管 + 走兽队列 + 翘角套兽 ----------
for s in (-1, 1):
    for q in (-1, 1):
        samples = []
        N = 24
        for j in range(N + 1):
            t = j / N
            cx = s * (RH + (W / 2 - RH) * t)
            cz = q * (D / 2) * t
            cy = ysurf(t) + 0.10
            dx = s * (W / 2 - RH)
            dz = q * D / 2
            n = math.hypot(dx, dz)
            px, pz = -dz / n, dx / n
            samples.append((cx, cy, cz, px, pz, t))
        i0 = len(V)
        rings = []
        for (cx, cy, cz, px, pz, t) in samples:
            w = 0.24 - 0.06 * t
            rings.append([(cx + px * w, cz + pz * w, cy), (cx - px * w, cz - pz * w, cy),
                          (cx - px * w, cz - pz * w, cy + 0.34), (cx + px * w, cz + pz * w, cy + 0.34)])
        for r in rings:
            V += r
        for j in range(len(rings) - 1):
            for k in range(4):
                k2 = (k + 1) % 4
                F.append((i0 + j * 4 + k, i0 + j * 4 + k2, i0 + (j + 1) * 4 + k2, i0 + (j + 1) * 4 + k))
        F.append(tuple(i0 + k for k in (0, 3, 2, 1)))
        F.append(tuple(i0 + (len(rings) - 1) * 4 + k for k in (0, 1, 2, 3)))
        ang = math.atan2(q * D / 2, s * (W / 2 - RH))
        for t in (0.50, 0.64, 0.78, 0.90):
            cx = s * (RH + (W / 2 - RH) * t)
            cz = q * (D / 2) * t
            cy = ysurf(t) + 0.44
            box(cx, cy + 0.05, cz, 0.15, 0.05, 0.15, ry=ang)
            box(cx, cy + 0.23, cz, 0.10, 0.13, 0.08, ry=ang)
            hx = cx + math.cos(ang) * 0.14
            hz = cz + math.sin(ang) * 0.14
            sphere(hx, cy + 0.40, hz, 0.09)
        # 翘角套兽
        cx = s * W / 2
        cz = q * D / 2
        cy = ysurf(1.0) + 0.30
        box(cx, cy, cz, 0.20, 0.18, 0.20, ry=ang)
        sphere(cx + math.cos(ang) * 0.22, cy + 0.22, cz + math.sin(ang) * 0.22, 0.12)

me = bpy.data.meshes.new('GateRidge')
me.from_pydata(V, [], F)
me.update()
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me)
bm.free()
ob = bpy.data.objects.new('GateRidge', me)
bpy.context.collection.objects.link(ob)
mat = bpy.data.materials.new('ridge')
mat.use_nodes = True
b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b.inputs['Base Color'].default_value = (0.115, 0.135, 0.16, 1)
b.inputs['Roughness'].default_value = 0.85
ob.data.materials.append(mat)

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                          export_apply=True, export_yup=True)
print('RIDGE_GLB_BYTES', os.path.getsize(OUT))

# 自检预览
from mathutils import Vector
scene = bpy.context.scene
cam_data = bpy.data.cameras.new('cam')
cam_data.lens = 45
cam = bpy.data.objects.new('cam', cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (26, -24, 16)
d = Vector((0, 0, 5.5)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
sun_data = bpy.data.lights.new('sun', 'SUN')
sun_data.energy = 3.0
sun = bpy.data.objects.new('sun', sun_data)
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
world = bpy.data.worlds.new('w')
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0.35, 0.5, 0.7, 1)
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.render.resolution_x = 900
scene.render.resolution_y = 600
scene.render.filepath = os.path.join(os.path.dirname(OUT), 'ridge_preview.png')
bpy.ops.render.render(write_still=True)
cam.location = (20, -13, 11)
d = Vector((12.5, 0, 6.5)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(os.path.dirname(OUT), 'ridge_preview2.png')
bpy.ops.render.render(write_still=True)
cam.location = (RH + 0.35, -9, H + 1.9)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.render.filepath = os.path.join(os.path.dirname(OUT), 'ridge_preview3.png')
bpy.ops.render.render(write_still=True)
print('PREVIEW_DONE')