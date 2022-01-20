class Driver(object):
    def __init__(self, driver_id: str, capacity:int, gps_id: str, operation_time: int, carrying_orders=None):
        '''
        Inputs:
        - driver_id: 骑手编号
        - capacity: 可以运送的订单数量(e.g., 10个订单)
        - carring_orders: List, 已经pickup，正在运送途中的订单
        '''
        self.id = driver_id
        self.capacity = capacity
        self.gps_id = gps_id
        self.operation_time = operation_time

        # private attributes
        if carrying_orders is None:
            carrying_orders = []
        self.__carrying_orders = carrying_orders

        '''
        gps_update_time: 更新现在地点的时间， second
        current_location: 现在司机在的地点，如果不在任何地点 (餐厅，顾客地点), 则等于""
        arrive_time_at_current_location: 骑手到达现在地点的时间
        leave_time_at_current_location: 骑手离开现在地点的时间
        destination: 骑手下一个地点，一旦确定不可以改变
        planned_route: List，骑手配送路线，可以改变（e.g., 插入新订单）
        '''
        self.gps_update_time = 0
        self.current_location_id = ""

        # add
        # self.current_coordinate = (0, 0) 


        self.arrive_time_at_current_location = 0
        self.leave_time_at_current_location = 0
        self.destination = None
        self.planned_route = []

    def add_order(self, order):
        '''
        Add new order to the driver
        '''
        self.__carrying_orders.append(order)
    
    def unload_order(self, order):
        '''
        Remove order from the driver
        '''
        self.__carrying_orders.remove(order)

    # getter method
    @property
    def carrying_orders(self):
        return self.__carrying_orders
    
    @carrying_orders.setter
    def carrying_orders(self, carrying_orders):
        self.__carrying_orders = carrying_orders


    # setter method
    @carrying_orders.setter
    def carrying_orders(self, carrying_orders):
        self.__carrying_orders = carrying_orders
        
    # add cur_coordinate
    def set_cur_position_info(self, cur_location_id, update_time: int, arrive_time_at_current_location=0, 
                              leave_time_at_current_location=0):
        '''
        更新现在骑手的位置信息: [current_location_id, gps_update_time, arrive time, leave time]
        '''
        self.current_location_id = cur_location_id
        # self.current_coordinate = cur_coordinate
        self.gps_update_time = update_time
        if len(self.current_location_id) > 0:
            self.arrive_time_at_current_location = arrive_time_at_current_location
            self.leave_time_at_current_location = leave_time_at_current_location
        else:
            self.arrive_time_at_current_location = 0
            self.leave_time_at_current_location = 0
    
    
    def __str__(self):
        return "[{}:{}]".format(self.__class__.__name__, self.gather_attrs())
    
    
    def gather_attrs(self):
        return ",".join("{}={}".format(k, getattr(self, k)) for k in self.__dict__.keys())


