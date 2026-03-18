from __future__ import annotations

import os
from typing import List

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

from spark_session import get_spark
from google_drive_io import download_file_by_name

from generate_data import BASE_DATA_PATH_ENV, DEFAULT_BASE_DATA_PATH, GOOGLE_DRIVE_FOLDER_ENV


def generate_vitrine_b(spark, customers: DataFrame) -> DataFrame:
    rnd = F.rand()
    return (
        customers
        .withColumn("_keep", rnd < F.lit(0.8))
        .where(F.col("_keep"))
        .select(
            F.concat(F.lit("b_"), F.col("customer_id").cast("string")).alias("id"),
            F.col("inn").alias("inn"),
        )
        .drop("_keep")
    )


def generate_vitrine_c(spark, vit_a: DataFrame) -> DataFrame:
    cookie_schema = T.ArrayType(
        T.StructType(
            [
                T.StructField("key", T.StringType(), True),
                T.StructField("value", T.StringType(), True),
            ]
        )
    )

    cookies = F.from_json(F.trim(F.col("raw_cookie")), cookie_schema)

    exploded = (
        vit_a
        .select(
            F.col("customer_id").cast("string").alias("customer_id"),
            cookies.alias("cookies"),
        )
        .withColumn("cookie", F.explode_outer(F.col("cookies")))
        .select(
            "customer_id",
            F.col("cookie.key").alias("cookie_key"),
            F.col("cookie.value").alias("cookie_value"),
        )
        .where(F.col("cookie_key") == F.lit("_sa_cookie_a"))
        .where(F.col("cookie_value").isNotNull() & (F.length(F.col("cookie_value")) > 0))
        .dropDuplicates(["customer_id", "cookie_value"])
    )

    return (
        exploded
        .select(
            F.concat(F.lit("c_"), F.col("customer_id")).alias("id"),
            F.col("cookie_value").alias("cookie_a"),
        )
    )


def generate_vitrine_d(spark, customers: DataFrame) -> DataFrame:
    rnd = F.rand()
    return (
        customers
        .withColumn("_keep", rnd < F.lit(0.6))
        .where(F.col("_keep"))
        .select(
            F.concat(F.lit("d_"), F.col("customer_id").cast("string")).alias("id"),
            F.col("inn").alias("inn"),
        )
        .drop("_keep")
    )


def generate_vitrine_e(spark, customers: DataFrame) -> DataFrame:
    rnd = F.rand()
    return (
        customers
        .withColumn("_keep", rnd < F.lit(0.7))
        .where(F.col("_keep"))
        .select(
            F.concat(F.lit("e_"), F.col("customer_id").cast("string")).alias("id"),
            F.col("phone_md5").alias("hash_phone_md5"),
        )
        .drop("_keep")
    )


def generate_vitrine_f(spark, customers: DataFrame) -> DataFrame:
    rnd = F.rand()
    return (
        customers
        .withColumn("_keep", rnd < F.lit(0.7))
        .where(F.col("_keep"))
        .select(
            F.concat(F.lit("f_"), F.col("customer_id").cast("string")).alias("id"),
            F.col("email_md5").alias("hash_email_md5"),
        )
        .drop("_keep")
    )


def generate_vitrine_g(spark, customers: DataFrame) -> DataFrame:
    rnd = F.rand()
    match_code = F.when(rnd < F.lit(0.5), F.lit("GAID")).otherwise(F.lit("IDFA"))
    user_uid = F.when(rnd < F.lit(0.5), F.col("gaid")).otherwise(F.col("idfa"))
    return (
        customers
        .select(
            match_code.alias("match_code"),
            user_uid.alias("user_uid"),
            F.concat(F.lit("g_"), F.col("customer_id").cast("string")).alias("id"),
        )
    )


def write_vitrine(df: DataFrame, path: str, partition_by: List[str] | None = None) -> None:
    writer = df.write.mode("overwrite")
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.parquet(path)


def main() -> None:
    spark = get_spark("build-vitrines")

    base_path = os.getenv(BASE_DATA_PATH_ENV, DEFAULT_BASE_DATA_PATH)
    base_path = base_path.rstrip("/")
    drive_folder_id = os.getenv(GOOGLE_DRIVE_FOLDER_ENV)
    if not drive_folder_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID is not set in environment/.env")

    tmp_dir = "/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    customers_csv = os.path.join(tmp_dir, "raw_customers.csv")
    events_csv = os.path.join(tmp_dir, "raw_events.csv")

    download_file_by_name(drive_folder_id, "raw_customers.csv", customers_csv)
    download_file_by_name(drive_folder_id, "raw_events.csv", events_csv)

    customers = (
        spark.read
        .option("header", "true")
        .csv(customers_csv)
    )
    vit_a = (
        spark.read
        .option("header", "true")
        .csv(events_csv)
    )

    vit_b = generate_vitrine_b(spark, customers)
    write_vitrine(vit_b, f"{base_path}/vitrine_b")

    vit_c = generate_vitrine_c(spark, vit_a)
    write_vitrine(vit_c, f"{base_path}/vitrine_c")

    vit_d = generate_vitrine_d(spark, customers)
    write_vitrine(vit_d, f"{base_path}/vitrine_d")

    vit_e = generate_vitrine_e(spark, customers)
    write_vitrine(vit_e, f"{base_path}/vitrine_e")

    vit_f = generate_vitrine_f(spark, customers)
    write_vitrine(vit_f, f"{base_path}/vitrine_f")

    vit_g = generate_vitrine_g(spark, customers)
    write_vitrine(vit_g, f"{base_path}/vitrine_g")

    print(f"Vitrines B–G built under base path: {base_path}")


if __name__ == "__main__":
    main()

