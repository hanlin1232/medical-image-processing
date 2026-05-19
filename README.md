# 医学图像处理系统

一个基于Vue3和FastAPI的医学图像处理可视化系统，支持NII文件预览、病灶识别和3D立体可视化。

## 功能特性

- 📊 **NII文件预览** - 支持医学影像文件的上传和实时预览
- 🔍 **病灶识别** - 基于机器学习模型的病灶检测
- 🎮 **3D立体可视化** - 多切片病灶分布的3D点云展示
- 📈 **特征提取** - 提取并展示PyRadiomics特征

## 技术栈

- **前端**: Vue 3 + Vite
- **后端**: FastAPI + Python
- **图像处理**: SimpleITK + NumPy + PIL
- **样式**: CSS3 + Tailwind CSS

## 快速开始

### 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖
pip install fastapi uvicorn numpy scipy simpleitk pillow scikit-image scikit-learn
```

### 开发模式

```bash
# 启动前端服务
npm run dev

# 启动后端服务
python backend/main.py
```

### 构建生产版本

```bash
npm run build
```

### 一键启动

双击 `start_app.bat` 文件即可启动服务。

## 项目结构

```
medical-image-processing/
├── src/                    # 前端源码
│   ├── MLWorkspace.vue     # 主工作区组件
│   ├── main.js             # 入口文件
│   └── style.css           # 全局样式
├── backend/               # 后端源码
│   └── main.py            # FastAPI应用
├── dist/                  # 构建产物
├── index.html             # HTML模板
├── vite.config.js         # Vite配置
├── package.json           # 前端依赖
└── start_app.bat          # 一键启动脚本
```

## 部署到GitHub Pages

1. 将代码推送到GitHub仓库
2. 在仓库设置中启用GitHub Pages
3. 选择 `gh-pages` 分支作为源

## API接口

### 预览NII文件
- **POST** `/preview-nii/` - 预览NII文件切片

### 病灶识别
- **POST** `/predict-lesion/` - 预测病灶

### 3D病灶检测
- **POST** `/detect-3d-lesions/` - 检测所有切片病灶

## 许可证

MIT License
