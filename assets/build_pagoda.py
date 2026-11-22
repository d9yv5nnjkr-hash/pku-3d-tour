# 博雅塔真网格建模：八角十三层密檐砖塔
# bpy 程序化建模 + 按墙面弧长展 UV + numpy 砖纹 + AO 烘焙叠乘 + GLB 导出
# 运行：blender --background --python build_pagoda.py
import bpy, bmesh, math, os
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'boya_pagoda.glb')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for b in list(block):
        if b.users == 0:
            block.remove(b)

ANG = math.pi / 8  # 八角面心朝向 45° 倍数，顶点偏移 22.5°


def ring(r, z, n=8):
    return [(r * math.cos(ANG + k * 2 * math.pi / n),
             r * math.sin(ANG + k * 2 * math.pi / n), z) for k in range(n)]


def prism(V, F, r0, r1, z0, z1):
    i0 = len(V)
    V += ring(r0, z0) + ring(r1, z1)
    for k in range(8):
        k2 = (k + 1) % 8
        F.append((i0 + k, i0 + k2, i0 + 8 + k2, i0 + 8 + k))
    F.append(tuple(i0 + 7 - k for k in range(8)))
    F.append(tuple(i0 + 8 + k for k in range(8)))


def revolve(V, F, prof, r, z):
    i0 = len(V)
    for rf, dz in prof:
        V += ring(r * rf, z + dz)
    m = len(prof)
    for j in range(m):
        j2 = (j + 1) % m
        for k in range(8):
            k2 = (k + 1) % 8
            F.append((i0 + j * 8 + k, i0 + j * 8 + k2, i0 + j2 * 8 + k2, i0 + j2 * 8 + k))


def new_obj(name, V, F, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], F)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def s2l(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def plain(name, srgb, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    lin = s2l(np.array(srgb, dtype=float))
    b.inputs['Base Color'].default_value = (*lin, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


stone = plain('stone', (150, 146, 138), 0.9)
eave = plain('eave', (118, 114, 106), 0.85)
marble = plain('marble', (208, 204, 194), 0.7)
bronze = plain('bronze', (112, 92, 52), 0.45, 0.85)
dark = plain('dark', (26, 21, 16), 0.9)
brick = plain('brick_baked', (142, 132, 116), 0.88)

# ---------- 塔身：十三层八角棱柱 ----------
V, F = [], []
z = 2.5
tiers = []
for i in range(13):
    r = 4.0 - i * 0.15
    h = 4.0 if i == 0 else 2.55 - (i - 1) * 0.085
    prism(V, F, r * 0.985, r, z, z + h)
    tiers.append((r, z, h))
    z += h + 0.42
body = new_obj('BoyaBody', V, F, brick)

# 按墙面弧长展 UV：u 沿周长（米），v 沿高度（米），贴图跨度 3 米
PER = 8 * 2 * 3.2 * math.sin(math.pi / 8)
me = body.data
uv = me.uv_layers.new(name='UVMap')
for poly in me.polygons:
    us, vs = [], []
    for li in poly.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        if len(poly.vertices) == 8:  # 顶/底盖
            us.append(co.x / 3 + 0.5)
            vs.append(co.y / 3 + 0.5)
        else:
            a = math.atan2(co.y, co.x)
            if a < 0:
                a += 2 * math.pi
            us.append(a / (2 * math.pi) * PER / 3)
            vs.append(co.z / 3)
    if len(poly.vertices) == 4 and max(us) - min(us) > PER / 6:
        us = [u + PER / 3 if u < PER / 6 else u for u in us]
    for li, u, v in zip(poly.loop_indices, us, vs):
        uv.data[li].uv = (u, v)

# ---------- 密檐：凹曲挑檐 + 檐下阴影带 + 顶部攒尖锥 ----------
V, F = [], []
prof = [(1.02, 0.15), (1.18, -0.16), (1.32, -0.30), (1.38, -0.20),
        (1.38, -0.27), (1.18, -0.38), (1.00, -0.26)]
for (r, tz, h) in tiers:
    ze = tz + h
    revolve(V, F, prof, r, ze)
    prism(V, F, r * 1.03, r * 1.03, ze - 0.30, ze - 0.02)
r_top = tiers[-1][0]
z_top = tiers[-1][1] + tiers[-1][2] + 0.42
prism(V, F, r_top * 1.52, 0.12, z_top, z_top + 2.6)
eaves = new_obj('BoyaEaves', V, F, eave)

# ---------- 须弥座 + 台阶 + 壶门石框 ----------
V, F = [], []
prism(V, F, 7.0, 6.6, 0.0, 0.7)
prism(V, F, 6.4, 6.0, 0.7, 1.3)
prism(V, F, 5.9, 5.4, 1.3, 2.5)
base = new_obj('BoyaBase', V, F, stone)


def op_cube(name, loc, scale, rot, mat):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    ob.data.materials.append(mat)
    return ob


extras_base = [
    op_cube('step1', (0, -7.2, 0.15), (1.7, 1.3, 0.15), (0, 0, 0), stone),
    op_cube('step2', (0, -6.4, 0.45), (1.4, 0.9, 0.15), (0, 0, 0), stone),
    op_cube('jambL', (-1.05, -3.74, 4.0), (0.16, 0.10, 1.5), (0, 0, 0), stone),
    op_cube('jambR', (1.05, -3.74, 4.0), (0.16, 0.10, 1.5), (0, 0, 0), stone),
]
bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.16,
                                 major_segments=16, minor_segments=8,
                                 location=(0, -3.74, 5.5), rotation=(math.pi / 2, 0, 0))
arch = bpy.context.object
arch.name = 'arch'
arch.data.materials.append(stone)
extras_base.append(arch)
bpy.ops.object.select_all(action='DESELECT')
for ob in extras_base:
    ob.select_set(True)
base.select_set(True)
bpy.context.view_layer.objects.active = base
bpy.ops.object.join()

# ---------- 望柱栏板（南面留门） ----------
V, F = [], []
for k in range(8):
    a = k * math.pi / 4
    n0 = len(V)
    prism(V, F, 0.16, 0.13, 2.5, 3.5)
    cx, cy = math.cos(ANG + k * math.pi / 4) * 6.7, math.sin(ANG + k * math.pi / 4) * 6.7
    for vi in range(n0, len(V)):
        V[vi] = (V[vi][0] + cx, V[vi][1] + cy, V[vi][2])
    if k == 6:
        continue
    rm = 6.7 * math.cos(math.pi / 8)
    px, py = math.cos(a) * rm, math.sin(a) * rm
    for (zc, hh) in ((2.95, 0.25), (3.42, 0.06)):
        i0 = len(V)
        hl, ht = 2.56, 0.06
        ca, sa = math.cos(a), math.sin(a)
        for zz in (zc - hh, zc + hh):
            for (lx, ly) in ((-hl, -ht), (hl, -ht), (hl, ht), (-hl, ht)):
                V.append((px - lx * sa + ly * ca, py + lx * ca + ly * sa, zz))
        F.append((i0, i0 + 1, i0 + 3, i0 + 2))
        F.append((i0 + 4, i0 + 6, i0 + 7, i0 + 5))
        for e in range(4):
            e2 = (e + 1) % 4
            F.append((i0 + e, i0 + 4 + e, i0 + 4 + e2, i0 + e2))
rail = new_obj('BoyaRail', V, F, marble)

# ---------- 壶门暗门 + 各层盲窗 ----------
V, F = [], []
V += [(-0.95, -3.68, 2.5), (0.95, -3.68, 2.5), (0.95, -3.68, 5.5), (-0.95, -3.68, 5.5),
      (-0.95, -3.56, 2.5), (0.95, -3.56, 2.5), (0.95, -3.56, 5.5), (-0.95, -3.56, 5.5)]
F += [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
opens = new_obj('BoyaOpen', V, F, dark)
win_obs = []
for i, (r, tz, h) in enumerate(tiers):
    ap = r * math.cos(math.pi / 8)
    faces_k = [0, 2, 4] + ([6] if i > 0 else [])
    w, hh = (0.36, 0.55) if i < 4 else (0.26, 0.42)
    for k in faces_k:
        a = k * math.pi / 4
        win_obs.append(op_cube('bw%d_%d' % (i, k),
                               (math.cos(a) * (ap - 0.04), math.sin(a) * (ap - 0.04), tz + h * 0.55),
                               (w, 0.06, hh), (0, 0, a - math.pi / 2), dark))
bpy.ops.object.select_all(action='DESELECT')
for ob in win_obs:
    ob.select_set(True)
opens.select_set(True)
bpy.context.view_layer.objects.active = opens
bpy.ops.object.join()

# ---------- 塔刹 + 檐角风铎 ----------
V, F = [], []
zf = z_top + 2.6
prism(V, F, 0.7, 0.5, zf, zf + 0.35)
for j in range(3):
    prism(V, F, 0.42 - j * 0.08, 0.42 - j * 0.08, zf + 0.45 + j * 0.22, zf + 0.57 + j * 0.22)
bronze_obj = new_obj('BoyaBronze', V, F, bronze)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.28,
                                     location=(0, 0, zf + 1.35))
ball = bpy.context.object
ball.name = 'jewel'
ball.data.materials.append(bronze)
chimes = []
for (r, tz, h) in tiers:
    ze = tz + h
    for k in range(8):
        a = ANG + k * math.pi / 4
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.10, radius2=0.0, depth=0.30,
                                        location=(math.cos(a) * r * 1.34, math.sin(a) * r * 1.34, ze - 0.42),
                                        rotation=(math.pi, 0, 0))
        c = bpy.context.object
        c.data.materials.append(bronze)
        chimes.append(c)
bpy.ops.object.select_all(action='DESELECT')
for ob in [ball] + chimes:
    ob.select_set(True)
bronze_obj.select_set(True)
bpy.context.view_layer.objects.active = bronze_obj
bpy.ops.object.join()

# ---------- AO 烘焙 ----------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
ao_img = bpy.data.images.new('ao_bake', 1024, 1024)
ao_img.colorspace_settings.name = 'Non-Color'
node = brick.node_tree.nodes.new('ShaderNodeTexImage')
node.image = ao_img
brick.node_tree.nodes.active = node
node.select = True
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.bake(type='AO', use_clear=True)
ao = np.empty(1024 * 1024 * 4, dtype=np.float32)
ao_img.pixels.foreach_get(ao)
ao = ao.reshape(1024, 1024, 4)[:, :, 0]

# ---------- numpy 砖纹 × AO ----------
rng = np.random.default_rng(7)
S = 1024
row_h = S * 0.10 / 3.0
brick_w = S * 0.30 / 3.0
mortar = 2.0
yy, xx = np.mgrid[0:S, 0:S]
row = np.floor(yy / row_h).astype(int)
off = (row % 2) * brick_w * 0.5
bx = np.floor((xx + off[:, :]) / brick_w).astype(int)
jit = rng.normal(0, 7, (row.max() + 2, bx.max() + 2))
col = np.stack([150 + jit[row, bx], 140 + jit[row, bx] * 0.9, 124 + jit[row, bx] * 0.8], -1)
mortar_mask = ((yy % row_h) < mortar) | (((xx + off[:, :]) % brick_w) < mortar)
col[mortar_mask] = (112, 104, 94)
streak = rng.normal(0, 1, S) * 0.5
streak = np.convolve(streak, np.ones(9) / 9, mode='same')
col += streak[:, None, None] * 6
shade = 0.75 + 0.25 * np.clip(ao, 0, 1)
col *= shade[:, :, None]
col = np.clip(col, 0, 255)
pix = np.concatenate([col / 255.0, np.ones((S, S, 1))], -1).astype(np.float32)
tex = bpy.data.images.new('brick_tex', S, S)
tex.colorspace_settings.name = 'sRGB'
tex.pixels.foreach_set(pix.ravel())
tex.pack()
node.image = tex
bsdf = next(n for n in brick.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
brick.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])

# ---------- 导出 GLB ----------
objs = [body, eaves, base, rail, opens, bronze_obj]
bpy.ops.object.select_all(action='DESELECT')
for ob in objs:
    ob.select_set(True)
bpy.context.view_layer.objects.active = body
try:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True,
                              export_image_format='JPEG', export_jpeg_quality=85)
except Exception as e:
    print('gltf op missing, enabling addon:', e)
    bpy.ops.preferences.addon_enable(module='io_scene_gltf2')
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True,
                              export_image_format='JPEG', export_jpeg_quality=85)
print('PAGODA_GLB_BYTES', os.path.getsize(OUT))
print('PAGODA_TOP_Z', zf + 1.63)

# ---------- 自检预览渲染 ----------
from mathutils import Vector
cam_data = bpy.data.cameras.new('cam')
cam_data.lens = 40
cam = bpy.data.objects.new('cam', cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (46, -52, 30)
d = Vector((0, 0, 20)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
sun_data = bpy.data.lights.new('sun', 'SUN')
sun_data.energy = 3.0
sun_data.angle = 0.02
sun = bpy.data.objects.new('sun', sun_data)
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
world = bpy.data.worlds.new('w') if not scene.world else scene.world
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0.35, 0.5, 0.7, 1)
bg.inputs[1].default_value = 1.0
scene.cycles.samples = 32
scene.render.resolution_x = 700
scene.render.resolution_y = 900
scene.render.filepath = os.path.join(os.path.dirname(OUT), 'pagoda_preview.png')
bpy.ops.render.render(write_still=True)
print('PREVIEW_DONE')