#!/usr/bin/env python3
"""
Data Migration Script: SQLite to PostgreSQL Microservices
Transfers all data from the original db.sqlite3 to the new microservices databases.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from decimal import Decimal

import psycopg2

# Database configurations
SQLITE_DB_PATH = (
    "/home/sneha/Downloads/project/django-student-management-system-master/db.sqlite3"
)
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "postgres",
    "password": "password",
}

# Microservice database mappings
MICROSERVICE_DBS = {
    "user_service_db": [
        "auth_user",
        "student_management_app_customuser",
        "student_management_app_adminhod",
        "student_management_app_staffs",
        "student_management_app_students",
    ],
    "academic_service_db": [
        "student_management_app_sessionyearmodel",
        "student_management_app_courses",
        "student_management_app_subjects",
    ],
    "attendance_service_db": [
        "student_management_app_attendance",
        "student_management_app_attendancereport",
    ],
    "leave_management_db": [
        "student_management_app_leavereportstudent",
        "student_management_app_leavereportstaff",
    ],
    "feedback_service_db": [
        "student_management_app_feedbackstudent",
        "student_management_app_feedbackstaffs",
    ],
    "notification_service_db": [
        "student_management_app_notificationstudent",
        "student_management_app_notificationstaffs",
    ],
    "assessment_service_db": [
        "student_management_app_studentresult",
        "student_management_app_assignment",
        "student_management_app_assignmentsubmission",
    ],
    "financial_service_db": [
        "student_management_app_fine",
        "student_management_app_finepayment",
    ],
}


class DataMigrator:
    def __init__(self):
        self.sqlite_conn = None
        self.postgres_connections = {}

    def connect_sqlite(self):
        """Connect to SQLite database"""
        try:
            self.sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
            self.sqlite_conn.row_factory = sqlite3.Row
            print(f"✅ Connected to SQLite database: {SQLITE_DB_PATH}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to SQLite: {e}")
            return False

    def connect_postgres(self, db_name):
        """Connect to PostgreSQL database"""
        try:
            conn = psycopg2.connect(
                host=POSTGRES_CONFIG["host"],
                port=POSTGRES_CONFIG["port"],
                database=db_name,
                user=POSTGRES_CONFIG["user"],
                password=POSTGRES_CONFIG["password"],
            )
            self.postgres_connections[db_name] = conn
            print(f"✅ Connected to PostgreSQL database: {db_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL {db_name}: {e}")
            return False

    def get_sqlite_tables(self):
        """Get all tables from SQLite database"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        return [
            t for t in tables if not t.startswith("django_") and t != "sqlite_sequence"
        ]

    def get_table_data(self, table_name):
        """Get all data from a SQLite table"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        return columns, rows

    def create_postgres_table_if_not_exists(
        self, db_name, table_name, columns, sample_row
    ):
        """Create PostgreSQL table based on SQLite structure"""
        conn = self.postgres_connections[db_name]
        cursor = conn.cursor()

        # Map SQLite types to PostgreSQL types
        column_definitions = []
        for i, col in enumerate(columns):
            value = sample_row[i] if sample_row else None

            if col == "id":
                col_type = "SERIAL PRIMARY KEY"
            elif isinstance(value, int):
                col_type = "INTEGER"
            elif isinstance(value, float):
                col_type = "REAL"
            elif isinstance(value, str):
                if len(str(value)) > 255:
                    col_type = "TEXT"
                else:
                    col_type = "VARCHAR(255)"
            elif "date" in col.lower():
                if "time" in col.lower():
                    col_type = "TIMESTAMP"
                else:
                    col_type = "DATE"
            else:
                col_type = "TEXT"

            if col != "id":
                column_definitions.append(f"{col} {col_type}")

        if column_definitions:
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                {', '.join(column_definitions)}
            )
            """
        else:
            create_sql = (
                f"CREATE TABLE IF NOT EXISTS {table_name} (id SERIAL PRIMARY KEY)"
            )

        try:
            cursor.execute(create_sql)
            conn.commit()
            print(f"✅ Created/verified table: {table_name}")
        except Exception as e:
            print(f"❌ Failed to create table {table_name}: {e}")
            conn.rollback()

    def insert_data_to_postgres(self, db_name, table_name, columns, rows):
        """Insert data into PostgreSQL table"""
        if not rows:
            print(f"⚠️  No data to migrate for table: {table_name}")
            return

        conn = self.postgres_connections[db_name]
        cursor = conn.cursor()

        # Prepare insert statement
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = (
            f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        )

        try:
            # Convert rows to list of tuples
            data_to_insert = []
            for row in rows:
                row_data = []
                for value in row:
                    if value is None:
                        row_data.append(None)
                    elif isinstance(value, str) and value.strip() == "":
                        row_data.append(None)
                    else:
                        row_data.append(value)
                data_to_insert.append(tuple(row_data))

            cursor.executemany(insert_sql, data_to_insert)
            conn.commit()
            print(f"✅ Migrated {len(data_to_insert)} records to {table_name}")
        except Exception as e:
            print(f"❌ Failed to insert data into {table_name}: {e}")
            conn.rollback()

    def migrate_table(self, table_name, target_db):
        """Migrate a single table to target database"""
        print(f"\n🔄 Migrating table: {table_name} -> {target_db}")

        # Get data from SQLite
        columns, rows = self.get_table_data(table_name)

        if not rows:
            print(f"⚠️  Table {table_name} is empty, skipping...")
            return

        # Create table in PostgreSQL if needed
        self.create_postgres_table_if_not_exists(
            target_db, table_name, columns, rows[0] if rows else None
        )

        # Insert data
        self.insert_data_to_postgres(target_db, table_name, columns, rows)

    def migrate_all_data(self):
        """Main migration function"""
        print("🚀 Starting data migration from SQLite to PostgreSQL microservices...")

        # Connect to SQLite
        if not self.connect_sqlite():
            return False

        # Connect to all PostgreSQL databases
        for db_name in MICROSERVICE_DBS.keys():
            if not self.connect_postgres(db_name):
                return False

        # Get all tables from SQLite
        sqlite_tables = self.get_sqlite_tables()
        print(f"📋 Found {len(sqlite_tables)} tables in SQLite: {sqlite_tables}")

        # Migrate tables to appropriate microservices
        for db_name, table_list in MICROSERVICE_DBS.items():
            print(f"\n🎯 Migrating to {db_name}...")
            for table_name in table_list:
                if table_name in sqlite_tables:
                    self.migrate_table(table_name, db_name)
                else:
                    print(f"⚠️  Table {table_name} not found in SQLite database")

        # Handle any remaining tables
        migrated_tables = []
        for table_list in MICROSERVICE_DBS.values():
            migrated_tables.extend(table_list)

        remaining_tables = set(sqlite_tables) - set(migrated_tables)
        if remaining_tables:
            print(f"\n⚠️  Unmapped tables found: {remaining_tables}")
            print(
                "These tables were not migrated. Please review and add to mapping if needed."
            )

        print("\n✅ Data migration completed!")
        return True

    def close_connections(self):
        """Close all database connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()

        for conn in self.postgres_connections.values():
            conn.close()

        print("🔌 All database connections closed")

    def verify_migration(self):
        """Verify data migration by comparing record counts"""
        print("\n🔍 Verifying migration...")

        sqlite_cursor = self.sqlite_conn.cursor()

        for db_name, table_list in MICROSERVICE_DBS.items():
            print(f"\n📊 Verifying {db_name}:")
            postgres_conn = self.postgres_connections[db_name]
            postgres_cursor = postgres_conn.cursor()

            for table_name in table_list:
                try:
                    # Count records in SQLite
                    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    sqlite_count = sqlite_cursor.fetchone()[0]

                    # Count records in PostgreSQL
                    postgres_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    postgres_count = postgres_cursor.fetchone()[0]

                    if sqlite_count == postgres_count:
                        print(f"  ✅ {table_name}: {sqlite_count} records")
                    else:
                        print(
                            f"  ❌ {table_name}: SQLite({sqlite_count}) != PostgreSQL({postgres_count})"
                        )

                except Exception as e:
                    print(f"  ⚠️  {table_name}: Could not verify - {e}")


def main():
    """Main execution function"""
    print("=" * 60)
    print("🔄 Django Student Management System - Data Migration")
    print("   SQLite → PostgreSQL Microservices")
    print("=" * 60)

    # Check if SQLite file exists
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ SQLite database not found: {SQLITE_DB_PATH}")
        print("Please ensure the original db.sqlite3 file exists.")
        return False

    migrator = DataMigrator()

    try:
        success = migrator.migrate_all_data()
        if success:
            migrator.verify_migration()
        return success
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        return False
    finally:
        migrator.close_connections()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
