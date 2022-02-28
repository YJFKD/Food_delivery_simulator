import datetime
import os
import sys
import time
from src.utils.json_tools import convert_node_to_json, write_json_to_file

from src.simulator.driver_simulator import DriverSimulator
from src.simulator.history import History
from src.common.dispatch_result import DispatchResult
from src.common.inform import InputInform
from src.configuration.config import Configs
from src.utils.logging_engine import logger

from src.utils.json_tools import convert_input_info_to_json_files
from src.utils.json_tools import get_output_of_algorithm
from src.utils.json_tools import subprocess_function, get_algorithm_calling_command
from src.utils.tools import get_orders_to_be_dispatched_of_cur_time
from src.utils.tools import get_order_list_of_drivers

from src.utils.checker import Checker
from src.utils.evaluator import Evaluator


class SimulateEnvironment(object):
    def __init__(self, initial_time: int, time_interval: int, id_to_order: dict, id_to_driver: dict,
                 id_to_location: dict, route_map):
        '''
        Inputs:
        initial_time: unix timestamp, unit is second
        time_interval: unit is second
        id_to_order: total orders
        id_to_driver: total drivers
        id_to_location: total locations (customer + restaurant)
        route_map: map of route
        '''
        self.initial_time = initial_time
        self.time_interval = time_interval
        self.cur_time = initial_time
        self.pre_time = initial_time

        # order, driver, location, route map
        self.id_to_order = id_to_order
        self.id_to_driver = id_to_driver
        self.id_to_location = id_to_location
        self.route_map = route_map

        # order type with different state
        self.id_to_generated_order = {}
        self.id_to_ongoing_order = {}
        self.id_to_completed_order = {}

        # driver simulator
        self.driver_simulator = DriverSimulator(route_map, id_to_location)

        # dispatch result for each time interval
        self.time_to_dispatch_result = {}

        # 保存每个骑手服务过的node, evaluation可以用
        self.history = self.__ini_history()

        # 目标函数
        self.total_score = sys.maxsize

        # 算法调用命令
        self.algorithm_calling_command = ''
    
    
    def __ini_history(self):
        '''
        初始化history, 记录每个骑手和订单的初始化信息
        '''
        history = History()
        # initialize the history of drivers and orders
        for driver_id, driver in self.id_to_driver.items():
            history.add_driver_position_history(driver_id, driver.gps_update_time, driver.current_location_id)
        for order_id, order in self.id_to_order.items():
            history.add_order_status_history(order.delivery_state, self.initial_time, order.committed_completion_time, order_id)

        return history

    
    # simulation
    def run(self):
        used_seconds = 0
        # 迭代
        while True:
            logger.info(f"{'*' * 50}")
            
            # 确定当前时间, 取算法执行时间和模拟器的切片时间的大值
            self.cur_time = self.pre_time + (used_seconds // self.time_interval + 1) * self.time_interval
            logger.info(f"cur time: {datetime.datetime.fromtimestamp(self.cur_time)}, "
                        f"pre time: {datetime.datetime.fromtimestamp(self.pre_time)}")
            
            # 更新时间段内的骑手信息和订单信息 [self.pre_time, self.cur_time]
            updated_input_info = self.update_input()
            
            # 派单环节, 设计与算法交互
            used_seconds, dispatch_result = self.dispatch(updated_input_info)
            self.time_to_dispatch_result[self.cur_time] = dispatch_result
            logger.info("Finish the dispatch.")
            
            # 校验, 车辆目的地不能改变
            if not Checker.check_dispatch_result(dispatch_result, self.id_to_driver, self.id_to_order, self.id_to_location):
                logger.error("Dispatch result is infeasible")
                return
            
            # 根据派单指令更新车辆
            self.deliver_control_command_to_drivers(dispatch_result)
            
            # 判断是否完成所有订单的派发
            if self.complete_the_dispatch_of_all_orders():
                break
            
            self.pre_time = self.cur_time
            
            # 若订单已经超时, 但是算法依旧未分配, 模拟终止
            if self.ignore_allocating_timeout_orders(dispatch_result):
                logger.error('Simulator terminated')
                sys.exit(-1)
            
            # 模拟完成车辆剩下的订单
        self.simulate_the_left_ongoing_orders_of_drivers(self.id_to_driver)

        logger.info("finished the left ongoing orders")
            
        # 根据self.history 计算指标
        self.total_score = Evaluator.calculate_total_score(self.history, self.route_map, len(self.id_to_driver))   
        
        # 输出骑手的历史路线和订单的历史状态
        write_json_to_file(Configs.algorithm_output_driver_node_history_path, self.history.get_driver_position_history()) 
        write_json_to_file(Configs.algorithm_output_order_update_history_path, self.history.get_order_status_history()) 
        
        # 单独输出订单的历史状态
        order_update_history = f"{Configs.root_folder_path}/Order_update_history/Instance_"\
                               f"{len(self.id_to_order)}o_{len(self.id_to_driver)}d_{len(self.id_to_location)}l.json"
        write_json_to_file(order_update_history, self.history.get_order_status_history()) 
        
    
    def update_input(self):
        '''
        更新骑手和订单信息
        '''
        logger.info(f"Start to update the input of {datetime.datetime.fromtimestamp(self.cur_time)}")
        
        # 获取车辆位置信息和订单状态
        self.driver_simulator.run(self.id_to_driver, self.pre_time)
        self.driver_simulator.parse_simulation_result(self.id_to_driver, self.cur_time)

        # 增加车辆和订单历史记录
        self.history.add_history_of_drivers(self.id_to_driver, self.cur_time)
        self.history.add_history_of_orders(self.id_to_driver, self.cur_time)
        
        # 更新订单状态和车辆状态
        self.update_status_of_orders(self.driver_simulator.completed_order_ids, self.driver_simulator.ongoing_order_ids)
        self.update_status_of_drivers(self.driver_simulator.driver_id_to_cur_position_info,
                                      self.driver_simulator.driver_id_to_destination,
                                      self.driver_simulator.driver_id_to_carrying_orders)
        
        # 当前时间待分配的订单集合
        self.id_to_generated_order = get_orders_to_be_dispatched_of_cur_time(self.id_to_order, self.cur_time)
        
        
        # 汇总骑手，订单和路网信息，作为派单算法的输入
        updated_input_info = InputInform(self.id_to_generated_order,
                                         self.id_to_ongoing_order,
                                         self.id_to_driver,
                                         self.id_to_location,
                                         self.route_map)

        # 打印更新结果
        logger.info(f"Get {len(self.id_to_generated_order)} unallocated orders, "
                    f"{len(self.id_to_ongoing_order)} ongoing orders, "
                    f"{len(self.id_to_completed_order)} completed orders.")
        
        return updated_input_info
    
    
    def update_status_of_orders(self, completed_order_ids, ongoing_order_ids):
        '''
        更新订单状态
        '''
        # 对已经完成的订单
        for order_id in completed_order_ids:
            order = self.id_to_order.get(order_id)
            if order is not None:
                if order_id not in self.id_to_completed_order:
                    self.id_to_completed_order[order_id] = order
                    order.delivery_state = Configs.ORDER_STATUS_TO_CODE.get("COMPLETED")
        
        # 对正在配送中的订单 
        for order_id in ongoing_order_ids:
            order = self.id_to_order.get(order_id)
            if order is not None:
                if order_id not in self.id_to_ongoing_order:
                    self.id_to_ongoing_order[order_id] = order
                    order.delivery_state = Configs.ORDER_STATUS_TO_CODE.get("ONGOING")
        
        # 移除已经完成的的订单
        expired_order_id_list = []
        for order_id, order in self.id_to_ongoing_order.items():
            # 如果订单已经完成
            if order.delivery_state > Configs.ORDER_STATUS_TO_CODE.get("ONGOING"):
                expired_order_id_list.append(order_id)
        for order_id in expired_order_id_list:
            self.id_to_ongoing_order.pop(order_id)
        
    
    def update_status_of_drivers(self, driver_id_to_cur_position_info, driver_id_to_destination,
                                  driver_id_to_carrying_orders):
        '''
        更新每个骑手的状态: [位置，下一个目的地，订单]
        '''
        for driver_id, driver in self.id_to_driver.items():
            # 更新骑手的位置信息和到达，离开时间
            if driver_id in driver_id_to_cur_position_info:
                cur_position_info = driver_id_to_cur_position_info.get(driver_id)
                driver.set_cur_position_info(cur_position_info.get("current_location_id"),
                                            #  cur_position_info.get("current_coordinate"),
                                             cur_position_info.get("update_time"),
                                             cur_position_info.get("arrive_time_at_current_location"),
                                             cur_position_info.get("leave_time_at_current_location"))
            else:
                logger.error(f"Driver {driver_id} does not have updated position information")
            # 更新骑手下一个目的地   
            if driver_id in driver_id_to_destination:
                driver.destination = driver_id_to_destination.get(driver_id)
            else:
                logger.error(f"Driver {driver_id} does not have the destination information")    
            # 更新骑手正在运送的订单
            if driver_id in driver_id_to_carrying_orders:
                driver.carrying_orders = driver_id_to_carrying_orders.get(driver_id)
            else:
                logger.error(f"Driver {driver_id} does not have the information of carrying orders")

            driver.planned_route = []
    
    
    def dispatch(self, input_info):
        '''
        根据输入信息进行派单
        '''
        # 准备派单输入json文件
        convert_input_info_to_json_files(input_info)

        # 运行派单算法
        if not self.algorithm_calling_command:
            self.algorithm_calling_command = get_algorithm_calling_command()
        time_start_algorithm = time.time()
        used_seconds, message = subprocess_function(self.algorithm_calling_command)

        # 解析算法输出json文件
        if Configs.ALGORITHM_SUCCESS_FLAG in message:
            if (time_start_algorithm < os.stat(Configs.algorithm_output_destination_path).st_mtime < time.time()
                    and time_start_algorithm < os.stat(
                        Configs.algorithm_output_planned_route_path).st_mtime < time.time()):
                driver_id_to_destination, driver_id_to_planned_route, driver_id_to_entire_planned_route = get_output_of_algorithm(self.id_to_order)
                dispatch_result = DispatchResult(driver_id_to_destination, driver_id_to_planned_route, driver_id_to_entire_planned_route)
                return used_seconds, dispatch_result
            else:
                logger.error("Output_json files from the algorithm is not the newest.")
                sys.exit(-1)
        else:
            logger.error(message)
            logger.error("Can not catch the 'SUCCESS' from the algorithm.")
            sys.exit(-1)
    
    
    def complete_the_dispatch_of_all_orders(self):
        '''
        判断是否完成了所有订单的分配
        '''
        for order in self.id_to_order.values():
            if order.delivery_state <= 1:
                logger.info(f"{datetime.datetime.fromtimestamp(self.cur_time)}, Order {order.id}: "
                            f"state = {order.delivery_state} < 2, we can not finish the simulation")
                return False
        logger.info(f"{datetime.datetime.fromtimestamp(self.cur_time)}, the status of all orders is greater than 1, "
                    f"we could finish the simulation")
        return True
    
    
    def simulate_the_left_ongoing_orders_of_drivers(self, id_to_driver: dict):
        '''
        模拟剩余订单
        '''
        self.driver_simulator.run(id_to_driver, self.cur_time)
        self.history.add_history_of_drivers(self.id_to_driver)
        self.history.add_history_of_orders(self.id_to_driver)
    
    
    def deliver_control_command_to_drivers(self, dispatch_result):
        '''
        根据派单结果更新骑手信息
        '''
        driver_id_to_destination = dispatch_result.driver_id_to_destination
        driver_id_to_planned_route = dispatch_result.driver_id_to_planned_route

        for driver_id, driver in self.id_to_driver.items():
            if driver_id not in driver_id_to_destination:
                logger.error(f"algorithm does not output the destination of driver {driver_id}")
                continue
            if driver_id not in driver_id_to_planned_route:
                logger.error(f"algorithm does not output the planned route of driver {driver_id}")
                continue
            
            # update destination, planned route, loading and uploading, service time
            driver.destination = driver_id_to_destination.get(driver_id)
            if driver.destination is not None:
                driver.destination.update_service_time()
            driver.planned_route = driver_id_to_planned_route.get(driver_id)
            for node in driver.planned_route:
                if node is not None:
                    node.update_service_time()
    
    
    def ignore_allocating_timeout_orders(self, dispatch_result):
        '''
        检查当前是否有订单已经超时却依旧未分配
        '''
        driver_id_to_order_list = get_order_list_of_drivers(dispatch_result, self.id_to_driver)
        total_order_ids_in_dispatch_result = []
        
        for driver_id, order_list in driver_id_to_order_list.items():
            for order in order_list:
                if order.id not in total_order_ids_in_dispatch_result:
                    total_order_ids_in_dispatch_result.append(order.id)

        for order_id, order in self.id_to_generated_order.items():
            if order_id not in total_order_ids_in_dispatch_result:
                if order.committed_completion_time < self.cur_time:
                    logger.error(f"{datetime.datetime.fromtimestamp(self.cur_time)}, "
                                 f"Order {order_id}'s committed_completion_time is "
                                 f"{datetime.datetime.fromtimestamp(order.committed_completion_time)} "
                                 f"which has timed out, "
                                 f"however it is still ignored in the dispatch result.")
                    return True
        return False