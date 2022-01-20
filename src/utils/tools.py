import copy

from src.configuration.config import Configs



def get_orders_to_be_dispatched_of_cur_time(id_to_order: dict, cur_time: int):
    """
    获取当前待分配的订单
    - id_to_order: 所有订单
    - cur_time: unix timestamp, unit is second
    
    返回当前时间新生成和delivery_state=1("GENERATED")的所有订单物料
    """
    # 获取当前时间之前还未到装货环节的订单, 依旧可以再分配
    id_to_generated_orders = {order.id: order for order in id_to_order.values()
                                  if order.delivery_state == Configs.ORDER_STATUS_TO_CODE.get("GENERATED")}

    # 获取当前之间之前新生成的订单
    id_to_generated_orders.update(__get_newly_generated_orders(id_to_order, cur_time))

    return id_to_generated_orders


def __get_newly_generated_orders(id_to_order: dict, cur_time: int):
    '''
    获取新生成的订单
    Inputs:
    - id_to_order: 记录的订单
    - cur_time: timestampe，更新时间
    Output:
    - id_to_new_order: 新生成的订单
    '''
    id_to_new_order = {}
    for order_id, order in id_to_order.items():
        if order.creation_time <= cur_time:
            if order.delivery_state == Configs.ORDER_STATUS_TO_CODE.get("INITIALIZATION"):
                # 修改订单状态
                order.delivery_state = Configs.ORDER_STATUS_TO_CODE.get("GENERATED")
                id_to_new_order[order_id] = order
    return id_to_new_order


def get_order_list_of_drivers(dispatch_result, id_to_driver: dict):
    '''
    从dispatch_result中，获取各车辆分配的订单集合
    Inputs:
    - dispatch_result: {driver_id: driver destination (Node)}, {driver_id: planned_route (list of Node)}
    '''
    # 初始化
    driver_id_to_order_list = {}

    driver_id_to_destination = dispatch_result.driver_id_to_destination
    driver_id_to_planned_route = dispatch_result.driver_id_to_planned_route

    for driver_id, driver in id_to_driver.items():
        order_list = []
        order_id_list = []
        carrying_orders = copy.deepcopy(driver.carrying_orders)
       
        # carrying orders
        for order in carrying_orders:
            if order.id not in order_id_list:
                order_id_list.append(order.id)
                order_list.append(order)

        # 下一个目的地的订单
        if driver_id in driver_id_to_destination:
            destination = driver_id_to_destination.get(driver_id)
            if destination is not None:
                # 获取需要在destination pickup的订单
                pickup_orders = destination.pickup_orders
                for order in pickup_orders:
                    if order.id not in order_id_list:
                        order_id_list.append(order.id)
                        order_list.append(order)

        # planned_route中的订单
        if driver_id in driver_id_to_planned_route:
            for node in driver_id_to_planned_route.get(driver_id):
                # 获取需要在destination pickup的订单
                pickup_orders = node.pickup_orders
                for order in pickup_orders:
                    if order.id not in order_id_list:
                        order_id_list.append(order.id)
                        order_list.append(order)

        # 对骑手更新订单信息
        driver_id_to_order_list[driver_id] = order_list

    return driver_id_to_order_list