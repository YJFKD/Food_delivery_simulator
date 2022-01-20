import datetime
from src.utils.logging_engine import logger

class Order(object):
    def __init__(self, order_id: str, demand: float, creation_time: int, committed_completion_time: int,
                 load_time:int, unload_time: int, order_restaurant_id: str, order_customer_id: str, state=0):
        '''
        Inputs: 9 features
        - order_id: 订单编号
        - order_restaurant: 订单餐厅
        - order_customer_id: 订单的顾客编号
        - creation_time: 订单生成时间
        - committed_completion_time: 订单预计送达时间
        - state: 订单状态 {0: 初始 initialization, 1: 已生成 generated, 2: 配送中 ongoing, 3: 已完成 finished}
        '''
        # id
        self.id = order_id
        self.demand = demand # order demand都一样，都等于1
        
        # time
        self.creation_time = creation_time
        self.committed_completion_time = committed_completion_time
        self.load_time = load_time # 常数，e.g., 1 min
        self.unload_time = unload_time # 常数，e.g., 1 min
        self.pickup_location_id = order_restaurant_id # restaurant_id
        self.delivery_location_id = order_customer_id # customer_id
        
        
        # state
        self.delivery_state = int(state)

        # output order information
        logger.debug(f"{order_id}, creation time: {datetime.datetime.fromtimestamp(creation_time)}, "
                     f"committed completion time: {datetime.datetime.fromtimestamp(committed_completion_time)}, "
                     f"pickup restaurant id: {order_restaurant_id}, delivery customer location id: {order_customer_id}"
                     )



        


