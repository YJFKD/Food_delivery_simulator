class Node(object):
    def __init__(self, location_id:str, lat:float, lng:float, pickup_order_list: list, delivery_order_list: list,
                 arrive_time=0, leave_time=0):
        '''
        Node: 餐厅地点和顾客订单地点
        Inputs:
        - location_id: 地点编号
        - lat: latitude 纬度
        - lng: longitude 经度
        - pickup_order_list: 取货订单，餐厅
        - delivery_order_list: 送货订单，顾客
        - arrive_time: 到达该地点的时间
        - leave_time: 离开该地点的时间
        '''
        self.__id = location_id
        self.__lat = lat
        self.__lng = lng

        # list of pickup orders 餐厅
        self.__pickup_orders = pickup_order_list
        self.__loading_time = self.calculate_loading_time()
        
        # list of delivery orders 顾客
        self.__delivery_orders = delivery_order_list
        self.__unloading_time = self.calculate_loading_time()

        # arrive, leave and service time
        self.arrive_time = arrive_time 
        self.leave_time = leave_time
        self.__service_time = self.__unloading_time + self.__loading_time # 服务时间等于取货时间或者送货时间

    # calculate loading and unloading time, and update
    def calculate_loading_time(self):
        loading_time = 0
        for order in self.__pickup_orders:
            loading_time += order.load_time
        return loading_time

    def calculate_unloading_time(self):
        unloading_time = 0
        for order in self.__delivery_orders:
            unloading_time += order.unload_time
        return unloading_time

    def update_service_time(self):
        self.__loading_time = self.calculate_loading_time()
        self.__unloading_time = self.calculate_unloading_time()
        self.__service_time = self.__unloading_time + self.__loading_time

    # getter and setter function
    @property
    def id(self):
        return self.__id

    @property
    def lat(self):
        return self.__lat

    @property
    def lng(self):
        return self.__lng

    @property
    def service_time(self):
        return self.__service_time

    @property
    def pickup_orders(self):
        return self.__pickup_orders

    @pickup_orders.setter
    def pickup_orders(self, pickup_order_list):
        self.__pickup_orders = pickup_order_list

    @property
    def delivery_orders(self):
        return self.__delivery_orders

    @delivery_orders.setter
    def delivery_orders(self, delivery_order_list):
        self.__delivery_orders = delivery_order_list