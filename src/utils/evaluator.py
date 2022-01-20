import sys

from src.utils.logging_engine import logger
from src.configuration.config import Configs


class Evaluator(object):
    
    @staticmethod
    def calculate_total_score(history, route_map, driver_num: int):
        '''
        目标函数
        '''
        # 所有骑手的总行驶距离
        total_distance = Evaluator.calculate_total_distance(history.get_driver_position_history(), route_map)
        logger.info(f"Total distance: {total_distance: .3f}")
        
        # 所有骑手的总延误时间
        total_over_time = Evaluator.calculate_total_over_time(history.get_order_status_history())
        logger.info(f"Sum over time: {total_over_time: .3f}")
        
        # 最终分数
        total_score = total_distance / driver_num + total_over_time * Configs.LAMDA / 3600
        logger.info(f"Total score: {total_score: .3f}")
        return total_score
    
    
    @staticmethod
    def calculate_total_over_time(order_id_to_status_list: dict):
        '''
        计算所有订单总的延误
        Inputs:
        - order_id_to_status_list: dict, {order_id: status_info_list}, 
        output of history.get_order_status_history()
        status_info_list: list of order info
        [
            {"state": order_state,
            "update_time": update_time,
            "finished time": del_time,
            "order_id": order_id}     
        ]
        '''
        total_over_time = 0

        # 订单完成时间和预估送达时间信息
        order_id_to_complete_time = {}
        order_id_to_committed_completion_time = {}
        
        # 是否成功
        failure_flag = False
        
        for order_id, status_info_list in order_id_to_status_list.items():
            # 筛选出已经完成的订单
            selected_status_info_list = [status_info for status_info in status_info_list
                                         if status_info["state"] == Configs.ORDER_STATUS_TO_CODE.get("COMPLETED")]

            if len(selected_status_info_list) == 0:
                logger.error(f"order {order_id} has no history of completion status")
                failure_flag = True
                continue
            
            # 按照update time进行排序，计算order status变成completed的时间
            selected_status_info_list.sort(key=lambda x: x["update_time"])
            order_id_to_complete_time[order_id] = selected_status_info_list[0].get("update_time")
            
            if order_id not in order_id_to_committed_completion_time:
                order_id_to_committed_completion_time[order_id] = selected_status_info_list[0].get("committed_completion_time")
            
        if failure_flag:
            return sys.maxsize

        # 计算延误总时间
        for order_id, order_complete_time in order_id_to_complete_time.items():
            committed_completion_time = order_id_to_committed_completion_time.get(order_id)
            over_time = order_complete_time - committed_completion_time
            if over_time > 0:
                total_over_time += over_time

        return total_over_time
    
    
    @staticmethod
    def calculate_total_distance(driver_id_to_node_list: dict, route_map):
        '''
        计算路线总长度
        Inputs:
        - driver_id_node_list: {driver_id: [visiting nodes]}
        - route_map: Map类
        '''
        total_distance = 0
        if not driver_id_to_node_list:
            return total_distance

        for driver_id, nodes in driver_id_to_node_list.items():
            # driver访问过地点的id集合
            travel_location_list = []
            for node in nodes:
                travel_location_list.append(node['location_id'])
            
            distance = calculate_traveling_distance_of_routes(travel_location_list, route_map)
            total_distance += distance
            logger.info(f"Traveling Distance of driver {driver_id} is {distance: .3f}, "
                        f"visited node list: {len(travel_location_list)}")
        return total_distance

    
def calculate_traveling_distance_of_routes(location_id_list, route_map):
    '''
    对于每个骑手，计算其访问的地点集合[location_id_list]的长度
    '''
    travel_distance = 0
    if len(location_id_list) <= 1:
        return travel_distance

    for index in range(len(location_id_list) - 1):
        travel_distance += route_map.calculate_distance_between_locations(location_id_list[index],
                                                                          location_id_list[index + 1])
    return travel_distance