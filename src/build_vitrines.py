from __future__ import annotations

import os
import random
from typing import List

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spark_session import get_spark
from google_drive_io import download_file_by_name

from generate_data import BASE_DATA_PATH_ENV, DEFAULT_BASE_DATA_PATH, GOOGLE_DRIVE_FOLDER_ENV


def generate_vitrine_b(spark, customers: DataFrame) -> DataFrame:
    rows = []
    for row in customers.collect():
        if random.random() < 0.8:
            rows.append(
                {
                    "id": f"b_{row['customer_id']}",
                    "inn": row["inn"],
                }
            )
    return spark.createDataFrame(rows)


def generate_vitrine_c(spark, vit_a: DataFrame) -> DataFrame:
    """
    Используем cookie_a (на базе _sa_cookie_a) из сырых событий (витрина A).
    Для простоты извлекаем одно значение на customer_id.
    """
    df = vit_a.select("customer_id", "raw_cookie").withColumn(
        "cookie_a",
        F.regexp_extract("raw_cookie", r'"_sa_cookie_a","value":"([^"]+)"', 1),
    )
    df = df.filter(F.col("cookie_a") != "").dropDuplicates(["customer_id", "cookie_a"])

    rows = []
    for row in df.collect():
        rows.append(
            {
                "id": f"c_{row['customer_id']}",
                "cookie_a": row["cookie_a"],
            }
        )
    return spark.createDataFrame(rows)


def generate_vitrine_d(spark, customers: DataFrame) -> DataFrame:
    rows = []
    for row in customers.collect():
        if random.random() < 0.6:
            rows.append(
                {
                    "id": f"d_{row['customer_id']}",
                    "inn": row["inn"],
                }
            )
    return spark.createDataFrame(rows)


def generate_vitrine_e(spark, customers: DataFrame) -> DataFrame:
    rows = []
    for row in customers.collect():
        if random.random() < 0.7:
            rows.append(
                {
                    "id": f"e_{row['customer_id']}",
                    "hash_phone_md5": row["phone_md5"],
                }
            )
    return spark.createDataFrame(rows)


def generate_vitrine_f(spark, customers: DataFrame) -> DataFrame:
    rows = []
    for row in customers.collect():
        if random.random() < 0.7:
            rows.append(
                {
                    "id": f"f_{row['customer_id']}",
                    "hash_email_md5": row["email_md5"],
                }
            )
    return spark.createDataFrame(rows)


def generate_vitrine_g(spark, customers: DataFrame) -> DataFrame:
    rows = []
    for row in customers.collect():
        # часть клиентов получает GAID, часть IDFA
        if random.random() < 0.5:
            rows.append(
                {
                    "match_code": "GAID",
                    "user_uid": row["gaid"],
                    "id": f"g_{row['customer_id']}",
                }
            )
        else:
            rows.append(
                {
                    "match_code": "IDFA",
                    "user_uid": row["idfa"],
                    "id": f"g_{row['customer_id']}",
                }
            )
    return spark.createDataFrame(rows)


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

