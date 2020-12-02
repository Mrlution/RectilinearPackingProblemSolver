# -*- encoding: utf-8 -*-
'''
@File    :   calculate_npf.py
@Time    :   2020/11/19 19:20:30
@Author  :   KingofCode 
@Version :   1.0
@Contact :   mrlution@qq.com
@Desc    :   NFP计算
'''

# here put the import lib
import copy
from . import nfp_utls
import pyclipper

def minkowski_difference(A, B):
    """
    两个多边形的相切空间
    http://www.angusj.com/delphi/clipper/documentation/Docs/Units/ClipperLib/Functions/MinkowskiDiff.htm
    :param A:
    :param B:
    :return:
    """
    #print("AC和Bc",A['points'],B['points'])
    Ac = [[ p['x'] ,  p['y']] for p in A['points']]
    Bc = [[ p['x'] * -1,p['y'] * -1] for p in B['points']]
    
    solution = pyclipper.MinkowskiSum(Ac, Bc, True)
    largest_area = None
    clipper_nfp = None
    for p in solution:
        p = [{'x': i[0], 'y':i[1]} for i in p]
        sarea = nfp_utls.polygon_area(p)
        if largest_area is None or largest_area > sarea:
            clipper_nfp = p
            largest_area = sarea

    clipper_nfp = [{
                    'x': clipper_nfp[i]['x'] + Bc[0][0] * -1,
                    'y':clipper_nfp[i]['y'] + Bc[0][1] * -1
                   } for i in range(0, len(clipper_nfp))]
    #print("结果",clipper_nfp)
    return [clipper_nfp]





class NFP_Calculater():
    """NFP计算类
    """

    # def __init__(self,config=None):
    #     if config:
    #         self.config=config
    #     else:
    #         config={
    #             'useHoles': False,       # 是否有洞，暂时都是没有洞
    #             'exploreConcave': False  # 寻找凹面，暂时是否
    #         }

    @staticmethod      
    def process_nfp(pair):
        """
        计算所有图形两两组合的相切多边形（NFP）
        :param pair: 两个组合图形的参数
        :return:
        """
        if pair is None or len(pair) == 0:
            return None

        # 考虑有没有洞和凹面
        # search_edges = self.config['exploreConcave']
        # use_holes = self.config['useHoles']
        search_edges=False
        use_holes=False

        # 图形参数
        #print("beforerotation",pair['A']['points'],pair['B']['points'])
        A = copy.deepcopy(pair['A'])
        A['points'] = nfp_utls.rotate_polygon(A['points'], pair['key']['A_rotation'])['points']
        B = copy.deepcopy(pair['B'])
        B['points'] = nfp_utls.rotate_polygon(B['points'], pair['key']['B_rotation'])['points']
        #print("afterrotation",A['points'],B['points'])


        if pair['key']['inside']:
            # 内切或者外切
            if nfp_utls.is_rectangle(A['points']):
                #print("points1",A['points'], B['points'])
                nfp = nfp_utls.nfp_rectangle(A['points'], B['points'])
                #print("nfp1",nfp)

            else:
                nfp = nfp_utls.nfp_polygon(A, B, True, search_edges)

            # ensure all interior NFPs have the same winding direction
            if nfp and len(nfp) > 0:
                for i in range(0, len(nfp)):
                    if nfp_utls.polygon_area(nfp[i]) > 0:
                        nfp[i].reverse()
            else:
                pass
                # print('NFP Warning:', pair['key'])

        else:
            if search_edges:
                #print(A['points'], B['points'])
                nfp = nfp_utls.nfp_polygon(A, B, False, search_edges)
            else:
                #print("points2",A['points'], B['points'])

                nfp = minkowski_difference(A, B)
                #print("nfp2",nfp)

            # 检查NFP多边形是否合理
            if nfp is None or len(nfp) == 0:
                pass
                # print('error in NFP 260')
                # print('NFP Error:', pair['key'])
                # print('A;', A)
                # print('B:', B)
                return None

            for i in range(0, len(nfp)):
                # if search edges is active, only the first NFP is guaranteed to pass sanity check
                if not search_edges or i == 0:
                    if abs(nfp_utls.polygon_area(nfp[i])) < abs(nfp_utls.polygon_area(A['points'])):
                        pass
                        # print('error in NFP area 269')
                        # print('NFP Area Error: ', abs(nfp_utls.polygon_area(nfp[i])), pair['key'])
                        # print('NFP:', json.dumps(nfp[i]))
                        # print('A: ', A)
                        # print('B: ', B)
                        nfp.pop(i)
                        return None

            if len(nfp) == 0:
                return None
            # for outer NFPs, the first is guaranteed to be the largest.
            # Any subsequent NFPs that lie inside the first are hole
            for i in range(0, len(nfp)):
                if nfp_utls.polygon_area(nfp[i]) > 0:
                    nfp[i].reverse()

                if i > 0:
                    if nfp_utls.point_in_polygon(nfp[i][0], nfp[0]):
                        if nfp_utls.polygon_area(nfp[i]) < 0:
                            nfp[i].reverse()

            # generate nfps for children (holes of parts) if any exist
            # 有洞的暂时不管
            if use_holes and len(A) > 0:
                pass
        
        return {'key': pair['key'], 'value': nfp}



