# -*- encoding: utf-8 -*-
'''
@File    :   setting.py
@Time    :   2020/11/19 19:16:36
@Author  :   KingofCode 
@Version :   1.0
@Contact :   mrlution@qq.com
@Desc    :   程序运行参数
'''
# here put the import lib
import platform

class Settings:
    DEBUG=True #开发模式

    #自动选择操作系统
    SysOS=platform.system()
    if SysOS == "Windows":
        LINUXOS=False #windows OS
        DRAWPIC=True #是否绘图
        NWORKER=4 # 线程数目
    else:
        LINUXOS=True #Linux OS
        DRAWPIC=False #勿改动 linux服务器不绘图
        NWORKER=31 #勿改动

    #遗传算法参数
    POPULATION_SIZE = 31  # 基因组数
    MUTA_RATE = 10       # 变异概率

    #初始容器参数
    USE_FORMULA=True
    SQRT_LENTH_SCALE=1.2 #容器高度BIN_HEIGHT为总面积乘以SQRT_LENTH_SCALE

    #中止条件
    STOP_GENERATION=1
    SMALLCASE_EXPECTATION=0.84

    #复杂度分类后按面积排序策略
    ORINGINAL_STRATEGY=False #为True时 图形不分类,从大到小排
    COMPLEX_FIRST_STRATEGY=True #为True时 分三类,每类从大到小排,一个类一个类排.
    COMPLEX_FIRST_AREA_SECOND_STRATEGY=False #为True复杂的大的先,不复杂的小的后,复杂的小的,不复杂的小的
    MIXED_COMPLEX_STRATEGY=False #为True时,分两类,每类从大到小排

    # Warning: 以下参数请勿改动
    # 容器尺寸 
    BIN_NORMAL = [[0, 0], [0, 1000], [2000, 1000], [2000, 0]]  #顺时针顺序      # 一般布是无限长
    SQRT_LENTH_SCALE2=2.0  #容器长度BIN_WIDTH为总面积乘以SQRT_LENTH_SCALE2  2是为了保证足够长
    SCALE=10.0
    SPACING = 0      # 图形间隔空间
    ROTATIONS = 4    # 旋转选择， 1： 不能旋转

settings=Settings()