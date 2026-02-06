#!/usr/bin/env python3
"""
FastAPI 应用测试脚本
测试所有 API 端点
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查"""
    print("\n📋 测试健康检查...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")
    assert response.status_code == 200
    print("   ✅ 健康检查通过")

def test_get_systems():
    """测试获取支持的系统列表"""
    print("\n📋 测试获取支持的系统列表...")
    response = requests.get(f"{BASE_URL}/api/systems")
    print(f"   状态码: {response.status_code}")
    systems = response.json()
    print(f"   支持的系统: {list(systems.keys())}")
    assert response.status_code == 200
    print("   ✅ 系统列表获取成功")

def test_list_tasks():
    """测试列出任务"""
    print("\n📋 测试列出任务...")
    response = requests.get(f"{BASE_URL}/api/tasks")
    print(f"   状态码: {response.status_code}")
    tasks = response.json()
    print(f"   任务数量: {len(tasks['tasks'])}")
    assert response.status_code == 200
    print("   ✅ 任务列表获取成功")

def test_create_download_task():
    """测试创建下载任务"""
    print("\n📋 测试创建下载任务...")
    
    request_data = {
        "packages": ["nginx"],
        "system_type": "rpm",
        "distribution": "centos-7",
        "arch": "x86_64",
        "deep_download": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/download",
        json=request_data
    )
    print(f"   状态码: {response.status_code}")
    result = response.json()
    print(f"   任务ID: {result['task_id']}")
    print(f"   状态: {result['status']}")
    
    assert response.status_code == 200
    assert "task_id" in result
    print("   ✅ 下载任务创建成功")
    
    return result['task_id']

def test_get_task_status(task_id):
    """测试获取任务状态"""
    print(f"\n📋 测试获取任务状态 (task_id: {task_id})...")
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
    print(f"   状态码: {response.status_code}")
    task = response.json()
    print(f"   任务状态: {task['status']}")
    print(f"   进度: {task['progress']}%")
    print(f"   消息: {task['message']}")
    assert response.status_code == 200
    print("   ✅ 任务状态获取成功")

def main():
    print("=" * 60)
    print("FastAPI 应用 API 测试")
    print("=" * 60)
    
    try:
        # 1. 健康检查
        test_health_check()
        
        # 2. 获取系统列表
        test_get_systems()
        
        # 3. 列出任务
        test_list_tasks()
        
        # 4. 创建下载任务
        task_id = test_create_download_task()
        
        # 等待一下
        time.sleep(2)
        
        # 5. 获取任务状态
        test_get_task_status(task_id)
        
        print("\n" + "=" * 60)
        print("所有测试通过! ✅")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print("请确保服务器正在运行: ./start.sh")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()
