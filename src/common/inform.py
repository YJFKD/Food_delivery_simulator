class InputInform(object):
    def __init__(self, id_to_unallocated_order: dict, id_to_ongoing_order: 
                    dict, id_to_driver: dict, id_to_location: dict, route_map):
        '''
        汇总所有的Input信息，包括车辆信息(车辆当前的位置信息&装载货物), 订单信息(待分配和进行中), 路网信息
        Inputs: 
        - id_to_unallocated_order: Dict, {key: id, value: order object (state: 'GENERATED')}
        - id_to_ongoing_order: Dict, {key: id, value: order object (state: 'ONGOING')}
        - id_to_driver: Dict, {key: driver id, value: driver object}
        - id_to_location: Dict, {key: location id, value: location object (customer + restaurant + driver)}
        - route_map: travel distance and time matrix between locations
        '''
        self.id_to_unallocated_order = id_to_unallocated_order
        self.id_to_ongoing_order = id_to_ongoing_order
        self.id_to_driver = id_to_driver
        self.id_to_location = id_to_location
        self.route_map = route_map