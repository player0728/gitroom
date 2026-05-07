#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SeaTunnel 交互式配置工具 
更友好的终端交互体验
支持 MySQL->MySQL (CDC/batch)、API->MySQL、达梦数据库直接同步 数据同步
成功
"""

import os
import sys
import subprocess
import getpass
from datetime import datetime
from pathlib import Path
import socket
import re

try:
    import mysql.connector
except ImportError:
    mysql_connector_available = False
else:
    mysql_connector_available = True

# 达梦 ODBC 连接器
try:
    import pyodbc
except ImportError:
    pyodbc_available = False
else:
    pyodbc_available = True

class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 50}{Colors.NC}")
    print(f"{Colors.BLUE}  {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.NC}\n")

def print_step(step_num, text):
    print(f"{Colors.YELLOW}【步骤 {step_num}/5】{text}{Colors.NC}\n")

def print_success(text):
    print(f"\n{Colors.GREEN}✓ {text}{Colors.NC}\n")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def get_input(prompt, default=None, required=False, hide=False):
    while True:
        if hide:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)

        if not value and default:
            return default

        if required and not value:
            print_error("此项不能为空")
            continue

        return value

def test_mysql_connection(host, port, user, password, database):
    """测试 MySQL 连接"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，跳过连接测试{Colors.NC}")
        return True

    print(f"\n{Colors.BLUE}正在测试 MySQL 连接...{Colors.NC}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, int(port)))
        sock.close()
        print(f"{Colors.GREEN}✓ 端口 {port} 可访问{Colors.NC}")

        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        conn.close()
        print(f"{Colors.GREEN}✓ 数据库连接成功{Colors.NC}")
        return True
    except socket.error as e:
        print_error(f"连接失败：端口 {port} 不可达 - {e}")
        return False
    except mysql.connector.Error as e:
        if "Access denied" in str(e):
            print_error(f"连接失败：用户名或密码错误")
        elif "Unknown database" in str(e):
            print_error(f"连接失败：数据库 '{database}' 不存在")
        else:
            print_error(f"连接失败：{e}")
        return False

def create_database(host, port, user, password, database):
    """创建数据库"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，无法创建数据库{Colors.NC}")
        return False
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()
        print(f"{Colors.GREEN}✓ 数据库 '{database}' 创建成功{Colors.NC}")
        return True
    except mysql.connector.Error as e:
        print_error(f"创建数据库失败：{e}")
        return False

def verify_table_exists(host, port, user, password, database, table):
    """验证表是否存在"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，跳过表验证{Colors.NC}")
        return True
    
    print(f"{Colors.BLUE}正在验证表 '{table}' 是否存在...{Colors.NC}")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"SHOW TABLES LIKE '{table}'")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            print(f"{Colors.GREEN}✓ 表 '{table}' 存在{Colors.NC}")
            return True
        else:
            print_error(f"表 '{table}' 不存在")
            return False
    except mysql.connector.Error as e:
        print_error(f"验证表失败：{e}")
        return False

def get_databases(host, port, user, password):
    """获取所有可用的数据库"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，无法获取数据库列表{Colors.NC}")
        return None
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [row[0] for row in cursor.fetchall()]
        # 过滤掉系统数据库
        system_dbs = ['information_schema', 'mysql', 'performance_schema', 'sys']
        databases = [db for db in databases if db not in system_dbs]
        cursor.close()
        conn.close()
        return databases
    except mysql.connector.Error as e:
        print_error(f"获取数据库列表失败：{e}")
        return None


def get_database_tables(host, port, user, password, database):
    """获取数据库中的所有表"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，无法获取表列表{Colors.NC}")
        return None
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except mysql.connector.Error as e:
        print_error(f"获取表列表失败：{e}")
        return None

def get_table_columns(host, port, user, password, database, table):
    """获取表的所有列名及类型"""
    if not mysql_connector_available:
        return None
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE `{table}`")
        columns = []
        for row in cursor.fetchall():
            column_name = row[0]
            column_type = row[1]
            # 简化类型映射
            if 'int' in str(column_type).lower():
                mapped_type = 'INT'
            elif 'datetime' in str(column_type).lower() or 'date' in str(column_type).lower():
                mapped_type = 'DATETIME'
            elif 'bool' in str(column_type).lower():
                mapped_type = 'BOOLEAN'
            else:
                mapped_type = 'STRING'
            columns.append({
                'source': column_name,
                'target': column_name,
                'type': mapped_type
            })
        cursor.close()
        conn.close()
        return columns
    except mysql.connector.Error as e:
        print_error(f"获取表结构失败：{e}")
        return None

def configure_field_mapping(source_columns, show_step=True):
    """配置字段映射"""
    if show_step:
        print_step(4, "字段映射配置")
    
    mapped_columns = source_columns.copy() if source_columns else []
    
    while True:
        print(f"\n{Colors.BLUE}当前字段映射：{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}{'源字段名'.ljust(20)}{'目标字段名'.ljust(20)}{'字段类型'.ljust(10)}{'操作'}{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        
        for i, col in enumerate(mapped_columns, 1):
            print(f"{str(i).ljust(5)} {col['source'].ljust(15)} → {col['target'].ljust(15)} → {col['type'].ljust(10)} [删除]")
        
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        
        print("\n操作选项：")
        print("  1) 修改目标字段名")
        print("  2) 修改字段类型")
        print("  3) 删除字段")
        print("  4) 手动添加字段")
        print("  5) 完成映射")
        
        choice = get_input("请选择操作 [1-5]: ", required=True)
        
        if choice == "1":
            # 修改目标字段名
            idx = int(get_input("请输入字段序号： ", required=True)) - 1
            if 0 <= idx < len(mapped_columns):
                new_target = get_input(f"新的目标字段名 [{mapped_columns[idx]['target']}]: ", 
                                    default=mapped_columns[idx]['target'], required=True)
                mapped_columns[idx]['target'] = new_target
                print_success(f"已修改目标字段名为：{new_target}")
            else:
                print_error("无效的字段序号")
                
        elif choice == "2":
            # 修改字段类型
            idx = int(get_input("请输入字段序号： ", required=True)) - 1
            if 0 <= idx < len(mapped_columns):
                print("选择字段类型：")
                print("  1) STRING")
                print("  2) INT")
                print("  3) DATETIME")
                print("  4) BOOLEAN")
                type_choice = get_input("请选择 [1-4]: ", required=True)
                type_map = {"1": "STRING", "2": "INT", "3": "DATETIME", "4": "BOOLEAN"}
                if type_choice in type_map:
                    mapped_columns[idx]['type'] = type_map[type_choice]
                    print_success(f"已修改字段类型为：{type_map[type_choice]}")
                else:
                    print_error("无效的类型选择")
            else:
                print_error("无效的字段序号")
                
        elif choice == "3":
            # 删除字段
            idx = int(get_input("请输入字段序号： ", required=True)) - 1
            if 0 <= idx < len(mapped_columns):
                deleted_field = mapped_columns.pop(idx)
                print_success(f"已删除字段：{deleted_field['source']}")
            else:
                print_error("无效的字段序号")
                
        elif choice == "4":
            # 手动添加字段
            source_field = get_input("源字段名： ", required=True)
            target_field = get_input(f"目标字段名 [{source_field}]: ", default=source_field, required=True)
            print("选择字段类型：")
            print("  1) STRING")
            print("  2) INT")
            print("  3) DATETIME")
            print("  4) BOOLEAN")
            type_choice = get_input("请选择 [1-4]: ", required=True)
            type_map = {"1": "STRING", "2": "INT", "3": "DATETIME", "4": "BOOLEAN"}
            if type_choice in type_map:
                new_column = {
                    'source': source_field,
                    'target': target_field,
                    'type': type_map[type_choice]
                }
                mapped_columns.append(new_column)
                print_success(f"已添加字段：{source_field} → {target_field} ({type_map[type_choice]})")
            else:
                print_error("无效的类型选择")
                
        elif choice == "5":
            if not mapped_columns:
                print_error("至少需要保留一个字段")
                continue
            break
        else:
            print_error("无效的选择")
    
    return mapped_columns

def config_mysql_database(is_source=True, is_cdc=False):
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction}数据库 ---{Colors.NC}\n")

    while True:
        host = get_input(f"{direction} MySQL 主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
        port = get_input(f"{direction} MySQL 端口 [默认：3306]: ", default="3306")
        user = get_input(f"{direction} MySQL 用户名： ", required=True)
        password = get_input(f"{direction} MySQL 密码： ", required=True, hide=True)
        
        # 自动检测数据库列表
        databases = get_databases(host, port, user, password)
        if databases and len(databases) > 0:
            print(f"\n{Colors.GREEN}可用的数据库：{Colors.NC}")
            for i, db in enumerate(databases, 1):
                print(f"  {i}) {db}")
            
            while True:
                db_choice = get_input(f"\n请选择数据库 [1-{len(databases)}] 或输入数据库名： ", required=True)
                
                if db_choice.isdigit():
                    idx = int(db_choice)
                    if 1 <= idx <= len(databases):
                        database = databases[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(databases)} 之间的数字")
                else:
                    database = db_choice
                    print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                    break
        else:
            database = get_input(f"{direction} 数据库名： ", required=True)

        if not test_mysql_connection(host, port, user, password, database):
            create_db = get_input("数据库不存在，是否创建？[y/N]: ", default="n").lower()
            if create_db == "y":
                if create_database(host, port, user, password, database):
                    break
                else:
                    retry = get_input("是否重新输入？[y/N]: ", default="y").lower()
                    if retry == "y":
                        continue
                    else:
                        print_error("操作已取消")
                        sys.exit(1)
            else:
                retry = get_input("是否重新输入？[y/N]: ", default="y").lower()
                if retry == "y":
                    continue
                else:
                    print_error("操作已取消")
                    sys.exit(1)
        
        tables = get_database_tables(host, port, user, password, database)
        
        if tables and len(tables) > 0:
            print(f"\n{Colors.GREEN}数据库 '{database}' 中的表：{Colors.NC}")
            for i, tbl in enumerate(tables, 1):
                print(f"  {i}) {tbl}")
            
            while True:
                table_choice = get_input(f"\n请选择表 [1-{len(tables)}] 或输入表名： ", required=True)
                
                if table_choice.isdigit():
                    idx = int(table_choice)
                    if 1 <= idx <= len(tables):
                        table = tables[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(tables)} 之间的数字")
                else:
                    table = table_choice
                    if table in tables:
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"表 '{table}' 不存在于数据库中")
                        if not is_source:
                            create_table = get_input("此表不存在，是否创建？[y/N]: ", default="n").lower()
                            if create_table == "y":
                                print(f"{Colors.YELLOW}表 '{table}' 将在执行时自动创建{Colors.NC}")
                                break
                            else:
                                retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                                if retry == "y":
                                    continue
                                else:
                                    print_error("操作已取消")
                                    sys.exit(1)
                        else:
                            retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                            if retry == "y":
                                continue
                            else:
                                print_error("操作已取消")
                                sys.exit(1)
        else:
            table = get_input(f"{direction} 表名： ", required=True)
            if not verify_table_exists(host, port, user, password, database, table):
                if not is_source:
                    create_table = get_input("此表不存在，是否创建？[y/N]: ", default="n").lower()
                    if create_table == "y":
                        print(f"{Colors.YELLOW}表 '{table}' 将在执行时自动创建{Colors.NC}")
                        break
                    else:
                        retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                        if retry == "y":
                            continue
                        else:
                            print_error("操作已取消")
                            sys.exit(1)
                else:
                    retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                    if retry == "y":
                        continue
                    else:
                        print_error("操作已取消")
                        sys.exit(1)
        
        break

    if is_source and is_cdc:
        server_id = get_input(f"CDC Server ID [默认：100-200]: ", default="100-200")
        startup_mode = get_input(f"启动模式 [initial/earliest/latest 默认：initial]: ", default="initial")
        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "table": table,
            "server_id": server_id,
            "startup_mode": startup_mode
        }

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

# ==================== 达梦数据库相关函数 ====================

def test_dameng_connection(host, port, user, password, database):
    """测试达梦数据库连接"""
    print(f"\n{Colors.BLUE}正在测试达梦连接...{Colors.NC}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, int(port)))
        sock.close()
        print(f"{Colors.GREEN}✓ 端口 {port} 可访问{Colors.NC}")

        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        conn.close()
        print(f"{Colors.GREEN}✓ 达梦数据库连接成功{Colors.NC}")
        return True
    except socket.error as e:
        print_error(f"连接失败：端口 {port} 不可达 - {e}")
        return False
    except Exception as e:
        print_error(f"连接失败：{e}")
        return False

def get_dameng_databases(host, port, user, password):
    """获取达梦数据库列表"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT OWNER FROM ALL_TABLES ORDER BY OWNER")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return databases
    except Exception as e:
        print_error(f"获取达梦数据库列表失败：{e}")
        return None

def get_dameng_database_tables(host, port, user, password, database):
    """获取达梦数据库中的所有表"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = '{database.upper()}' ORDER BY TABLE_NAME")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        print_error(f"获取达梦表列表失败：{e}")
        return None

def get_dameng_table_columns(host, port, user, password, database, table):
    """获取达梦表的所有列名"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER = '{database.upper()}' AND TABLE_NAME = '{table.upper()}' ORDER BY COLUMN_ID")
        columns = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return columns
    except Exception as e:
        print_error(f"获取达梦表结构失败：{e}")
        return None

def config_dameng_database(is_source=True):
    """配置达梦数据库"""
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction}达梦数据库 ---{Colors.NC}\n")

    while True:
        host = get_input(f"{direction} 达梦主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
        port = get_input(f"{direction} 达梦端口 [默认：5236]: ", default="5236")
        user = get_input(f"{direction} 达梦用户名 [默认：SYSDBA]: ", default="SYSDBA")
        password = get_input(f"{direction} 达梦密码： ", required=True, hide=True)
        
        databases = get_dameng_databases(host, port, user, password)
        if databases and len(databases) > 0:
            print(f"\n{Colors.GREEN}可用的数据库：{Colors.NC}")
            for i, db in enumerate(databases, 1):
                print(f"  {i}) {db}")
            
            while True:
                db_choice = get_input(f"\n请选择数据库 [1-{len(databases)}] 或输入数据库名： ", required=True)
                
                if db_choice.isdigit():
                    idx = int(db_choice)
                    if 1 <= idx <= len(databases):
                        database = databases[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(databases)} 之间的数字")
                else:
                    database = db_choice
                    print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                    break
        else:
            database = get_input(f"{direction} 数据库名： ", required=True)

        if not test_dameng_connection(host, port, user, password, database):
            retry = get_input("是否重新输入？[y/N]: ", default="n").lower()
            if retry == "y":
                continue
            else:
                print_error("操作已取消")
                sys.exit(1)
        
        tables = get_dameng_database_tables(host, port, user, password, database)
        
        if tables and len(tables) > 0:
            print(f"\n{Colors.GREEN}数据库 '{database}' 中的表：{Colors.NC}")
            for i, tbl in enumerate(tables, 1):
                print(f"  {i}) {tbl}")
            
            while True:
                table_choice = get_input(f"\n请选择表 [1-{len(tables)}] 或输入表名： ", required=True)
                
                if table_choice.isdigit():
                    idx = int(table_choice)
                    if 1 <= idx <= len(tables):
                        table = tables[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(tables)} 之间的数字")
                else:
                    table = table_choice
                    if table.upper() in [t.upper() for t in tables]:
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"表 '{table}' 不存在于数据库中")
                        if not is_source:
                            print(f"{Colors.YELLOW}表 '{table}' 将在执行时自动创建{Colors.NC}")
                            break
                        else:
                            retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                            if retry == "y":
                                continue
                            else:
                                print_error("操作已取消")
                                sys.exit(1)
        else:
            table = get_input(f"{direction} 表名： ", required=True)
        
        break

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

def sync_dameng_to_dameng(source_config, sink_config):
    """直接同步达梦数据库到达梦数据库"""
    print(f"\n{Colors.BLUE}开始同步数据...{Colors.NC}")
    
    source_conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={source_config['host']};PORT={source_config['port']};UID={source_config['user']};PWD={source_config['password']};DATABASE={source_config['database']}"
    sink_conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={sink_config['host']};PORT={sink_config['port']};UID={sink_config['user']};PWD={sink_config['password']};DATABASE={sink_config['database']}"
    
    try:
        # 获取源表字段
        source_columns = get_dameng_table_columns(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database'],
            source_config['table']
        )
        
        if not source_columns:
            print_error("无法获取源表字段信息")
            return False
        
        columns_str = ", ".join(source_columns)
        source_table = f"{source_config['database'].upper()}.{source_config['table'].upper()}"
        sink_table = f"{sink_config['database'].upper()}.{sink_config['table'].upper()}"
        
        print(f"{Colors.BLUE}源表：{source_table}{Colors.NC}")
        print(f"{Colors.BLUE}目标表：{sink_table}{Colors.NC}")
        print(f"{Colors.BLUE}字段：{columns_str}{Colors.NC}")
        
        # 连接源数据库
        source_conn = pyodbc.connect(source_conn_str)
        source_cursor = source_conn.cursor()
        
        # 连接目标数据库
        sink_conn = pyodbc.connect(sink_conn_str)
        sink_cursor = sink_conn.cursor()
        
        # 查询源数据
        query_sql = f"SELECT {columns_str} FROM {source_table}"
        print(f"\n{Colors.BLUE}执行查询：{query_sql}{Colors.NC}")
        source_cursor.execute(query_sql)
        
        # 获取数据
        rows = source_cursor.fetchall()
        total_rows = len(rows)
        print(f"{Colors.GREEN}✓ 查询完成，共 {total_rows} 条数据{Colors.NC}")
        
        if total_rows == 0:
            print(f"{Colors.YELLOW}警告：源表没有数据{Colors.NC}")
            source_conn.close()
            sink_conn.close()
            return True
        
        # 构建插入语句
        placeholders = ", ".join(["?" for _ in source_columns])
        insert_sql = f"INSERT INTO {sink_table} ({columns_str}) VALUES ({placeholders})"
        
        # 统计变量
        inserted = 0
        updated = 0
        failed = 0
        
        print(f"\n{Colors.BLUE}开始写入目标表...{Colors.NC}")
        
        for i, row in enumerate(rows, 1):
            pk_column = source_columns[0]
            pk_value = row[0]

            try:
                # 先查询目标表是否存在该主键
                check_sql = f"SELECT {columns_str} FROM {sink_table} WHERE {pk_column} = ?"
                sink_cursor.execute(check_sql, (pk_value,))
                existing_row = sink_cursor.fetchone()
                
                if existing_row:
                    # 主键存在，比较数据
                    if list(existing_row) == list(row):
                        # 数据完全相同，跳过
                        continue
                    else:
                        # 数据不同，执行更新
                        update_set = ", ".join([f"{col} = ?" for col in source_columns[1:]])
                        update_sql = f"UPDATE {sink_table} SET {update_set} WHERE {pk_column} = ?"
                        sink_cursor.execute(update_sql, row[1:] + (pk_value,))
                        sink_conn.commit()
                        updated += 1
                else:
                    # 主键不存在，执行插入
                    sink_cursor.execute(insert_sql, row)
                    sink_conn.commit()
                    inserted += 1
            except Exception as e:
                print_error(f"处理失败（行 {i}）：{e}")
                failed += 1

            if i % 100 == 0:
                print(f"{Colors.BLUE}已处理 {i}/{total_rows} 条数据{Colors.NC}")
        
        # 关闭连接
        source_conn.close()
        sink_conn.close()
        
        # 输出统计
        print(f"\n{Colors.GREEN}✓ 同步完成！{Colors.NC}")
        print(f"  插入：{inserted} 条")
        print(f"  更新：{updated} 条")
        print(f"  失败：{failed} 条")

        if failed > 0:
            print_error(f"同步完成但有 {failed} 条数据处理失败")
            return False

        return True
        
    except Exception as e:
        print_error(f"同步失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print_header("SeaTunnel 数据采集配置向导")

    print_step(1, "选择数据源类型")

    print("选择数据源类型:")
    print("  1) MySQL 数据库")
    print("  2) HTTP API")
    print("  3) 达梦数据库")
    print("  4) 测试模式 (使用 FakeSource)")

    source_choice = get_input("请选择 [1-4] [默认：1]: ", default="1")

    source_config = None
    sink_config = None
    api_config = None

    if source_choice == "1":
        print_success("数据源：MySQL 数据库")
        print_step(2, "配置源 MySQL 数据库")

        job_name = get_input("作业名称 [默认：MySQL_to_MySQL_Sync]: ", default="MySQL_to_MySQL_Sync")
        print("选择作业模式:")
        print("  1) STREAMING (实时同步)")
        print("  2) BATCH (批量同步)")
        mode_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
        if mode_choice == "1":
            job_mode = "STREAMING"
        else:
            job_mode = "BATCH"
        parallelism = get_input("并行度 [默认：1]: ", default="1")

        is_cdc = (job_mode == "STREAMING")
        source_config = config_mysql_database(is_source=True, is_cdc=is_cdc)

        # 获取源表字段信息
        source_columns = get_table_columns(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database'],
            source_config['table']
        )

        print_step(3, "字段映射配置")
        field_mapping = configure_field_mapping(source_columns, show_step=False)

        print_step(4, "配置目标 MySQL 数据库")
        sink_config = config_mysql_database(is_source=False)

        # 验证目标表结构
        if field_mapping:
            print(f"\n{Colors.BLUE}验证目标表结构...{Colors.NC}")
            sink_columns = get_table_columns(
                sink_config['host'],
                sink_config['port'],
                sink_config['user'],
                sink_config['password'],
                sink_config['database'],
                sink_config['table']
            )
            
            if sink_columns:
                sink_field_names = [col['source'] for col in sink_columns]
                mapped_target_fields = [col['target'] for col in field_mapping]
                
                missing_fields = [field for field in mapped_target_fields if field not in sink_field_names]
                if missing_fields:
                    print(f"{Colors.YELLOW}警告：目标表中缺少以下字段：{', '.join(missing_fields)}{Colors.NC}")
                    print(f"{Colors.YELLOW}建议：在目标表中创建这些字段或修改字段映射{Colors.NC}")
                    
                    # 询问用户是否继续
                    continue_anyway = get_input("是否继续执行？[y/N]: ", default="n").lower()
                    if continue_anyway != "y":
                        print_error("操作已取消")
                        sys.exit(1)
            else:
                # 目标表不存在，且使用了字段映射
                # 手动创建目标表结构
                print(f"{Colors.YELLOW}目标表不存在，根据字段映射创建表结构...{Colors.NC}")
                try:
                    conn = mysql.connector.connect(
                        host=sink_config['host'],
                        port=int(sink_config['port']),
                        user=sink_config['user'],
                        password=sink_config['password'],
                        database=sink_config['database'],
                        connect_timeout=5
                    )
                    cursor = conn.cursor()
                    
                    # 生成建表SQL
                    create_table_sql = f"CREATE TABLE `{sink_config['table']}` ("
                    for i, col in enumerate(field_mapping):
                        if i > 0:
                            create_table_sql += ", "
                        # 根据字段类型映射到MySQL类型
                        mysql_type = "VARCHAR(255)"
                        if col['type'] == "INT":
                            mysql_type = "INT"
                        elif col['type'] == "DATETIME":
                            mysql_type = "DATETIME"
                        elif col['type'] == "BOOLEAN":
                            mysql_type = "BOOLEAN"
                        create_table_sql += f"`{col['target']}` {mysql_type} NULL"
                    create_table_sql += ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
                    
                    print(f"{Colors.BLUE}执行建表SQL: {create_table_sql}{Colors.NC}")
                    cursor.execute(create_table_sql)
                    conn.commit()
                    print(f"{Colors.GREEN}✓ 目标表创建成功{Colors.NC}")
                    
                    cursor.close()
                    conn.close()
                except mysql.connector.Error as e:
                    print_error(f"创建目标表失败：{e}")
                    print_error("请手动创建目标表后再执行")
                    sys.exit(1)

    elif source_choice == "2":
        print_success("数据源：HTTP API")
        print_step(2, "配置源 API")

        print("选择 API 类型:")
        print("  1) Random User Generator API (https://randomuser.me/)")
        print("  2) 自定义 API")

        api_type = get_input("请选择 [1-2] [默认：1]: ", default="1")

        if api_type == "1":
            api_url = "https://randomuser.me/api/"
            api_method = "GET"
            content_field = "results"
            api_returns_array = True
            print_success("使用 Random User Generator API")
        else:
            api_url = get_input("API URL: ", required=True)
            print("选择 HTTP 方法:")
            print("  1) GET")
            print("  2) POST")
            method_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
            if method_choice == "1":
                api_method = "GET"
            else:
                api_method = "POST"
            content_field = get_input("JSON 内容字段 [默认：results]: ", default="results")
            
            # 尝试获取API返回内容，解析字段
            print(f"\n{Colors.BLUE}正在测试 API 连接并解析字段...{Colors.NC}")
            default_columns = []
            api_returns_array = False  # 标记API返回数组还是单个对象
            try:
                import requests
                import json
                
                # 发送请求
                if api_method == "GET":
                    response = requests.get(api_url, timeout=10)
                else:
                    response = requests.post(api_url, timeout=10)
                
                if 200 <= response.status_code < 300:
                    # 解析JSON
                    data = response.json()
                    
                    # 检测数据格式并自动设置 content_field
                    if isinstance(data, list):
                        # API直接返回数组，不需要 content_field
                        content_field = ""
                        content = data
                        api_returns_array = True
                        print(f"{Colors.GREEN}✓ API 返回数组格式，无需设置 content_field{Colors.NC}")
                    elif isinstance(data, dict):
                        # API返回对象，尝试提取内容字段
                        content = data
                        if content_field:
                            # 支持嵌套字段，如 data.items
                            for part in content_field.split('.'):
                                if part in content:
                                    content = content[part]
                                else:
                                    print(f"{Colors.YELLOW}警告：未找到字段 '{part}'，使用完整响应{Colors.NC}")
                                    content_field = ""
                                    content = data
                                    break
                        # 检查提取后的内容是数组还是对象
                        api_returns_array = isinstance(content, list)
                        
                        # 如果还是单个对象，尝试找 "data" 或 "json" 字段作为数据
                        if not api_returns_array and isinstance(content, dict):
                            if "data" in content:
                                content = content["data"]
                                content_field = "data"
                                api_returns_array = isinstance(content, list)
                            elif "json" in content and isinstance(content["json"], (dict, list)):
                                content = content["json"]
                                content_field = "json"
                                api_returns_array = isinstance(content, list)
                                print(f"{Colors.GREEN}✓ 检测到嵌套数据字段 'json'{Colors.NC}")
                    
                    # 提取字段（只提取顶层字段，不递归解析嵌套结构）
                    if isinstance(content, list) and len(content) > 0:
                        # 假设第一个元素是代表项
                        sample_item = content[0]
                        
                        # 只提取顶层字段
                        def extract_top_fields(obj):
                            fields = []
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    # 只处理顶层字段，不递归
                                    field_type = "STRING"
                                    if isinstance(value, int):
                                        field_type = "INT"
                                    elif isinstance(value, bool):
                                        field_type = "BOOLEAN"
                                    fields.append({
                                        'source': key,
                                        'target': key,
                                        'type': field_type
                                    })
                            return fields
                        
                        default_columns = extract_top_fields(sample_item)
                        
                        if default_columns:
                            print(f"{Colors.GREEN}✓ 成功解析 API 字段，共 {len(default_columns)} 个字段{Colors.NC}")
                        else:
                            print(f"{Colors.YELLOW}警告：无法从 API 响应中提取字段，使用默认字段{Colors.NC}")
                            # 使用默认字段
                            default_columns = [
                                {'source': 'id', 'target': 'id', 'type': 'INT'},
                                {'source': 'name', 'target': 'name', 'type': 'STRING'},
                                {'source': 'value', 'target': 'value', 'type': 'STRING'}
                            ]
                    elif isinstance(content, dict):
                        # API返回单个对象，直接提取这个对象的字段
                        api_returns_array = False
                        def extract_top_fields(obj):
                            fields = []
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    # 只处理顶层字段，不递归
                                    field_type = "STRING"
                                    if isinstance(value, int):
                                        field_type = "INT"
                                    elif isinstance(value, bool):
                                        field_type = "BOOLEAN"
                                    fields.append({
                                        'source': key,
                                        'target': key,
                                        'type': field_type
                                    })
                            return fields
                        
                        default_columns = extract_top_fields(content)
                        
                        if default_columns:
                            print(f"{Colors.GREEN}✓ 成功解析 API 字段，共 {len(default_columns)} 个字段{Colors.NC}")
                        else:
                            print(f"{Colors.YELLOW}警告：无法从 API 响应中提取字段，使用默认字段{Colors.NC}")
                            # 使用默认字段
                            default_columns = [
                                {'source': 'id', 'target': 'id', 'type': 'INT'},
                                {'source': 'name', 'target': 'name', 'type': 'STRING'},
                                {'source': 'value', 'target': 'value', 'type': 'STRING'}
                            ]
                    else:
                        print(f"{Colors.YELLOW}警告：API 响应格式不符合预期，使用默认字段{Colors.NC}")
                        # 使用默认字段
                        default_columns = [
                            {'source': 'id', 'target': 'id', 'type': 'INT'},
                            {'source': 'name', 'target': 'name', 'type': 'STRING'},
                            {'source': 'value', 'target': 'value', 'type': 'STRING'}
                        ]
                else:
                    print(f"{Colors.YELLOW}警告：API 请求失败 (状态码: {response.status_code})，使用默认字段{Colors.NC}")
                    # 使用默认字段
                    default_columns = [
                        {'source': 'id', 'target': 'id', 'type': 'INT'},
                        {'source': 'name', 'target': 'name', 'type': 'STRING'},
                        {'source': 'value', 'target': 'value', 'type': 'STRING'}
                    ]
            except Exception as e:
                print(f"{Colors.YELLOW}警告：无法连接到 API ({e})，使用默认字段{Colors.NC}")
                # 使用默认字段
                default_columns = [
                    {'source': 'id', 'target': 'id', 'type': 'INT'},
                    {'source': 'name', 'target': 'name', 'type': 'STRING'},
                    {'source': 'value', 'target': 'value', 'type': 'STRING'}
                ]
            
            print_success("自定义 API 配置完成")

        api_config = {
            "url": api_url,
            "method": api_method,
            "content_field": content_field,
            "returns_array": api_returns_array
        }

        # API 字段映射
        if api_type == "1":
            # Random User API 默认字段
            default_columns = [
                {'source': 'name.first', 'target': 'first_name', 'type': 'STRING'},
                {'source': 'name.last', 'target': 'last_name', 'type': 'STRING'},
                {'source': 'email', 'target': 'email', 'type': 'STRING'},
                {'source': 'gender', 'target': 'gender', 'type': 'STRING'},
                {'source': 'dob.age', 'target': 'age', 'type': 'INT'},
                {'source': 'location.city', 'target': 'city', 'type': 'STRING'}
            ]
        # 自定义 API 的 default_columns 已经在上面动态生成

        print_step(3, "字段映射配置")
        field_mapping = configure_field_mapping(default_columns, show_step=False)

        print_step(4, "配置目标 MySQL 数据库")
        sink_config = config_mysql_database(is_source=False)

        # 验证目标表结构
        if field_mapping:
            print(f"\n{Colors.BLUE}验证目标表结构...{Colors.NC}")
            sink_columns = get_table_columns(
                sink_config['host'],
                sink_config['port'],
                sink_config['user'],
                sink_config['password'],
                sink_config['database'],
                sink_config['table']
            )
            
            if sink_columns:
                sink_field_names = [col['source'] for col in sink_columns]
                mapped_target_fields = [col['target'] for col in field_mapping]
                
                missing_fields = [field for field in mapped_target_fields if field not in sink_field_names]
                if missing_fields:
                    print(f"{Colors.YELLOW}警告：目标表中缺少以下字段：{', '.join(missing_fields)}{Colors.NC}")
                    print(f"{Colors.YELLOW}建议：在目标表中创建这些字段或修改字段映射{Colors.NC}")
                    
                    # 询问用户是否继续
                    continue_anyway = get_input("是否继续执行？[y/N]: ", default="n").lower()
                    if continue_anyway != "y":
                        print_error("操作已取消")
                        sys.exit(1)
            else:
                # 目标表不存在，且使用了字段映射
                # 手动创建目标表结构
                print(f"{Colors.YELLOW}目标表不存在，根据字段映射创建表结构...{Colors.NC}")
                try:
                    conn = mysql.connector.connect(
                        host=sink_config['host'],
                        port=int(sink_config['port']),
                        user=sink_config['user'],
                        password=sink_config['password'],
                        database=sink_config['database'],
                        connect_timeout=5
                    )
                    cursor = conn.cursor()
                    
                    # 生成建表SQL
                    create_table_sql = f"CREATE TABLE `{sink_config['table']}` ("
                    for i, col in enumerate(field_mapping):
                        if i > 0:
                            create_table_sql += ", "
                        # 根据字段类型映射到MySQL类型
                        mysql_type = "VARCHAR(255)"
                        if col['type'] == "INT":
                            mysql_type = "INT"
                        elif col['type'] == "DATETIME":
                            mysql_type = "DATETIME"
                        elif col['type'] == "BOOLEAN":
                            mysql_type = "BOOLEAN"
                        create_table_sql += f"`{col['target']}` {mysql_type} NULL"
                    create_table_sql += ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
                    
                    print(f"{Colors.BLUE}执行建表SQL: {create_table_sql}{Colors.NC}")
                    cursor.execute(create_table_sql)
                    conn.commit()
                    print(f"{Colors.GREEN}✓ 目标表创建成功{Colors.NC}")
                    
                    cursor.close()
                    conn.close()
                except mysql.connector.Error as e:
                    print_error(f"创建目标表失败：{e}")
                    print_error("请手动创建目标表后再执行")
                    sys.exit(1)

        job_name = get_input("作业名称 [默认：API_to_MySQL_Sync]: ", default="API_to_MySQL_Sync")
        job_mode = get_input("作业模式 [STREAMING/BATCH 默认：BATCH]: ", default="BATCH").upper()
        parallelism = get_input("并行度 [默认：1]: ", default="1")

    elif source_choice == "3":
        print_success("数据源：达梦数据库")
        print_step(2, "配置源达梦数据库")
        source_config = config_dameng_database(is_source=True)

        print_step(3, "配置目标达梦数据库")
        sink_config = config_dameng_database(is_source=False)

        job_name = get_input("作业名称 [默认：Dameng_to_Dameng_Sync]: ", default="Dameng_to_Dameng_Sync")
        job_mode = "BATCH"
        parallelism = "1"

    elif source_choice == "4":
        print_success("使用测试模式 (FakeSource)")
        print_step(2, "配置作业信息")
        job_name = get_input("作业名称 [默认：FakeSource_Test]: ", default="FakeSource_Test")
        job_mode = get_input("作业模式 [默认：BATCH]: ", default="BATCH").upper()
        parallelism = get_input("并行度 [默认：1]: ", default="1")
    else:
        print_error("无效的选择")
        sys.exit(1)

    print_step(4, "确认配置")

    print("┌─────────────────────────────────────────────┐")
    print("│  数据同步配置                                 │")
    print("├─────────────────────────────────────────────┤")

    if source_choice == "1":
        sync_mode = "CDC" if job_mode == "STREAMING" else "Batch"
        print(f"│  同步模式：{sync_mode:<39}│")
        print("│  源数据库                                   │")
        print(f"│    主机：{source_config['host']}:{source_config['port']:<30}│")
        print(f"│    用户：{source_config['user']:<36}│")
        print(f"│    数据库：{source_config['database']:<32}│")
        print(f"│    表：{source_config['table']:<38}│")
        print("├─────────────────────────────────────────────┤")
        print("│  目标数据库                                 │")
        print(f"│    主机：{sink_config['host']}:{sink_config['port']:<30}│")
        print(f"│    用户：{sink_config['user']:<36}│")
        print(f"│    数据库：{sink_config['database']:<32}│")
        print(f"│    表：{sink_config['table']:<38}│")
    elif source_choice == "2":
        print(f"│  API URL: {api_config['url'][:37]:<37}│")
        print(f"│  方法：{api_config['method']:<36}│")
        print(f"│  内容字段：{api_config.get('content_field', '无'):<32}│")
        print("├─────────────────────────────────────────────┤")
        print("│  目标数据库                                 │")
        print(f"│    主机：{sink_config['host']}:{sink_config['port']:<30}│")
        print(f"│    用户：{sink_config['user']:<36}│")
        print(f"│    数据库：{sink_config['database']:<32}│")
        print(f"│    表：{sink_config['table']:<38}│")
    elif source_choice == "3":
        print("│  模式：达梦数据库同步                         │")
        print("├─────────────────────────────────────────────┤")
        print("│  源数据库                                   │")
        print(f"│    主机：{source_config['host']}:{source_config['port']:<30}│")
        print(f"│    用户：{source_config['user']:<36}│")
        print(f"│    数据库：{source_config['database']:<32}│")
        print(f"│    表：{source_config['table']:<38}│")
        print("├─────────────────────────────────────────────┤")
        print("│  目标数据库                                 │")
        print(f"│    主机：{sink_config['host']}:{sink_config['port']:<30}│")
        print(f"│    用户：{sink_config['user']:<36}│")
        print(f"│    数据库：{sink_config['database']:<32}│")
        print(f"│    表：{sink_config['table']:<38}│")
    else:
        print("│  模式：测试模式 (FakeSource + Console)       │")

    print("├─────────────────────────────────────────────┤")
    print("│  作业配置                                    │")
    print("├─────────────────────────────────────────────┤")
    print(f"│  名称：{job_name:<36}│")
    print(f"│  模式：{job_mode:<36}│")
    print(f"│  并行度：{parallelism:<34}│")
    print("└─────────────────────────────────────────────┘")

    confirm = get_input("\n确认生成配置文件并执行？[y/N]: ", default="n").lower()

    if confirm != "y":
        print_error("操作已取消")
        sys.exit(0)

    # 达梦数据库同步直接执行，不生成 SeaTunnel 配置
    if source_choice == "3":
        print(f"\n{Colors.BLUE}准备执行达梦数据库同步...{Colors.NC}")
        
        confirm = get_input("确认执行达梦数据库同步？[Y/n]: ", default="Y").upper()
        if confirm == "Y":
            start_time = datetime.now()
            success = sync_dameng_to_dameng(source_config, sink_config)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n{Colors.BLUE}耗时：{duration:.2f} 秒{Colors.NC}")
            
            if success:
                print_success("达梦数据库同步任务执行成功")
            else:
                print_error("达梦数据库同步任务执行失败")
                sys.exit(1)
        else:
            print_error("操作已取消")
            sys.exit(0)
        return

    print("\n正在生成配置文件...")

    if os.name == 'nt':
        workspace = Path(os.environ.get('TEMP', 'D:\temp')) / 'seatunnel'
    else:
        workspace = Path("/home/admin/openclaw/workspace/temp")

    workspace.mkdir(parents=True, exist_ok=True)
    output_config = workspace / "generated_config.conf"

    if source_choice == "1":
        if job_mode == "STREAMING":
            # 生成字段映射配置（只有当字段映射有实际变化时才生成）
            mapping_config = ""
            save_mode = "create"
            primary_keys = "\"id\""
            if 'field_mapping' in locals() and field_mapping:
                # 检查是否有字段被实际修改（源字段名和目标字段名不同）
                has_mapping = any(col['source'] != col['target'] for col in field_mapping)
                if has_mapping:
                    # 当使用字段映射时，需要先确保目标表存在
                    # 解决方案：先创建表结构，再进行字段映射
                    mapping_config = "\n\ntransform {\n  FieldMapper {\n    field_mapper = {"
                    # 查找id字段的映射
                    id_mapped = False
                    for col in field_mapping:
                        mapping_config += f"\n      {col['source']} = {col['target']},"
                        if col['source'] == 'id':
                            primary_keys = f"\"{col['target']}\""
                            id_mapped = True
                    mapping_config += "\n    }\n  }\n}\n"
                    # 当使用字段映射时，改为upsert模式，以处理主键冲突
                    save_mode = "upsert"
                    # 如果没有映射id字段，使用第一个字段作为主键
                    if not id_mapped and field_mapping:
                        primary_keys = f"\"{field_mapping[0]['target']}\""
            
            config_content = f"""# ============================================
# SeaTunnel MySQL CDC->MySQL 实时同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "STREAMING"
  job.name = "{job_name}"
  parallelism = {parallelism}
  checkpoint.interval = 10000
}}

source {{
  MySQL-CDC {{
    base-url = "jdbc:mysql://{source_config['host']}:{source_config['port']}/{source_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai"
    hostname = "{source_config['host']}"
    port = {source_config['port']}
    username = "{source_config['user']}"
    password = "{source_config['password']}"
    database-names = ["{source_config['database']}"]
    table-names = ["{source_config['database']}.{source_config['table']}"]
    server-id = "{source_config['server_id']}"
    startup.mode = "{source_config['startup_mode']}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = [{primary_keys}]
  }}
}}
"""
        else:
            # 生成字段映射配置（只有当字段映射有实际变化时才生成）
            mapping_config = ""
            save_mode = "create"
            primary_keys = "\"id\""
            if 'field_mapping' in locals() and field_mapping:
                # 检查是否有字段被实际修改（源字段名和目标字段名不同）
                has_mapping = any(col['source'] != col['target'] for col in field_mapping)
                if has_mapping:
                    # 当使用字段映射时，需要先确保目标表存在
                    # 解决方案：先创建表结构，再进行字段映射
                    mapping_config = "\n\ntransform {\n  FieldMapper {\n    field_mapper = {"
                    # 查找id字段的映射
                    id_mapped = False
                    for col in field_mapping:
                        mapping_config += f"\n      {col['source']} = {col['target']},"
                        if col['source'] == 'id':
                            primary_keys = f"\"{col['target']}\""
                            id_mapped = True
                    mapping_config += "\n    }\n  }\n}\n"
                    # 当使用字段映射时，改为upsert模式，以处理主键冲突
                    save_mode = "upsert"
                    # 如果没有映射id字段，使用第一个字段作为主键
                    if not id_mapped and field_mapping:
                        primary_keys = f"\"{field_mapping[0]['target']}\""
            
            config_content = f"""# ============================================
# SeaTunnel MySQL->MySQL 批量同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  Jdbc {{
    url = "jdbc:mysql://{source_config['host']}:{source_config['port']}/{source_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{source_config['user']}"
    password = "{source_config['password']}"
    database = "{source_config['database']}"
    table = "{source_config['table']}"

    query = "SELECT * FROM {source_config['table']}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = [{primary_keys}]
  }}
}}
"""
    elif source_choice == "2":
        # API 数据源 - 使用 json_field 和 schema 配置
        # 生成 json_field 配置
        json_field_lines = []
        schema_field_lines = []
        
        for col in field_mapping:
            source_field = col['source']
            target_field = col['target']
            field_type = col['type']
            
            # 根据 content_field 和 returns_array 决定 JsonPath 格式
            if api_config.get('content_field'):
                if api_config.get('returns_array'):
                    json_path = f"$.{api_config['content_field']}[*].{source_field}"
                else:
                    json_path = f"$.{api_config['content_field']}.{source_field}"
            else:
                if api_config.get('returns_array'):
                    json_path = f"$[*].{source_field}"
                else:
                    json_path = f"$.{source_field}"
            
            json_field_lines.append(f'      "{target_field}" = "{json_path}"')
            
            # 映射字段类型到 SeaTunnel 类型
            seatunnel_type = "STRING"
            if field_type == "INT":
                seatunnel_type = "INT"
            elif field_type == "BOOLEAN":
                seatunnel_type = "BOOLEAN"
            elif field_type == "DATETIME":
                seatunnel_type = "TIMESTAMP"
            
            schema_field_lines.append(f'        {target_field} = "{seatunnel_type}"')
        
        # 确定主键
        primary_keys = "\"id\""
        for col in field_mapping:
            if col['source'] == 'id':
                primary_keys = f"\"{col['target']}\""
                break
        if primary_keys == "\"id\"" and field_mapping:
            primary_keys = f"\"{field_mapping[0]['target']}\""
        
        # 构建配置内容
        json_field_section = "    json_field = {\n" + "\n".join(json_field_lines) + "\n    }"
        schema_section = "    schema = {\n      fields {\n" + "\n".join(schema_field_lines) + "\n      }\n    }"
        
        config_content = f"""# ============================================
# SeaTunnel API->MySQL 同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  Http {{
    url = "{api_config['url']}"
    method = "{api_config['method']}"
    format = "json"

{json_field_section}

{schema_section}
    batch_size = 100

    socket_timeout_ms = 30000
    connect_timeout_ms = 30000
  }}
}}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "upsert"
    primary_keys = [{primary_keys}]
  }}
}}
"""
    else:
        config_content = f"""# ============================================
# SeaTunnel 测试配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  FakeSource {{
    parallelism = {parallelism}
    schema = {{
      fields {{
        name = "string"
        age = "int"
        email = "string"
      }}
    }}
    row.num = 3
    result_table_name = "fake"
  }}
}}

sink {{
  Console {{
    parallelism = 1
  }}
}}
"""

    with open(output_config, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print_success(f"配置文件已生成：{output_config}")

    print(f"\n{Colors.BLUE}========== 生成的配置文件内容 =========={Colors.NC}")
    print(config_content)
    print(f"{Colors.BLUE}==========================================={Colors.NC}\n")

    if job_mode == "STREAMING" and source_choice == "1":
        print(f"{Colors.YELLOW}注意：CDC 模式会持续监听 MySQL binlog，任务不会自动结束{Colors.NC}")
        print(f"{Colors.YELLOW}按 Ctrl+C 可以停止任务{Colors.NC}\n")

    print(f"{Colors.BLUE}准备执行 SeaTunnel 任务...{Colors.NC}\n")

    seatunnel_bin = None
    if os.name == 'nt':
        if os.environ.get("SEATUNNEL_HOME"):
            seatunnel_bin = os.path.join(os.environ["SEATUNNEL_HOME"], "bin", "seatunnel.cmd")
        elif os.path.exists(r"D:\software\apache-seatunnel-2.3.5\bin\seatunnel.cmd"):
            seatunnel_bin = r"D:\software\apache-seatunnel-2.3.5\bin\seatunnel.cmd"
        elif os.path.exists(os.path.join(os.getcwd(), "bin", "seatunnel.cmd")):
            seatunnel_bin = os.path.join(os.getcwd(), "bin", "seatunnel.cmd")
    else:
        if os.environ.get("SEATUNNEL_HOME"):
            seatunnel_bin = os.path.join(os.environ["SEATUNNEL_HOME"], "bin/seatunnel.sh")
        elif os.path.exists("/opt/seatunnel/bin/seatunnel.sh"):
            seatunnel_bin = "/opt/seatunnel/bin/seatunnel.sh"
        elif os.path.exists(os.path.expanduser("~/seatunnel/bin/seatunnel.sh")):
            seatunnel_bin = os.path.expanduser("~/seatunnel/bin/seatunnel.sh")

    if not seatunnel_bin or not os.path.exists(seatunnel_bin):
        print(f"{Colors.YELLOW}警告：未找到 SeaTunnel 安装路径{Colors.NC}")
        print("\n请设置 SEATUNNEL_HOME 环境变量或手动执行以下命令:")
        if os.name == 'nt':
            print(f"\n  seatunnel.cmd --config \"{output_config}\" -m local\n")
        else:
            print(f"\n  seatunnel.sh --config \"{output_config}\" -m local\n")
        sys.exit(0)

    print(f"{Colors.GREEN}找到 SeaTunnel: {seatunnel_bin}{Colors.NC}\n")

    config_path = str(output_config).replace('\\', '/')
    print(f"{Colors.BLUE}执行命令：{seatunnel_bin} --config \"{config_path}\" -m local{Colors.NC}\n")

    cmd = [seatunnel_bin, "--config", config_path, "-m", "local"]

    try:
        result = subprocess.run(cmd, capture_output=False)
        exit_code = result.returncode
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}任务被用户中断{Colors.NC}")
        exit_code = 0
    except Exception as e:
        print_error(f"执行命令失败：{e}")
        exit_code = 1

    if exit_code == 0:
        print(f"\n{Colors.GREEN}{'=' * 50}{Colors.NC}")
        print(f"{Colors.GREEN}  ✓ 任务执行完成！{Colors.NC}")
        print(f"{Colors.GREEN}{'=' * 50}{Colors.NC}")
    else:
        print(f"\n{Colors.RED}{'=' * 50}{Colors.NC}")
        print(f"{Colors.RED}  ✗ 任务执行失败 (退出码：{exit_code}){Colors.NC}")
        print(f"{Colors.RED}{'=' * 50}{Colors.NC}")
        sys.exit(exit_code)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}操作被用户中断{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print_error(f"发生错误：{e}")
        sys.exit(1)
