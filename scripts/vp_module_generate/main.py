import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Union
from tqdm import tqdm

# 常量定义
JAVA_PROJECTS_DIR = "java_projects"
VP_DIR = "vp"
LANG_DIR = "lang"
JSON_EXT = ".json"
ENCODING = "utf-8"


def create_folders() -> None:
    """创建必要的文件夹结构，处理权限错误"""
    for folder in [JAVA_PROJECTS_DIR, VP_DIR, LANG_DIR]:
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
            print(f"已创建/验证文件夹: {folder}")
        except (PermissionError, OSError) as e:
            print(f"无法创建文件夹 {folder}：{e}")
            print("请检查目录权限或路径是否有效")
            raise SystemExit(1)


def extract_strings_from_java(java_file_path: str) -> List[str]:
    """从Java文件中提取特定字符串"""
    pattern = re.compile(r'Component\.m_237113_\("([^"]+)"\)')
    extracted_strings = []
    try:
        with open(java_file_path, "r", encoding=ENCODING) as file:
            for line in file:
                matches = pattern.findall(line)
                extracted_strings.extend(matches)
    except Exception as e:
        print(f"读取 {java_file_path} 出错：{e}")
    return extracted_strings


def create_json_template(project_name: str, class_data: List[Dict]) -> List[Dict]:
    """创建JSON模板"""
    template = [
        {
            "name": project_name,
            "desc": "",
            "mods": project_name,
            "authors": "",
            "dynamic": False,
            "i18n": True,
        }
    ]
    template.extend(class_data)
    return template


def generate_json_from_java() -> None:
    """从Java文件生成JSON文件到vp目录"""
    input_dir = JAVA_PROJECTS_DIR
    output_dir = VP_DIR
    generated_files = []
    try:
        for project_name in os.listdir(input_dir):
            project_path = os.path.join(input_dir, project_name)
            if not os.path.isdir(project_path):
                continue
            class_data = []
            for root, _, files in os.walk(project_path):
                for file in files:
                    if file.endswith(".java"):
                        java_file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(java_file_path, project_path)
                        class_path = os.path.splitext(relative_path)[0].replace(
                            os.sep, "/"
                        )
                        strings = extract_strings_from_java(java_file_path)
                        if strings:
                            class_data.append(
                                {
                                    "target_class": {"name": class_path, "method": ""},
                                    "pairs": [{"key": s, "value": s} for s in strings],
                                }
                            )
            if class_data:
                output_json_path = os.path.join(output_dir, f"{project_name}.json")
                json_data = create_json_template(project_name, class_data)
                try:
                    with open(output_json_path, "w", encoding=ENCODING) as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    generated_files.append(output_json_path)
                except Exception as e:
                    print(f"写入 {output_json_path} 出错：{e}")
    except Exception as e:
        print(f"遍历 {input_dir} 出错：{e}")
    print("\n=== 生成 JSON 操作日志 ===")
    if generated_files:
        print(f"成功生成 {len(generated_files)} 个 JSON 文件:")
        for file in generated_files:
            print(f"- {file}")
    else:
        print("未生成任何 JSON 文件")


def load_json_file(file_path: Path) -> Union[Dict, List, None]:
    """安全加载JSON文件"""
    try:
        with open(file_path, "r", encoding=ENCODING) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误：文件 {file_path} 不是有效的JSON格式: {e}")
        return None
    except Exception as e:
        print(f"错误：读取文件 {file_path} 时出错: {e}")
        return None


def save_json_file(file_path: Path, data: Any) -> bool:
    """安全保存JSON文件"""
    try:
        with open(file_path, "w", encoding=ENCODING) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"错误：保存文件 {file_path} 时出错: {e}")
        return False


def process_json_data(data: List[Dict]) -> Dict[str, str]:
    """处理JSON数据，生成基于pairs.value的键值映射"""
    output_data = {}
    seen_values = {}
    current_idx = 1
    for item in data[1:]:
        if "pairs" in item and item["pairs"]:
            class_name = item["target_class"]["name"]
            dirs = class_name.split("/")[:-1]  # 提取目录名，去掉类名
            prefix = dirs[0] if dirs else "default"  # 使用第一个目录名或默认值
            for pair in item["pairs"]:
                value = pair.get("value")  # 提取pairs.value
                if value and value not in seen_values:
                    seen_values[value] = f"{prefix}.{current_idx}"
                    output_data[f"{prefix}.{current_idx}"] = value
                    current_idx += 1
                if value:  # 更新pair的value字段
                    pair["value"] = seen_values[value]
    return output_data


def extract_json() -> None:
    """从vp文件夹提取JSON数据并处理到lang文件夹"""
    processed_files = []
    output_files = []
    # 清空 lang 文件夹，跳过无法删除的文件
    lang_path = Path(LANG_DIR)
    try:
        for file in lang_path.glob("*"):
            try:
                file.unlink()
            except Exception as e:
                print(f"无法删除 {file}：{e}，跳过")
    except Exception as e:
        print(f"访问 {lang_path} 出错：{e}")
    input_files = list(Path(VP_DIR).glob(f"*{JSON_EXT}"))
    for input_path in tqdm(input_files, desc="处理 JSON 文件"):
        output_path = Path(LANG_DIR) / input_path.name
        try:
            data = load_json_file(input_path)
            if data is None:
                print(f"跳过文件 {input_path}：无效的JSON数据")
                continue
            output_data = process_json_data(data)
            if save_json_file(output_path, output_data) and save_json_file(
                input_path, data
            ):
                processed_files.append(str(input_path))
                output_files.append(str(output_path))
            else:
                print(f"跳过文件 {input_path}：保存失败")
        except Exception as e:
            print(f"跳过文件 {input_path} 的处理：{e}")
            continue
    print("\n=== 提取 JSON 操作日志 ===")
    print(f"已处理 {len(processed_files)} 个文件")
    if processed_files:
        print("处理的文件:")
        for file in processed_files:
            print(f"- 输入: {file}")
        print("生成的文件:")
        for file in output_files:
            print(f"- 输出: {file}")
    else:
        print("未处理任何文件")


def write_back() -> None:
    """将lang文件夹的数据写回vp文件夹"""
    processed_files = []
    output_files = list(Path(LANG_DIR).glob(f"*{JSON_EXT}"))
    for output_path in tqdm(output_files, desc="写回 JSON 文件"):
        input_path = Path(VP_DIR) / output_path.name
        if not input_path.exists():
            print(f"警告：{input_path} 不存在，跳过")
            continue
        try:
            output_data = load_json_file(output_path)
            if output_data is None:
                print(f"跳过文件 {output_path}：无效的JSON数据")
                continue
            input_data = load_json_file(input_path)
            if input_data is None:
                print(f"跳过文件 {input_path}：无效的JSON数据")
                continue
            for item in input_data[1:]:
                if "pairs" in item and item["pairs"]:
                    for pair in item["pairs"]:
                        current_value = pair.get("value")
                        if current_value in output_data:
                            pair["value"] = output_data[current_value]
            if save_json_file(input_path, input_data):
                processed_files.append(str(input_path))
            else:
                print(f"跳过文件 {input_path}：保存失败")
        except Exception as e:
            print(f"跳过文件 {output_path} 的处理：{e}")
            continue
    print("\n=== 写回 JSON 操作日志 ===")
    print(f"已写回 {len(processed_files)} 个文件")
    if processed_files:
        print("写回的文件:")
        for file in processed_files:
            print(f"- {file}")
    else:
        print("未写回任何文件")


def display_menu() -> None:
    """显示用户菜单"""
    print("\n用户面板：")
    print("1. 从 Java 文件生成 JSON")
    print("2. 提取 JSON 数据")
    print("3. 写回 JSON 数据")
    print("4. 退出")


def get_user_choice() -> str:
    """获取用户输入并验证"""
    while True:
        choice = input("请输入数字选择操作：").strip()
        if choice in ("1", "2", "3", "4"):
            return choice
        print("无效输入，请重新选择")


def main() -> None:
    """主程序入口"""
    create_folders()  # 在程序启动时创建所有必要文件夹
    while True:
        display_menu()
        choice = get_user_choice()
        if choice == "1":
            generate_json_from_java()
        elif choice == "2":
            extract_json()
        elif choice == "3":
            write_back()
        elif choice == "4":
            print("程序退出")
            break


if __name__ == "__main__":
    main()
