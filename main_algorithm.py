# 派单算法主程序
import traceback

from src.utils.logging_engine import logger
from Algorithm.algorithm_demo import scheduling


if __name__ == '__main__':
    try:
        scheduling()
        print("SUCCESS")
    except Exception as e:
        logger.error("Failed to run algorithm")
        logger.error(f"Error: {e}, {traceback.format_exc()}")
        print("FAIL")