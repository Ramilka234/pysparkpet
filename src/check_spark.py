from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("check-spark")
    .master("local[*]")
    .getOrCreate()
)

df = spark.range(10)

df.show()

spark.stop()