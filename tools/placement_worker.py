# -*- encoding: utf-8 -*-
'''
@File    :   placement_worker.py
@Time    :   2020/11/19 19:17:57
@Author  :   KingofCode 
@Version :   1.0
@Contact :   mrlution@qq.com
@Desc    :   放置过程
'''

# here put the import lib
import json
from .nfp_utls import almost_equal, rotate_polygon, get_polygon_bounds, polygon_area
import copy
import pyclipper

FITNESSSCALE=10


class PlacementWorker():
    """放置图形并得到结果
    """
    def __init__(self, bin_polygon, paths, ids, rotations, config, nfp_cache):
        self.bin_polygon = bin_polygon
        self.paths = copy.deepcopy(paths)
        self.ids = ids       # 图形原来的ID顺序
        self.rotations = rotations
        self.config = config
        self.nfpCache = nfp_cache or {}
        

    def place_paths(self):
        # 排列图形
        if self.bin_polygon is None:
            return None

        # rotate paths by given rotation
        rotated = list()
        for i in range(0, len(self.paths)):
            r = rotate_polygon(self.paths[i][1]['points'], self.paths[i][2])
            r['rotation'] = self.paths[i][2]
            r['source'] = self.paths[i][1]['p_id']
            r['p_id'] = self.paths[i][0]
            rotated.append(r)

        paths = rotated
        # 保存所有布局后的布局数据
        all_placements = list()
        # 基因组的适应值
        fitness = 0
        bin_area = abs(polygon_area(self.bin_polygon['points']))
        min_width = None
        while len(paths) > 0:#当还有形状没安排上
            placed = list()
            placements = list()
            # add 1 for each new bin opened (lower fitness is better)
            fitness += 1
            for i in range(0, len(paths)):#对于每个剩余形状
                path = paths[i] #当前剩余图形
                # 图形的坐标
                key = json.dumps({
                    'A': '-1',
                    'B': path['p_id'],#当前剩余图形的id
                    'inside': True,
                    'A_rotation': 0,
                    'B_rotation': path['rotation']
                })

                binNfp = self.nfpCache.get(key) #{"pair['key']":nfp}#取出当前图形和容器的内切多边形列表
                if binNfp is None or len(binNfp) == 0:
                    print("error:binNfp缺失:"+key)
                    continue #没有就忽略当前图形不放了

                # 无法放下,跳过
                error = False

                # 确保所有必要的 NFPs 存在
                for p in placed:#对于每个已经放下的图形
                    key = json.dumps({
                        'A': p['p_id'],
                        'B': path['p_id'],
                        'inside': False,
                        'A_rotation': p['rotation'],
                        'B_rotation': path['rotation']
                    })
                    nfp = self.nfpCache.get(key) #每个已经放下的图形和当前图形的外切多边形列表
                    if nfp is None:
                        error = True
                        print("error:图形之间的nfp缺失:"+key)
                        break #没有就结束,没法搞

                # 无法放下,跳过
                if error:
                    print("error:无法放下")
                    continue

                position = None
                if len(placed) == 0: #如果一个图形都还没放进去
                    for j in range(0, len(binNfp)):#对于每个当前图形和容器外接多边形
                        for k in range(0, len(binNfp[j])):#对于每个nfp的坐标
                            if position is None or (binNfp[j][k]['x']-path['points'][0]['x'] < position['x']):
                                position = {
                                    'x': binNfp[j][k]['x'] - path['points'][0]['x'], #NFP中最小x与图形参考点x的距离,将图形平移到那一点要将每个x减去这个距离
                                    'y': binNfp[j][k]['y'] - path['points'][0]['y'], #y要减去这个距离
                                    'p_id': path['p_id'],
                                    'rotation': path['rotation']
                                }

                    placements.append(position) #存储着第一个图像应该做什么移动到目标布局
                    placed.append(path) #第一个图像摆完
                    continue #结束这个循环,放置下一个图形

                clipper_bin_nfp = list()
                for j in range(0, len(binNfp)): #对于每一个与Bin的NFP
                    clipper_bin_nfp.append([[p['x'], p['y']] for p in binNfp[j]])#将NFP的每个坐标都压入clipper_bin_nfp

                clipper = pyclipper.Pyclipper()

                for j in range(0, len(placed)):#对于每一个放好的图形
                    p = placed[j]
                    key = json.dumps({
                        'A': p['p_id'],
                        'B': path['p_id'],
                        'inside': False,
                        'A_rotation': p['rotation'],
                        'B_rotation': path['rotation']
                    })
                    nfp = self.nfpCache.get(key) #得到当前要摆放的图形和观察放好的图形之间的nfp

                    if nfp is None:
                        print("error:nfp缺失:"+key)
                        continue
                    for k in range(0, len(nfp)):#对于每一个nfp
                        clone = [[np['x'] + placements[j]['x'], np['y'] + placements[j]['y']] for np in nfp[k]] #每个nfp移动到已放好块的周围
                        clone = pyclipper.CleanPolygon(clone)#移除以下类型的点集 距离过近的相邻点 等等
                        if len(clone) > 2:
                            clipper.AddPath(clone, pyclipper.PT_SUBJECT, True)#NFP交给clipper
                #所有放置好的图形的NFP并集
                combine_nfp = clipper.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                if len(combine_nfp) == 0:
                    print("error:nfp错误:nfp并集长度为0")
                    continue

                clipper = pyclipper.Pyclipper()
                clipper.AddPaths(combine_nfp, pyclipper.PT_CLIP, True)#将合并好的NFP交给clipper
                try:
                    clipper.AddPaths(clipper_bin_nfp, pyclipper.PT_SUBJECT, True)#将要放置的图形与盒子的NFP交给clipper
                except:
                    print( u'图形坐标出错', clipper_bin_nfp)

                # choose placement that results in the smallest bounding box
                #与盒子NFP(可行)-放好图形的NFP(不可行)
                finalNfp = clipper.Execute(pyclipper.CT_DIFFERENCE, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                if len(finalNfp) == 0:
                    continue
                finalNfp = pyclipper.CleanPolygons(finalNfp)

                for j in range(len(finalNfp)-1, -1, -1):
                    if len(finalNfp[j]) < 3:
                        finalNfp.pop(j)
                if len(finalNfp) == 0:
                    continue

                finalNfp = [[{'x': p[0], 'y': p[1]}for p in polygon] for polygon in finalNfp]#将所有finalNFP的点取出

                min_width = None
                min_area = None
                min_x = None

                for nf in finalNfp:#对于每个NFP

                    if abs(polygon_area(nf)) < 2:
                        continue

                    for p_nf in nf:#对于每个NFP的点
                        # 生成nfp多边形
                        all_points = list()
                        for m in range(0, len(placed)):#对于每个已放置图形
                            for p in placed[m]['points']:#对于每个点
                                all_points.append({
                                    'x': p['x']+placements[m]['x'],#每个点都移动到布局
                                    'y': p['y']+placements[m]['y']
                                })
                        # path 坐标
                        shift_vector = { 
                            'x': p_nf['x'] - path['points'][0]['x'],
                            'y': p_nf['y'] - path['points'][0]['y'],
                            'p_id': path['p_id'],
                            'rotation': path['rotation'],
                        }

                        # 找新坐标后的最小矩形
                        for m in range(0, len(path['points'])):
                            all_points.append({
                                'x': path['points'][m]['x'] + shift_vector['x'],
                                'y': path['points'][m]['y'] + shift_vector['y']
                            })

                        rect_bounds = get_polygon_bounds(all_points)
                        # weigh width more, to help compress in direction of gravity
                        area = rect_bounds['width'] * 2 + rect_bounds['height']

                        if (min_area is None or area < min_area or almost_equal(min_area, area)) and (
                                        min_x is None or shift_vector['x'] <= min_x):
                            min_area = area
                            min_width = rect_bounds['width']
                            position = shift_vector
                            min_x = shift_vector['x']

                if position:
                    placed.append(path)
                    placements.append(position)

            if min_width:
                fitness += FITNESSSCALE*min_width / bin_area

            for p in placed:#将安排上的形状从剩余形状中剔除
                p_id = paths.index(p)
                if p_id >= 0:
                    paths.pop(p_id)

            if placements and len(placements) > 0:
                all_placements.append(placements)

            else:
                # something wrong
                break

        fitness += 2 * len(paths)
       

        return {'placements': all_placements, 'fitness': fitness,'min_width':min_width, 'paths': paths, 'area': bin_area}
