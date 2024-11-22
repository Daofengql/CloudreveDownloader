import argparse
import aiohttp
import asyncio
import os
import hashlib
import pickle
from urllib.parse import quote
from aria2p import API, Client
import subprocess
from loguru import logger
import re

CACHE_DIR = "./cache"

def format_size(size):
    """
    将字节大小格式化为带单位的字符串。
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.2f} {units[index]}"


def parse_share_url(share_url):
    """
    使用正则表达式从分享 URL 中提取 base 和 code，忽略参数和 fragment。
    :param share_url: 分享 URL，例如 https://cloud.furserver.com/s/AB5so?param=value#fragment
    :return: base 和 code
    """
    # 移除参数和 fragment
    cleaned_url = re.sub(r"[?#].*$", "", share_url)
    
    # 匹配 URL 的正则表达式
    match = re.match(r"(https?://[^/]+)/s/([^/?#]+)", cleaned_url)
    if match:
        base, code = match.groups()
        return base, code
    else:
        raise ValueError("无效的分享 URL 格式")
    

def is_aria2c_running():
    """
    检查是否存在 aria2c 进程。
    兼容 Windows 和类 UNIX 系统。
    """
    try:
        if os.name == "nt":  # Windows 系统
            tasks = subprocess.check_output("tasklist", shell=True).decode("gbk", errors="ignore")
            return "aria2c.exe" in tasks
        else:  # 类 UNIX 系统
            subprocess.check_output(["pgrep", "-f", "aria2c"])
            return True
    except subprocess.CalledProcessError:
        return False


async def start_aria2c():
    """
    启动 aria2c 并监听端口 6800。
    如果已运行，则不执行任何操作。
    启动失败时记录错误并终止程序。
    """
    if is_aria2c_running():
        logger.info("aria2c 已在运行，跳过启动。")
        return

    logger.info("启动 aria2c...")
    try:
        process = subprocess.Popen(
            [
                "./aria2c",
                "--enable-rpc",
                "--rpc-listen-all=false",
                "--rpc-listen-port=6800",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 等待 2 秒以确保进程成功启动
        await asyncio.sleep(2)

        if not is_aria2c_running():
            logger.error("aria2c 启动失败，请检查是否已正确安装或配置。")
            process.terminate()
            raise RuntimeError("aria2c 启动失败")
    except FileNotFoundError:
        logger.error("aria2c 未找到，请确保已正确安装并将其路径添加到系统环境变量中。")
        os._exit(1)
    except Exception as e:
        logger.error(f"启动 aria2c 时发生错误: {e}")
        os._exit(1)
    logger.info("aria2c 已启动。")





def generate_cache_key(base_url, share_code):
    """
    生成缓存文件的 MD5 键。
    """
    key = f"{base_url}:{share_code}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def save_to_cache(data, cache_key):
    """
    保存数据到缓存。
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    with open(cache_file, "wb") as f:
        pickle.dump(data, f)
    logger.info(f"数据已缓存到 {cache_file}")


def load_from_cache(cache_key):
    """
    从缓存中加载数据。
    """
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            logger.info(f"从缓存加载数据 {cache_file}")
            return pickle.load(f)
    return None


async def fetch_file_paths(session, base_url, share_code, path="", collected_files=None):
    """
    递归获取所有文件的完整路径和大小。
    """
    if collected_files is None:
        collected_files = []

    path = path.strip('/')
    encoded_path = quote(path, safe="")
    url = f"{base_url}/api/v3/share/list/{share_code}%2F{encoded_path}"

    async with session.get(url) as response:
        if response.status != 200:
            logger.error(f"请求失败：{url}, 状态码: {response.status}")
            return collected_files

        data = await response.json()
        if data.get("code") != 0:
            logger.error(f"API 错误: {data.get('msg')}, URL: {url}")
            return collected_files

        for obj in data["data"].get("objects", []):
            obj_name = obj['name']
            obj_path = f"{path}/{obj_name}".strip('/')
            if obj["type"] == "dir":
                await fetch_file_paths(session, base_url, share_code, path=obj_path, collected_files=collected_files)
            else:
                collected_files.append((f"/{obj_path}", obj["size"]))

    return collected_files


async def get_download_links(session, base_url, share_code, file_paths):
    """
    获取所有文件的下载链接。
    """
    links = {}
    for file_path in file_paths:
        encoded_file_path = quote(file_path, safe="")
        url = f"{base_url}/api/v3/share/download/{share_code}?path={encoded_file_path}"

        async with session.put(url) as response:
            if response.status != 200:
                logger.error(f"下载链接请求失败：{url}, 状态码: {response.status}")
                continue

            data = await response.json()
            if data.get("code") != 0:
                logger.error(f"获取下载链接失败: {data.get('msg')}, URL: {url}")
                continue

            links[file_path] = data.get("data")
    return links


async def monitor_overall_progress(api, total_files, total_size):
    """
    每 15 秒更新一次总下载进度，直到剩余文件数为 0 或 aria2c 进程退出。
    """
    while True:
        # 检查 aria2c 是否仍在运行
        if not is_aria2c_running():
            logger.warning("aria2c 进程已退出，停止监控下载进度。")
            break

        downloads = api.get_downloads()
        completed_files = sum(1 for d in downloads if d.is_complete)
        remaining_files = total_files - completed_files
        downloaded_size = sum(d.completed_length for d in downloads)
        progress = (downloaded_size / total_size) * 100 if total_size > 0 else 0

        logger.info(
            f"下载进度: 已完成 {completed_files}/{total_files} 文件，"
            f"已下载大小: {format_size(downloaded_size)}/{format_size(total_size)}，"
            f"总进度: {progress:.2f}%"
        )

        # 如果剩余文件为 0，停止监控
        if remaining_files <= 0:
            logger.info("所有文件已下载完成，停止监控进度。")
            break

        await asyncio.sleep(15)


async def download_file(semaphore, api, download_link, file_path, download_root):
    """
    下载单个文件的协程。
    """
    async with semaphore:
        try:
            local_file_path = os.path.join(download_root, file_path.lstrip('/'))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            api.add_uris([download_link], options={"dir": os.path.dirname(local_file_path)})
            logger.info(f"已添加到下载队列: {file_path}")
        except Exception as e:
            logger.error(f"下载失败: {file_path}, 错误: {e}")


async def main(share_url, download_root, max_concurrent_downloads):
    base_url, share_code = parse_share_url(share_url)

    await start_aria2c()  # 确保 aria2c 启动

    # 初始化 aria2p API
    client = Client(host="http://localhost", port=6800, secret="")
    api = API(client)

    cache_key = generate_cache_key(base_url, share_code)
    cache_data = load_from_cache(cache_key)

    async with aiohttp.ClientSession() as session:
        if cache_data:
            collected_files, download_links = cache_data
        else:
            collected_files = await fetch_file_paths(session, base_url, share_code)
            collected_files.sort(key=lambda x: x[1])  # 按文件大小排序
            file_paths = [file[0] for file in collected_files]
            download_links = await get_download_links(session, base_url, share_code, file_paths)
            save_to_cache((collected_files, download_links), cache_key)

        total_files = len(collected_files)
        total_size = sum(size for _, size in collected_files)
        logger.info(f"\n总文件数: {total_files}, 总大小: {format_size(total_size)}")

        if collected_files:
            tasks = []
            for file_path, _ in collected_files:
                download_link = download_links.get(file_path)
                if download_link:
                    task = asyncio.create_task(
                        download_file(asyncio.Semaphore(max_concurrent_downloads), api, download_link, file_path, download_root)
                    )
                    tasks.append(task)

            monitor_task = asyncio.create_task(monitor_overall_progress(api, total_files, total_size))
            await asyncio.gather(*tasks)
            await monitor_task


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载分享链接中的文件")
    parser.add_argument("share_url", help="分享链接，例如 https://cloud.furserver.com/s/AB5so")
    parser.add_argument("-d", "--download-root", default="./download", help="下载保存的根目录 (默认: ./download)")
    parser.add_argument("-n", "--max-concurrent-downloads", type=int, default=10, help="最大并发下载数 (默认: 10)")
    args = parser.parse_args()

    logger.add("download.log", rotation="10 MB", retention="7 days", level="INFO")
    asyncio.run(main(args.share_url, args.download_root, args.max_concurrent_downloads))
