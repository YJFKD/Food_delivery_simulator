import datetime
import time
import pandas as pd

from src.common.restaurant import Restaurant
from src.common.customer import Customer
from src.common.order import Order
from src.common.route import Map
from src.common.route import RouteInfo
from src.common.driver import Driver
from src.configuration.config import Configs
from src.utils.logging_engine import logger

def get_initial_data(data_file_path:str, driver_info_file_path:str, route_info_file_path:str,
                        customer_location_info_file_path:str, restaurant_location_info_file_path:str, initial_time:str):
    '''
    获取模拟器的输入数据, 包括订单, 骑手, 地图, 餐厅和顾客地点等
    Inputs:
    - data_file_path: 订单数据文件路径
    - driver_info_file_path: 车辆数据文件路径
    - route_info_file_path: 地图数据文件路径
    - customer_location_info_file_path: 顾客数据文件路径
    - restaurant_location_info_file_path: 餐厅数据文件路径
    - initial_time: unix timestampe, 开始时间
    Output:
    - id_to_order: Dict {id: Order object}
    - id_to_driver: Dict {id: Driver object}
    - id_to_customer_location: Dict {id: Customer object}
    - id_to_restaurant_location: Dict {id: Restaurant object}
    - route_map: Dict {code: RouteInfor object}
    '''
    # 获得餐厅和顾客地理信息
    id_to_customer_location = get_customer_info(customer_location_info_file_path)
    id_to_restaurant_location = get_restaurant_info(restaurant_location_info_file_path)
    id_to_location = {**id_to_customer_location, **id_to_restaurant_location}
    logger.info(f"Get {len(id_to_customer_location) + len(id_to_restaurant_location)} locations")
    
    # 获取地图信息
    code_to_route = get_route_map(route_info_file_path)
    logger.info(f"Get {len(code_to_route)} routes")
    route_map = Map(code_to_route)
    
    # 获取车辆信息
    id_to_driver = get_driver_info(driver_info_file_path)
    logger.info(f"Get {len(id_to_driver)} drivers")
    
    # 获取订单信息
    id_to_order = get_order_info(data_file_path, initial_time)
    logger.info(f"Get {len(id_to_order)} orders")
    
    return id_to_order, id_to_driver, route_map, id_to_restaurant_location, id_to_location


def get_customer_info(file_path: str):
    '''
    获取顾客信息
    '''
    df = pd.read_csv(file_path)
    id_to_customer = {}
    # 迭代读取每个顾客信息
    for index, row in df.iterrows():
        customer_id = str(row['customer_id'])
        lat = float(row['latitude'])
        lng = float(row['longitude'])
        customer = Customer(customer_id, lat, lng)
        if customer_id not in id_to_customer:
            id_to_customer[customer_id] = customer
    return id_to_customer


def get_restaurant_info(file_path: str):
    '''
    获取餐厅信息
    '''
    df = pd.read_csv(file_path)
    id_to_restaurant = {}
    # 迭代读取每个餐厅信息
    for index, row in df.iterrows():
        restaurant_id = str(row['restaurant_id'])
        lat = float(row['latitude'])
        lng = float(row['longitude'])
        dispatch_radius = int(row['dispatch_radius'])
        customer_radius = int(row['customer_radius'])
        wait_time = int(row['wait_time'])
        restaurant = Restaurant(restaurant_id, lat, lng, dispatch_radius, customer_radius, wait_time)
        if restaurant_id not in id_to_restaurant:
            id_to_restaurant[restaurant_id] = restaurant
    return id_to_restaurant


def get_order_info(file_path: str, ini_time: int):
    '''
    获取订单信息
    ['order_id', 'pickup_id', 'delivery_id', 'create_time', 'committed_completion_time', 'load_time', 'unload_time']
    Input:
    - file_path: 订单信息表
    - ini_time: 获得订单信息的时间
    '''
    order_df = pd.read_csv(file_path, dtype={'order_id': object}) # 避免丢失前几个为0的id信息
    
    id_to_order = {}
    for index, row in order_df.iterrows():
        # 读取每个订单信息
        order_id = str(row['order_id'])
        pickup_id = str(row['pickup_id']).strip()
        delivery_id = str(row['delivery_id']).strip()
        demand = float(row['demand'])
        load_time = int(row['load_time']) # restaurant pickup time
        unload_time = int(row['unload_time']) # customer delivery time
        
        # 开始的时间
        ini_datetime = datetime.datetime.fromtimestamp(ini_time)
        
        # 结合date和time
        creation_datetime = datetime.datetime.combine(
            ini_datetime.date(), datetime.datetime.strptime(row['creation_time'], '%H:%M:%S').time())
        creation_time = time.mktime(creation_datetime.timetuple())
        
        committed_completion_datetime = datetime.datetime.combine(
            ini_datetime.date(), datetime.datetime.strptime(row['committed_completion_time'], '%H:%M:%S').time())
        committed_completion_time = time.mktime(committed_completion_datetime.timetuple())
        
        # 不清楚其功能
        if committed_completion_time < creation_time:
            committed_completion_time += Configs.A_DAY_TIME_SECONDS
        
        order = Order(order_id, demand, order_restaurant_id=pickup_id, order_customer_id=delivery_id, 
                      creation_time=int(creation_time), committed_completion_time=int(committed_completion_time),
                      load_time=load_time, unload_time=unload_time)

        # 添加订单至id_to_order Dict
        if order_id not in id_to_order:
            id_to_order[order_id] = order

    return id_to_order


def get_route_map(file_path: str):
    '''
    获取路网信息, 路线的距离和时间
    ['route_code', 'start_location_id', 'end_location_id', 'distance', 'time']
    '''
    route_df = pd.read_csv(file_path)
    code_to_route = {}
    # 迭代读取路线信息
    for index, row in route_df.iterrows():
        route_code = str(row['route_code'])
        start_location_id = str(row['start_location_id'])
        end_location_id = str(row['end_location_id'])
        distance = float(row['distance'])
        transport_time = int(row['time'])
        route = RouteInfo(route_code, start_location_id, end_location_id, distance, transport_time)
        if route_code not in code_to_route:
            code_to_route[route_code] = route
    return code_to_route


def get_driver_info(file_path: str):
    '''
    获取骑手信息
    ['car_num', 'capacity', 'operation_time', 'gps_id']
    '''
    driver_df = pd.read_csv(file_path)
    id_to_driver = {}
    for index, row in driver_df.iterrows():
        car_num = str(row['car_num'])
        capacity = int(row['capacity'])
        operation_time = int(row['operation_time'])
        gps_id = str(row['gps_id'])
        driver = Driver(car_num, capacity, gps_id, operation_time)
        if car_num not in id_to_driver:
            id_to_driver[car_num] = driver
    return id_to_driver
    
    
    