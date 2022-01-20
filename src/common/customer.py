class Customer(object):
    def __init__(self, customer_id: str, lat: float, lng: float):
        '''
        Inputs: customer can connect to orders
        - customer_id: 顾客订单编号
        - lat: 地理位置纬度 
        - lng: 地理位置经度
        '''
        self.id = customer_id
        self.lat = lat
        self.lng = lng