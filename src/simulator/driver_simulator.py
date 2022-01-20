import datetime
import simpy
import haversine as hs
from geographiclib.geodesic import Geodesic
from src.utils.logging_engine import logger


class DriverSimulator(object):
    def __init__(self, route_map, id_to_location):
        '''
        初始化骑手模拟环境，包括路网，地点等
        Inputs:
        - route_map: travel distance and time matrix between locations
        - id_to_location: dict, {key: id, value: location}
        '''
        self.env = simpy.Environment()
        self.route_map = route_map
        self.id_to_location = id_to_location
        self.ongoing_order_ids = [] 
        self.completed_order_ids = [] 
        self.driver_id_to_destination = {}
        self.driver_id_to_cur_position_info = {}
        self.driver_id_to_carrying_orders = {}
    

    def run(self, id_to_driver: dict, from_time: int):
        """
        运行骑手模拟器(从from_time开始)
        Inputs:
        - id_to_driver:  {driver_id: driver object}
        - from_time: the begin time of simulation
        """
        # initialize the simulation environment
        self.env = simpy.rt.RealtimeEnvironment(initial_time=from_time, factor=0.000000000001, strict=False)

        # sort_drivers by leave time in their locations
        sorted_drivers = self.__sort_drivers(id_to_driver, from_time)

        # in simulation, each driver starts to visit its route
        for driver in sorted_drivers:
            self.env.process(self.work(driver))
        self.env.run()


    def work(self, driver):
        '''
        模拟一个骑手的送餐路线
        Inputs:
        - driver: driver object
        '''
        # 骑手现在的地点
        cur_location_id = driver.current_location_id
        
        # 在当前地点
        if len(cur_location_id) > 0:
            # 还没到离开的时间 (可能存在issue，需要关注)
            if driver.leave_time_at_current_location > self.env.now:
                yield self.env.timeout(driver.leave_time_at_current_location - self.env.now)
            # 停车状态 
            else:
                driver.leave_time_at_current_location = self.env.now
        
        # 不在当前地点，且没有下一个目的地
        if driver.destination == None:
            if len(cur_location_id) == 0:
                logger.error(f"Driver {driver.id}: both the current location and the destination are None!!!")
            return
        
        # 在当前地点，且有下一个目的地
        if len(cur_location_id) > 0:
            next_location_id = driver.destination.id
            transport_time = self.route_map.calculate_time_between_locations(cur_location_id, next_location_id)
            yield self.env.timeout(transport_time)
        else:
            # 不在当前地点，正在前往下一个目的地的路上
            arr_time = driver.destination.arrive_time
            if arr_time >= self.env.now:
                yield self.env.timeout(arr_time - self.env.now)
            else:
                # bug，汇报bug
                logger.error(f"Driver {driver.id} is driving toward the destination, "
                                f"however current time {datetime.datetime.fromtimestamp(self.env.now)} is greater than "
                                f"the arrival time {datetime.datetime.fromtimestamp(arr_time)} of destination!!!")

        # 到达了下一个目的地，更新时间
        driver.destination.arrive_time = self.env.now
        service_time = driver.destination.service_time
        cur_location_id = driver.destination.id
        yield self.env.timeout(service_time)

        # 离开目的地
        driver.destination.leave_time = self.env.now

        # 前往剩下的地点(执行planned route中所有的订单)
        for node in driver.planned_route:
            next_location_id = node.id

            # calculate travel time
            transport_time = self.route_map.calculate_time_between_locations(cur_location_id, next_location_id)
            yield self.env.timeout(transport_time)

            # calculate service time
            arr_time = self.env.now
            service_time = node.service_time
            yield self.env.timeout(service_time)
            leave_time = self.env.now
            
            # update time and location
            node.arrive_time = arr_time
            node.leave_time = leave_time
            cur_location_id = next_location_id
    

    @staticmethod
    def __sort_drivers(id_to_driver:dict, start_time:int):
        '''
        对骑手进行排序
        Inputs:
        - id_to_driver: total drivers, {key: id, value: list of driver object}
        - start_time: simulation start time
        '''
        # 记录到达过地点的骑手, {key: location id, value: list of drivers}
        # 一个地点(e.g., 餐厅), 可能有多个骑手
        location_id_to_drivers = {}
        
        for driver_id, driver in id_to_driver.items():
            # 如果骑手正在当前位置(current_location),并且离开的时间在开始时间(start_time)之后
            if len(driver.current_location_id) > 0 and driver.leave_time_at_current_location > start_time:
                location_id = driver.current_location_id
                if location_id not in location_id_to_drivers:
                    location_id_to_drivers[location_id] = []
                location_id_to_drivers[location_id].append(driver)
        
        # 对每个地点的访问过的骑手，按照离开时间进行排序
        sorted_driver_ids = []
        for location_id, drivers in location_id_to_drivers.items():
            # sort by leave time
            tmp_dt = [(driver.id, driver.leave_time_at_current_location) for driver in drivers]
            tmp_dt.sort(key=lambda x: x[1])
            for dt in tmp_dt:
                sorted_driver_ids.append(dt[0])
        
        for driver_id in id_to_driver.keys():
            if driver_id not in sorted_driver_ids:
                sorted_driver_ids.append(driver_id)

        # get sorted driver object list 
        sorted_drivers = [id_to_driver.get(driver_id) for driver_id in sorted_driver_ids]
        return sorted_drivers
    
    
    # 解析输出, 加快照
    def parse_simulation_result(self, id_to_driver: dict, to_time: int):
        # 重置骑手信息
        self.ongoing_order_ids = []
        self.completed_order_ids = []
        self.driver_id_to_destination = {}
        self.driver_id_to_cur_position_info = {}
        self.driver_id_to_carrying_orders = {}

        # 重新得到在to_time时刻骑手信息
        self.get_position_info_of_drivers(id_to_driver, to_time)
        self.get_destination_of_drivers(id_to_driver, to_time)
        self.get_loading_and_unloading_result_of_drivers(id_to_driver, to_time)
    

    def get_position_info_of_drivers(self, id_to_driver:dict, to_time:int):
        '''
        获取每个骑手的在某个时刻的地理信息
        Get the position information of each driver, construct the dict self.driver_id_to_cur_position_info
        Inputs:
        - id_to_driver: dict, {key: driver id, value: driver}
        - to time: time you want to get the position of driver
        Output: self attribute, driver_id_to_cur_position_info (dict)
        '''
        for driver_id, driver in id_to_driver.items():
            # 骑手不在当前地点，且骑手没有下一个目的地
            if len(driver.current_location_id) == 0 and driver.destination is None:
                logger.error(f"Driver {driver_id}, the current position {driver.current_location_id}, the destination is None")
                continue
            
            # 骑手的计划路线(planned_route)经过的地点信息(location, arrive time, leave time)
            node_list = self.get_node_list_of_driver(driver)
            current_location_id = driver.current_location_id


            # # add
            # if driver.current_location_id == "":
            #     current_coordinate = (0.0, 0.0)
            # else:
            #     current_coordinate = (self.id_to_location.get(driver.current_location_id).lat, 
            #                           self.id_to_location.get(driver.current_location_id).lng) 


            arrive_time_at_current_location = 0
            leave_time_at_current_location = 0
            
            # 对骑手计划路线的location进行迭代，找到当前骑手所在位置
            for node in node_list:
            # for index in range(1, len(node_list)):
            #     node = node_list[index]
            #     pre_node = node_list[index-1]
                


                # # add
                # # 在前往下一个node途中
                # if to_time < node.arr_time and current_location_id == "":

                #     # if driver.current_location_id != "":
                #     #     pre_location_id = driver.current_location_id
                #     #     pre_location = self.id_to_location.get(pre_location_id)
                #     # else:
                #     pre_location = driver.current_coordinate

                #     next_location_id = node.id
                #     next_location = self.id_to_location.get(next_location_id)
                #     # 计算两点间的距离
                #     travel_distance = round((to_time - pre_node.arr_time) / 120, 2)
                #     # 计算两点之间弧度和目前地点经纬度
                #     brng = Geodesic.WGS84.Inverse(pre_location[0], pre_location[0], next_location.lat, next_location.lng)['azi1']
                #     current_coordinate = hs.inverse_haversine((pre_location[0], pre_location[1]), travel_distance, brng)
                #     arrive_time_at_current_location = to_time
                #     leave_time_at_current_location = to_time
                #     # 找到了下一个目的地，跳出循环
                #     break
                





                # 正在某个地点
                if node.arr_time <= to_time <= node.leave_time:
                    current_location_id = node.id
                    arrive_time_at_current_location = node.arr_time
                    leave_time_at_current_location = node.leave_time
            
            # 骑手完成了最后一个的订单
            if len(current_location_id) == 0 and node_list[-1].leave_time < to_time:
                current_location_id = node_list[-1].id
                arrive_time_at_current_location = node_list[-1].arr_time
                leave_time_at_current_location = max(node_list[-1].leave_time, to_time)
            
            self.driver_id_to_cur_position_info[driver_id] = {"current_location_id": current_location_id,
                                                            #   "current_coordinate": current_coordinate,
                                                              "arrive_time_at_current_location": arrive_time_at_current_location,
                                                              "leave_time_at_current_location": leave_time_at_current_location,
                                                              "update_time": to_time}


    def get_destination_of_drivers(self, id_to_driver: dict, to_time: int):
        '''
        获取每个骑手的在时刻to_time时下一个目的地
        Inputs:
        - id_to_driver: dict, {key: driver id, value: driver}
        - to_time: time you want to get the destination of driver
        Output: self attribute, driver_id_to_destination (dict)
        '''
        for driver_id, driver in id_to_driver.items():
            # 骑手没有目的地(默认值:None)
            if driver.destination is None:
                self.driver_id_to_destination[driver_id] = None
                continue
            
            # 骑手的下一个目的地的到达时间大于to_time, 骑手还没有到达目的地
            if driver.destination.arrive_time > to_time:
                self.driver_id_to_destination[driver_id] = driver.destination
            # 骑手已经到达了下一个目的地,则需要更新目的地
            else:
                destination = None
                for node in driver.planned_route:
                    if node.arrive_time > to_time:
                        destination = node
                        break
                self.driver_id_to_destination[driver_id] = destination


    def get_loading_and_unloading_result_of_drivers(self, id_to_driver: dict, to_time: int):
        '''
        获取每个骑手取货和送货的情况(更新, ongoing_order_ids, completed_order_ids)
        Update the driver's pickup and delivery behaviour
        '''
        for driver_id, driver in id_to_driver.items():
            # 获取骑手正在运载的订单
            carrying_orders = driver.carrying_orders
            
            # 骑手没有下一个目的地
            if driver.destination is None:
                self.driver_id_to_carrying_orders[driver_id] = carrying_orders
                continue
            
            # 骑手已经到达了下一个目的地, 更新订单
            if driver.destination.arrive_time <= to_time:
                self.loading_and_unloading(driver.destination, carrying_orders, 
                                            self.completed_order_ids, self.ongoing_order_ids)
            
            # 对骑手planned_route的所有location都进行遍历, 更新订单
            for node in driver.planned_route:
                arr_time = node.arrive_time
                leave_time = node.leave_time
                if arr_time <= to_time:
                    self.loading_and_unloading(node, carrying_orders, self.completed_order_ids, self.ongoing_order_ids)
                if leave_time > to_time:
                    break
            
            self.driver_id_to_carrying_orders[driver_id] = carrying_orders


    @staticmethod
    def loading_and_unloading(node, carrying_orders, completed_orders_ids, ongoing_orders_ids):
        '''
        骑手取餐和送餐，更新订单信息
        Inputs:
        - carrying_orders: 骑手正在运送的订单
        - completed_orders_ids: orders id which are already completed delivery
        - ongoing_orders_ids: orders id is now prepare to pickup or delivery
        '''
        # 在food delivery问题中，要么只有pickup(餐厅)，要么只有delivery(顾客)
        delivery_orders = node.delivery_orders
        pickup_orders = node.pickup_orders
        delivery_orders_ids = [order.id for order in delivery_orders]
        
        # 顾客地点, 将订单从carrying_orders里面删除, 加入到completed_orders_id
        for order_id in delivery_orders_ids:
            for order in carrying_orders:
                if order.id == order_id:
                    carrying_orders.remove(order)
                    completed_orders_ids.append(order_id)
                    break
        
        # 餐厅地点, 将订单加入carrying_orders和ongoing_orders_id
        for order in pickup_orders:
            carrying_orders.append(order)
            ongoing_orders_ids.append(order.id)


    @staticmethod
    def get_node_list_of_driver(driver):
        '''
        Get the list of node (location, arrive time, leave time) of each driver
        Should including the current_location node?
        '''
        node_list = []
        
        # add driver current information
        if len(driver.current_location_id) >= 0:
            node_list.append(EasyNode(driver.current_location_id,
                                      driver.arrive_time_at_current_location,
                                      driver.leave_time_at_current_location))
        
        # add driver next destination information
        if driver.destination is not None:
            node_list.append(EasyNode(driver.destination.id,
                                      driver.destination.arrive_time,
                                      driver.destination.leave_time))

        # add driver planned route information
        if len(driver.planned_route) > 0:
            for node in driver.planned_route:
                node_list.append(EasyNode(node.id, node.arrive_time, node.leave_time)) 
        
        return node_list



'''
    A simply version of node class, only include the location id, arrive time, and leave time
'''


class EasyNode(object):
    def __init__(self, location_id, arr_time, leave_time):
        self.id = location_id
        self.arr_time = arr_time
        self.leave_time = leave_time
        







            
