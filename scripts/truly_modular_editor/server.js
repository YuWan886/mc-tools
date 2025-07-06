const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = 3000;
const MATERIALS_DIR = path.join(__dirname, 'data', 'miapi', 'materials');

// 确保材料目录存在
if (!fs.existsSync(MATERIALS_DIR)) {
    fs.mkdirSync(MATERIALS_DIR, { recursive: true });
}

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// 根路由
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'editor.html'));
});

// API路由
app.get('/api/files', (req, res) => {
    fs.readdir(MATERIALS_DIR, (err, files) => {
        if (err) {
            console.error('读取文件列表失败:', err);
            return res.status(500).json({ error: '无法读取文件列表' });
        }
        res.json(files.filter(file => file.endsWith('.json')));
    });
});

app.get('/api/files/:filename', (req, res) => {
    const filePath = path.join(MATERIALS_DIR, req.params.filename);
    
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            if (err.code === 'ENOENT') {
                return res.status(404).json({ error: '文件不存在' });
            }
            console.error('读取文件失败:', err);
            return res.status(500).json({ error: '无法读取文件' });
        }
        
        try {
            const jsonData = JSON.parse(data);
            res.json(jsonData);
        } catch (parseErr) {
            console.error('解析JSON失败:', parseErr);
            res.status(500).json({ error: '无效的JSON格式' });
        }
    });
});

app.post('/api/files/:filename', (req, res) => {
    const filePath = path.join(MATERIALS_DIR, req.params.filename);
    
    if (fs.existsSync(filePath)) {
        return res.status(400).json({ error: '文件已存在' });
    }
    
    saveFileData(filePath, req.body, res);
});

app.put('/api/files/:filename', (req, res) => {
    const filePath = path.join(MATERIALS_DIR, req.params.filename);
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ error: '文件不存在' });
    }
    
    saveFileData(filePath, req.body, res);
});

app.delete('/api/files/:filename', (req, res) => {
    const filePath = path.join(MATERIALS_DIR, req.params.filename);
    
    fs.unlink(filePath, (err) => {
        if (err) {
            if (err.code === 'ENOENT') {
                return res.status(404).json({ error: '文件不存在' });
            }
            console.error('删除文件失败:', err);
            return res.status(500).json({ error: '无法删除文件' });
        }
        res.json({ success: true });
    });
});

// 辅助函数：保存文件数据
function saveFileData(filePath, data, res) {
    try {
        const jsonString = JSON.stringify(data, null, 2);
        fs.writeFile(filePath, jsonString, 'utf8', (err) => {
            if (err) {
                console.error('保存文件失败:', err);
                return res.status(500).json({ error: '无法保存文件' });
            }
            res.json({ success: true });
        });
    } catch (stringifyErr) {
        console.error('序列化JSON失败:', stringifyErr);
        res.status(400).json({ error: '无效的JSON数据' });
    }
}

// 启动服务器
app.listen(PORT, () => {
    console.log(`服务器运行在 http://localhost:${PORT}`);
    console.log(`材料目录: ${MATERIALS_DIR}`);
});