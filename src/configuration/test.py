import os

print("this file path:", os.path.abspath(__file__))
root_folder_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print("root folder path:", root_folder_path)
benchmark_folder_path = os.path.join(root_folder_path, "Benchmark")
print("benthmark folder path:", benchmark_folder_path)