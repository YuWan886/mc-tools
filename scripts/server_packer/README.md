# Modrinth Server Packer

一个用于将 Modrinth 整合包（.mrpack）打包成 Minecraft 服务端的 Python 脚本。

## 功能

- 解析 `.mrpack` 文件，提取 `modrinth.index.json` 和覆盖文件。
- 自动检测模组加载器（Forge、Fabric、Quilt、NeoForge）并下载对应的服务器核心。
- 过滤客户端资源（资源包、光影包）和仅客户端模组（通过 Modrinth API 检测环境支持）。
- 并行下载模组和其他文件，支持重试。
- 复制覆盖文件到输出目录。
- 生成跨平台启动脚本（Windows 批处理文件和 Linux/macOS Shell 脚本）。
- 清理临时文件。

## 优化特点

- **精简服务端大小**：仅下载安装器但不运行，用户可手动运行以保持最小输出。
- **并行下载**：使用线程池加速模组下载。
- **智能过滤**：根据 `env.server` 字段或 API 查询跳过仅客户端模组。

## 使用方法

### [使用 Python 脚本](./modrinth_server_packer.py)

```bash
python modrinth_server_packer.py <modpack_file> [--output OUTPUT_DIR]
```

- `<modpack_file>`：Modrinth 整合包文件路径（.mrpack）。
- `--output` 或 `-o`：输出目录（可选）。如果未指定，将自动生成 `output_server/<整合包名称>`。

### [使用可执行文件（推荐）](https://github.com/YuWan886/mc-tools/releases/download/server-packer/modrinth_server_packer.exe)

脚本已打包为单个可执行文件，无需安装 Python 或依赖库。下载 [`modrinth_server_packer.exe`](https://github.com/YuWan886/mc-tools/releases/download/server-packer/modrinth_server_packer.exe) 并直接运行。

```bash
modrinth_server_packer.exe <modpack_file> [--output OUTPUT_DIR]
```

### 示例

```bash
# 使用自动输出目录
python modrinth_server_packer.py "modpack"
# 或使用可执行文件
modrinth_server_packer.exe "modpack"

# 指定输出目录
python modrinth_server_packer.py "modpack" --output my_server
modrinth_server_packer.exe "modpack" --output my_server
```

## 输出结构

输出目录将包含：

- `forge-<version>-installer.jar` 或对应的安装器 JAR。
- `mods/`：过滤后的服务端/通用模组。
- `config/`、`global_packs/` 等：从覆盖文件复制的配置和资源。
- `start.bat` 和 `start.sh`：启动脚本（如果获得了服务器 JAR）。
- 其他必要的文件。

## 依赖

- Python 3.12+
- `requests` 库
- `tqdm` 库

安装依赖：

```bash
pip install -r requirements.txt
```

## 注意事项

- 需要网络连接以下载模组和服务器核心。
- 脚本仅下载安装器，用户需要手动运行安装器来生成服务器文件。
- 启动脚本假设 Java 已安装并位于 PATH 中。