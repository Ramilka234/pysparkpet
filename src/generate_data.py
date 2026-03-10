from __future__ import annotations

import os
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any

from pyspark.sql import DataFrame
from spark_session import get_spark


BASE_DATA_PATH_ENV = "DATA_BASE_PATH"
DEFAULT_BASE_DATA_PATH = "/app/data"


def _random_digits(n: int) -> str:
    return "".join(random.choice(string.digits) for _ in range(n))


def _random_letters(n: int) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(n))


def _hash_md5(s: str) -> str:
    import hashlib

    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _hash_sha256(s: str) -> str:
    import hashlib

    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def generate_customers(spark, n_customers: int = 100) -> DataFrame:
    """
    Базовая таблица "клиентов", от которой будут строиться витрины A–G.
    """
    rows: List[Dict[str, Any]] = []
    domains = ["example.com", "mail.io", "test.org"]

    for i in range(n_customers):
        inn = _random_digits(12)
        phone = f"+7{_random_digits(10)}"
        email_local = _random_letters(8)
        email_domain = random.choice(domains)
        email = f"{email_local}@{email_domain}"

        site_user_id = f"site_{1000 + i}"
        gaid = f"gaid-{_random_letters(8)}-{_random_letters(4)}"
        idfa = f"idfa-{_random_letters(8)}-{_random_letters(4)}"

        rows.append(
            {
                "customer_id": i,
                "inn": inn,
                "phone": phone,
                "email": email,
                "site_user_id": site_user_id,
                "gaid": gaid,
                "idfa": idfa,
                "inn_md5": _hash_md5(inn),
                "inn_sha256": _hash_sha256(inn),
                "phone_md5": _hash_md5(phone),
                "email_md5": _hash_md5(email),
            }
        )

    return spark.createDataFrame(rows)


def generate_raw_events(spark, customers: DataFrame, days: int = 3) -> DataFrame:
    """
    Генерация сырых событий (аналог витрины A), партиционированных по дате.
    Заполняем колонку raw_cookie сложной структурой, как в ТЗ.
    """
    base_date = datetime(2023, 1, 1)
    event_types = ["SUBMIT", "REGISTER", "SUBMIT_MD5"]
    event_actions = ["pageview", "event", "login-check-otp"]
    countries = ["Russia", "Mongolia", "USA"]
    cities = ["Moscow", "Ulan-Batar", "New York"]
    oss = ["Windows", "Mac", "Linux", "Android", "iOS"]
    languages = ["RU", "ENG"]
    platforms = ["WEB", "MOBILE"]
    screens = ["1920x1080", "1366x768", "1080x1920"]

    customers_local = customers.collect()
    events: List[Dict[str, Any]] = []

    for d in range(days):
        event_date = (base_date + timedelta(days=d)).date()
        for c in customers_local:
            # Количество событий на клиента в день
            for _ in range(random.randint(1, 5)):
                event_type = random.choice(event_types)
                event_action = random.choice(event_actions)

                # data_value: хэш ИНН в зависимости от event_type
                if event_type == "SUBMIT_MD5":
                    data_value = c["inn_md5"]
                elif event_type == "SUBMIT":
                    data_value = c["inn_sha256"]
                else:
                    data_value = None

                # raw_cookie — список пар key/value, сериализованный в JSON
                cookie_struct = [
                    {"key": "_sa_cookie_a", "value": f"SA1.{c['inn_md5']}.{int(base_date.timestamp())}"},
                    {"key": "_fa_cookie_b", "value": f"ads2.{c['phone_md5']}.{int(base_date.timestamp())}"},
                    {"key": "_ym_cookie_c", "value": _random_digits(20)},
                    {"key": "_fbp", "value": f"fb.1.{_random_digits(13)}.{_random_digits(9)}"},
                    {"key": "org_uid", "value": str(c["customer_id"])},
                    {"key": "user_uid", "value": c["site_user_id"]},
                    {"key": "user_phone", "value": c["phone"]},
                    {"key": "user_mail", "value": c["email"]},
                ]

                import json

                raw_cookie = json.dumps(cookie_struct, ensure_ascii=False)

                ts = datetime.combine(event_date, datetime.min.time()) + timedelta(
                    seconds=random.randint(0, 86399)
                )

                events.append(
                    {
                        "event_id": f"evt_{c['customer_id']}_{event_date}_{random.randint(1, 1_000_000)}",
                        "raw_cookie": raw_cookie,
                        "event_type": event_type,
                        "event_action": event_action,
                        "data_value": data_value,
                        "geocountry": random.choice(countries),
                        "city": random.choice(cities),
                        "user_os": random.choice(oss),
                        "systemlanguage": random.choice(languages),
                        "geoaltitude": float(f"{random.uniform(0, 500):.3f}"),
                        "meta_platform": random.choice(platforms),
                        "screensize": random.choice(screens),
                        "timestampcolumn": ts,
                        "event_date": str(event_date),
                        "customer_id": c["customer_id"],
                    }
                )

def write_dataset(df: DataFrame, path: str, partition_by: List[str] | None = None) -> None:
    writer = df.write.mode("overwrite")
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.parquet(path)


def main() -> None:
    spark = get_spark("generate-data")

    base_path = os.getenv(BASE_DATA_PATH_ENV, DEFAULT_BASE_DATA_PATH)
    base_path = base_path.rstrip("/")

    customers = generate_customers(spark, n_customers=100)
    write_dataset(customers, f"{base_path}/raw/customers")

    raw_events = generate_raw_events(spark, customers, days=3)
    write_dataset(raw_events, f"{base_path}/raw/events", partition_by=["event_date"])

    print(f"Raw synthetic data generated under base path: {base_path}")


if __name__ == "__main__":
    main()
