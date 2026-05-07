#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Git 仓库同步工具
支持功能：
  1. 克隆远程仓库到本地
  2. 检查远程更新
  3. 自动拉取最新代码
"""

import os
import sys
import subprocess
import getpass
from datetime import datetime

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

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.NC}")

def get_input(prompt, default=None, required=False, hide=False):
    while True:
        if hide:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)
        
        if value.strip() == "":
            if default is not None:
                return default
            elif not required:
                return ""
            else:
                print_error("该选项不能为空")
                continue
        return value.strip()

def run_git_command(cmd, cwd=None):
    """执行 git 命令"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)

def check_git_installed():
    """检查 git 是否安装"""
    returncode, _, _ = run_git_command(["git", "--version"])
    return returncode == 0

def clone_repository(repo_url, local_path):
    """克隆远程仓库"""
    print(f"\n{Colors.BLUE}正在克隆仓库：{repo_url}{Colors.NC}")
    print(f"{Colors.BLUE}目标路径：{local_path}{Colors.NC}")
    
    if os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 已存在")
        return False
    
    cmd = ["git", "clone", repo_url, local_path]
    returncode, stdout, stderr = run_git_command(cmd)
    
    if returncode == 0:
        print_success("仓库克隆成功")
        print(f"\n{Colors.BLUE}克隆输出：{Colors.NC}")
        print(stdout)
        return True
    else:
        print_error(f"仓库克隆失败")
        if stderr:
            print(f"\n{Colors.RED}错误信息：{stderr}{Colors.NC}")
        return False

def check_updates(local_path):
    """检查远程是否有更新"""
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return None
    
    # 先获取当前分支
    returncode, current_branch, _ = run_git_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取当前分支")
        return None
    
    current_branch = current_branch.strip()
    print(f"\n{Colors.BLUE}当前分支：{current_branch}{Colors.NC}")
    
    # 获取本地提交
    returncode, local_commit, _ = run_git_command(
        ["git", "rev-parse", "HEAD"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取本地提交")
        return None
    
    # 拉取远程信息
    returncode, _, stderr = run_git_command(
        ["git", "fetch", "origin"],
        cwd=local_path
    )
    if returncode != 0:
        print_error(f"无法获取远程信息：{stderr}")
        return None
    
    # 获取远程提交
    returncode, remote_commit, _ = run_git_command(
        ["git", "rev-parse", f"origin/{current_branch}"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取远程提交")
        return None
    
    local_commit = local_commit.strip()
    remote_commit = remote_commit.strip()
    
    print(f"本地提交：{local_commit[:7]}")
    print(f"远程提交：{remote_commit[:7]}")
    
    if local_commit == remote_commit:
        print_success("本地代码已是最新")
        return 0  # 0 = 无更新
    else:
        print(f"{Colors.YELLOW}发现新提交！{Colors.NC}")
        # 获取更新日志
        returncode, log, _ = run_git_command(
            ["git", "log", "--oneline", f"{local_commit}..{remote_commit}"],
            cwd=local_path
        )
        if returncode == 0 and log:
            print(f"\n{Colors.BLUE}更新日志：{Colors.NC}")
            print(log)
        return 1  # 1 = 有更新

def pull_updates(local_path):
    """拉取最新代码"""
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return False
    
    print(f"\n{Colors.BLUE}正在拉取最新代码到：{local_path}{Colors.NC}")
    
    cmd = ["git", "pull", "origin"]
    returncode, stdout, stderr = run_git_command(cmd, cwd=local_path)
    
    if returncode == 0:
        print_success("代码拉取成功")
        if stdout:
            print(f"\n{Colors.BLUE}拉取输出：{Colors.NC}")
            print(stdout)
        return True
    else:
        print_error("代码拉取失败")
        if stderr:
            print(f"\n{Colors.RED}错误信息：{stderr}{Colors.NC}")
        return False

def get_repo_info(local_path):
    """获取仓库信息"""
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return
    
    print(f"\n{Colors.BLUE}仓库信息：{Colors.NC}")
    
    # 获取远程地址
    returncode, remote_url, _ = run_git_command(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=local_path
    )
    if returncode == 0:
        print(f"远程地址：{remote_url.strip()}")
    
    # 获取当前分支
    returncode, branch, _ = run_git_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=local_path
    )
    if returncode == 0:
        print(f"当前分支：{branch.strip()}")
    
    # 获取状态
    returncode, status, _ = run_git_command(
        ["git", "status", "--short"],
        cwd=local_path
    )
    if returncode == 0:
        if status.strip() == "":
            print_success("工作区干净")
        else:
            print(f"{Colors.YELLOW}工作区有修改：{Colors.NC}")
            print(status)

def main():
    print_header("Git 仓库同步工具")
    
    # 检查 git 是否安装
    if not check_git_installed():
        print_error("错误：未检测到 Git 安装")
        print_info("请先安装 Git：https://git-scm.com/downloads")
        sys.exit(1)
    
    while True:
        print("\n请选择操作：")
        print("  1) 克隆远程仓库")
        print("  2) 检查更新")
        print("  3) 拉取最新代码")
        print("  4) 查看仓库信息")
        print("  5) 退出")
        
        choice = get_input("请选择 [1-5] [默认：5]: ", default="5")
        
        if choice == "1":
            print("\n【克隆远程仓库】")
            repo_url = get_input("仓库地址 (HTTPS/SSH): ", required=True)
            local_path = get_input("本地路径: ", required=True)
            clone_repository(repo_url, local_path)
        
        elif choice == "2":
            print("\n【检查更新】")
            local_path = get_input("本地仓库路径: ", required=True)
            result = check_updates(local_path)
            if result == 1:
                pull_now = get_input("是否立即拉取更新？[y/N]: ", default="n").lower()
                if pull_now == "y":
                    pull_updates(local_path)
        
        elif choice == "3":
            print("\n【拉取最新代码】")
            local_path = get_input("本地仓库路径: ", required=True)
            pull_updates(local_path)
        
        elif choice == "4":
            print("\n【查看仓库信息】")
            local_path = get_input("本地仓库路径: ", required=True)
            get_repo_info(local_path)
        
        elif choice == "5":
            print("\n感谢使用！")
            break
        
        else:
            print_error("无效的选择")

if __name__ == "__main__":
    main()
