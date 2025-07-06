// 全局变量
let currentFile = null;
const apiBaseUrl = 'http://localhost:3000/api';
let propertyCounter = 0;

// DOM元素获取函数
const getEl = (id) => document.getElementById(id);

// DOM元素引用
const fileListEl = getEl('file-list');
const currentFileEl = getEl('current-file');
const newFileBtn = getEl('new-file');
const refreshBtn = getEl('refresh-list');
const saveBtn = getEl('save-file');
const deleteBtn = getEl('delete-file');
const addItemBtn = getEl('add-item');
const addPropertyButton = getEl('add-property');
const editorForm = getEl('editor-form');
const keyInput = getEl('key');
const translationInput = getEl('translation');
const iconTypeSelect = getEl('icon-type');
const iconValueInput = getEl('icon-value');
const hardnessInput = getEl('hardness');
const densityInput = getEl('density');
const durabilityInput = getEl('durability');
const itemsContainer = getEl('items-container');
const versionSelect = getEl('version');
const miningLevelInput = getEl('mining_level');
const miningSpeedInput = getEl('mining_speed');
const flexibilityInput = getEl('flexibility');
const materialGroupsContainer = document.querySelector('.checkbox-group');
const modulePropertiesContainer = getEl('module-properties');
const colorPaletteTypeSelect = getEl('color-palette-type');
const colorPaletteEditor = getEl('color-palette-editor');
const tierInput = getEl('tier');
const enchantabilityInput = getEl('enchantability');
const texturesSelect = getEl('textures');
const searchInput = getEl('search-input');
const searchBtn = getEl('search-btn');
const propertySelect = getEl('property-select');

// 定义所有可用属性
const allProperties = [
    { key: "name", type: "text", description: "模块名称" },
    { key: "slots", type: "json", description: "管理允许的子模块" },
    { key: "allowedInSlots", type: "json-array", description: "允许此模块存在于的槽位列表" },
    { key: "allowedMaterial", type: "json", description: "允许的材料及其消耗" },
    { key: "texture", type: "json", description: "模型列表" },
    { key: "overlay_texture_model", type: "json", description: "叠加模型列表" },
    { key: "abilities", type: "json-array", description: "右键能力列表" },
    { key: "blocking", type: "number", description: "格挡能力缩放" },
    { key: "edible", type: "json", description: "可食用属性" },
    { key: "air_drag", type: "number", description: "空中阻力" },
    { key: "water_drag", type: "number", description: "水中阻力" },
    { key: "water_gravity", type: "number", description: "水中重力" },
    { key: "is_arrow", type: "boolean", description: "是否视为箭" },
    { key: "crossbowAmmunition", type: "boolean", description: "是否可作为弩箭发射" },
    { key: "is_enderpearl", type: "boolean", description: "是否表现得像末影珍珠" },
    { key: "teleport_target", type: "boolean", description: "是否让被击中的实体传送" },
    { key: "enchantments", type: "json", description: "允许或禁止的附魔" },
    { key: "crafting_enchants", type: "json", description: "合成时附魔" },
    { key: "enchantment_transformers", type: "json-array", description: "调整现有附魔" },
    { key: "attributes", type: "json-array", description: "属性列表" },
    { key: "armor_pen", type: "number", description: "护甲穿透" },
    { key: "crafting_condition", type: "json", description: "合成条件" },
    { key: "channeling", type: "boolean", description: "是否召唤闪电" },
    { key: "cryo", type: "number", description: "冰冻效果强度" },
    { key: "displayName", type: "text", description: "物品显示名称的语言键" },
    { key: "durability", type: "number", description: "总耐久度" },
    { key: "emissive", type: "json", description: "发光属性" },
    { key: "equipmentSlot", type: "text", description: "装备槽位" },
    { key: "fake_item_tag", type: "json-array", description: "伪造物品标签" },
    { key: "fireProof", type: "boolean", description: "是否防火" },
    { key: "food_exhaustion", type: "number", description: "被动食物消耗" },
    { key: "fortune", type: "number", description: "增加物品的精准采集等级" },
    { key: "fracturing", type: "number", description: "耐久度越低伤害越高" },
    { key: "gui_stat", type: "json", description: "GUI中额外显示的数据" },
    { key: "healthPercent", type: "number", description: "根据目标当前生命值增加伤害" },
    { key: "illagerBane", type: "number", description: "增加对掠夺者和其他袭击相关生物的伤害" },
    { key: "immolate", type: "number", description: "燃烧持有者或目标" },
    { key: "isPiglinGold", type: "boolean", description: "猪灵是否会攻击佩戴者" },
    { key: "itemId", type: "text", description: "物品标识符" },
    { key: "itemLore", type: "json-array", description: "物品 Lore" },
    { key: "leeching", type: "number", description: "吸血属性" },
    { key: "luminiousLearning", type: "number", description: "增加方块和掉落物的经验掉落" },
    { key: "mining_level", type: "json", description: "挖掘等级" },
    { key: "module_stats", type: "json", description: "模块统计数据" },
    { key: "tag", type: "json-array", description: "标签列表" },
    { key: "pillagerGuard", type: "number", description: "减少来自掠夺者和其他袭击相关生物的伤害" },
    { key: "priority", type: "number", description: "GUI 中的排序优先级" },
    { key: "rarity", type: "text", description: "自定义稀有度" },
    { key: "repairPriority", type: "number", description: "决定哪些模块可以用于修复" },
    { key: "riptide", type: "json", description: "激流行为" },
    { key: "canWalkOnSnow", type: "boolean", description: "是否可以在细雪上行走" },
    { key: "isWeapon", type: "boolean", description: "是否表现得更像武器" },
    { key: "apoli_powers", type: "json-array", description: "Apoli 能力列表" },
    { key: "on_attack_potion", type: "json-array", description: "攻击时施加药水效果" },
    { key: "on_hurt_potion", type: "json-array", description: "受伤时施加药水效果" }
];

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadFileList();
    setupEventListeners();
    populatePropertySelect();
});

// 设置事件监听器
function setupEventListeners() {
    newFileBtn.addEventListener('click', createNewFile);
    refreshBtn.addEventListener('click', loadFileList);
    saveBtn.addEventListener('click', saveCurrentFile);
    deleteBtn.addEventListener('click', deleteCurrentFile);
    addItemBtn.addEventListener('click', () => addItemEntry());
    addPropertyButton.addEventListener('click', addSelectedProperty);
    colorPaletteTypeSelect.addEventListener('change', updatePaletteEditor);
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
}

// 填充属性选择下拉菜单
function populatePropertySelect() {
    allProperties.forEach(prop => {
        const option = document.createElement('option');
        option.value = prop.key;
        option.textContent = `${prop.key} (${prop.description})`;
        propertySelect.appendChild(option);
    });
}

// 添加选中的属性
function addSelectedProperty() {
    const selectedPropertyKey = propertySelect.value;
    if (!selectedPropertyKey) {
        alert('请选择一个属性');
        return;
    }
    const property = allProperties.find(p => p.key === selectedPropertyKey);
    addPropertyInput(property);
}

// 添加属性输入字段
function addPropertyInput(property) {
    const container = modulePropertiesContainer;
    const propertyId = `prop-${property.key}-${propertyCounter++}`;
    const propertyGroup = document.createElement('div');
    propertyGroup.classList.add('form-group', 'property-input-group');
    propertyGroup.dataset.propertyKey = property.key;
    propertyGroup.dataset.propertyType = property.type;

    let inputElement;
    switch (property.type) {
        case 'text':
            inputElement = document.createElement('input');
            inputElement.type = 'text';
            break;
        case 'number':
            inputElement = document.createElement('input');
            inputElement.type = 'number';
            inputElement.step = 'any';
            break;
        case 'boolean':
            inputElement = document.createElement('input');
            inputElement.type = 'checkbox';
            break;
        case 'json':
        case 'json-array':
            inputElement = document.createElement('textarea');
            inputElement.rows = 3;
            inputElement.placeholder = property.type === 'json' ? '输入 JSON 对象' : '输入 JSON 数组';
            break;
        default:
            inputElement = document.createElement('input');
            inputElement.type = 'text';
    }
    inputElement.id = propertyId;
    inputElement.classList.add('form-control');

    const labelElement = document.createElement('label');
    labelElement.htmlFor = propertyId;
    labelElement.textContent = `${property.key} (${property.description})`;

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.classList.add('remove-button');
    removeButton.textContent = '删除';
    removeButton.addEventListener('click', () => propertyGroup.remove());

    propertyGroup.appendChild(labelElement);
    propertyGroup.appendChild(inputElement);
    propertyGroup.appendChild(removeButton);

    container.appendChild(propertyGroup);
}

// 加载文件列表
async function loadFileList() {
    try {
        const response = await fetch(`${apiBaseUrl}/files`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const files = await response.json();

        fileListEl.innerHTML = '';
        files.forEach(file => {
            const li = document.createElement('li');
            li.textContent = file;
            li.dataset.filename = file;
            li.addEventListener('click', () => loadFileContent(file));
            fileListEl.appendChild(li);
        });
    } catch (error) {
        console.error('加载文件列表失败:', error);
        alert('加载文件列表失败，请检查控制台');
    }
}

// 加载并填充文件内容到表单
async function loadFileContent(filename) {
    try {
        const response = await fetch(`${apiBaseUrl}/files/${filename}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        currentFile = filename;
        currentFileEl.textContent = filename;

        resetForm();

        keyInput.value = data.key ?? '';
        translationInput.value = data.translation ?? '';
        hardnessInput.value = data.hardness ?? '1';
        densityInput.value = data.density ?? '1';
        durabilityInput.value = data.durability ?? '50';
        flexibilityInput.value = data.flexibility ?? '0.5';
        miningLevelInput.value = data.mining_level ?? 'minecraft:incorrect_for_stone_tool';
        miningSpeedInput.value = data.mining_speed ?? '1';
        versionSelect.value = data.version ?? '1.21.1';

        tierInput.value = data.tier ?? '';
        enchantabilityInput.value = data.enchantability ?? '';

        if (data.icon) {
            iconTypeSelect.value = data.icon.type ?? 'item';
            iconValueInput.value = data.icon.item ?? '';
        }

        if (data.items && data.items.length > 0) {
            data.items.forEach(item => addItemEntry(item));
        }

        if (data.groups && data.groups.length > 0) {
            materialGroupsContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.checked = data.groups.includes(cb.value);
            });
        }

        if (data.textures && data.textures.length > 0) {
            Array.from(texturesSelect.options).forEach(opt => {
                opt.selected = data.textures.includes(opt.value);
            });
        }

        if (data.properties) {
            for (const propKey in data.properties) {
                const propValue = data.properties[propKey];
                const property = allProperties.find(p => p.key === propKey);
                if (property) {
                    addPropertyInput(property);
                    const inputElement = modulePropertiesContainer.querySelector(`[data-property-key="${propKey}"] .form-control`);
                    if (property.type === 'json' || property.type === 'json-array') {
                        inputElement.value = JSON.stringify(propValue, null, 2);
                    } else if (property.type === 'boolean') {
                        inputElement.checked = propValue;
                    } else {
                        inputElement.value = propValue;
                    }
                }
            }
        }

        if (data.color_palette) {
            colorPaletteTypeSelect.value = data.color_palette.type ?? '';
            updatePaletteEditor(data.color_palette);
        }

        Array.from(fileListEl.children).forEach(li => {
            li.classList.toggle('active', li.textContent === filename);
        });

    } catch (error) {
        console.error(`加载文件 '${filename}' 失败:`, error);
        alert(`加载文件 '${filename}' 失败，请检查控制台`);
    }
}

// 创建新文件
function createNewFile() {
    currentFile = null;
    currentFileEl.textContent = '新文件 (未保存)';
    resetForm();
    Array.from(fileListEl.children).forEach(li => li.classList.remove('active'));
    keyInput.focus();
}

// 重置表单
function resetForm() {
    editorForm.reset();
    itemsContainer.innerHTML = '';
    modulePropertiesContainer.innerHTML = '';
    colorPaletteEditor.innerHTML = '';
    materialGroupsContainer.querySelectorAll('input').forEach(cb => cb.checked = false);
    Array.from(texturesSelect.options).forEach(opt => opt.selected = false);
}

// 添加物品条目
function addItemEntry(itemData = {}) {
    const div = document.createElement('div');
    div.className = 'item-entry';
    div.innerHTML = `
        <input type="text" placeholder="物品ID (例如: minecraft:iron_ingot)" class="form-control" value="${itemData.item || ''}" required>
        <input type="number" placeholder="数量" class="form-control" value="${itemData.value || 1}" min="1" required>
        <button type="button" class="remove-button">删除</button>
    `;
    div.querySelector('.remove-button').addEventListener('click', () => div.remove());
    itemsContainer.appendChild(div);
}

// 更新调色板编辑器
function updatePaletteEditor(paletteData = {}) {
    const type = colorPaletteTypeSelect.value;
    colorPaletteEditor.innerHTML = '';
    if (type === 'grayscale_map') {
        colorPaletteEditor.innerHTML = `
            <div class="form-group">
                <label>Key</label>
                <input type="text" class="form-control" id="palette-key" value="${paletteData.key || ''}">
            </div>
            <div class="form-group">
                <label>Path</label>
                <input type="text" class="form-control" id="palette-path" value="${paletteData.path || ''}">
            </div>
        `;
    } else if (type === 'image_generated_item') {
        colorPaletteEditor.innerHTML = `
            <div class="form-group">
                <label>物品 Key</label>
                <input type="text" class="form-control" id="palette-item-key" value="${paletteData.item || ''}">
            </div>
        `;
    }
}

// 保存当前文件
async function saveCurrentFile() {
    const requiredFields = [keyInput, translationInput, hardnessInput, densityInput, durabilityInput, flexibilityInput, miningSpeedInput, iconValueInput];
    const checkedGroups = materialGroupsContainer.querySelectorAll('input:checked');
    if (checkedGroups.length === 0) {
        alert('必须至少选择一个材料组别');
        return;
    }
    for (const field of requiredFields) {
        if (!field.value.trim()) {
            alert(`必填字段 '${field.labels[0].textContent}' 不能为空.`);
            field.focus();
            return;
        }
    }

    let filename = currentFile;
    if (!filename) {
        filename = keyInput.value.trim().toLowerCase().replace(/\s+/g, '_') + '.json';
        if (!filename || filename === '.json') {
            alert('请输入一个有效的文件名 (Key).');
            keyInput.focus();
            return;
        }
        filename = prompt('请输入文件名:', filename);
        if (!filename) return;
    }

    const formData = {
        key: keyInput.value,
        translation: translationInput.value,
        hardness: parseFloat(hardnessInput.value),
        density: parseFloat(densityInput.value),
        durability: parseInt(durabilityInput.value),
        flexibility: parseFloat(flexibilityInput.value),
        mining_level: miningLevelInput.value,
        mining_speed: parseFloat(miningSpeedInput.value),
        version: versionSelect.value,
    };

    if (iconValueInput.value) {
        formData.icon = {
            type: iconTypeSelect.value,
            item: iconValueInput.value
        };
    }
    if (tierInput.value) formData.tier = parseInt(tierInput.value);
    if (enchantabilityInput.value) formData.enchantability = parseInt(enchantabilityInput.value);

    const items = Array.from(itemsContainer.children).map(el => ({
        item: el.querySelector('input[type="text"]').value,
        value: parseInt(el.querySelector('input[type="number"]').value)
    })).filter(item => item.item);
    if (items.length > 0) formData.items = items;

    const groups = Array.from(materialGroupsContainer.querySelectorAll('input:checked')).map(cb => cb.value);
    if (groups.length > 0) formData.groups = groups;

    const textures = Array.from(texturesSelect.selectedOptions).map(opt => opt.value);
    if (textures.length > 0) formData.textures = textures;

    const properties = {};
    let hasPropertyErrors = false;
    Array.from(modulePropertiesContainer.children).forEach(propGroup => {
        const propKey = propGroup.dataset.propertyKey;
        const propType = propGroup.dataset.propertyType;
        const inputElement = propGroup.querySelector('.form-control');
        let value;
        switch (propType) {
            case 'text':
                value = inputElement.value;
                break;
            case 'number':
                value = parseFloat(inputElement.value);
                break;
            case 'boolean':
                value = inputElement.checked;
                break;
            case 'json':
            case 'json-array':
                try {
                    value = JSON.parse(inputElement.value.trim());
                } catch (e) {
                    alert(`属性 '${propKey}' 的 JSON 值无效: ${e.message}`);
                    hasPropertyErrors = true;
                    return;
                }
                break;
            default:
                value = inputElement.value;
        }
        if (value !== '' && (value === 0 || value === false || value === true || typeof value === 'object' || String(value).trim() !== '')) {
            properties[propKey] = value;
        }
    });

    if (hasPropertyErrors) return;
    if (Object.keys(properties).length > 0) formData.properties = properties;

    const paletteType = colorPaletteTypeSelect.value;
    if (paletteType) {
        formData.color_palette = { type: paletteType };
        if (paletteType === 'grayscale_map') {
            formData.color_palette.key = getEl('palette-key')?.value || '';
            formData.color_palette.path = getEl('palette-path')?.value || '';
        } else if (paletteType === 'image_generated_item') {
            formData.color_palette.item = getEl('palette-item-key')?.value || '';
        }
    }

    try {
        const method = currentFile ? 'PUT' : 'POST';
        const url = currentFile ? `${apiBaseUrl}/files/${currentFile}` : `${apiBaseUrl}/files/${filename}`;

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData, null, 4)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '保存失败');
        }

        alert('文件保存成功!');
        await loadFileList();
        loadFileContent(filename);

    } catch (error) {
        console.error('保存文件失败:', error);
        alert(`保存文件失败: ${error.message}`);
    }
}

// 删除当前文件
async function deleteCurrentFile() {
    if (!currentFile || !confirm(`您确定要永久删除 '${currentFile}' 吗？此操作无法撤销。`)) return;

    try {
        const response = await fetch(`${apiBaseUrl}/files/${currentFile}`, { method: 'DELETE' });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '删除失败');
        }
        alert('文件删除成功!');
        createNewFile();
        await loadFileList();
    } catch (error) {
        console.error('删除文件失败:', error);
        alert(`删除文件失败: ${error.message}`);
    }
}

// 处理搜索
async function handleSearch() {
    const searchTerm = searchInput.value.trim().toLowerCase();
    const fileListItems = Array.from(fileListEl.children);

    if (!searchTerm) {
        fileListItems.forEach(li => {
            li.style.display = '';
        });
        return;
    }

    searchBtn.disabled = true;
    searchInput.disabled = true;

    const checkPromises = fileListItems.map(li => {
        const filename = li.dataset.filename;
        return (async () => {
            try {
                const response = await fetch(`${apiBaseUrl}/files/${filename}`);
                if (!response.ok) return { li, isMatch: false };
                const data = await response.json();

                let isMatch = false;
                if (filename.toLowerCase().includes(searchTerm)) {
                    isMatch = true;
                } else if (data.key && data.key.toLowerCase().includes(searchTerm)) {
                    isMatch = true;
                } else if (data.items && Array.isArray(data.items)) {
                    if (data.items.some(item => item.item && item.item.toLowerCase().includes(searchTerm))) {
                        isMatch = true;
                    }
                }
                return { li, isMatch };
            } catch (error) {
                console.error(`Error processing search for ${filename}:`, error);
                return { li, isMatch: false };
            }
        })();
    });

    const results = await Promise.all(checkPromises);
    results.forEach(result => {
        result.li.style.display = result.isMatch ? '' : 'none';
    });

    searchBtn.disabled = false;
    searchInput.disabled = false;
}