from asyncio.log import logger
import sys


class RouteInfo(object):
    def __init__(self, route_id: str, start_location_id: str, end_location_id: str, distance: float, time: float):
        '''
        路线类
        Inputs:
        - route_id: index of the route
        - start_location_id: start location id
        - end_location_id: end location id
        - distance: route distance
        - time: route travel time 
        '''
        self.route_id = str(route_id)
        self.start_location_id = str(start_location_id)
        self.end_location_id = str(end_location_id)
        self.distance = float(distance)
        self.time = float(time)



class Map(object):
    def __init__(self, id_to_route):
        '''
        Input:
        - id_to_route: dict, {key: route_id, value: route}
        '''
        self.__id_to_route = id_to_route
        # get the distance between locations, unit is km
        self.__location_id_pair_to_distance = self.__get_distance_matrix_between_locations()
        # get the time between locations, unit is mins
        self.__location_id_pair_to_time = self.__get_time_matrix_between_locations()


    def __get_distance_matrix_between_locations(self):
        '''
        Get all locations distance matrix
        Output: dict, {key: (start location, end location), value: distance}
        '''
        if len(self.__id_to_route) == 0:
            return
        # define distance matrix
        dist_matrix = {}
        for route_id, route in self.__id_to_route.items():
            if (route.start_location_id, route.end_location_id) not in dist_matrix:
                dist_matrix[(route.start_location_id, route.end_location_id)] = route.distance
        
        return dist_matrix
    
    
    def __get_time_matrix_between_locations(self):
        '''
        Get all locations time matrix
        Output: dict, {key: (start location, end location), value: travel time}
        '''
        if len(self.__id_to_route) == 0:
            return 
        # define time matrix
        time_matrix = {}
        for route_id, route in self.__id_to_route.items():
            if (route.start_location_id, route.end_location_id) not in time_matrix:
                time_matrix[(route.start_location_id, route.end_location_id)] = route.time 
        
        return time_matrix


    def calculate_distance_between_locations(self, org_location_id, dest_location_id):
        '''
        计算origin和destination的距离
        '''
        if org_location_id == dest_location_id:
            return 0
        
        if (org_location_id, dest_location_id) in self.__location_id_pair_to_distance:
            return self.__location_id_pair_to_distance.get((org_location_id, dest_location_id))
        elif (dest_location_id, org_location_id) in self.__location_id_pair_to_distance:
            return self.__location_id_pair_to_distance.get((dest_location_id, org_location_id))
        else:
            logger.error(f"({org_location_id}, {dest_location_id}) is not in distance matrix.")
            return sys.maxsize
    

    def calculate_time_between_locations(self, org_location_id, dest_location_id):
        '''
        计算origin和destination的时间
        '''
        if org_location_id == dest_location_id:
            return 0
        
        if (org_location_id, dest_location_id) in self.__location_id_pair_to_distance:
            return self.__location_id_pair_to_time.get((org_location_id, dest_location_id))
        elif (dest_location_id, org_location_id) in self.__location_id_pair_to_distance:
            return self.__location_id_pair_to_time.get((dest_location_id, org_location_id))
        else:
            logger.error(f"({org_location_id}, {dest_location_id}) is not in time matrix.")
            return sys.maxsize