import copy

from src.utils.logging_engine import logger
# from Food_delivery_simulator.utils.tools import get_order_list_of_drivers

class Checker(object):
    '''
    检测派单过程中的各种约束
    '''
    @staticmethod
    def check_dispatch_result(dispatch_result, id_to_driver: dict, id_to_order: dict):
        driver_id_to_destination = dispatch_result.driver_id_to_destination
        driver_id_to_planned_route = dispatch_result.driver_id_to_planned_route

        # 检查是否所有的车辆都有返回值
        if len(driver_id_to_destination) != len(id_to_driver):
            logger.error(f"Num of returned destination {len(driver_id_to_destination)} "
                         f"is not equal to driver number {len(id_to_driver)}")
            return False

        if len(driver_id_to_planned_route) != len(id_to_driver):
            logger.error(f"Num of returned planned route {len(driver_id_to_planned_route)} "
                         f"is not equal to driver number {len(id_to_driver)}")
            return False

        # 逐个检查各车辆路径
        for driver_id, driver in id_to_driver.items():
            if driver_id not in driver_id_to_destination:
                logger.error(f"Destination information of driver {driver_id} is not in the returned result")
                return False

            # check destination
            destination_in_result = driver_id_to_destination.get(driver_id)
            if not Checker.__is_returned_destination_valid(destination_in_result, driver):
                logger.error(f"Returned destination of driver {driver_id} is not valid")
                return False

            # check routes
            if driver_id not in driver_id_to_planned_route:
                logger.error(f"Planned route of driver {driver_id} is not in the returned result")
                return False

            # 创建一个新的route，合并destination和planned_route
            route = []
            if destination_in_result is not None:
                route.append(destination_in_result)
            route.extend(driver_id_to_planned_route.get(driver_id))

            if len(route) > 0:
                # 骑手容量约束
                if not Checker.__meet_capacity_constraint(route, copy.deepcopy(driver.carrying_orders),
                                                          driver.capacity):
                    logger.error(f"driver {driver_id} violates the capacity constraint")
                    return False

                # 相邻节点约束
                Checker.__contain_duplicated_nodes(driver_id, route)

                # 重复订单约束
                if Checker.__contain_duplicate_orders(route, copy.deepcopy(driver.carrying_orders)):
                    return False

                # 
                if not Checker.__do_pickup_and_delivery_orders_match_the_node(route):
                    return False

        return True
    
    
    @staticmethod
    def __is_returned_destination_valid(returned_destination, driver):
        '''
        检测算法分配的目的地是否有效
        '''
        # driver原来的目的地
        origin_destination = driver.destination
        
        if origin_destination is not None:
            if returned_destination is None:
                logger.error(f"driver {driver.id}, returned destination is None, "
                             f"however the origin destination is not None.")
                return False
            else:
                # 下一个目的地一旦确认，不可更改，车辆不处于停车状态
                if origin_destination.id != returned_destination.id:
                    logger.error(f"driver {driver.id}, returned destination id is {returned_destination.id}, "
                                 f"however the origin destination id is {origin_destination.id}.")
                    return False

                if origin_destination.arrive_time != returned_destination.arrive_time:
                    logger.error(f"driver {driver.id}, arrive time of returned destination is "
                                 f"{returned_destination.arrive_time}, "
                                 f"however the arrive time of origin destination is "
                                 f"{origin_destination.arrive_time}.")
                    return False
        elif len(driver.current_location_id) == 0 and returned_destination is None:
            logger.error(f"Currently, driver {driver.id} is not in the location(current_location_id==''), "
                         f"however, returned destination is also None, we cannot locate the driver.")
            return False

        return True
    
    
    @staticmethod
    def __meet_capacity_constraint(route: list, carrying_orders, capacity):
        '''
        载重约束，capacity constraint
        Inputs:
        - route: 骑手运送路线，[destination, planned_route]
        - carrying_orders: 正在配送的订单
        - capacity: 骑手的capacity
        '''
        left_capacity = capacity

        # 检测去掉carrying_orders的剩余capacity
        for order in carrying_orders:
            left_capacity -= order.demand
            if left_capacity < 0:
                logger.error(f"left capacity {left_capacity} < 0")
                return False

        # 对运送路线上每个node进行检测
        for node in route:
            # 在food delivery问题中，一个node要么是餐厅(只有pickup)，要么是顾客(只有delivery)
            delivery_orders = node.delivery_orders
            pickup_orders = node.pickup_orders
            # delivery orders
            for order in delivery_orders:
                left_capacity += order.demand
                if left_capacity > capacity:
                    logger.error(f"left capacity {left_capacity} > capacity {capacity}")
                    return False
            # pickup orders
            for order in pickup_orders:
                left_capacity -= order.demand
                if left_capacity < 0:
                    logger.error(f"left capacity {left_capacity} < 0")
                    return False
        return True

    
    @staticmethod
    def __contain_duplicated_nodes(driver_id, route):
        '''
        检查相邻的节点是否重复，并警告，鼓励把相邻重复节点进行合并
        '''
        for n in range(len(route) - 1):
            if route[n].id == route[n + 1].id:
                logger.warning(f"{driver_id} has adjacent-duplicated nodes which are encouraged to be combined in one.")
                
    
    @staticmethod
    def __contain_duplicate_orders(route, carrying_orders):
        '''
        检测路线中是否有重复的订单
        '''
        order_id_list = []
        # for carrying_orders
        for order in carrying_orders:
            if order.id not in order_id_list:
                order_id_list.append(order.id)
            else:
                logger.error(f"order {order.id}: duplicate order id")
                return True
        # for pickup orders in route
        for node in route:
            pickup_orders = node.pickup_orders
            for order in pickup_orders:
                if order.id not in order_id_list:
                    order_id_list.append(order.id)
                else:
                    logger.error(f"order {order.id}: duplicate order id")
                    return True
        return False
    
    
    @staticmethod
    def __do_pickup_and_delivery_orders_match_the_node(route: list):
        '''
        检查pickup和delivery orders的地点是否正确对应
        '''
        for node in route:
            # 路线中的地点
            location_id = node.id
            # pickup orders
            pickup_orders = node.pickup_orders
            for order in pickup_orders:
                if order.pickup_location_id != location_id:
                    logger.error(f"Pickup location of order {order.id} is {order.pickup_location_id}, "
                                 f"however you allocate the driver to pickup this order in {location_id}")
                    return False
            # delivery orders
            delivery_orders = node.delivery_orders
            for order in delivery_orders:
                if order.delivery_location_id != location_id:
                    logger.error(f"Delivery location of order {order.id} is {order.delivery_location_id}, "
                                 f"however you allocate the driver to delivery this order in {location_id}")
                    return False
        return True