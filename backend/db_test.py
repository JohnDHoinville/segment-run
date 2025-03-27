#!/usr/bin/env python3
"""
Database test script for GPX4U application.
This script tests the database connection and provides diagnostic information.
Run it directly on Heroku to verify the database connection.
"""

import os
import sys
import json
import traceback
import psycopg2
from psycopg2.extras import DictCursor
import sqlite3
from urllib.parse import urlparse
from datetime import datetime

def test_database_connection():
    """Test database connection and provide detailed diagnostic information."""
    print("===== GPX4U Database Connection Test =====")
    print(f"Testing database connection at: {datetime.now().isoformat()}")
    
    # Get environment variables
    database_url = os.environ.get('DATABASE_URL')
    flask_env = os.environ.get('FLASK_ENV', 'development')
    dyno = os.environ.get('DYNO', 'local')
    
    print(f"Environment: FLASK_ENV={flask_env}, DYNO={dyno}")
    print(f"DATABASE_URL exists: {database_url is not None}")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "environment": flask_env,
        "is_heroku": dyno is not None,
        "database_url_exists": database_url is not None,
        "tests": []
    }
    
    # Test 1: Parse DATABASE_URL if it exists
    if database_url:
        print("\n----- Test 1: DATABASE_URL parsing -----")
        try:
            # Handle Heroku-specific postgres:// vs postgresql:// prefix
            if database_url.startswith('postgres://'):
                parsed_url = database_url.replace('postgres://', 'postgresql://', 1)
                print("Converted postgres:// to postgresql:// for psycopg2 compatibility")
            else:
                parsed_url = database_url
                
            url = urlparse(parsed_url)
            
            # Mask password for security
            masked_password = "***" if url.password else None
            
            print(f"Protocol: {url.scheme}")
            print(f"Username: {url.username}")
            print(f"Password: {'[MASKED]' if url.password else 'None'}")
            print(f"Host: {url.hostname}")
            print(f"Port: {url.port}")
            print(f"Database: {url.path[1:] if url.path else 'None'}")
            
            results["tests"].append({
                "name": "DATABASE_URL parsing",
                "success": True,
                "details": {
                    "protocol": url.scheme,
                    "host": url.hostname,
                    "port": url.port,
                    "database": url.path[1:] if url.path else 'None',
                    "username": url.username,
                    "has_password": url.password is not None
                }
            })
        except Exception as e:
            print(f"Error parsing DATABASE_URL: {str(e)}")
            traceback.print_exc()
            results["tests"].append({
                "name": "DATABASE_URL parsing",
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    # Test 2: PostgreSQL Connection Test
    print("\n----- Test 2: PostgreSQL Connection Test -----")
    conn = None
    cursor = None
    pg_test_success = False
    
    try:
        if database_url:
            # Handle Heroku-specific postgres:// vs postgresql:// prefix
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
                
            url = urlparse(database_url)
            
            print("Attempting direct connection with individual parameters...")
            conn = psycopg2.connect(
                dbname=url.path[1:] if url.path else 'postgres',
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Test basic query
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"Connected to PostgreSQL: {version}")
            
            # Test database queries
            print("Testing database tables...")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [table[0] for table in cursor.fetchall()]
            print(f"Tables found: {', '.join(tables)}")
            
            # Test users table
            if 'users' in tables:
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                print(f"Users table contains {user_count} records")
            
            # Test runs table
            if 'runs' in tables:
                cursor.execute("SELECT COUNT(*) FROM runs")
                runs_count = cursor.fetchone()[0]
                print(f"Runs table contains {runs_count} records")
            
            pg_test_success = True
            results["tests"].append({
                "name": "PostgreSQL Connection",
                "success": True,
                "details": {
                    "version": version,
                    "tables": tables,
                    "user_count": user_count if 'users' in tables else 0,
                    "runs_count": runs_count if 'runs' in tables else 0
                }
            })
        else:
            print("Skipping PostgreSQL test: No DATABASE_URL found")
            results["tests"].append({
                "name": "PostgreSQL Connection",
                "success": False,
                "error": "No DATABASE_URL found",
                "skipped": True
            })
    except Exception as e:
        print(f"PostgreSQL connection error: {str(e)}")
        traceback.print_exc()
        results["tests"].append({
            "name": "PostgreSQL Connection",
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
    
    # Test 3: SQLite Connection Test
    print("\n----- Test 3: SQLite Connection Test -----")
    sqlite_conn = None
    sqlite_cursor = None
    
    try:
        db_path = 'runs.db'
        print(f"Attempting to connect to SQLite database: {db_path}")
        
        sqlite_conn = sqlite3.connect(db_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Test basic query
        sqlite_cursor.execute("SELECT sqlite_version()")
        version = sqlite_cursor.fetchone()[0]
        print(f"Connected to SQLite: {version}")
        
        # Test tables
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in sqlite_cursor.fetchall()]
        print(f"Tables found: {', '.join(tables)}")
        
        # Test users table
        if 'users' in tables:
            sqlite_cursor.execute("SELECT COUNT(*) FROM users")
            user_count = sqlite_cursor.fetchone()[0]
            print(f"Users table contains {user_count} records")
        
        # Test runs table
        if 'runs' in tables:
            sqlite_cursor.execute("SELECT COUNT(*) FROM runs")
            runs_count = sqlite_cursor.fetchone()[0]
            print(f"Runs table contains {runs_count} records")
        
        results["tests"].append({
            "name": "SQLite Connection",
            "success": True,
            "details": {
                "version": version,
                "tables": tables,
                "user_count": user_count if 'users' in tables else 0,
                "runs_count": runs_count if 'runs' in tables else 0
            }
        })
    except Exception as e:
        print(f"SQLite connection error: {str(e)}")
        traceback.print_exc()
        results["tests"].append({
            "name": "SQLite Connection",
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        if sqlite_cursor:
            try:
                sqlite_cursor.close()
            except:
                pass
        if sqlite_conn:
            try:
                sqlite_conn.close()
            except:
                pass
    
    # Test 4: Test Data Write
    print("\n----- Test 4: Test Data Write -----")
    
    if pg_test_success:
        try:
            print("Testing data write to PostgreSQL...")
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # Create test table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_tests (
                    id SERIAL PRIMARY KEY,
                    test_time TIMESTAMP,
                    test_data JSONB
                )
            """)
            
            # Insert test data
            test_data = {
                "test_time": datetime.now().isoformat(),
                "environment": flask_env
            }
            
            cursor.execute(
                "INSERT INTO connection_tests (test_time, test_data) VALUES (%s, %s) RETURNING id",
                (datetime.now(), json.dumps(test_data))
            )
            
            test_id = cursor.fetchone()[0]
            conn.commit()
            
            print(f"Test data written with ID: {test_id}")
            
            # Read it back
            cursor.execute("SELECT * FROM connection_tests WHERE id = %s", (test_id,))
            test_record = cursor.fetchone()
            
            if test_record:
                print("Successfully read back test data")
                results["tests"].append({
                    "name": "PostgreSQL Write Test",
                    "success": True,
                    "details": {
                        "record_id": test_id
                    }
                })
            else:
                print("Failed to read back test data")
                results["tests"].append({
                    "name": "PostgreSQL Write Test",
                    "success": False,
                    "error": "Data was written but could not be read back"
                })
                
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"PostgreSQL write test error: {str(e)}")
            traceback.print_exc()
            results["tests"].append({
                "name": "PostgreSQL Write Test",
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    else:
        print("Skipping PostgreSQL write test: Connection failed earlier")
        results["tests"].append({
            "name": "PostgreSQL Write Test",
            "success": False,
            "error": "PostgreSQL connection failed earlier",
            "skipped": True
        })
    
    # Calculate overall status
    success_count = sum(1 for test in results["tests"] if test.get("success", False))
    total_tests = sum(1 for test in results["tests"] if not test.get("skipped", False))
    
    results["summary"] = {
        "total_tests": total_tests,
        "successful_tests": success_count,
        "overall_success": success_count == total_tests and total_tests > 0
    }
    
    print("\n===== Test Results Summary =====")
    print(f"Total tests: {total_tests}")
    print(f"Successful tests: {success_count}")
    print(f"Overall success: {results['summary']['overall_success']}")
    
    return results

if __name__ == "__main__":
    try:
        results = test_database_connection()
        
        # Print final summary
        if results["summary"]["overall_success"]:
            print("\n✓ All database tests passed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some database tests failed. Review the output for details.")
            sys.exit(1)
    except Exception as e:
        print(f"Critical error running tests: {str(e)}")
        traceback.print_exc()
        sys.exit(2) 