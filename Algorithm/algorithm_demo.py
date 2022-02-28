import os
import copy
import numpy as np
import haversine as hs
from python_tsp.exact import solve_tsp_dynamic_programming
import logging
import random


from src.common.node import Node
from src.common.route import Map
from src.configuration.config import Configs
from src.utils.input_utils import get_restaurant_info, get_customer_info
from src.utils.json_tools import convert_nodes_to_json
from src.utils.json_tools import get_driver_instance_dict, get_order_dict
from src.utils.json_tools import read_json_from_file, write_json_to_file
from src.utils.logging_engine import logger


def dispatch_orders_to_drivers(id_to_unallocated_order: dict, id_to_driver: dict, id_to_location: dict, id_to_restaurant: dict):
    """
    Inputs:
    - id_to_unallocated_order: {order_id ——> Order object(state: "GENERATED")}
    - id_to_driver: {driver_id ---> driver object}
    - id_to_location: {location_id ---> location object (restaurant or customer)}
    """
    # random.seed(Configs.RANDOM_SEED)
    driver_id_to_destination = {}
    driver_id_to_planned_route = {} 
    driver_id_to_entire_planned_route = {} # entire planned route include current location, destination & planned route
    driver_id_to_all_locations_id = {driver_id:[] for driver_id, driver in id_to_driver.items()}
    
    # First decide the planned route for carrying orders
    for driver_id, driver in id_to_driver.items():
        driver_id_to_planned_route[driver_id] = []
        carrying_orders = driver.carrying_orders
        # initialize the location of driver
        if driver.current_location_id != "":
            driver_location_id = driver.current_location_id
            logging.warn(f"The current location of driver {driver_id} is: {driver_location_id}") 
        else:
            driver_location_id = driver.destination.id
            logging.warn(f"The destination location of driver {driver_id} is: {driver_location_id}") 
        driver_id_to_all_locations_id[driver_id].append(driver_location_id)
        
        # if driver has carrying orders, do TSP
        if len(carrying_orders) > 0:
            logging.warn(f"Carrying orders: {[order.id for order in carrying_orders]}")
            
            # driver & order location id
            for order in carrying_orders:
                customer_location_id = order.delivery_location_id
                if customer_location_id != driver_location_id:
                    driver_id_to_all_locations_id[driver_id].append(customer_location_id)
            
            num_locations = len(driver_id_to_all_locations_id[driver_id])
            # delivery node distance matrix
            distance_matrix = np.zeros(shape=(num_locations, num_locations))
            for index_1, location_1_id in enumerate(driver_id_to_all_locations_id[driver_id]):
                for index_2, location_2_id in enumerate(driver_id_to_all_locations_id[driver_id]):
                    location_1 = id_to_location.get(location_1_id)
                    location_2 = id_to_location.get(location_2_id)
                    distance_matrix[index_1, index_2] = hs.haversine((location_1.lat, location_1.lng), (location_2.lat, location_2.lng))
            # get visiting sequence
            visiting_sequence, travel_distance = solve_tsp_dynamic_programming(distance_matrix)
            # add delivery orders nodes to planned route (exclude the first node: driver.destination or current location)
            for tsp_index in visiting_sequence: # delete [1:], include the destination
                location_id = driver_id_to_all_locations_id[driver_id][tsp_index]
                location = id_to_location.get(location_id)
                delivery_order_list = [o for o in carrying_orders if o.delivery_location_id == location_id]
                node = Node(location_id, location.lat, location.lng, [], delivery_order_list)
                driver_id_to_planned_route[driver_id].append(node)
        
        
    
    # Second, add the next destination pickup orders into planned route (pre-matching orders)
    pre_matching_order_ids = []
    for driver_id, driver in id_to_driver.items():
        # if destination is restaurant
        destination = driver.destination
        if destination is not None and destination.id in id_to_restaurant and len(driver.carrying_orders) == 0:
            pickup_orders = destination.pickup_orders 
            
            # add for debug
            # logging.warn(f"driver_id is {driver_id}, destination is {destination.id}, pickup orders are {[order.id for order in pickup_orders]}")
            
            
            
            pickup_node_list, delivery_node_list = __create_pickup_and_delivery_nodes_of_orders(pickup_orders, id_to_location)
            driver_id_to_planned_route[driver_id].append(pickup_node_list[0])
            
            
            # the pickup node for next destination should be insert at the begin of planned route
            # if pickup_node_list != None:
            #     driver_id_to_planned_route[driver_id].insert(0, pickup_node_list[0]) # add for debug
            
            
            
            for node in delivery_node_list:
                driver_id_to_planned_route[driver_id].append(node)
            pre_matching_order_ids.extend([order.id for order in pickup_orders])
    #         logging.warn(f"I love you!!!!!!!!!")               
    #         pickup_orders = driver.destination.pickup_orders 
    #         # add the delivery location id into all locations set
    #         delivery_locations_id = [order.delivery_location_id for order in pickup_orders]
    #         driver_id_to_all_locations_id[driver_id].extend(delivery_locations_id)
    #         # get node of order
    #         pickup_node_list, delivery_node_list = __create_pickup_and_delivery_nodes_of_orders(pickup_orders, id_to_location)
    #         num_locations = len(driver_id_to_all_locations_id[driver_id])
    #         # delivery node distance matrix
    #         distance_matrix = np.zeros(shape=(num_locations, num_locations))
    #         for index_1, location_1_id in enumerate(driver_id_to_all_locations_id[driver_id]):
    #             for index_2, location_2_id in enumerate(driver_id_to_all_locations_id[driver_id]):
    #                 location_1 = id_to_location.get(location_1_id)
    #                 location_2 = id_to_location.get(location_2_id)
    #                 distance_matrix[index_1, index_2] = hs.haversine((location_1.lat, location_1.lng), (location_2.lat, location_2.lng))
    #         # get visiting sequence
    #         visiting_sequence, travel_distance = solve_tsp_dynamic_programming(distance_matrix)
    #         # add delivery orders nodes to planned route (exclude the first node: driver.destination or current location)
    #         for tsp_index in visiting_sequence[1:]:
    #             location_id = driver_id_to_all_locations_id[driver_id][tsp_index]
    #             location = id_to_location.get(location_id)
    #             delivery_order_list = [o for o in carrying_orders if o.delivery_location_id == location_id]
    #             node = Node(location_id, location.lat, location.lng, [], delivery_order_list)
    #             driver_id_to_planned_route[driver_id].append(node) 
            
    #         # insert the pickup orders node in the begin of the planned route
    #         driver_id_to_planned_route[driver_id] = pickup_node_list + driver_id_to_planned_route[driver_id]
    #         pre_matching_order_ids.extend([order.id for order in pickup_orders]) 
    
           
    
    # Third, deal with unallocated orders (newly generated orders + assigned orders but not pickup)
    for order_id, order in id_to_unallocated_order.items():
        if order_id in pre_matching_order_ids:
            continue
        # calculate the left capacity before assign an order
        available_driver_ids = [] 
        for driver_id, driver in id_to_driver.items():
            if len(driver_id_to_planned_route[driver_id]) <= 8: # need improve later
                available_driver_ids.append(driver_id)
        
        order_driver_distance_dict = {}
        driver_id_capacity_dict = {}

        # order pickup restaurant & delivery location
        restaurant_location_id = order.pickup_location_id
        customer_location_id = order.delivery_location_id
        restaurant_location = id_to_location.get(restaurant_location_id)
        customer_location = id_to_location.get(customer_location_id)
        
        for driver_id, driver in id_to_driver.items():
            if driver_id in available_driver_ids:
                # get pickup location
                driver_location = id_to_location.get(driver_id_to_all_locations_id[driver_id][0])
                order_driver_distance = hs.haversine((restaurant_location.lat, restaurant_location.lng),
                                                     (driver_location.lat, driver_location.lng))
                order_driver_distance_dict[driver_id] = order_driver_distance
                
                # get driver capacity
                driver_id_capacity_dict[driver_id] = len(driver_id_to_planned_route[driver_id])
        
        # dispatch order to nearest driver or maximum available capacity
        min_distance = min(order_driver_distance_dict.values())
        min_distance_driver_id = [driver_id for driver_id in order_driver_distance_dict if order_driver_distance_dict[driver_id] == min_distance]
        min_weight = min(driver_id_capacity_dict.values())
        min_weight_driver_id = [driver_id for driver_id in driver_id_capacity_dict if driver_id_capacity_dict[driver_id] == min_weight]
        
        # randomly select nearest or minimal weight driver
        random.seed(Configs.RANDOM_SEED)
        random_select_value = random.randint(0, 1)
        min_distance_driver_index = random.randint(0, len(min_distance_driver_id) - 1)
        min_weight_driver_index = random.randint(0, len(min_weight_driver_id) - 1) 
        
        if random_select_value == 0:
            # select nearest driver first
            if len(driver_id_to_planned_route[min_distance_driver_id[min_distance_driver_index]]) <= 6:
                assign_driver_id = min_distance_driver_id[min_distance_driver_index]
            else:
                assign_driver_id = min_weight_driver_id[min_weight_driver_index]
        else:
            # select minimal weight driver directly
            assign_driver_id = min_weight_driver_id[min_weight_driver_index]
        
        
        # if len(driver_id_to_planned_route[min_distance_driver_id[min_distance_driver_index]]) <= 6:
        #     assign_driver_id = min_distance_driver_id[min_distance_driver_index]
        # else:
        #     assign_driver_id = min_weight_driver_id[min_weight_driver_index]
        
        logging.warn(f"order {order_id} is assigned to driver {assign_driver_id}")
        
        
        # create node
        pickup_node_list, delivery_node_list = __create_pickup_and_delivery_nodes_of_orders([order], id_to_location)
        node_pair_list = [(pickup_node_list[index], delivery_node_list[index]) for index in range(len(pickup_node_list))]
        # insert pickup node
        driver_old_planned_route = driver_id_to_planned_route[assign_driver_id].copy() # not include the assign driver destination, bug
        __combine_duplicated_nodes(driver_old_planned_route)
        
        for node_pair in node_pair_list:
            pickup_node = node_pair[0]
            delivery_node = node_pair[1]
            # if no planned route
            if len(driver_old_planned_route) == 0:
                driver_old_planned_route.append(pickup_node)
                driver_old_planned_route.append(delivery_node)
                continue
            # insert pickup node
            pickup_insert_index_distance_dict = {}
            for index in range(1, len(driver_old_planned_route)+1): # can't insert at the begin of the route, will change destination
                add_distance = 0.0
                if index == 0:
                    add_distance = hs.haversine((pickup_node.lat, pickup_node.lng),
                                                (driver_old_planned_route[index].lat, driver_old_planned_route[index].lng))
                    pickup_insert_index_distance_dict[0] = add_distance
                elif index == len(driver_old_planned_route):
                    add_distance = hs.haversine((pickup_node.lat, pickup_node.lng),
                                                (driver_old_planned_route[index-1].lat, driver_old_planned_route[index-1].lng))
                else:
                    add_distance = hs.haversine((pickup_node.lat, pickup_node.lng),
                                                (driver_old_planned_route[index-1].lat, driver_old_planned_route[index-1].lng)) + \
                                   hs.haversine((pickup_node.lat, pickup_node.lng),
                                                (driver_old_planned_route[index].lat, driver_old_planned_route[index].lng)) - \
                                   hs.haversine((driver_old_planned_route[index-1].lat, driver_old_planned_route[index-1].lng),
                                                (driver_old_planned_route[index].lat, driver_old_planned_route[index].lng))
                pickup_insert_index_distance_dict[index] = add_distance
            min_insert_distance = min(pickup_insert_index_distance_dict.values())
            min_insert_index = [index for index in pickup_insert_index_distance_dict if pickup_insert_index_distance_dict[index] == min_insert_distance]
            pickup_node_insert_index = min_insert_index[0]
            driver_old_planned_route.insert(pickup_node_insert_index, pickup_node)
            # insert delivery node after pickup node index
            delivery_insert_index_distance_dict = {}
            for index in range(pickup_node_insert_index+1, len(driver_old_planned_route)+1):
                add_distance = 0.0
                if index == len(driver_old_planned_route):
                    add_distance = hs.haversine((delivery_node.lat, delivery_node.lng),
                                                (driver_old_planned_route[index-1].lat, driver_old_planned_route[index-1].lng))
                else:
                    add_distance = hs.haversine((delivery_node.lat, delivery_node.lng),
                                                (driver_old_planned_route[index-1].lat, driver_old_planned_route[index-1].lng)) + \
                                   hs.haversine((delivery_node.lat, delivery_node.lng),
                                                (driver_old_planned_route[index].lat, driver_old_planned_route[index].lng)) - \
                                   hs.haversine((driver_old_planned_route[index-1].lat, driver_old_planned_route[index-1].lng),
                                                (driver_old_planned_route[index].lat, driver_old_planned_route[index].lng))
                delivery_insert_index_distance_dict[index] = add_distance
            min_insert_distance = min(delivery_insert_index_distance_dict.values())
            min_insert_index = [index for index in delivery_insert_index_distance_dict if delivery_insert_index_distance_dict[index] == min_insert_distance]
            delivery_node_insert_index = min_insert_index[0]
            driver_old_planned_route.insert(delivery_node_insert_index, delivery_node)
        
        # update driver planned route
        __combine_duplicated_nodes(driver_old_planned_route)
        driver_id_to_planned_route[assign_driver_id] = driver_old_planned_route
         
                
            
        
    
    
    
    

    # # for non-empty driver, based on the carrying orders, generate planned_route
    # for driver_id, driver in id_to_driver.items():
    #     driver_id_to_planned_route[driver_id] = []
    #     carrying_orders = driver.carrying_orders
    #     # initialize the location of driver
    #     if driver.current_location_id != "":
    #         driver_location_id = driver.current_location_id
    #         # driver_id_to_planned_route[driver_id] = [] 
    #     else:
    #         driver_location_id = driver.destination.id
    #         # location = driver.destination
    #         # node = Node(driver_location_id, location.lat, location.lng, location.pickup_orders, location.delivery_orders)
    #         # driver_id_to_planned_route[driver_id] = [node] # if driver has destination, add it into planned route
        
    #     all_locations_id = [driver_location_id]
    #     if len(carrying_orders) > 0:
    #         # driver & order location id
    #         for order in carrying_orders:
    #             customer_location_id = order.delivery_location_id
    #             all_locations_id.append(customer_location_id)
    #         num_locations = len(all_locations_id)
            
    #         # construct distance matrix
    #         distance_matrix = np.zeros(shape=(num_locations, num_locations))
    #         for index_1, location_1_id in enumerate(all_locations_id):
    #             for index_2, location_2_id in enumerate(all_locations_id):
    #                 location_1 = id_to_location.get(location_1_id)
    #                 location_2 = id_to_location.get(location_2_id)
    #                 distance_matrix[index_1, index_2] = hs.haversine((location_1.lat, location_1.lng), (location_2.lat, location_2.lng))
            
    #         # driver routing as a TSP
    #         visiting_sequence, travel_distance = solve_tsp_dynamic_programming(distance_matrix)
            
    #         # add delivery orders nodes to planned route (exclude the first node: driver.destination or current location)
    #         for tsp_index in visiting_sequence[1:]:
    #             location_id = all_locations_id[tsp_index]
    #             location = id_to_location.get(location_id)
    #             delivery_order_list = [o for o in carrying_orders if o.delivery_location_id == location_id]
    #             node = Node(location_id, location.lat, location.lng, [], delivery_order_list)
    #             driver_id_to_planned_route[driver_id].append(node) 
    
    # # for the empty driver, it has been allocated to the order, but have not yet arrived at the pickup location (restaurant)
    # pre_matching_order_ids = []
    # for driver_id, driver in id_to_driver.items():
    #     # pickup orders from next destination
    #     if len(driver.carrying_orders) == 0 and driver.destination is not None:            
    #         pickup_orders = driver.destination.pickup_orders 
    #         pickup_node_list, delivery_node_list = __create_pickup_and_delivery_nodes_of_orders(pickup_orders, id_to_location)
    #         driver_id_to_planned_route[driver_id].extend(pickup_node_list)
    #         driver_id_to_planned_route[driver_id].extend(delivery_node_list)
    #         pre_matching_order_ids.extend([order.id for order in pickup_orders]) 
            
    # # dispatch unallocated orders to drivers (largest capacity)
    # driver_id_to_left_capacity = __get_left_capacity_of_driver(id_to_driver)
    # for order_id, order in id_to_unallocated_order.items():
    #     # calculate the available drivers
    #     # available_driver_ids = [driver_id for driver_id, driver in id_to_driver.items() if driver_id_to_left_capacity[driver_id] > 0] 
    #     if order_id in pre_matching_order_ids:
    #         continue
    #     pickup_node_list, delivery_node_list = __create_pickup_and_delivery_nodes_of_orders([order], id_to_location)
    #     if pickup_node_list == [] or delivery_node_list == []:
    #         continue
    #     assign_driver_id = max(driver_id_to_left_capacity, key=driver_id_to_left_capacity.get)
    #     assign_driver = id_to_driver.get(assign_driver_id)
    #     driver_id_to_planned_route[assign_driver.id].extend(pickup_node_list)
    #     driver_id_to_planned_route[assign_driver.id].extend(delivery_node_list)
    #     driver_id_to_left_capacity[assign_driver_id] -= len(pickup_node_list)
        
        
        
    
    
    
    
    
    
    
    
    
    
    
    
       
    # create the output of the dispatch
    for driver_id, driver in id_to_driver.items():
        origin_planned_route = driver_id_to_planned_route.get(driver_id) # origin planned route include driver destination
        
        # Combine adjacent-duplicated nodes.
        __combine_duplicated_nodes(origin_planned_route)
        logging.warn(f"driver {driver_id} planned route: {[node.id for node in origin_planned_route]}")
        
        # # add for debug
        # if driver_id == "D_14":
        #     later_pickup_orders = []
        #     for node in origin_planned_route:
        #         if node.pickup_orders != []:
        #             for order in node.pickup_orders:
        #                 later_pickup_orders.append(order.id)
        #     logging.warn(f"driver {driver_id} later pickup orders: {later_pickup_orders}")
        #     for node in origin_planned_route:
        #         logging.warn(f"node id is {node.id}, node delivery orders are {[order.id for order in node.delivery_orders]}")
        
        destination = None
        planned_route = []
        # determine the destination
        if driver.destination is not None:
            if len(origin_planned_route) == 0:
                logger.error(f"Planned route of driver {driver_id} is wrong")
            else:
                # if driver in current location
                if driver.current_location_id != "": 
                    destination = origin_planned_route[1]
                    destination.arrive_time = driver.destination.arrive_time
                    planned_route = [origin_planned_route[i] for i in range(2, len(origin_planned_route))]
                    
                    # add a case: 骑手在餐厅，且正在取上一次派单分发的订单，且被分发了此餐厅新的订单
                    if driver.current_location_id in id_to_restaurant: 
                        if len(origin_planned_route[1:]) > len(driver.carrying_orders):
                            destination = origin_planned_route[0]
                            destination.arrive_time = driver.destination.arrive_time
                            planned_route = [origin_planned_route[i] for i in range(1, len(origin_planned_route))]
                            # logging.warn(f"Modified destination is {destination.id}")    
                
                    # add a case: 骑手在顾客点，carrying orders为空，original planned route没有包括current location
                    if driver.current_location_id not in id_to_restaurant:
                        if len(driver.carrying_orders) == 0:
                            destination = origin_planned_route[0]
                            destination.arrive_time = driver.destination.arrive_time
                            planned_route = [origin_planned_route[i] for i in range(1, len(origin_planned_route))]      
                
                else:
                    destination = origin_planned_route[0]
                    destination.arrive_time = driver.destination.arrive_time
                    planned_route = [origin_planned_route[i] for i in range(1, len(origin_planned_route))]
        elif len(origin_planned_route) > 0:
            destination = origin_planned_route[0]
            planned_route = [origin_planned_route[i] for i in range(1, len(origin_planned_route))]
        # set the destination and planned route
        driver_id_to_destination[driver_id] = destination 
        driver_id_to_planned_route[driver_id] = planned_route
        driver_id_to_entire_planned_route[driver_id] = origin_planned_route
      
    return driver_id_to_destination, driver_id_to_planned_route, driver_id_to_entire_planned_route
            

def __calculate_demand(order_list: list):
    demand = 0
    for order in order_list:
        demand += order.demand
    return demand


def __remove_adjacent_duplicate(location_list: list):
    i = 1
    while i < len(location_list):    
        if location_list[i] == location_list[i-1]:
            location_list.pop(i)
            i -= 1  
        i += 1
    return location_list
    

def __get_left_capacity_of_driver(id_to_driver: dict):
    '''
    Get driver left capacity
    Input:
    - id_to_driver: {driver_id: driver object}
    Output:
    - left capacity of each driver: {driver_id: left capacity}
    '''
    driver_id_to_left_capacity = {}
    for driver_id, driver in id_to_driver.items():
        carrying_orders = driver.carrying_orders
        left_capacity = driver.capacity
        for order in carrying_orders:
            left_capacity -= order.demand
        driver_id_to_left_capacity[driver_id] = left_capacity

    return driver_id_to_left_capacity


def __calculate_distance_of_route(route: list):
    '''
    Calculate the distance of route (planned route)
    Input:
    - route: list of Node object
    '''
    travel_distance = 0
    if len(route) <= 1:
        return travel_distance

    for index in range(len(route) - 1):
        travel_distance += hs.haversine((route[index].lat, route[index].lng), 
                                        (route[index+1].lat, route[index+1].lng))
    return travel_distance
    
    

def __create_pickup_and_delivery_nodes_of_orders(orders: list, id_to_location: dict):
    '''
    Get the pickup and delivery nodes of orders
    Inputs:
    - orders: list of orders
    - id_location: dict, {location_id: location}
    Output:
    - pickup_node_list, delivery_node_list
    '''
    pickup_location_id_list = __get_pickup_location_id(orders)
    delivery_location_id_list = __get_delivery_location_id(orders)
    
    # order must have both pickup and delivery location
    if len(pickup_location_id_list) == 0 or len(delivery_location_id_list) == 0:
        return None, None

    # pickup node
    pickup_location_list = [] # 只有一个餐厅
    pickup_node_list = []
    for pickup_location_id in pickup_location_id_list:
        pickup_location = id_to_location.get(pickup_location_id)
        pickup_location_list.append(pickup_location)
        pickup_node = Node(pickup_location_id, pickup_location.lat, pickup_location.lng, copy.copy(orders), [])
        pickup_node_list.append(pickup_node)
    
    # delivery node
    delivery_location_list = []
    delivery_node_list = [] # 有多个顾客
    
    for index in range(len(delivery_location_id_list)):
        delivery_location_id = delivery_location_id_list[index]
        delivery_location = id_to_location.get(delivery_location_id)
        delivery_location_list.append(delivery_location)
        delivery_node = Node(delivery_location_id, delivery_location.lat, delivery_location.lng, [], [copy.copy(orders[index])])
        delivery_node_list.append(delivery_node)
    
    return pickup_node_list, delivery_node_list


def __get_pickup_location_id(orders):
    '''
    Get the pickup location id of orders
    订单的pickup location就是餐厅，如果orders来自同一个餐厅，那么所有orders的pickup location都一样
    Input:
    - orders: list of order object
    Output:
    - location_id: list of order pickup location id
    '''
    if len(orders) == 0:
        logger.error("Length of orders is 0")
        return ""

    location_id = []
    for order in orders:
        if order.pickup_location_id not in location_id:
            location_id.append(order.pickup_location_id)

    return location_id


def __get_delivery_location_id(orders):
    '''
    Get the delivery location id of orders
    订单的delivery location是顾客所在地，每个order的delivery location可以不一样
    '''
    if len(orders) == 0:
        logger.error("Length of orders is 0")
        return ""

    location_id = []
    for order in orders:
        # if order.delivery_location_id not in location_id:
            # location_id.append(order.delivery_location_id)
            
        # add for debug
        location_id.append(order.delivery_location_id) # good, solve the bug

    return location_id


def __combine_duplicated_nodes(nodes):
    '''
    合并相邻重复节点 Combine adjacent-duplicated nodes.
    '''
    n = 0
    while n < len(nodes)-1:
        if nodes[n].id == nodes[n+1].id:
            pop_node = nodes.pop(n+1)
            nodes[n].pickup_orders.extend(pop_node.pickup_orders)
            nodes[n].delivery_orders.extend(pop_node.delivery_orders)    
        n += 1


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
                logger.error(f"now left capacity {left_capacity} < 0")
                return left_capacity

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
                    return left_capacity
            # pickup orders
            for order in pickup_orders:
                left_capacity -= order.demand
                if left_capacity < 0:
                    logger.error(f"left capacity {left_capacity} < 0")
                    return left_capacity
        return left_capacity
    




"""

Main body
# Note
# This is the demo to show the main flowchart of the algorithm

"""



def scheduling():
    '''
    派单算法执行程序
    '''

    # read the input json, you can design your own classes
    id_to_location, id_to_restaurant, id_to_unallocated_order, id_to_ongoing_order, id_to_driver = __read_input_json()

    # dispatching algorithm
    driver_id_to_destination, driver_id_to_planned_route, driver_id_to_entire_planned_route = dispatch_orders_to_drivers(
        id_to_unallocated_order,
        id_to_driver,
        id_to_location,
        id_to_restaurant,
        )

    # output the dispatch result
    __output_json(driver_id_to_destination, driver_id_to_planned_route, driver_id_to_entire_planned_route)
    

def __read_input_json():
    '''
    Read the information from json
    '''
    # read the restaurant & customer location info
    id_to_restaurant = get_restaurant_info(Configs.restaurant_info_file_path)
    id_to_customer = get_customer_info(Configs.customer_info_file_path)
    id_to_location = {**id_to_restaurant, **id_to_customer}

    # 未分配的订单
    unallocated_orders = read_json_from_file(Configs.algorithm_unallocated_orders_input_path)
    id_to_unallocated_order = get_order_dict(unallocated_orders, 'Order')

    # 已分配正在运送的订单
    ongoing_orders = read_json_from_file(Configs.algorithm_ongoing_orders_input_path)
    id_to_ongoing_order = get_order_dict(ongoing_orders, 'Order')
    
    # 总的订单
    id_to_order = {**id_to_unallocated_order, **id_to_ongoing_order}

    # 骑手信息
    driver_infos = read_json_from_file(Configs.algorithm_driver_input_info_path)
    id_to_driver = get_driver_instance_dict(driver_infos, id_to_order, id_to_location)

    return id_to_location, id_to_restaurant, id_to_unallocated_order, id_to_ongoing_order,  id_to_driver


def __output_json(driver_id_to_destination, driver_id_to_planned_route, driver_id_to_entire_planned_route):
    '''
    Output the dispatch result to data interaction fold
    '''
    # read json as dict first into a list, then append new dict and write back to json
    if os.path.getsize(Configs.algorithm_output_total_destination_path) == 0:
        total_dispatch_destination = []
    else:
        total_dispatch_destination = read_json_from_file(Configs.algorithm_output_total_destination_path)
    total_dispatch_destination.append(convert_nodes_to_json(driver_id_to_destination))
    write_json_to_file(Configs.algorithm_output_total_destination_path, total_dispatch_destination)
    
    # total planned route
    if os.path.getsize(Configs.algorithm_output_total_planned_route_path) == 0:
        total_dispatch_planned_route = []
    else:
        total_dispatch_planned_route = read_json_from_file(Configs.algorithm_output_total_planned_route_path)
    total_dispatch_planned_route.append(convert_nodes_to_json(driver_id_to_planned_route))
    write_json_to_file(Configs.algorithm_output_total_planned_route_path, total_dispatch_planned_route)
    
    
    # data interaction
    write_json_to_file(Configs.algorithm_output_destination_path, convert_nodes_to_json(driver_id_to_destination))
    write_json_to_file(Configs.algorithm_output_planned_route_path, convert_nodes_to_json(driver_id_to_planned_route))
    write_json_to_file(Configs.algorithm_output_entire_planned_route_path, convert_nodes_to_json(driver_id_to_entire_planned_route))