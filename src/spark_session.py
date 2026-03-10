from pyspark.sql import SparkSession
from dotenv import load_dotenv
import os


# Загружаем переменные окружения из .env один раз при импорте модуля
load_dotenv()


def get_spark(app_name: str = "identity-mart") -> SparkSession:
   

    master = os.getenv("SPARK_MASTER", "local[*]")
    warehouse_dir = os.getenv("SPARK_WAREHOUSE_DIR", "/app/data/warehouse")
    shuffle_partitions = os.getenv("SPARK_SHUFFLE_PARTITIONS", "4")
    driver_memory = os.getenv("SPARK_DRIVER_MEMORY", "2g")
    executor_memory = os.getenv("SPARK_EXECUTOR_MEMORY", "2g")

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.sql.warehouse.dir", warehouse_dir)
        .config("spark.sql.shuffle.partitions", shuffle_partitions)
        .config("spark.driver.memory", driver_memory)
        .config("spark.executor.memory", executor_memory)
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    return spark