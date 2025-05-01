# VP模块生成工具 v1.0

## 功能说明
本脚本用于处理Java项目源代码，自动生成VaultPatcher(VP)模块所需的JSON文件，并提取处理语言文件。

主要功能：
1. 从Java源代码中提取特定字符串模式
2. 生成VP模块JSON模板
3. 处理JSON数据并生成语言文件
4. 支持数据写回操作

## 文件夹结构
- `java_projects/` - 存放需要处理的Java项目源代码
- `vp/` - 存放生成的VP模块JSON文件
- `lang/` - 存放处理后的语言文件(JSON格式)

## 使用步骤
1. 将Java项目放入`java_projects`文件夹
2. 运行脚本`VP模块生成-v1.0.py`
3. 选择菜单操作：
   - 1: 从Java文件生成JSON
   - 2: 提取JSON数据到语言文件
   - 3: 将语言文件数据写回JSON
   - 4: 退出程序

## 依赖安装
运行前请确保安装所需依赖：
```bash
pip install -r requirements.txt
```

## 注意事项
- Java文件需包含特定字符串模式：`Component.m_237113_("...")`
- 生成的JSON文件会保存在vp目录
- 语言文件会保存在lang目录