# -*- encoding: utf-8 -*-
'''
@File    :   main.py
@Time    :   2020/11/19 18:30:11
@Author  :   KingofCode 
@Version :   1.0
@Contact :   mrlution@qq.com
@Desc    :   文件完成MPI的启动,配置初始化,数据集加载,启动打包过程
'''

# here put the import lib
from setting import settings
from nest import Nester
from nest import find_fitness
from tools.calculate_npf import NFP_Calculater
from tools import input_utls
import os
import sys
import time
import math
import argparse
import subprocess
import re

# MPI
from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()

def master(data):
    """主程序

    Args:
        data (str): 数据集路径
    """
    if settings.DEBUG:
        import time
        start_time = time.time()
    from nest import content_loop_rate

    n = Nester()
    global nWorker
    n.nWorker=nWorker

    file_path,file_name=os.path.split(data)
    if settings.LINUXOS:
        file_path="/home/eda20303/project/verify_results"
    file_id=re.findall("\d+",file_name)[0]

    #s = input_utls.input_polygon('tools/f6.dxf')
    shapes,shapes_str=input_utls.load_input_file(data)
    n.add_objects(shapes,shapes_str)
    nshapes=len(shapes)
    if settings.USE_FORMULA:
        if nshapes<10:
            settings.SQRT_LENTH_SCALE=1.1102
        elif nshapes>900:
            settings.SQRT_LENTH_SCALE=1.0645
        else:
            settings.SQRT_LENTH_SCALE=(-8.2175e-11)*(nshapes**3)+(1.9941e-07)*(nshapes**2)-(1.6552e-04)*nshapes+1.1118
            #settings.SQRT_LENTH_SCALE=(nshapes^3)*(-6.6730e-11)+(nshapes^2)*(2.0656e-07)+nshapes*(-2.0632e-04)+1.1292;
    if nshapes<=90:
        settings.STOP_GENERATION=10
    else:
        settings.STOP_GENERATION=1
        
    
    sqrt_lenth=math.sqrt(n.shapes_total_area)

    bin_width=sqrt_lenth*settings.SQRT_LENTH_SCALE
    
    if bin_width>300*settings.SCALE:
        bin_width=300*settings.SCALE
    
    settings.BIN_NORMAL[1][1] = bin_width    #y轴方向的BIN_HEIGHT #TODO:优化 重力方向为x轴负方向,所以要确定一个BIN_HEIGHT,使得打包后更像正方形
    settings.BIN_NORMAL[2][1] = bin_width     #TODO:优化 确定系数,我随便设置的0.8

    settings.BIN_NORMAL[2][0] = int(sqrt_lenth*settings.SQRT_LENTH_SCALE2)    #x轴方向的BIN_WIDTH 乘以2是为了保证所有的块都打包
    settings.BIN_NORMAL[3][0] = int(sqrt_lenth*settings.SQRT_LENTH_SCALE2)
    
    print(settings.BIN_NORMAL)
    # 选择面布
    n.add_container(settings.BIN_NORMAL)

    # 运行计算
    n.run()

    best = n.best

    # 循环特定次数
    content_loop_rate(best, n,file_path=file_path,file_id=file_id, loop_time=settings.STOP_GENERATION,height=settings.BIN_NORMAL[1][1])   # T7 , T4

    stopAllWorkers()

    if settings.DEBUG:
        end_time = time.time()
        print("run time:",end_time-start_time)

def batchMpiEval(nWorker,pop):
    """批量评估个体

    Args:
        nWorker (int): 工人数量
        pop (type):种群

    Returns:
        [int]: fitness
    """
    
    nSlave = nWorker-1
    nJobs = len(pop)
    nBatch= math.ceil(nJobs/nSlave) #将pop分成多少批

    reward =[]
    i = 0 
    for iBatch in range(nBatch): #对于每一批
        for iWork in range(nSlave): #对于每一个slave
            if i < nJobs:
                signal_type = i #个体的编号
                message   = pop[i]  #个体
                comm.send(signal_type, dest=(iWork)+1, tag=1) #发送个体编号
                comm.send(  message, dest=(iWork)+1, tag=2) #发送个体
            else: 
                signal_type = -1 
                comm.send(signal_type,  dest=(iWork)+1) #发送中止信号
            i = i+1 
        i -= nSlave
        for iWork in range(1,nSlave+1):
            if i < nJobs:
                workResult =comm.recv(source=iWork,tag=0) #TODO:complete 接收不到数据
                reward.append(workResult)
            i+=1
    return reward

def batchNFPCalculate(nWorker,nfp_pairs):
    """批量计算NFP

    Args:
        nWorker (int): 工人数量
        nfp_pairs (dict): 待计算nfp对

    Returns:
        list: NFP结果
    """
    nSlave = nWorker-1
    nJobs = len(nfp_pairs)
    nBatch= math.ceil(nJobs/nSlave) 

    pair_list =[]
    i = 0
    for iBatch in range(nBatch): #  对于每一批
        for iWork in range(nSlave): # 对于每一个slave
            if i < nJobs:
                signal_type = -3 #信号类型
                message   = nfp_pairs[i]  #待计算量
                comm.send(signal_type, dest=(iWork)+1, tag=1) #发送信号类型
                comm.send(  message, dest=(iWork)+1, tag=2) #发送待计算量
            #后续还要用worker,不终止
            i = i+1 
        i -= nSlave
        for iWork in range(1,nSlave+1):
            if i < nJobs:
                workResult =comm.recv(source=iWork,tag=0) #TODO:complete 接收不到数据
                pair_list.append(workResult)
            i+=1
    return pair_list

def batchSendContainerAndNFPCache(nWorker,origin_container,nfp_cache):
    """批量发送容器和NFP缓存

    Args:
        nWorker (int): 工人数目
        origin_container (dict): 初始容器
        nfp_cache (dict): nfp缓存
    """
    nSlave = nWorker-1
    nJobs = nSlave
    nBatch= math.ceil(nJobs/nSlave) 

    pair_list =[]
    i = 0 
    for iBatch in range(nBatch): 
        for iWork in range(nSlave):
            if i < nJobs:
                signal_type = -4 #信号类型
                message1 = origin_container  
                message2 = nfp_cache
                comm.send(signal_type, dest=(iWork)+1, tag=1) #发送信号类型
                comm.send(  message1, dest=(iWork)+1, tag=2) #发送待计算量
                comm.send(  message2, dest=(iWork)+1, tag=3) #发送待计算量
            #后续还要用worker,不终止
            i = i+1 

def slave():
    origin_container=None
    nfp_cache=None
    while True:
        signal_type = comm.recv(source=0,
                           tag=1)  #接收个体编号
        if signal_type >= 0: #不是中止信号
            message =comm.recv(source=0, tag=2)  # 接收个体
            result = find_fitness(message,origin_container,nfp_cache)  
            #print("rank:",rank,len(nfp_cache))
            comm.send(result, dest=0,tag=0)  # send it back 发送fitness结果 TODO:检查 个体的fitness和个体是不是一一对应
        elif signal_type==-3:#计算NFP
            pair =comm.recv(source=0, tag=2)
            result=NFP_Calculater.process_nfp(pair)
            comm.send(result, dest=0,tag=0) 
            
        elif signal_type==-4:
            origin_container=comm.recv(source=0, tag=2)
            nfp_cache=comm.recv(source=0,tag=3)
        if signal_type ==-1:  # End signal recieved
            # if settings.DEBUG:
            #     print('Worker # ', rank, ' shutting down.')
            break

def stopAllWorkers():
    """给所有工人发送停止信号
    """
    global nWorker
    nSlave = nWorker - 1
    #print('stopping workers')
    for iWork in range(nSlave):
        comm.send(-1, dest=(iWork) + 1, tag=1)

def mpi_fork(n):
    """重启进程

    Args:
        n (int): 核数

    Returns:
        str: 主为parent,子为children
    """ 
    if n <= 1:  #如果只有一个核，就直接跑任务
        return "child"
    if os.getenv("IN_MPI") is None:  #如果不止一个核，主进程启动mpi去并发执行，mpi中的儿子跑完后再回到这里
        env = os.environ.copy()
        env.update(MKL_NUM_THREADS="1", OMP_NUM_THREADS="1", IN_MPI="1") #MKL intel数学核心库MKL_NUM_THREADS，MKL_NUM_THREADS OpenMP是用于共享内存并行系统的预编译处理方案，OMP_NUM_THREADS是控制OpenMP并行线程数的标准环境变量
        # if settings.DEBUG:
        #     print("执行:",
        #         ["mpiexec", "-np", str(n), sys.executable] + sys.argv
        #     )  #['mpiexec', '-np', '9', 'C:\\Users\\Lution\\AppData\\Local\\Programs\\Python\\Python37\\python.exe', 'wann_train.py'] sys.executable Python解释程序路径  sys.argv 命令行参数List，第一个元素是程序本身路径
        if settings.LINUXOS:
            mpicmd="mpirun" 
            shellcmd=False
        else:
            mpicmd="mpiexec"
            shellcmd=True
        subprocess.check_call(
            [mpicmd, "-np", str(n), sys.executable] + ['-u'] + sys.argv,
            env=env,
            shell=shellcmd
        )  #shell=True 解决FileNotFoundError: [WinError 2] 系统找不到指定的文件。
        #主程序跑到上面这里，用mpi启动了好几个儿子去跑本程序，儿子看到父亲已经设好了环境变量IN_MPI标志，就都去跑下面的else，儿子全部跑完后才会执行下面的return "parent"，至此也就结束了
        return "parent"
    else:  #儿子们跑任务
        global nWorker, rank
        nWorker = comm.Get_size()  
        rank = comm.Get_rank() 
        #print(nWorker,rank)
        return "child"

def main(argv):
    """根据mpi rank执行对应的函数

    Args:
        argv (dict): 输入参数
    """
    if (rank == 0):
        master(argv.data)
    else:
        slave()

def run():
    """解析输入参数并启动
    """
    parser = argparse.ArgumentParser(description=('Evolve'))
    
    parser.add_argument('-d', '--data', type=str,\
    help='data file', default='data/polygon_area_etc_input_0.txt') #polygon_area_etc_input
    
    parser.add_argument('-n', '--num_worker', type=int,\
    help='number of cores to use', default=settings.NWORKER)
    
    args = parser.parse_args()

    if "parent" == mpi_fork(args.num_worker+1): os._exit(0)

    main(args)                              

if __name__ == "__main__":
    run()    

