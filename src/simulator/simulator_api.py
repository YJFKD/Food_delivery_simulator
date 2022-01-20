import datetime
import os
import random
import time
import traceback

from src.configuration.config import Configs
from src.simulator.simulator_env import SimulateEnvironment
from src.utils.input_utils import get_initial_data
from src.utils.logging_engine import logger


def __initialize(customer_info_file_name: str, restaurant_info_file_name:str, route_info_file_name: str, instance_folder: str):
    '''
    初始化模拟器
    location_info_file_name: 地点数据文件名, 包括餐厅和顾客地点
    route_info_file_name: 地图路线数据文件名
    instance_folder: 测试例对应的文件夹
    '''
    # 获取文件绝对路径
    route_info_file_path = os.path.join(Configs.benchmark_folder_path, route_info_file_name)
    customer_location_info_file_path = os.path.join(Configs.benchmark_folder_path, customer_info_file_name)
    restaurant_location_info_file_path = os.path.join(Configs.benchmark_folder_path, restaurant_info_file_name)
    instance_folder_path = os.path.join(Configs.benchmark_folder_path, instance_folder)
    
    # 骑手数据文件名
    driver_info_file_path = ""
    # 订单数据文件名
    data_file_path = ""
    
    for file_name in os.listdir(instance_folder_path):
        # 读取driver_info和data_file
        if file_name.startswith("driver"):
            driver_info_file_path = os.path.join(instance_folder_path, file_name)
        else:
            data_file_path = os.path.join(instance_folder_path, file_name)
    
    # 初始化时间
    now = datetime.datetime.now()
    initial_datetime = datetime.datetime(now.year, now.month, now.day, 6) # start from 6 AM
    initial_time = int(time.mktime(initial_datetime.timetuple()))
    time_interval = Configs.ALG_RUN_FREQUENCY * 60
    logger.info(f"Start time of the simulator: {initial_datetime}, time interval: {time_interval: .2f}")

    try:
        # 获取初始化数据, get_initial_data
        id_to_order, id_to_driver, route_map, id_to_restaurant_location, id_to_location = get_initial_data(data_file_path,
                                                                                driver_info_file_path,
                                                                                route_info_file_path,
                                                                                customer_location_info_file_path,
                                                                                restaurant_location_info_file_path,
                                                                                initial_time)
        # 初始化骑手位置
        __initial_position_of_drivers(id_to_restaurant_location, id_to_driver, initial_time)

        # return instance of the object SimulateEnvironment
        return SimulateEnvironment(initial_time, time_interval, id_to_order, id_to_driver, id_to_location, route_map)
    except Exception as exception:
        logger.error("Failed to read initial data")
        logger.error(f"Error: {exception}, {traceback.format_exc()}")
        return None


def __initial_position_of_drivers(id_to_restaurant: dict, id_to_driver: dict, ini_time: int):
    '''
    初始化骑手位置, 骑手初始化在各个餐厅
    Inputs:
    - id_to_locations
    '''
    restaurant_id_list = [*id_to_restaurant] # get the key of id_to_location
    random.seed(Configs.RANDOM_SEED)
    for driver_id, driver in id_to_driver.items():
        index = random.randint(0, len(restaurant_id_list) - 1)
        restaurant_id = restaurant_id_list[index]
        driver.set_cur_position_info(restaurant_id, ini_time, ini_time, ini_time)
        logger.info(f"Initial position of {driver_id} is {restaurant_id}")
    

def simulate(customer_info_file: str, restaurant_info_file: str, route_info_file: str, instance: str):
    '''
    运行模拟器
    '''
    simulate_env = __initialize(customer_info_file, restaurant_info_file, route_info_file, instance)
    if simulate_env is not None:
        # 模拟器仿真过程
        simulate_env.run()
    return simulate_env.total_score