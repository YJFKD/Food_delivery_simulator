import os


class Configs(object):
    MAX_SCORE = 999999999
    
    # 多目标权重之间的系数
    LAMDA = 10000

    # Time interval of the algorithm
    ALG_RUN_FREQUENCY = 10  # minute
    ORDER_STATUS_TO_CODE = {"INITIALIZATION": 0, "GENERATED": 1, "ONGOING": 2, "COMPLETED": 3}

    # file path
    root_folder_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    benchmark_folder_path = os.path.join(root_folder_path, "Benchmark")
    src_folder_path = os.path.join(root_folder_path, "src")
    algorithm_folder_path = os.path.join(root_folder_path, "Algorithm")
    output_folder = os.path.join(src_folder_path, "Output")
    # if output folder not exit
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # route, location data 
    route_info_file = "route_info.csv"
    restaurant_info_file = "restaurant_info.csv"
    customer_info_file = "customer_info.csv"
    
    route_info_file_path = os.path.join(benchmark_folder_path, route_info_file)
    restaurant_info_file_path = os.path.join(benchmark_folder_path, restaurant_info_file)
    customer_info_file_path = os.path.join(benchmark_folder_path, customer_info_file)

    # algorithm file
    algorithm_data_interaction_folder_path = os.path.join(algorithm_folder_path, "data_interaction")
    if not os.path.exists(algorithm_data_interaction_folder_path):
        os.makedirs(algorithm_data_interaction_folder_path)
    algorithm_driver_input_info_path = os.path.join(algorithm_data_interaction_folder_path, "driver_info.json")
    algorithm_unallocated_orders_input_path = os.path.join(algorithm_data_interaction_folder_path,
                                                                "unallocated_orders.json")
    algorithm_ongoing_orders_input_path = os.path.join(algorithm_data_interaction_folder_path,
                                                            "ongoing_orders.json")
    algorithm_output_destination_path = os.path.join(algorithm_data_interaction_folder_path, 'output_destination.json')
    algorithm_output_planned_route_path = os.path.join(algorithm_data_interaction_folder_path, 'output_route.json')

    ALGORITHM_ENTRY_FILE_NAME = 'main_algorithm'
    
    # programming language
    ALGORITHM_LANGUAGE_MAP = {'py': 'python',
                              'class': 'java',
                              'exe': 'c',
                              'out': 'c',
                              }

    # random seed
    RANDOM_SEED = 0

    # limitation of algorithm running time
    MAX_RUNTIME_OF_ALGORITHM = 600

    # algorithm running success or not
    ALGORITHM_SUCCESS_FLAG = 'SUCCESS'

    # maximum number of log files
    MAX_LOG_FILE_NUM = 100

    # total seconds in a day
    A_DAY_TIME_SECONDS = 24 * 60 * 60

    # dataset choice, if empty means all dataset, e.g., []，[1], [1, 2, 3], [64]
    selected_instances = [3]
    all_test_instances = range(1, 65)