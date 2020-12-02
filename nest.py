# -*- encoding: utf-8 -*-
'''
@File    :   nest.py
@Time    :   2020/11/19 18:52:28
@Author  :   KingofCode 
@Version :   1.0
@Contact :   mrlution@qq.com
@Desc    :   主要的打包类
'''

# here put the import lib
from tools import placement_worker, nfp_utls
import math
import json
import random
import copy
from Polygon import Polygon
import pyclipper
#from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
#from matplotlib.figure import Figure
#from settings import SPACING, ROTATIONS, POPULATION_SIZE, MUTA_RATE,DEBUG,DRAWPIC,SCALE,COMPLEX_FIRST_STRATEGY,COMPLEX_FIRST_AREA_SECOND_STRATEGY,MIXED_COMPLEX_STRATEGY,STOP_GENERATION
from setting import settings
from GAlgo import genetic_algorithm



class ThisClass():
    """仅仅用作初始参数的存储
    """
    config = {
                'curveTolerance': 0,                        # 允许的最大误差.更小的将需要更长的时间来计算
                'spacing': settings.SPACING,                # 积木块间的间隔
                'rotations': settings.ROTATIONS,            # 旋转的颗粒度，360°的n份，如：4 = [0, 90 ,180, 270]
                'populationSize': settings.POPULATION_SIZE, # 基因群数量
                'mutationRate': settings.MUTA_RATE,         # 变异概率
                'useHoles': False,                          # 是否有洞，暂时都是没有洞
                'exploreConcave': False                     # 寻找凹面，暂时是否
            }
    container = None
    container_bounds=None
    nfp_cache = {} 




class Nester:
    """主要的打包模块,控制着打包过程
    """
    def __init__(self, container=None, shapes=None):
        
        self.originalshapes=[]
        self.container = container  # 打包容器
        self.shapes = shapes        # 积木块形状信息
        self.shapes_total_area=None
        #self.shapes_max_length = 0 # 在无限长的布
        self.results = list()       # storage for the different results
        self.nfp_cache = {}         # 缓存中间计算结果

        # 遗传算法的参数
        self.config = ThisClass.config
        self.GA = None              # 遗传算法
        self.best = None            # 记录最佳结果
        self.worker = None          # 根据NFP结果，计算每个图形的转移数据
        self.container_bounds = None # 容器的最小包络矩形作为输出图的坐标

    def add_objects(self, objects,objects_str):
        """加载形状

        Args:
            objects (list): 形状信息
            objects_str (str): 因为打分程序要求输入点的顺序不能改变,使用它来存储这一信息
        """
        if not isinstance(objects, list):
            objects = [objects]
        if not self.shapes:
            self.shapes = []

        self.originalshapes=objects_str
        p_id = 0
        total_area = 0
        for obj in objects:
            points = self.clean_polygon(obj)
            shape = {
                'area': 0,
                'p_id': str(p_id),
                'points': [{'x': p[0], 'y': p[1]} for p in points]
            }
            # 确定多边形的线段方向
            area = nfp_utls.polygon_area(shape['points'])
            if area > 0:
                shape['points'].reverse()

            shape['area'] = abs(area)
            total_area += shape['area']
            self.shapes.append(shape)

        #积木形状总面积
        self.shapes_total_area=total_area

        # 如果是一般布，需要这个尺寸
        #self.shapes_max_length = math.sqrt(total_area) 

    def add_container(self, container):
        """加载容器

        Args:
            container (dict): 容器
        """
        if not self.container:
            self.container = {}

        self.origin_container=container

        container = self.clean_polygon(container)

        self.container['points'] = [{'x': p[0], 'y':p[1]} for p in container]
        self.container['p_id'] = '-1'
        xbinmax = self.container['points'][0]['x']
        xbinmin = self.container['points'][0]['x']
        ybinmax = self.container['points'][0]['y']
        ybinmin = self.container['points'][0]['y']

        for point in self.container['points']:
            if point['x'] > xbinmax:
                xbinmax = point['x']
            elif point['x'] < xbinmin:
                xbinmin = point['x']
            if point['y'] > ybinmax:
                ybinmax = point['y']
            elif point['y'] < ybinmin:
                ybinmin = point['y']

        self.container['width'] = xbinmax - xbinmin
        self.container['height'] = ybinmax - ybinmin

        # 最小包络多边形
        self.container_bounds = nfp_utls.get_polygon_bounds(self.container['points'])

        #添加完容器后计算积木块与容器之间,积木块之间的NFP
        self.calculateNFP()

 
    def calculateNFP(self):
        """计算NFP
        """
        #self.nfp_cache     #Nest的NFP缓存
        nfp_pairs = []      #待计算列表
        new_cache = {}      #NFP缓存 
        place_list=copy.deepcopy(self.shapes)
        #print(place_list)
        
        for i in range(0, len(place_list)):
            # 容器和图形的内切多边形计算
            part = place_list[i]
            key = {
                'A': '-1',
                'B': str(i), #TODO:检查 应该是B在数据集中的顺序
                'inside': True,
                'A_rotation': 0,
                'B_rotation': 0
            }
            tmp_json_key = json.dumps(key)
            if not tmp_json_key in self.nfp_cache: #如果不在NEST缓存中就加入待计算列表
                nfp_pairs.append({
                    'A': self.container,
                    'B': part, # {'area': 169.0, 'p_id': '0', 'points': [{'x': 165, 'y': 233}, {'x': 152, 'y': 233}, {'x': 152, 'y': 220}, {'x': 165, 'y': 220}]}
                    'key': key 
                })
            # else: #如果在NEST缓存中,就将其提取出来放到new_cache中,等下用于替换NEST缓存,这样nest缓存中的nfp更可能用到
            #     # 万年用不到的NEST NFP缓存就丢弃
            #     new_cache[tmp_json_key] = self.nfp_cache[tmp_json_key]
            
            # 图形与图形之间的外切多边形计算
            for j in range(0, len(place_list)):
                placed = place_list[j]
                key = {
                    'A': str(j),
                    'B': str(i),
                    'inside': False,
                    'A_rotation': 0,
                    'B_rotation': 0
                }
                tmp_json_key = json.dumps(key)
                if not tmp_json_key in self.nfp_cache:
                    nfp_pairs.append({
                        'A': placed,
                        'B': part,
                        'key': key
                    })
                # else:
                #     new_cache[tmp_json_key] = self.nfp_cache[tmp_json_key]
        
        #不删除旧NFP
        #self.nfp_cache = new_cache


        
        # 计算所有图形两两组合的相切多边形（NFP）             
        # from tool.calculate_npf import NFP_Calculater
        # nfp_calculater=NFP_Calculater(self.config)
        # pair_list = []
        # for pair in nfp_pairs: #计算待计算NFP
        #     pair_list.append(nfp_calculater.process_nfp(pair))

        #**********批量计算nfp***************************************************#
        from main import batchNFPCalculate
        pair_list=batchNFPCalculate(self.nWorker,nfp_pairs)
        #***********************************************************************#

        #print(pair_list)
        
        #将待计算列表计算出的nfp添加到cache中
        if pair_list:
            for i in range(0, len(pair_list)):
                if pair_list[i]:#{'key': pair['key'], 'value': nfp}
                    key = json.dumps(pair_list[i]['key'])
                    self.nfp_cache[key] = pair_list[i]['value']#{"pair['key']":nfp}
                    
        #计算结束.计算结果在self.nfp_cache中
        #print("nfp",self.nfp_cache)
        #print("计算NFP结束")
        #向子线程发送缓存和容器
        from main import batchSendContainerAndNFPCache
        batchSendContainerAndNFPCache(self.nWorker,self.container,self.nfp_cache)

    def polygon_offset(self, polygon, offset):
        """偏移多边形

        Args:
            polygon (list): 多边形
            offset ([type]): 偏移量

        Returns:
            list: 偏移后的图形
        """
        is_list = True
        if isinstance(polygon[0], dict):
            polygon = [[p['x'], p['y']] for p in polygon]
            is_list = False

        miter_limit = 2
        co = pyclipper.PyclipperOffset(miter_limit, self.config['curveTolerance'])
        co.AddPath(polygon, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
        result = co.Execute(1*offset)
        if not is_list:
            result = [{'x': p[0], 'y':p[1]} for p in result[0]]
        return result

    def clear(self):
        """从打包模块中清除所有多边形
        """
        self.shapes = None

    def run(self):
        """
        运行打包操作
        如果开多线程，可以在这里设计检查中断信号
        """
        
        if self.GA is None:
            faces = list()
            for i in range(0, len(self.shapes)):
                shape = copy.deepcopy(self.shapes[i])
                shape['points'] = self.polygon_offset(shape['points'], self.config['spacing'])
                faces.append([str(i), shape])

            # 按面积排序
            faces = sorted(faces, reverse=True, key=lambda face: face[1]['area'])

            #TODO:施工
            #按复杂度分类,重新排
            if settings.COMPLEX_FIRST_STRATEGY:
                do1=True
                do2=False
                do3=False
            elif settings.COMPLEX_FIRST_AREA_SECOND_STRATEGY:
                do1=True
                do2=True
                do3=False
            elif settings.MIXED_COMPLEX_STRATEGY:
                do1=True
                do2=False
                do3=True
            if do1:
                list_Dio=[]
                list_L=[]
                list_Square=[]
                for item in faces:
                    if len(item[1]["points"])>6:
                        list_Dio.append(item)
                    elif len(item[1]["points"])==6:
                        list_L.append(item)
                    else:
                        list_Square.append(item)
                if do2:
                    percent=0.9
                    BigDio=list_Dio[0:int(len(list_Dio)*percent)]
                    SmallDio=list_Dio[int(len(list_Dio)*percent):]
                    BigL=list_L[0:int(len(list_L)*percent)]
                    SmallL=list_L[int(len(list_L)*percent):]
                    BigS=list_Square[0:int(len(list_Square)*percent)]
                    SmallS=list_Square[int(len(list_Square)*percent):]
                    faces=BigDio+BigL+BigS+SmallDio+SmallL+SmallS
                elif do3:
                    percent=0.5
                    SmallS=list_Square[int(len(list_Square)*percent):]
                    BigS=list_Square[0:int(len(list_Square)*percent)]
                    Mixed=list_Dio+list_L+BigS
                    Mixed=sorted(Mixed, reverse=True, key=lambda Mixed: Mixed[1]['area'])
                    print(Mixed)
                    print("****")
                    print(SmallS)
                    faces=Mixed+SmallS
                else:
                    faces=list_Dio+list_L+list_Square
            self.launch_workers(faces)
        else:
            self.launch_workers()
    
    def launch_workers(self, adam=None):
        """
        主过程，根据生成的基因组，求适应值，找最佳结果

        Args:
            adam (list, optional): 初始个体. Defaults to None.
        """
        if self.GA is None:
            offset_bin = copy.deepcopy(self.container)
            offset_bin['points'] = self.polygon_offset(self.container['points'], self.config['spacing'])
            self.GA = genetic_algorithm(adam, offset_bin, self.config)
        else:
            self.GA.generation()

        # 计算每一组基因的适应值
        # for i in range(0, self.GA.config['populationSize']):
        #     res = self.find_fitness(self.GA.population[i])
        #     self.GA.population[i]['fitness'] = res['fitness']
        #     self.results.append(res)

        from main import batchMpiEval
        self.results=batchMpiEval(self.nWorker,self.GA.population)
        for i in range(0, self.GA.config['populationSize']):
            self.GA.population[i]['fitness'] = self.results[i]['fitness']

        # 找最佳结果
        if len(self.results) > 0:
            best_result = self.results[0]

            for p in self.results:
                if p['fitness'] < best_result['fitness']:
                    best_result = p

            if self.best is None or best_result['fitness'] < self.best['fitness']:
                self.best = best_result

        #self.results [{'placements': all_placements, 'fitness': fitness,'min_width':min_width, 'paths': paths, 'area': bin_area}]
        #精英 self.best
        #print(self.best)

    def clean_polygon(self, polygon):
        """清多边形

        Args:
            polygon ([type]): [description]

        Returns:
            [type]: [description]
        """
        simple = pyclipper.SimplifyPolygon(polygon, pyclipper.PFT_NONZERO)

        if simple is None or len(simple) == 0:
            return None

        biggest = simple[0]
        biggest_area = pyclipper.Area(biggest)
        for i in range(1, len(simple)):
            area = abs(pyclipper.Area(simple[i]))
            if area > biggest_area:
                biggest = simple[i]
                biggest_area = area

        clean = pyclipper.CleanPolygon(biggest, self.config['curveTolerance'])
        if clean is None or len(clean) == 0:
            return None
        return clean


from tools.calculate_npf import NFP_Calculater
def find_fitness(individual,container,nfp_cache):
    """
    求解适应值

    Args:
        individual (dict): 个体
        container (dict): 容器
        nfp_cache (dict): nfp缓存

    Returns:
        dict: 评估结果
    """
    place_list = copy.deepcopy(individual['placement'])
    rotations = copy.deepcopy(individual['rotation'])
    ids = [p[0] for p in place_list]

    for i in range(0, len(place_list)):
        place_list[i].append(rotations[i])
    

    nfp_pairs = list()
    for i in range(0, len(place_list)):
        # 容器和图形的内切多边形计算
        part = place_list[i]
        key = {
            'A': '-1',
            'B': part[0],
            'inside': True,
            'A_rotation': 0,
            'B_rotation': rotations[i]
        }

        tmp_json_key = json.dumps(key)
        if not tmp_json_key in nfp_cache:
            nfp_pairs.append({
                'A': container,
                'B': part[1],
                'key': key
            })


        # 图形与图形之间的外切多边形计算
        for j in range(0, i):
            placed = place_list[j]
            key = {
                'A': placed[0],
                'B': part[0],
                'inside': False,
                'A_rotation': rotations[j],
                'B_rotation': rotations[i]
            }
            tmp_json_key = json.dumps(key)
            if not tmp_json_key in nfp_cache:
                nfp_pairs.append({
                    'A': placed[1],
                    'B': part[1],
                    'key': key
                })
    pair_list = list()
    for pair in nfp_pairs:
        pair_list.append(NFP_Calculater.process_nfp(pair))
    if pair_list:
        for i in range(0, len(pair_list)):
            if pair_list[i]:#{'key': pair['key'], 'value': nfp}
                key = json.dumps(pair_list[i]['key'])
                nfp_cache[key] = pair_list[i]['value']#{"pair['key']":nfp}

    worker = placement_worker.PlacementWorker(
            container, place_list, ids, rotations, ThisClass.config, nfp_cache)
    result=worker.place_paths()
    return result

def draw_result(shift_data, polygons,polygons_str, bin_polygon, bin_bounds,file_path,file_id):
    """从结果中得到平移旋转的数据，把原始图像移到到目标地方，然后保存结果
    """
    def myrotate_polygon(contour, angle):
        rotated = []
        #angle = angle * math.pi / 180
        if angle==0:
            cosangle=1
            sinangle=0
        elif angle==90:
            cosangle=0
            sinangle=1
        elif angle==180:
            cosangle=-1
            sinangle=0
        elif angle==270:
            cosangle=0
            sinangle=-1
        for x,y in contour:
            rotated.append([
                x *cosangle - y * sinangle,
                x * sinangle + y *cosangle
            ])
        return Polygon(rotated)

    # 生产多边形类
    #print(polygons)
    shapes = list()
    for polygon in polygons:
        contour = [[p['x'], p['y']] for p in polygon['points']]
        shapes.append(Polygon(contour))

    bin_shape = Polygon([[p['x'], p['y']] for p in bin_polygon['points']])
    
    shape_area = bin_shape.area(0)

    solution = list()
    rates = list()
    #loops=1
    #print(shift_data)
    shapes_before=copy.deepcopy(shapes)
    for s_data in shift_data:
        #print(loops)
        #loops=loops+1
        # 一个循环代表一个容器的排版
        tmp_bin = list()
        total_area = 0.0
        for move_step in s_data:
            if move_step['rotation'] > 0:#改为大于0
                # 坐标原点旋转
                #print("before",[p for p in shapes[int(move_step['p_id'])].contour(0)])
                #shapes[int(move_step['p_id'])].rotate(math.pi / 180 * move_step['rotation'], 0, 0)
                shapes[int(move_step['p_id'])]= myrotate_polygon(shapes[int(move_step['p_id'])].contour(0),move_step['rotation'])   
                #print("after",[p for p in shapes[int(move_step['p_id'])].contour(0)])
                #shapes[int(move_step['p_id'])]=  shapes[int(move_step['p_id'])]
            # 平移
            shapes[int(move_step['p_id'])].shift(move_step['x'], move_step['y'])
            tmp_bin.append(shapes[int(move_step['p_id'])])
            total_area += shapes[int(move_step['p_id'])].area(0)
            #print("total_area",total_area)
        # 当前排版总面积
        rates.append(total_area)
        solution.append(tmp_bin)
    # 显示结果
    idx=0
    myresult=""
    max_x=0
    max_y=0
    while(idx<len(shapes)):
        inpolygon= polygons_str[idx]
        # inpolygon=""
        # for x,y in shapes_before[idx].contour(0):
        #     inpolygon=inpolygon+"({x},{y})".format(x=x/SCALE,y=y/SCALE)
        outpolygon=""
        for x,y in shapes[idx].contour(0):
            if x>max_x:max_x=x 
            if y>max_y:max_y=y
            outpolygon=outpolygon+"({x},{y})".format(x=x/settings.SCALE,y=y/settings.SCALE)
        text=\
"""In Polygon:
{inpolygon}
Out Polygon:
{outpolygon}\n""".format(inpolygon=inpolygon,outpolygon=outpolygon)
        myresult=myresult+text
        idx=idx+1
    myresult=myresult.rstrip("\n")
    result_file=file_path+"/result_"+file_id+".txt"
    # import os
    # if os.path.exists(file_path+"/result.txt"):
    #     i=1 
    #     flag=1
    #     while flag:
    #         if os.path.exists(file_path+"/result_"+str(i)+".txt"):
    #             i=i+1
    #             continue
    #         result_file=file_path+"/result_"+str(i)+".txt"
    #         flag=0
    with open(result_file,"w")as file_hand:
        file_hand.write(myresult)
    if settings.DEBUG:
        print("polygon total area:",rates[-1]/(settings.SCALE*settings.SCALE))
        print("bin:",max_x/10,max_y/10)
        print("occupation:",rates[-1]/(max_x*max_y))
    if settings.DRAWPIC:
        draw_polygon(solution, rates, bin_bounds, bin_shape,max_x,max_y,rates[-1]/(max_x*max_y))


def draw_polygon(solution, rates, bin_bounds, bin_shape,packed_x,packed_y,occupation):
    """绘制多边形

    Args:
        solution (dict): 解决方案
        rates (list): rates
        bin_bounds (dict): 容器边界
        bin_shape (dict): 容器
        packed_x (float): 打包后最大的x
        packed_y (float): 打包后最大的y
        occupation (float): 占用率
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    base_width = 8
    base_height = base_width * bin_bounds['height'] / bin_bounds['width']
    num_bin = len(solution)
    fig_height = num_bin * base_height
    # fig1 = Figure(figsize=(base_width, fig_height))
    # FigureCanvas(fig1)
    fig1 = plt.figure(figsize=(base_width, fig_height))
    fig1.suptitle('Polygon packing', fontweight='bold')

    i_pic = 1  # 记录图片的索引
    for shapes in solution:
        # 坐标设置
        ax = plt.subplot(num_bin, 1, i_pic, aspect='equal')
        # ax = fig1.set_subplot(num_bin, 1, i_pic, aspect='equal')
        #ax.set_title('Num %d bin, rate is %0.4f' % (i_pic, rates[i_pic-1]))
        ax.set_title('%0.4f,%0.4f,%0.4f'%(packed_x,packed_y,occupation))
        i_pic += 1
        ax.set_xlim(bin_bounds['x'] - 10, bin_bounds['width'] + 50)
        ax.set_ylim(bin_bounds['y'] - 10, bin_bounds['height'] + 50)

        output_obj = list()
        output_obj.append(patches.Polygon(bin_shape.contour(0),fc="white"))
        output_obj.append(patches.Polygon([(0,0),(packed_x,0),(packed_x,packed_y),(0,packed_y)],lw=1,edgecolor='m'))
        #output_obj.append(patches.Polygon(bin_shape.contour(0), fc='green'))
        for s in shapes:
            color=[random.random(),random.random(),random.random()]
            output_obj.append(patches.Polygon(s.contour(0),color=color,alpha=0.5))

            #output_obj.append(patches.Polygon(s.contour(0), fc='yellow', lw=1, edgecolor='m'))
        for p in output_obj:
            ax.add_patch(p)
    plt.show()
    # fig1.save()

def content_loop_rate(best, n,file_path,file_id, loop_time=20,height=100):
    """固定迭代次数

    Args:
        best (dict): 最优良的个体
        n (NEST): 打包者
        file_path (str): 保存路径
        file_id (str): 文件id
        loop_time (int, optional): 迭代次数. Defaults to 20.
        height (int, optional): 默认高度. Defaults to 100.
    """
    print("STOP_GENERATION",settings.STOP_GENERATION)
    res = best
    run_time = loop_time
    loops=1
    if settings.DEBUG:
        import time
        current_time=time.time()
        last_time=current_time
        generation_time=[]
        best_fitness_for_all_generation=[]
        best_fitness_for_current_generation=[]
        square_like_for_all_generation=[]
        square_like_for_current_generation=[]
    while run_time:
        #print("content_loop_rate",loops)
        loops=loops+1
        n.run()
        best = n.best
        #print (best['fitness'])
        if best['fitness'] <= res['fitness']:
            res = best
            #print ('change', res['fitness'])
 
        #################各代个体的评估结果############################
        #self.results [{'placements': all_placements, 'fitness': fitness,'min_width':min_width, 'paths': paths, 'area': bin_area}]
        #精英 self.best
        if settings.DEBUG:
            current_time=time.time()
            generation_time.append(10*(current_time-last_time))
            last_time=current_time
            best_fitness_for_all_generation.append(res['fitness'])
            best_fitness_for_current_generation.append(best['fitness'])
            square_like_for_all_generation.append(res['min_width']/height)
            square_like_for_current_generation.append(best['min_width']/height)
        ####################################################

        run_time -= 1

        #TODO:改 
        if n.shapes_total_area/(best['min_width']*settings.BIN_NORMAL[2][1])>settings.SMALLCASE_EXPECTATION:
            #print("***",n.shapes_total_area/(best['min_width']*settings.BIN_NORMAL[2][1]))
            #print(n.shapes_total_area,best['min_width'],settings.BIN_NORMAL[2][1])
            run_time=False

    if settings.DEBUG:
        print("best_fitness_for_all_generation",best_fitness_for_all_generation)
    if settings.DRAWPIC:
        from matplotlib import pyplot as plt
        from matplotlib.pyplot import MultipleLocator

        x = range(1,len(best_fitness_for_all_generation)+1)       

        plt.grid(axis='x',color='0.95')
        plt.step(x,best_fitness_for_all_generation, label="best_fitness_for_all_generation",color='red',marker='^')
        plt.step(x,best_fitness_for_current_generation, label="best_fitness_for_current_generation",color='blue')
        plt.xlabel('generation')
        plt.ylabel('fitness',color='b')
        #ax.legend()
        #x_major_locator=MultipleLocator(1)
        #ax.xaxis.set_major_locator(x_major_locator) #设置x轴尺度

        plt.figure(2)
        plt.step(x,square_like_for_all_generation, label="square_like_for_all_generation",linestyle="--",color='red',marker='^')
        plt.step(x,square_like_for_current_generation, label="square_like_for_current_generation",linestyle="--",color='blue')
        plt.xlabel('generation')
        plt.ylabel('square_like',color='r')
        plt.title('Sample Run')

        plt.figure(3)
        plt.bar(x, generation_time, color='rgb', tick_label=x)

    draw_result(res['placements'], n.shapes,n.originalshapes, n.container, n.container_bounds,file_path,file_id)

