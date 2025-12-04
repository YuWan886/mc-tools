import argparse
import json
import os
import shutil
import zipfile
import requests
import sys
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
from tqdm import tqdm

# 配置日志
log_file = "modrinth_server_packer.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8',
    handlers=[
        logging.FileHandler(log_file, mode='w'),  # 将日志写入文件，每次运行覆盖
        logging.StreamHandler(sys.stdout)  # 将日志输出到控制台
    ]
)
logger = logging.getLogger(__name__)

# 全局缓存
_version_details_cache: Dict[str, Any] = {}
_project_details_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()

def main():
    # 临时启用调试日志
    # logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(description="将 Modrinth 整合包打包为 Minecraft 服务器。")
    parser.add_argument("path", help=".mrpack 文件或包含 .mrpack 文件的目录的路径。")
    parser.add_argument("--output", "-o", help="输出服务器文件的基础目录。如果未提供,将使用 'output_server/'。对于单个文件,输出将为 'output_server/<modpack_name>'。")
    parser.add_argument("--parallel", "-p", action="store_true", help="并行处理多个整合包 (默认: 顺序)。")
    args = parser.parse_args()

    path = args.path
    output_base = args.output
    parallel = args.parallel

    # 判断路径是文件还是目录
    if os.path.isfile(path):
        modpack_files = [path]
    elif os.path.isdir(path):
        # 递归查找所有 .mrpack 文件
        modpack_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.lower().endswith('.mrpack'):
                    modpack_files.append(os.path.join(root, file))
        if not modpack_files:
            print(f"错误: 在目录 {path} 中未找到任何 .mrpack 文件。")
            sys.exit(1)
        print(f"找到 {len(modpack_files)} 个 .mrpack 文件。")
    else:
        print(f"错误: 路径 '{path}' 不存在。")
        sys.exit(1)

    # 处理每个整合包
    success_count = 0
    if parallel:
        print(f"并行处理 {len(modpack_files)} 个整合包...")
        # 使用线程池，最大工作线程数为 min(10, 文件数量)
        max_workers = min(10, len(modpack_files))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}
            for modpack_file in modpack_files:
                # 确定此整合包的输出目录
                if output_base:
                    base_dir = output_base
                else:
                    base_dir = "output_server"
                modpack_name = os.path.splitext(os.path.basename(modpack_file))[0]
                output_dir = os.path.join(base_dir, modpack_name)
                future = executor.submit(process_single_modpack, modpack_file, output_dir)
                future_to_file[future] = (modpack_file, output_dir)
            
            # 等待所有任务完成
            for future in as_completed(future_to_file):
                modpack_file, output_dir = future_to_file[future]
                try:
                    future.result()
                    success_count += 1
                    print(f"成功处理: {modpack_file}")
                except Exception as e:
                    print(f"处理 {modpack_file} 时发生错误: {e}")
    else:
        for modpack_file in modpack_files:
            print(f"\n=== 正在处理 {modpack_file} ===")
            # 确定此整合包的输出目录
            if output_base:
                base_dir = output_base
            else:
                base_dir = "output_server"
            modpack_name = os.path.splitext(os.path.basename(modpack_file))[0]
            output_dir = os.path.join(base_dir, modpack_name)
            print(f"输出目录: {output_dir}")
            try:
                process_modpack(modpack_file, output_dir)
                success_count += 1
            except Exception as e:
                print(f"处理 {modpack_file} 时发生错误: {e}")
                continue

    print(f"\n成功处理了 {success_count}/{len(modpack_files)} 个整合包。")

def process_single_modpack(modpack_file, output_dir):
    """包装器函数，用于并行处理单个整合包，捕获异常。"""
    try:
        process_modpack(modpack_file, output_dir)
    except Exception as e:
        logger.error(f"处理整合包时发生错误: {e}")
        raise

def process_modpack(modpack_file, output_dir):
    """处理单个整合包文件并生成服务器文件。"""
    if not os.path.exists(modpack_file):
        raise FileNotFoundError(f"Modpack file not found at {modpack_file}")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"正在处理整合包: {modpack_file}")
    logger.info(f"输出目录: {output_dir}")

    # 步骤1: 解压.mrpack文件
    extract_path = os.path.join(output_dir, "extracted_modpack")
    os.makedirs(extract_path, exist_ok=True)
    with zipfile.ZipFile(modpack_file, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    logger.info(f"整合包已解压到 {extract_path}")

    # 步骤2: 解析modrinth.index.json
    modrinth_index_path = os.path.join(extract_path, "modrinth.index.json")
    if not os.path.exists(modrinth_index_path):
        raise FileNotFoundError(f"在整合包中未找到 modrinth.index.json 文件: {modrinth_index_path}")

    with open(modrinth_index_path, 'r', encoding='utf-8') as f:
        modrinth_index = json.load(f)

    game_version = modrinth_index["dependencies"]["minecraft"]
    logger.info(f"Minecraft版本: {game_version}")

    # 确定模组加载器
    loader = None
    loader_version = None
    if "forge" in modrinth_index["dependencies"]:
        loader = "forge"
        loader_version = modrinth_index["dependencies"]["forge"]
    elif "fabric-loader" in modrinth_index["dependencies"]:
        loader = "fabric"
        loader_version = modrinth_index["dependencies"]["fabric-loader"]
    elif "quilt-loader" in modrinth_index["dependencies"]:
        loader = "quilt"
        loader_version = modrinth_index["dependencies"]["quilt-loader"]
    elif "neoforge" in modrinth_index["dependencies"]:
        loader = "neoforge"
        loader_version = modrinth_index["dependencies"]["neoforge"]
    else:
        raise ValueError("整合包中使用了不支持或未知的模组加载器。")

    logger.info(f"模组加载器: {loader} {loader_version}")

    # 步骤3: 下载服务器安装程序
    server_jar_name = install_server(output_dir, game_version, loader, loader_version)
    if not server_jar_name:
        logger.warning("警告: 未获取到服务器JAR文件。您需要手动运行安装程序。")
        # 继续下载模组和覆盖文件,但跳过创建启动脚本。

    # 步骤4: 下载模组(并行)
    mods_dir = os.path.join(output_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    # 准备下载任务并收集项目ID以进行批量查询
    download_tasks = []
    mod_file_hashes = []
    file_hash_to_file_entry = {}

    for file_entry in modrinth_index["files"]:
        path = file_entry["path"]
        if path.startswith("resourcepacks/") or path.startswith("shaderpacks/") or \
           (os.sep not in path and (path == "options.txt" or path == "servers.dat")) or \
           path.startswith("essential/"):
            logger.info(f"跳过客户端资源或排除的文件/目录: {path}")
            continue

        if path.startswith("mods/"):
            file_hash = file_entry["hashes"].get("sha1") or file_entry["hashes"].get("sha512")
            if not file_hash:
                logger.warning(f"警告: {path} 没有哈希值,跳过")
                continue
            mod_file_hashes.append(file_hash)
            file_hash_to_file_entry[file_hash] = file_entry
        else:
            # 其他文件(configs, scripts等) - 直接下载到输出目录并保留路径
            dest = os.path.join(output_dir, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            url = file_entry["downloads"][0] if isinstance(file_entry["downloads"], list) else file_entry["downloads"]
            download_tasks.append((url, dest, path))

    all_project_ids = []
    file_hash_to_project_id = {}
    # 批量获取版本详情
    version_details_map = get_mod_version_details_batch(mod_file_hashes)
    logger.debug(f"version_details_map keys: {list(version_details_map.keys())}")
    for file_hash in mod_file_hashes:
        version_details = version_details_map.get(file_hash)
        logger.debug(f"hash {file_hash}: version_details type {type(version_details)} value {version_details}")
        if version_details and version_details.get("project_id"):
            project_id = version_details["project_id"]
            all_project_ids.append(project_id)
            file_hash_to_project_id[file_hash] = project_id
        else:
            logger.warning(f"警告: 无法获取哈希值为 {file_hash} 的模组的 project_id")

    # 批量获取项目详情
    project_details_cache = get_mods_project_details_batch(all_project_ids)

    # 现在,再次遍历模组以确定服务器支持并准备下载任务
    for file_hash in mod_file_hashes:
        file_entry = file_hash_to_file_entry[file_hash]
        path = file_entry["path"]
        
        project_id = file_hash_to_project_id.get(file_hash)
        if not project_id:
            server_support = "unknown"
        else:
            project_details = project_details_cache.get(project_id)
            server_support = get_mod_server_support_from_details(project_details)

        if server_support in ["required", "optional"]:
            url = file_entry["downloads"][0] if isinstance(file_entry["downloads"], list) else file_entry["downloads"]
            filename = os.path.basename(path)
            dest = os.path.join(mods_dir, filename)
            download_tasks.append((url, dest, filename))
            logger.info(f"包含模组(服务器支持: {server_support}): {path}")
        else:
            logger.info(f"跳过客户端或不支持的模组(服务器支持: {server_support}): {path}")

    # 并行下载并显示进度
    if download_tasks:
        logger.info(f"正在下载 {len(download_tasks)} 个文件...")
        success = download_files_parallel(download_tasks)
        if not success:
            logger.warning("警告: 部分下载失败,但继续执行。")
    else:
        logger.info("没有文件需要下载。")

    # 步骤5: 复制覆盖文件,排除客户端资源
    overrides_path = os.path.join(extract_path, "overrides")
    if os.path.exists(overrides_path):
        logger.info(f"正在将覆盖文件从 {overrides_path} 复制到 {output_dir}")
        # 定义一个函数来忽略客户端资源目录
        def ignore_client_resources(src, names):
            ignored = set()
            for name in names:
                full_path = os.path.join(src, name)
                rel_path = os.path.relpath(full_path, overrides_path)
                # 跳过任何级别的resourcepacks或shaderpacks目录
                if (name in ('resourcepacks', 'shaderpacks') and os.path.isdir(full_path)) or \
                   (rel_path == "options.txt" or rel_path == "servers.dat") or \
                   (name == 'essential' and os.path.isdir(full_path)):
                    ignored.add(name)
                    logger.info(f"跳过客户端资源或排除的文件/目录: {rel_path}")
            return ignored
        shutil.copytree(overrides_path, output_dir, dirs_exist_ok=True, ignore=ignore_client_resources)

    # 步骤6: 如果有服务器JAR,则创建启动脚本
    if server_jar_name:
        create_start_script(output_dir, server_jar_name, loader)
    else:
        logger.info("跳过创建启动脚本,因为没有可用的服务器JAR文件。")

    # 步骤7: 清理临时提取目录
    shutil.rmtree(extract_path, ignore_errors=True)
    logger.info(f"已清理临时提取目录: {extract_path}")

    logger.info("服务器打包完成!")
    logger.info(f"服务器已准备就绪: {os.path.abspath(output_dir)}")


def download_file(url, dest_path, max_retries=3):
    """下载文件并支持重试"""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if isinstance(url, list):
        url = url[0]
    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=16384):  # 增加 chunk_size
                    f.write(chunk)
            return True
        except Exception as e:
            logger.debug(f"下载尝试 {attempt + 1} 失败 (URL: {url}): {e}")
            if attempt == max_retries - 1:
                logger.error(f"所有下载尝试均失败 (URL: {url}): {e}")
                return False
            time.sleep(2)
    return False

def get_mod_version_details(file_hash):
    """
    使用文件哈希从Modrinth API获取模组版本详情。
    返回包含'project_id'的完整JSON响应。
    """
    # 首先检查缓存
    global _version_details_cache, _cache_lock
    with _cache_lock:
        if file_hash in _version_details_cache:
            return _version_details_cache[file_hash]
    api_url = f"https://api.modrinth.com/v2/version_file/{file_hash}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        details = response.json()
        with _cache_lock:
            _version_details_cache[file_hash] = details
        return details
    except requests.exceptions.RequestException as e:
        logger.error(f"获取哈希值为 {file_hash} 的模组版本详情时发生错误: {e}")
        return None

def get_mod_version_details_batch(hashes):
    """
    批量获取多个哈希的版本详情。
    返回字典 {hash: version_details}。
    """
    global _version_details_cache, _cache_lock
    result = {}
    missing = []
    with _cache_lock:
        for h in hashes:
            if h in _version_details_cache:
                result[h] = _version_details_cache[h]
            else:
                missing.append(h)
    if not missing:
        return result

    # 分块请求，每块最多200个哈希
    chunk_size = 200
    for i in range(0, len(missing), chunk_size):
        chunk = missing[i:i + chunk_size]
        api_url = "https://api.modrinth.com/v2/version_files"
        try:
            response = requests.post(api_url, json={"hashes": chunk}, timeout=15)
            response.raise_for_status()
            data = response.json()  # 可能是列表或字典
            logger.debug(f"Batch response type: {type(data)}, length: {len(data) if isinstance(data, list) else 'not list'}")
            if isinstance(data, dict):
                logger.debug(f"Batch response dict keys: {list(data.keys())}")
                # 记录第一个键的值以检查类型
                if data:
                    first_key = next(iter(data))
                    logger.debug(f"First value type: {type(data[first_key])}, value: {data[first_key]}")
            if isinstance(data, list) and data:
                logger.debug(f"First element type: {type(data[0])}, value: {data[0]}")
            with _cache_lock:
                if isinstance(data, dict):
                    # 字典映射哈希 -> 详情
                    for h in chunk:
                        detail = data.get(h)
                        if detail is not None:
                            _version_details_cache[h] = detail
                            result[h] = detail
                        else:
                            logger.warning(f"警告: 无法获取哈希值为 {h} 的模组版本详情")
                else:
                    # 假设是列表，顺序与请求相同
                    for h, detail in zip(chunk, data):
                        if detail is not None:
                            _version_details_cache[h] = detail
                            result[h] = detail
                        else:
                            logger.warning(f"警告: 无法获取哈希值为 {h} 的模组版本详情")
        except requests.exceptions.RequestException as e:
            logger.error(f"批量获取版本详情时发生错误: {e}")
            # 回退到逐个获取
            for h in chunk:
                detail = get_mod_version_details(h)
                if detail:
                    with _cache_lock:
                        _version_details_cache[h] = detail
                    result[h] = detail
    return result

def get_mods_project_details_batch(project_ids: List[str], chunk_size: int = 100, max_workers: int = 10) -> Dict[str, Any]:
    """
    使用项目ID列表从Modrinth API批量获取多个模组项目的详情。
    支持分块并发查询以加快速度,并使用全局缓存。
    返回一个字典,其中键是项目ID,值是项目详情。
    """
    if not project_ids:
        return {}

    global _project_details_cache, _cache_lock
    results = {}
    missing_project_ids = []

    with _cache_lock:
        for pid in project_ids:
            if pid in _project_details_cache:
                results[pid] = _project_details_cache[pid]
            else:
                missing_project_ids.append(pid)

    if not missing_project_ids:
        return results

    total_missing = len(missing_project_ids)
    logger.info(f"正在从Modrinth API批量获取 {total_missing} 个缺失的项目详情...")

    # 如果数量小于等于chunk_size,直接单次请求(避免不必要的并发)
    if total_missing <= chunk_size:
        chunk_result = _fetch_project_chunk(missing_project_ids)
        with _cache_lock:
            _project_details_cache.update(chunk_result)
        results.update(chunk_result)
        return results

    # 分块
    chunks = []
    for i in range(0, total_missing, chunk_size):
        chunk = missing_project_ids[i:i + chunk_size]
        chunks.append(chunk)

    logger.info(f"分 {len(chunks)} 个块并发查询...")

    failed_chunks = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {executor.submit(_fetch_project_chunk, chunk): chunk for chunk in chunks}
        for future in as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            try:
                chunk_result = future.result()
                if chunk_result:
                    with _cache_lock:
                        _project_details_cache.update(chunk_result)
                    results.update(chunk_result)
                else:
                    failed_chunks.append(chunk)
            except Exception as e:
                logger.error(f"获取块 {chunk} 时发生错误: {e}")
                failed_chunks.append(chunk)

    # 如果有失败的块,尝试重试(简单重试一次)
    if failed_chunks:
        logger.warning(f"{len(failed_chunks)} 个块查询失败,正在重试...")
        for chunk in failed_chunks[:]:  # 复制列表以便修改
            try:
                chunk_result = _fetch_project_chunk(chunk)
                if chunk_result:
                    with _cache_lock:
                        _project_details_cache.update(chunk_result)
                    results.update(chunk_result)
                    failed_chunks.remove(chunk)
            except Exception as e:
                logger.error(f"重试块 {chunk} 时仍然失败: {e}")

        if failed_chunks:
            logger.error(f"{len(failed_chunks)} 个块最终失败,将丢失这些项目详情。")

    return results


def _fetch_project_chunk(project_ids: List[str]) -> Dict[str, Any]:
    """
    内部函数:获取单个块的项目详情。
    """
    if not project_ids:
        return {}
    
    ids_param = json.dumps(project_ids)
    api_url = f"https://api.modrinth.com/v2/projects?ids={ids_param}"
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        projects_data = response.json()
        return {project["id"]: project for project in projects_data}
    except requests.exceptions.RequestException as e:
        logger.error(f"获取块 {project_ids} 时发生错误: {e}")
        raise  # 抛出异常供上层处理

def get_mod_server_support_from_details(project_details: Optional[Dict[str, Any]]) -> str:
    """根据项目详情返回 'required'、'optional'、'unsupported' 或 'unknown'。"""
    if not project_details:
        return "unknown"
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"project_details type: {type(project_details)}, value: {project_details}")
    if isinstance(project_details, str):
        logger.error(f"project_details is a string: {project_details}")
        return "unknown"

    client_side = project_details.get("client_side")
    server_side = project_details.get("server_side")

    if server_side == "required":
        return "required"
    elif server_side == "optional":
        return "optional"
    elif server_side == "unsupported":
        return "unsupported"
    elif client_side == "required" and server_side == "unspecified":
        # If client_side is required and server_side is unspecified, it's likely client-only
        return "unsupported"
    else:
        # Default to optional if information is ambiguous or unspecified
        return "optional"

def get_mod_server_support(file_hash):
    """此函数现已被弃用。请确保项目详情已预缓存并使用 get_mod_server_support_from_details。"""
    logger.warning("警告: get_mod_server_support 已弃用。请确保项目详情已预缓存并使用 get_mod_server_support_from_details。")
    return "unknown" # Fallback, should not be called directly in optimized flow

def install_server(output_dir, game_version, loader, loader_version):
    """下载并运行服务器安装程序，返回服务器 JAR 文件名。"""
    if loader == "forge":
        return install_forge(output_dir, game_version, loader_version)
    elif loader == "fabric":
        return install_fabric(output_dir, game_version, loader_version)
    elif loader == "quilt":
        return install_quilt(output_dir, game_version, loader_version)
    elif loader == "neoforge":
        return install_neoforge(output_dir, game_version, loader_version)
    else:
        print(f"Unsupported loader: {loader}")
        return None

def install_forge(output_dir, game_version, forge_version):
    """下载 Forge 安装程序 (不运行安装程序)。"""
    # 下载安装程序但不运行它
    installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{game_version}-{forge_version}/forge-{game_version}-{forge_version}-installer.jar"
    installer_path = os.path.join(output_dir, f"forge-{game_version}-{forge_version}-installer.jar")
    logger.info(f"正在下载 Forge 安装程序: {installer_url}")
    if not download_file(installer_url, installer_path):
        logger.error("下载 Forge 安装程序失败。")
        return None

    logger.info(f"安装程序已保存为: {os.path.basename(installer_path)}")
    return os.path.basename(installer_path)

def install_fabric(output_dir, game_version, fabric_version):
    """下载 Fabric 服务器 JAR。"""
    # 获取最新的 Fabric 安装程序版本
    installer_versions_url = "https://meta.fabricmc.net/v2/versions/installer"
    logger.info(f"正在从 {installer_versions_url} 获取 Fabric 安装程序版本")
    try:
        response = requests.get(installer_versions_url, timeout=10)
        response.raise_for_status()
        installer_versions = response.json()
        if not installer_versions:
            logger.error("错误: 未找到 Fabric 安装程序版本。")
            return None
        # 查找最新的稳定安装程序版本
        latest_installer_version = next((v["version"] for v in installer_versions if not v["stable"] == False), None)
        if not latest_installer_version:
            logger.error("错误: 未找到稳定的 Fabric 安装程序版本。")
            return None
        logger.info(f"最新的 Fabric 安装程序版本: {latest_installer_version}")
    except requests.exceptions.RequestException as e:
        logger.error(f"获取 Fabric 安装程序版本时发生错误: {e}")
        return None

    # 使用安装程序版本构建服务器 JAR URL
    server_jar_url = f"https://meta.fabricmc.net/v2/versions/loader/{game_version}/{fabric_version}/{latest_installer_version}/server/jar"
    server_jar_name = f"fabric-server-mc.{game_version}-loader.{fabric_version}-installer.{latest_installer_version}.jar"
    server_jar_path = os.path.join(output_dir, server_jar_name)

    logger.info(f"正在从 {server_jar_url} 下载 Fabric 服务器 JAR")
    if not download_file(server_jar_url, server_jar_path):
        logger.error("下载 Fabric 服务器 JAR 失败。")
        return None
    logger.info(f"已下载 Fabric 服务器 JAR: {os.path.basename(server_jar_path)}")
    return os.path.basename(server_jar_path)

def install_quilt(output_dir, game_version, quilt_version):
    """下载 Quilt 安装程序 (不运行)。"""
    installer_url = f"https://maven.quiltmc.org/repository/release/org/quiltmc/quilt-installer/{quilt_version}/quilt-installer-{quilt_version}.jar"
    installer_path = os.path.join(output_dir, f"quilt-installer-{quilt_version}.jar")
    logger.info(f"正在从 {installer_url} 下载 Quilt 安装程序")
    if not download_file(installer_url, installer_path):
        logger.error("下载 Quilt 安装程序失败。")
        return None
    logger.info("跳过安装程序执行 (用户必须手动运行)。")
    logger.info(f"安装程序已保存为: {os.path.basename(installer_path)}")
    return None

def install_neoforge(output_dir, game_version, neoforge_version):
    """下载 NeoForge 安装程序。"""
    installer_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neoforge_version}/neoforge-{neoforge_version}-installer.jar"
    installer_path = os.path.join(output_dir, f"neoforge-{neoforge_version}-installer.jar")
    logger.info(f"正在从 {installer_url} 下载 NeoForge 安装程序")
    if not download_file(installer_url, installer_path):
        logger.error("下载 NeoForge 安装程序失败。")
        return None
    
    logger.info(f"安装程序已保存为: {os.path.basename(installer_path)}")
    return os.path.basename(installer_path)

def download_files_parallel(tasks, max_workers=10):  # 增加 max_workers
    """使用进度条并行下载多个文件。"""
    failed = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(download_file, url, dest): (url, dest, name) for url, dest, name in tasks}
        
        for future in tqdm(as_completed(future_to_task), total=len(tasks), desc="下载文件"):
            url, dest, name = future_to_task[future]
            try:
                success = future.result()
                if success:
                    logger.info(f"已下载 {name}")
                else:
                    logger.warning(f"下载失败 {name}")
                    failed.append((url, dest, name))
            except Exception as e:
                logger.error(f"下载 {name} 时发生错误: {e}")
                failed.append((url, dest, name))

    if failed:
        logger.error(f"{len(failed)} 个文件下载失败。")
        return False
    return True

def create_start_script(output_dir, server_jar_name, loader):
    """为 Windows 和 Linux 创建启动脚本。"""
    # 根据加载器确定 Java 参数
    java_args = "-Xmx4G -Xms4G"
    # 根据加载器确定附加参数
    additional_args = "nogui"
    if loader == "neoforge" or loader == "forge":
        additional_args = "--installServer"
    
    # Windows 批处理脚本
    if loader == "neoforge" or loader == "forge":
        bat_content = f"""@echo off
java {java_args} -jar {server_jar_name} {additional_args}
if %ERRORLEVEL% == 0 (
    del /f /q {server_jar_name}
    del /f /q "%~f0"
    del /f /q "installer.log"
    del /f /q "start.sh" 2>nul
)
"""
    else:
        bat_content = f"""@echo off
java {java_args} -jar {server_jar_name} {additional_args}
pause
"""
    
    bat_path = os.path.join(output_dir, "start.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    # Linux Shell 脚本
    if loader == "neoforge" or loader == "forge":
        sh_content = f"""#!/bin/bash
java {java_args} -jar {server_jar_name} {additional_args}
if [ $? -eq 0 ]; then
    rm -f {server_jar_name}
    rm -f "$0"
    del /f /q "installer.log"
    rm -f "start.bat" 2>/dev/null
fi
"""
    else:
        sh_content = f"""#!/bin/bash
java {java_args} -jar {server_jar_name} {additional_args}
"""
    
    sh_path = os.path.join(output_dir, "start.sh")
    with open(sh_path, "w", encoding="utf-8") as f:
        f.write(sh_content)
    os.chmod(sh_path, 0o755)


if __name__ == "__main__":
    main()