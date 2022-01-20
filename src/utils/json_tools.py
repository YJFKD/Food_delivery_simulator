import json
import os
import platform
import subprocess
import sys
import time
from importlib import import_module

from src.common.node import Node
from src.common.driver import Driver
from src.configuration.config import Configs
from src.utils.logging_engine import logger


COMMON_CLASS = {'Driver': 'src.common.driver',
                'Order': 'src.common.order',
                'Node': 'src.common.node',
                'Customer': 'src.common.customer',
                'Restaurant': 'src.common.restaurant'
                }


def import_common_class(class_name):
    '''
    通过类的名称导入common类的数据结构
    '''
    module = import_module(COMMON_CLASS.get(class_name))
    return getattr(module, class_name)


""" Schedule the algorithm"""


def get_algorithm_calling_command():
    files = os.listdir(Configs.root_folder_path)
    for file in files:
        # 调度算法的入口文件必须以main_algorithm开头
        if file.startswith(Configs.ALGORITHM_ENTRY_FILE_NAME):
            end_name = file.split('.')[-1]
            algorithm_language = Configs.ALGORITHM_LANGUAGE_MAP.get(end_name)
            if algorithm_language == 'python':
                return 'python {}'.format(file)
            elif algorithm_language == 'java':
                return 'java {}'.format(file.split('.')[0])
            # c和c++调用方式一样，但系统不同调用方式有异
            elif algorithm_language == 'c':
                system = platform.system()
                if system == 'Windows':
                    return file
                elif system == 'Linux':
                    os.system(f'chmod 777 {file}')
                    return './{}'.format(file)
    logger.error('Can not find main_algorithm file.')
    sys.exit(-1)


# 开启进程，调用算法
def subprocess_function(cmd):
    # 开启子进程，并连接到它们的输入/输出/错误管道，获取返回值
    sub_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    try:
        start_time = time.time()
        # 设置超时
        sub_process.wait(Configs.MAX_RUNTIME_OF_ALGORITHM)
        end_time = time.time()
        # 返回算法运行时间和算法返回值
        return end_time - start_time, sub_process.stdout.read().decode()
    except Exception as e:
        logger.error(e)
        sys.exit(-1)


""" IO"""


def read_json_from_file(file_name):
    with open(file_name, 'r') as fd:
        data = fd.read()
    return json.loads(data)


def write_json_to_file(file_name, data):
    with open(file_name, 'w') as fd:
        fd.write(json.dumps(data, indent=4))



""" create the input of the algorithm (output json of simulation)"""


def convert_input_info_to_json_files(input_info):
    '''
    输出input_info数据到input.json
    '''
    driver_info_list = __get_driver_info_list(input_info.id_to_driver)
    write_json_to_file(Configs.algorithm_driver_input_info_path, driver_info_list)

    unallocated_orders = convert_dict_to_list(input_info.id_to_unallocated_order)
    write_json_to_file(Configs.algorithm_unallocated_orders_input_path, unallocated_orders)

    ongoing_orders = convert_dict_to_list(input_info.id_to_ongoing_order)
    write_json_to_file(Configs.algorithm_ongoing_orders_input_path, ongoing_orders)


def __get_driver_info_list(id_to_driver: dict):
    '''
    获取每个骑手的信息, 输出一个列表, 每个元素为一个python dict
    '''
    driver_info_list = []
    for driver_id, driver in id_to_driver.items():
        driver_info_list.append(__convert_driver_to_dict(driver))
    return driver_info_list


def __convert_driver_to_dict(driver):
    '''
    将driver对象转换成python dict对象
    '''
    carrying_orders = driver.carrying_orders

    driver_property = {
        "id": driver.id,
        "operation_time": driver.operation_time,
        "capacity": driver.capacity,
        "gps_id": driver.gps_id,
        "update_time": driver.gps_update_time,
        "current_location_id": driver.current_location_id,
        # "current_coordinate": driver.current_coordinate, # add
        "arrive_time_at_current_location": driver.arrive_time_at_current_location,
        "leave_time_at_current_location": driver.leave_time_at_current_location,
        "carrying_orders": [order.id for order in carrying_orders],
        "destination": __convert_destination_to_dict(driver.destination)
    }
    return driver_property


def __convert_destination_to_dict(destination):
    '''
    将destination(node对象)转换成python dict对象
    '''
    if destination is None:
        return None

    destination_property = {
        'location_id': destination.id,
        'delivery_order_list': [order.id for order in destination.delivery_orders],
        'pickup_order_list': [order.id for order in destination.pickup_orders],
        'arrive_time': destination.arrive_time,
        'leave_time': destination.leave_time}
    return destination_property


def convert_dict_to_list(_dict):
    '''
    实例的属性转数组
    '''
    _list = []
    for key, value in _dict.items():
        if hasattr(value, '__dict__'):
            d = value.__dict__
            _list.append({key: d[key] for key in d if "__" not in key})
    return _list


""" Read the input of the algorithm (read the output json of simulator)"""


def get_driver_instance_dict(driver_infos: list, id_to_order: dict, id_to_location: dict):
    '''
    从driver_infos中读取driver数据，添加到id_to_driver中
    Inputs:
    - driver_infos: __get_driver_info_list的输出，每个元素为一个driver的信息
    - id_to_order: {order_id: order object}
    - id_to_location: {location_id: node object}
    '''
    id_to_driver = {}
    
    for driver_info in driver_infos:
        # 获取骑手driver信息
        driver_id = driver_info.get("id")
        operation_time = driver_info.get("operation_time")
        capacity = driver_info.get("capacity")
        gps_id = driver_info.get("gps_id")
        carrying_order_id_list = driver_info.get("carrying_orders")
        carrying_orders = [id_to_order.get(order_id) for order_id in carrying_order_id_list
                          if order_id in carrying_order_id_list]
        
        destination = driver_info.get("destination")
        if destination is not None:
            destination = __get_destination(destination, id_to_location, id_to_order)

        current_location_id = driver_info.get("current_location_id")
        
        # current_coordinate = driver_info.get("current_coordinate") # add

        arrive_time_at_current_location = driver_info.get("arrive_time_at_current_location")
        leave_time_at_current_location = driver_info.get("leave_time_at_current_location")
        update_time = driver_info.get("update_time")

        logger.debug(f"Get driver {driver_id} instance from json, "
                     f"order id list = {len(carrying_order_id_list)},"
                     f"order list = {len(carrying_orders)}")
        
        # 添加新的骑手信息到id_to_driver dict中
        if driver_id not in id_to_driver:
            driver = Driver(driver_id, capacity, gps_id, operation_time, carrying_orders)
            driver.destination = destination
            driver.set_cur_position_info(current_location_id, update_time,
                                          arrive_time_at_current_location, leave_time_at_current_location)
            id_to_driver[driver_id] = driver
    
    return id_to_driver


def __get_destination(_dict, id_to_location: dict, id_to_order: dict):
    '''
    将destination dict转换成Node对象
    Inputs:
    - _dict: destination dict
    - id_location: {location_id: node object}
    - id_to_order: {order_id: order object}
    '''
    location_id = _dict.get("location_id")
    location = id_to_location.get(location_id)
    delivery_order_ids = _dict.get("delivery_order_list")
    delivery_orders = [id_to_order.get(order_id) for order_id in delivery_order_ids]
    pickup_order_ids = _dict.get("pickup_order_list")
    pickup_orders = [id_to_order.get(order_id) for order_id in pickup_order_ids]
    arr_time = _dict.get("arrive_time")
    leave_time = _dict.get("leave_time")
    
    return Node(location_id, location.lat, location.lng, pickup_orders, delivery_orders, arr_time, leave_time)


def get_order_dict(_order_list, class_name):
    '''
    获取order dict，value为order object
    Inputs:
    - _order_list: 订单列表，dict_list
    '''
    orders = convert_dicts_list_to_instances_list(_order_list, class_name)
    id_to_order = {}
    for order in orders:
        if order.id not in id_to_order:
            id_to_order[order.id] = order
    return id_to_order


def convert_dicts_list_to_instances_list(_dicts_list, class_name):
    '''
    字典列表转换为实例列表
    '''
    instances_list = []
    # 通过类名取导入类
    for _dict in _dicts_list:
        common_class = import_common_class(class_name)
        instance = common_class.__new__(common_class)
        instance.__dict__ = _dict
        instances_list.append(instance)
    return instances_list



def convert_nodes_to_json(driver_id_to_nodes):
    '''
    把Node实例属性转为可用于实例化的参数字典
    '''
    result_dict = {}
    for key, value in driver_id_to_nodes.items():
        if value is None:
            result_dict[key] = None
            continue

        # 字典的情况
        if hasattr(value, '__dict__'):
            result_dict[key] = convert_node_to_json(value)
        # 列表的情况
        elif not value:
            result_dict[key] = []
        elif value and isinstance(value, list) and hasattr(value[0], '__dict__'):
            result_dict[key] = [convert_node_to_json(node) for node in value]
    return result_dict


def convert_node_to_json(node):
    '''
    # 把node实例的属性转为可用于后续实例化的参数
    '''
    print(node.delivery_orders)
    node_property = {'location_id': node.id, 'lat': node.lat, 'lng': node.lng,
                     'delivery_order_list': [order.id for order in node.delivery_orders],
                     'pickup_order_list': [order.id for order in node.pickup_orders],
                     'arrive_time': node.arrive_time,
                     'leave_time': node.leave_time}
    return node_property



""" Read the output json files of the algorithm"""


def get_output_of_algorithm(id_to_order: dict):
    '''
    从output.json获取数据，并进行数据结构转换
    '''
    driver_id_to_destination_from_json = read_json_from_file(Configs.algorithm_output_destination_path)
    driver_id_to_destination = __convert_json_to_nodes(driver_id_to_destination_from_json, id_to_order)
    driver_id_to_planned_route_from_json = read_json_from_file(Configs.algorithm_output_planned_route_path)
    driver_id_to_planned_route = __convert_json_to_nodes(driver_id_to_planned_route_from_json, id_to_order)
    return driver_id_to_destination, driver_id_to_planned_route


def __convert_json_to_nodes(driver_id_to_nodes_from_json: dict, id_to_order: dict):
    result_dict = {}

    node_class = import_common_class('Node')
    for key, value in driver_id_to_nodes_from_json.items():
        if value is None:
            result_dict[key] = None
            continue
        if isinstance(value, dict):
            __get_order(value, id_to_order)
            # 传入参数创建新的Node实例
            result_dict[key] = Node(**value)
        elif not value:
            result_dict[key] = []
        elif isinstance(value, list):
            node_list = []
            for node in value:
                __get_order(node, id_to_order)
                node_list.append(node_class(**node))
            result_dict[key] = node_list
    return result_dict


def __get_order(node, id_to_order):
    '''
    通过order的id找到实例
    '''
    node['delivery_order_list'] = [id_to_order.get(order_id) for order_id in node['delivery_order_list']]
    node['pickup_order_list'] = [id_to_order.get(order_id) for order_id in node['pickup_order_list']]