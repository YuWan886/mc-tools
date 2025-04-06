import requests
from datetime import datetime
import json
import os
import sys
import html
import re
from tqdm import tqdm
import argparse
import configparser

# 资源路径修正 - 针对 Nuitka 打包后路径处理
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # 打包后路径：直接使用可执行文件所在目录
        return os.path.dirname(sys.executable)
    # 开发环境路径
    return os.path.dirname(os.path.abspath(__file__))

# 设置基础目录和配置文件路径
BASE_DIR = get_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config():
    """加载配置文件，如果不存在则创建默认配置"""
    default_config = {
        "api": {
            "key": "xxx",  # 你的key
            "base_url": "https://api.curseforge.com/v1"
        },
        "search": {
            "gameId": 432,  # Minecraft的游戏ID
            "searchFilter": "tacz",  # 搜索关键词
            "classId": 4546,  # classId 4546 对应 customization 类别
            "pageSize": 50,  # 每页最大项目
            "sortField": 1,
            "sortOrder": "desc"
        },
        "output": {
            "filename": "tacz_gun_pack.html",
            "title": "永恒枪械工坊：零 (TaCZ) 枪包列表"
        }
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"成功加载配置文件: {CONFIG_FILE}")
                return config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            print("使用默认配置...")
            return default_config
    else:
        # 创建默认配置文件
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
                print(f"已创建默认配置文件: {CONFIG_FILE}")
        except Exception as e:
            print(f"创建配置文件失败: {e}")
        
        return default_config


def fetch_projects_via_api(config, index=0):
    """从CurseForge API获取项目数据，支持分页"""
    url = f"{config['api']['base_url']}/mods/search"
    headers = {
        'x-api-key': config['api']['key'],
        'Accept': 'application/json'
    }
    
    # 从配置文件中获取搜索参数
    params = config['search'].copy()
    params['index'] = index
    
    try:
        print(f"正在请求第{index//params['pageSize'] + 1}页数据...")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"API请求失败: {e}")
        if hasattr(response, 'status_code') and response.status_code == 403:
            print("请检查API密钥是否正确")
        return [], 0

    projects = []
    for item in data.get('data', []):
        try:
            # 处理日期格式（支持带和不带毫秒的情况）
            date_str = item['dateModified']
            try:
                date_modified = datetime.strptime(
                    date_str, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).strftime("%b %d, %Y")
            except ValueError:
                date_modified = datetime.strptime(
                    date_str, "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%b %d, %Y")

            # 获取项目的封面图
            logo_url = ""
            if item.get('logo'):
                logo_url = item['logo'].get('url', '')

            projects.append({
                'title': item['name'],
                'link': item['links']['websiteUrl'],
                'updated': date_modified,
                'iso_date': item['dateModified'],
                'downloads': item['downloadCount'],
                'downloads_display': f"{item['downloadCount']:,}",
                'description': item.get('summary', ''),
                'logo_url': logo_url,
                'id': item['id']
            })
        except KeyError as e:
            print(f"缺少必要字段: {e}")
            continue

    total_count = data.get('pagination', {}).get('totalCount', 0)
    return projects, total_count


def fetch_project_details(config, project_id):
    """获取单个项目的详细信息，包括描述和图片画廊"""
    description_url = f"{config['api']['base_url']}/mods/{project_id}/description"
    headers = {
        'x-api-key': config['api']['key'],
        'Accept': 'application/json'
    }

    try:
        # 获取描述
        response = requests.get(description_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        description = data.get('data', '')
        
        # 处理HTML中的图片和视频尺寸
        description = process_media_sizes(description)
        
        # 获取截图和文件下载信息
        project_url = f"{config['api']['base_url']}/mods/{project_id}"
        project_response = requests.get(project_url, headers=headers)
        project_response.raise_for_status()
        project_data = project_response.json().get('data', {})
        
        screenshots = []
        if 'screenshots' in project_data:
            for screenshot in project_data['screenshots']:
                screenshots.append({
                    'url': screenshot.get('url', ''),
                    'title': screenshot.get('title', '')
                })
        
        # 获取最新文件下载信息 - 修复下载链接问题
        download_url = None
        
        # 获取项目的文件列表
        files_url = f"{config['api']['base_url']}/mods/{project_id}/files"
        files_response = requests.get(files_url, headers=headers)
        files_response.raise_for_status()
        files_data = files_response.json()
        
        # 检查是否有文件
        if files_data.get('data') and len(files_data['data']) > 0:
            # 获取最新的文件
            latest_file = files_data['data'][0]
            download_url = latest_file.get('downloadUrl')
        
        return {
            'description': description,
            'screenshots': screenshots,
            'download_url': download_url
        }
    except Exception as e:
        print(f"获取项目详情失败 (ID: {project_id}): {e}")
        return {'description': '', 'screenshots': [], 'download_url': None}


def process_media_sizes(html_content):
    """处理HTML内容中图片和视频的尺寸，防止它们过大"""
    # 处理图片
    img_pattern = re.compile(r'<img(.*?)>')
    img_with_size_pattern = re.compile(r'<img(.*?)(width|height)\s*=\s*["\'](\d+)["\'].*?>')
    
    # 限制图片最大宽度
    def img_replace(match):
        img_tag = match.group(0)
        if 'width=' not in img_tag.lower() and 'height=' not in img_tag.lower():
            return img_tag.replace('<img', '<img style="max-width:100%; height:auto;"')
        return img_tag
    
    html_content = img_pattern.sub(img_replace, html_content)
    
    # 处理视频嵌入
    iframe_pattern = re.compile(r'<iframe(.*?)>')
    
    def iframe_replace(match):
        iframe_tag = match.group(0)
        if 'width=' in iframe_tag.lower() or 'height=' in iframe_tag.lower():
            # 替换掉现有的宽高属性
            iframe_tag = re.sub(r'(width|height)\s*=\s*["\'](\d+)["\']', '', iframe_tag)
        # 添加响应式样式
        return iframe_tag.replace('<iframe', '<iframe style="max-width:100%; width:560px; height:315px;"')
    
    html_content = iframe_pattern.sub(iframe_replace, html_content)
    
    return html_content


def generate_html(config, projects):
    """生成HTML文件展示项目信息"""
    # 创建docs目录如果不存在
    docs_dir = os.path.join(BASE_DIR, "../../docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    output_path = os.path.join(docs_dir, config['output']['filename'])
    
    # 获取当前系统时间作为更新时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* 基础样式 */
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif; 
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            color: #212529;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        h1 {{ 
            text-align: center; 
            color: #343a40;
            margin-bottom: 30px;
            font-weight: 600;
            padding-bottom: 15px;
            border-bottom: 2px solid #e9ecef;
        }}
        h2 {{
            color: #343a40;
            margin-top: 0;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        /* 表格样式 */
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 20px; 
            box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }}
        th, td {{ 
            padding: 12px 15px; 
            text-align: left; 
            border-bottom: 1px solid #dee2e6; 
        }}
        th {{ 
            background-color: #e9ecef; 
            cursor: pointer; 
            font-weight: 600;
        }}
        tr:hover {{ 
            background-color: #f8f9fa; 
        }}
        
        /* 按钮样式 */
        .button-group {{
            display: flex;
            justify-content: center;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }}
        .btn {{ 
            padding: 10px 20px; 
            margin: 8px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }}
        .btn:hover {{ 
            background-color: #0069d9; 
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .btn-success {{
            background-color: #28a745;
        }}
        .btn-success:hover {{
            background-color: #218838;
        }}
        .btn-secondary {{
            background-color: #6c757d;
        }}
        .btn-secondary:hover {{
            background-color: #5a6268;
        }}
        .btn-danger {{
            background-color: #dc3545;
        }}
        .btn-danger:hover {{
            background-color: #c82333;
        }}
        .btn-warning {{
            background-color: #ffc107;
            color: #212529;
        }}
        .btn-warning:hover {{
            background-color: #e0a800;
        }}
        .btn-info {{
            background-color: #17a2b8;
        }}
        .btn-info:hover {{
            background-color: #138496;
        }}
        .btn-cta {{
            background-color: #28a745;
            padding: 8px 16px;
            font-size: 0.9rem;
            margin-top: 10px;
            margin-right: 10px;
            display: inline-block;
        }}
        .btn-cta:hover {{
            background-color: #218838;
        }}
        .download-cta {{
            background-color: #dc3545;
        }}
        .download-cta:hover {{
            background-color: #c82333;
        }}
        
        /* 项目卡片样式 */
        .project-card {{
            display: flex;
            border: 1px solid #dee2e6;
            margin-bottom: 25px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            background-color: white;
        }}
        .project-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }}
        .project-logo {{
            width: 150px;
            height: 150px;
            object-fit: cover;
            border-right: 1px solid #e9ecef;
        }}
        .project-info {{
            padding: 20px;
            flex-grow: 1;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            background-color: #6c757d;
            color: white;
            border-radius: 4px;
            font-size: 0.75rem;
            margin-right: 5px;
        }}
        .badge-info {{
            background-color: #17a2b8;
        }}
        .badge-success {{
            background-color: #28a745;
        }}
        
        /* 可折叠内容样式 */
        .collapsible {{
            background-color: #f8f9fa;
            color: #343a40;
            cursor: pointer;
            padding: 12px 15px;
            width: 100%;
            border: 1px solid #dee2e6;
            text-align: left;
            outline: none;
            font-size: 16px;
            border-radius: 4px;
            margin-top: 15px;
            transition: background-color 0.3s ease;
            font-weight: 500;
        }}
        .active, .collapsible:hover {{
            background-color: #e9ecef;
        }}
        .content {{
            padding: 0;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-top: none;
            border-radius: 0 0 4px 4px;
        }}
        
        /* 画廊样式 */
        .gallery {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding: 20px;
            justify-content: center;
        }}
        .gallery img {{
            width: 220px;
            height: 165px;
            object-fit: cover;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}
        .gallery img:hover {{
            transform: scale(1.05);
        }}
        
        /* 排序选项样式 */
        .sorting-options {{
            text-align: center;
            margin-bottom: 25px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        /* 描述样式 */
        .description {{
            padding: 20px;
            max-width: 100%;
            overflow-x: auto;
            background-color: white;
            border-radius: 4px;
        }}
        .description img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .description iframe {{
            max-width: 100%;
            border-radius: 4px;
            margin: 10px 0;
        }}
        
        /* 返回顶部按钮 */
        .back-to-top {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: #007bff;
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            text-decoration: none;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
            z-index: 1000;
        }}
        .back-to-top.visible {{
            opacity: 1;
            visibility: visible;
        }}
        .back-to-top:hover {{
            background-color: #0069d9;
        }}
        
        /* Credit 样式 */
        .credits {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 0.9rem;
        }}
        
        /* 响应式调整 */
        @media (max-width: 768px) {{
            .project-card {{
                flex-direction: column;
            }}
            .project-logo {{
                width: 100%;
                height: 200px;
                border-right: none;
                border-bottom: 1px solid #e9ecef;
            }}
            .btn {{
                width: 100%;
                margin: 5px 0;
            }}
            .button-group {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <div class="sorting-options">
            <div class="button-group">
                <button class="btn" onclick="sortTable('updated')">按更新时间排序</button>
                <button class="btn" onclick="sortTable('downloads')">按下载量排序</button>
            </div>
        </div>

        <div id="projectsContainer">
            {project_cards}
        </div>
        
        <!-- 添加 Credit 信息 -->
        <div class="credits">
            <p>© 2025 <a href="https://space.bilibili.com/438381132" target="_blank">一条鱼丸_</a></p>
            <p>最后更新: {update_time}</p>
        </div>
    </div>
    
    <a href="#" class="back-to-top" id="backToTop" title="返回顶部">↑</a>

    <script>
        // 等待文档加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {{
            // 初始化所有可折叠元素
            initCollapsibles();
            
            // 初始化返回顶部按钮
            initBackToTop();
        }});

        // 初始化所有可折叠元素
        function initCollapsibles() {{
            var coll = document.getElementsByClassName("collapsible");
            for (var i = 0; i < coll.length; i++) {{
                coll[i].addEventListener("click", function() {{
                    this.classList.toggle("active");
                    var content = this.nextElementSibling;
                    if (content.style.maxHeight) {{
                        content.style.maxHeight = null;
                    }} else {{
                        content.style.maxHeight = content.scrollHeight + "px";
                    }}
                }});
            }}
        }}
        
        // 初始化返回顶部按钮
        function initBackToTop() {{
            var backToTopButton = document.getElementById("backToTop");
            
            // 当页面滚动超过300px时显示按钮
            window.addEventListener('scroll', function() {{
                if (window.pageYOffset > 300) {{
                    backToTopButton.classList.add('visible');
                }} else {{
                    backToTopButton.classList.remove('visible');
                }}
            }});
            
            // 点击按钮时平滑滚动到顶部
            backToTopButton.addEventListener('click', function(e) {{
                e.preventDefault();
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }});
        }}

        // 排序功能
        function sortTable(criteria) {{
            const container = document.getElementById('projectsContainer');
            const cards = Array.from(container.getElementsByClassName('project-card'));
            
            cards.sort((a, b) => {{
                if(criteria === 'updated') {{
                    return b.dataset.updated.localeCompare(a.dataset.updated);
                }} else if(criteria === 'downloads') {{
                    return parseInt(b.dataset.downloads) - parseInt(a.dataset.downloads);
                }}
                return 0;
            }});

            container.innerHTML = '';
            cards.forEach(card => container.appendChild(card));
        }}
    </script>
</body>
</html>
    """

    project_cards = []
    # 使用tqdm创建进度条
    for project in tqdm(projects, desc="生成项目卡片", unit="项目"):
        # 获取项目的详细信息
        details = fetch_project_details(config, project['id'])
        
        # 准备画廊HTML
        gallery_html = ""
        if details['screenshots']:
            for img in details['screenshots']:
                gallery_html += f'<img src="{img["url"]}" alt="{img["title"]}" title="{img["title"]}">'
        else:
            gallery_html = "<p>暂无图片</p>"

        # 如果没有logo，使用默认图片
        logo_url = project['logo_url'] if project['logo_url'] else "/api/placeholder/150/150"
        
        # 下载按钮HTML - 确保总是显示下载按钮
        download_button = ""
        if details['download_url']:
            download_button = f'<a href="{details["download_url"]}" class="btn btn-cta download-cta" target="_blank">立即下载</a>'
        else:
            # 提供默认的项目页面作为备选
            download_button = f'<a href="{project["link"]}" class="btn btn-cta download-cta" target="_blank">查看下载</a>'
        
        card = f"""
        <div class="project-card" data-updated="{project['iso_date']}" data-downloads="{project['downloads']}">
            <img class="project-logo" src="{logo_url}" alt="{project['title']} Logo">
            <div class="project-info">
                <h2>{project['title']}</h2>
                <p><strong>更新时间:</strong> <span class="badge badge-info">{project['updated']}</span></p>
                <p><strong>下载量:</strong> <span class="badge badge-success">{project['downloads_display']}</span></p>
                <p><strong>简要描述:</strong> {project['description']}</p>
                <div>
                    <a href="{project['link']}" class="btn btn-cta" target="_blank">访问项目页面</a>
                    {download_button}
                </div>
                
                <button class="collapsible">详细描述</button>
                <div class="content">
                    <div class="description">
                        {details['description']}
                    </div>
                </div>
                
                <button class="collapsible">画廊</button>
                <div class="content">
                    <div class="gallery">
                        {gallery_html}
                    </div>
                </div>
            </div>
        </div>
        """
        project_cards.append(card)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template.format(
            project_cards="".join(project_cards),
            title=config['output']['title'],
            update_time=current_time
        ))

    return output_path


def fetch_all_projects(config):
    """获取所有项目，包括分页处理"""
    all_projects = []
    index = 0
    total_count = None
    page_size = config['search']['pageSize']
    
    print(f"搜索关键词: {config['search']['searchFilter']}")
    print(f"搜索类别: {config['search']['classId']}")
    print(f"每页大小: {page_size}")
    
    progress_bar = None
    
    while total_count is None or index < total_count:
        current_page = index // page_size + 1
        projects, total = fetch_projects_via_api(config, index)
        
        if not projects:
            print("没有更多项目数据")
            break
            
        all_projects.extend(projects)
        
        if total_count is None:
            total_count = total
            print(f"总共有 {total_count} 个项目")
            # 初始化进度条
            progress_bar = tqdm(total=total_count, desc="获取项目", unit="项目")
            progress_bar.update(len(projects))
        else:
            progress_bar.update(len(projects))
        
        index += len(projects)
        if len(projects) < page_size:  # 如果返回的项目数小于请求的页面大小，说明已经到达末尾
            break
    
    if progress_bar is not None:
        progress_bar.close()
    
    return all_projects

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='CurseForge项目爬取工具')
    parser.add_argument('--config', help='指定配置文件路径', default=CONFIG_FILE)
    parser.add_argument('--search', help='搜索关键词', default=None)
    parser.add_argument('--output', help='输出文件名', default=None)
    return parser.parse_args()

def main():
    """主函数"""
    global CONFIG_FILE  # Moved to the top of the function
    
    print("=" * 50)
    print("CurseForge项目爬取工具 - 启动")
    print("=" * 50)
    
    print(f"运行路径: {BASE_DIR}")
    print(f"配置文件: {CONFIG_FILE}")
    
    args = parse_arguments()
    
    # 如果指定了配置文件路径，更新全局变量
    if args.config != CONFIG_FILE:
        CONFIG_FILE = args.config
        print(f"使用指定配置文件: {CONFIG_FILE}")
    
    # 加载配置
    config = load_config()
    
    # 应用命令行参数覆盖配置
    if args.search:
        config['search']['searchFilter'] = args.search
        print(f"使用命令行搜索关键词: {args.search}")
    
    if args.output:
        config['output']['filename'] = args.output
        print(f"使用命令行输出文件名: {args.output}")
    
    # 检查API密钥
    if not config['api']['key'] or config['api']['key'] == "xxx":
        print("请先在配置文件中设置CurseForge API密钥")
        print(f"配置文件路径: {os.path.abspath(CONFIG_FILE)}")
        # 等待用户按键退出
        input("按任意键退出...")
        sys.exit(1)
    
    print(f"正在获取{config['search']['searchFilter']}相关数据...")
    projects = fetch_all_projects(config)
    
    if projects:
        print(f"找到 {len(projects)} 个相关项目，正在生成HTML...")
        output_file = generate_html(config, projects)
        print(f"HTML文件已生成：{os.path.abspath(output_file)}")
    else:
        print("没有找到项目数据")
    
    print("=" * 50)
    print("任务完成!")
    print("=" * 50)
    
    # 等待用户按键退出，这样窗口不会立即关闭
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")