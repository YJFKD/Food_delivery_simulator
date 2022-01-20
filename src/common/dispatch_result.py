class DispatchResult(object):
    """ 
    Output of the dispatching algorithm
    """
    def __init__(self, driver_id_to_destination: dict, driver_id_to_planned_route: dict):
        """
        - driver_id_to_destination: {driver id, destination(next node) of the driver}
        - driver_id_to_planned_route: {driver id, planned route(except the destination) of driver, namely node list}
        """
        # Have to return the destination of each driver. If the driver has no destination (stand-by, e.t.c), the destination is None
        self.driver_id_to_destination = driver_id_to_destination
        # Have to return the planned route of each driver. Set the value [] when the driver has no planned route
        self.driver_id_to_planned_route = driver_id_to_planned_route