# Not used now

class Restaurant(object):
    def __init__(self, restaurant_id: str, lat: float, lng: float, d_radius: int, c_radius: int, wait_time: int):
        '''
        Inputs: 
        - restaurant_id: index of restaurant 
        - lat: restaurant latitude
        - lng: restaurant longitude
        - d_radius: radius of courier dispatch area
        - c_radius: radius of customer service area 
        - wait_time: avg waiting time at restaurant, 和node中的loading time结合
        '''
        self.id = str(restaurant_id)
        self.lat = float(lat)
        self.lng = float(lng)
        self.dispatch_radius = int(d_radius)
        self.customer_radius = int(c_radius)
        self.wait_time = int(wait_time)

        