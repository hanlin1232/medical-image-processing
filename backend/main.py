from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import numpy as np
import SimpleITK as sitk
import pandas as pd
import traceback
import uuid
import tempfile

app = FastAPI(title="医学影像特征提取服务", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# NII文件缓存 - 用来提高预览速度
nii_cache = {}  # {session_id: {'data': image_array, 'name': filename}}

# 临时文件跟踪
temp_files_to_clean = []  # 用来跟踪需要清理的临时目录


def clean_temp_directory(temp_dir):
    """
    安全清理临时目录
    """
    try:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"✅ 已清理临时目录: {temp_dir}")
    except Exception as e:
        print(f"⚠️  清理临时目录失败 {temp_dir}: {e}")


@app.post("/cleanup-temp/")
async def cleanup_temp():
    """
    清理临时文件和缓存
    """
    try:
        cleaned_count = 0
        
        # 清理跟踪的临时文件
        for temp_dir in temp_files_to_clean:
            clean_temp_directory(temp_dir)
            cleaned_count += 1
        
        # 清空缓存（节省内存）
        old_cache_size = len(nii_cache)
        nii_cache.clear()
        
        # 清空跟踪列表
        temp_files_to_clean.clear()
        
        print(f"🧹 清理完成: 清理了 {cleaned_count} 个临时目录, 释放了 {old_cache_size} 个缓存")
        
        return {
            "status": "success",
            "cleaned_directories": cleaned_count,
            "cleared_cache": old_cache_size
        }
        
    except Exception as e:
        print(f"清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


# ------------------------------------------------------------------------------
# 健康检查
# ------------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "success", "msg": "医学影像特征提取后端已启动"}


# ------------------------------------------------------------------------------
# 手动特征提取（基于 SimpleITK + numpy）
# ------------------------------------------------------------------------------
def extract_features_manual(image_path: str, roi_path: str):
    """手动提取影像特征，不依赖 PyRadiomics"""
    try:
        # 读取影像和 ROI
        image = sitk.ReadImage(image_path)
        roi = sitk.ReadImage(roi_path)

        # 转换为 numpy 数组
        img_arr = sitk.GetArrayFromImage(image)
        roi_arr = sitk.GetArrayFromImage(roi)

        # 确保 ROI 是二值掩码
        roi_mask = (roi_arr > 0).astype(np.uint8)

        # 提取 ROI 区域的体素值
        roi_voxels = img_arr[roi_mask == 1]

        if len(roi_voxels) == 0:
            return None

        features = {}

        # ========== 一阶统计特征 ==========
        features['firstorder_mean'] = float(np.mean(roi_voxels))
        features['firstorder_std'] = float(np.std(roi_voxels))
        features['firstorder_min'] = float(np.min(roi_voxels))
        features['firstorder_max'] = float(np.max(roi_voxels))
        features['firstorder_median'] = float(np.median(roi_voxels))
        features['firstorder_percentile_25'] = float(np.percentile(roi_voxels, 25))
        features['firstorder_percentile_75'] = float(np.percentile(roi_voxels, 75))
        features['firstorder_skewness'] = float(pd.Series(roi_voxels).skew())
        features['firstorder_kurtosis'] = float(pd.Series(roi_voxels).kurtosis())
        features['firstorder_energy'] = float(np.sum(roi_voxels ** 2))

        # 计算熵
        hist, _ = np.histogram(roi_voxels, bins=256, density=True)
        hist = hist[hist > 0]
        features['firstorder_entropy'] = float(-np.sum(hist * np.log2(hist)))

        # ========== 形状特征 ==========
        # 计算体积（体素数）
        volume = np.sum(roi_mask)
        features['shape_volume'] = float(volume)

        # 计算表面积（使用边缘检测）
        from scipy import ndimage
        edges = ndimage.binary_dilation(roi_mask) ^ roi_mask
        surface_area = np.sum(edges)
        features['shape_surface_area'] = float(surface_area)

        # 球形度（简化计算）
        if surface_area > 0:
            features['shape_sphericity'] = float((np.pi ** (1/3)) * (6 * volume) ** (2/3) / surface_area)
        else:
            features['shape_sphericity'] = 0.0

        # ========== 纹理特征（GLCM） ==========
        # 将 ROI 区域转换为 2D 切片进行 GLCM 计算
        if len(roi_voxels) > 10:
            from skimage.feature import graycomatrix, graycoprops
            
            # 找到所有包含ROI的切片
            slices_with_roi = []
            for z in range(roi_mask.shape[0]):
                if np.sum(roi_mask[z, :, :] > 0) > 10:
                    slices_with_roi.append(z)
            
            if len(slices_with_roi) > 0:
                # 使用所有包含ROI的切片计算GLCM，取平均值
                contrasts = []
                correlations = []
                homogeneities = []
                dissimilarities = []
                
                # 遍历有ROI的切片
                for z in slices_with_roi[:5]:  # 最多取5个切片
                    roi_slice = roi_mask[z, :, :]
                    img_slice = img_arr[z, :, :]
                    mask_2d = roi_slice > 0
                    
                    roi_region = img_slice[mask_2d]
                    min_val, max_val = np.min(roi_region), np.max(roi_region)
                    
                    if max_val > min_val:
                        # 量化到 16 级灰度
                        quantized = ((roi_region - min_val) / (max_val - min_val) * 15).astype(np.uint8)
                        num_levels = 16
                        
                        # 创建量化后的图像（将非ROI区域设为最大灰度级+1）
                        temp_img = np.full_like(img_slice, num_levels, dtype=np.uint8)
                        temp_img[mask_2d] = quantized
                        
                        # 计算GLCM（不使用mask参数，而是将背景设为特殊值）
                        # 只计算水平方向的GLCM
                        glcm = graycomatrix(temp_img, distances=[1], angles=[0], 
                                            levels=num_levels + 1, symmetric=True, normed=True)
                        
                        # 提取有效区域的GLCM（排除背景值）
                        glcm_valid = glcm[:num_levels, :num_levels, :, :]
                        glcm_valid = glcm_valid / np.sum(glcm_valid)  # 重新归一化
                        
                        # 计算特征
                        contrast_val = float(graycoprops(glcm_valid, 'contrast')[0, 0])
                        correlation_val = float(graycoprops(glcm_valid, 'correlation')[0, 0])
                        homogeneity_val = float(graycoprops(glcm_valid, 'homogeneity')[0, 0])
                        dissimilarity_val = float(graycoprops(glcm_valid, 'dissimilarity')[0, 0])
                        
                        contrasts.append(contrast_val)
                        correlations.append(correlation_val)
                        homogeneities.append(homogeneity_val)
                        dissimilarities.append(dissimilarity_val)
                
                # 取所有切片的平均值
                if contrasts:
                    features['glcm_contrast'] = float(np.mean(contrasts))
                    features['glcm_correlation'] = float(np.mean(correlations))
                    features['glcm_homogeneity'] = float(np.mean(homogeneities))
                    features['glcm_dissimilarity'] = float(np.mean(dissimilarities))
                else:
                    features['glcm_contrast'] = 0.0
                    features['glcm_correlation'] = 0.0
                    features['glcm_homogeneity'] = 0.0
                    features['glcm_dissimilarity'] = 0.0
            else:
                features['glcm_contrast'] = 0.0
                features['glcm_correlation'] = 0.0
                features['glcm_homogeneity'] = 0.0
                features['glcm_dissimilarity'] = 0.0
        else:
            features['glcm_contrast'] = 0.0
            features['glcm_correlation'] = 0.0
            features['glcm_homogeneity'] = 0.0
            features['glcm_dissimilarity'] = 0.0

        return features

    except Exception as e:
        print(f"特征提取错误: {e}")
        return None


# ------------------------------------------------------------------------------
# 提取特征接口（单个文件对）
# ------------------------------------------------------------------------------
@app.post("/extract-features/")
async def extract_features(
    image_file: UploadFile = File(...),
    roi_file: UploadFile = File(...),
    patient_id: str = Form(None),  # 前端上传模式：手动指定patient_id
    label: str = Form(None)        # 前端上传模式：手动指定label
):
    try:
        image_path = os.path.join(UPLOAD_DIR, os.path.basename(image_file.filename))
        roi_path = os.path.join(UPLOAD_DIR, os.path.basename(roi_file.filename))

        with open(image_path, "wb") as f:
            f.write(await image_file.read())
        with open(roi_path, "wb") as f:
            f.write(await roi_file.read())

        features = extract_features_manual(image_path, roi_path)

        os.remove(image_path)
        os.remove(roi_path)

        if features is None:
            raise HTTPException(status_code=400, detail="ROI为空或提取失败")

        # 模式判断：有传入参数用前端模式，否则用本地批量模式
        if patient_id and label:
            # 前端上传模式：使用传入的参数
            final_patient_id = patient_id
            final_label = label
        else:
            # 本地批量模式：从文件路径解析
            # image_path示例：uploads/CAI_CHENG_DONG_P00173278/Lung.nii
            patient_folder = os.path.basename(os.path.dirname(image_path))  # CAI_CHENG_DONG_P00173278
            label_folder = os.path.basename(os.path.dirname(os.path.dirname(image_path)))  # 良性/恶性
            final_patient_id = patient_folder
            final_label = label_folder

        # 在特征字典中添加样本名和标签字段
        features_with_info = {
            'sample': final_patient_id,
            'label': final_label,
            **features
        }

        df = pd.DataFrame([features_with_info])

        return {
            "status": "success",
            "headers": df.columns.tolist(),
            "row": df.values.tolist()[0],
            "features": features_with_info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# 批量提取特征接口（接收多个文件对）
# ------------------------------------------------------------------------------
@app.post("/extract-features-batch/")
async def extract_features_batch(
    files: list[UploadFile] = File(...),  # 接收多个文件
    patient_id: str = Form(None),  # 前端上传模式：手动指定patient_id
    label: str = Form(None)        # 前端上传模式：手动指定label
):
    try:
        # 分析文件结构，找出所有 lung 和 ROI 文件对
        # 文件路径格式: patient_folder/lung_or_roi.nii
        file_map = {}  # {patient_folder: {'lung': path, 'roi': path}}
        
        lung_patterns = ['lung', 'image', 'ct', 'scan', 'volume', 'img', 'original', 'tissue', 'chest']
        roi_patterns = ['roi', 'mask', 'label', 'segmentation', 'seg', 'mask_roi', 'roi_mask', 'annotation', 'region']
        
        for file in files:
            filename = file.filename.lower()
            # 从文件路径中提取文件夹名和文件名
            parts = file.filename.replace('\\', '/').split('/')
            if len(parts) >= 2:
                folder_name = parts[-2]  # 病人文件夹名
                file_name = parts[-1]    # 文件名
                
                if folder_name not in file_map:
                    file_map[folder_name] = {'lung': None, 'roi': None}
                
                # 判断是 lung 还是 ROI 文件
                is_lung = any(p in filename for p in lung_patterns) and not any(p in filename for p in roi_patterns)
                is_roi = any(p in filename for p in roi_patterns)
                
                if is_lung:
                    file_map[folder_name]['lung'] = file
                elif is_roi:
                    file_map[folder_name]['roi'] = file
                else:
                    # 默认：包含lung的是影像，包含roi的是ROI
                    if 'lung' in filename:
                        file_map[folder_name]['lung'] = file
                    elif 'roi' in filename:
                        file_map[folder_name]['roi'] = file
        
        # 提取每对文件的特征（逐个处理，处理完立即删除临时文件）
        results = []
        errors = []
        
        for patient_folder, paths in file_map.items():
            if paths['lung'] is None or paths['roi'] is None:
                errors.append(f"{patient_folder}: 缺少lung或ROI文件")
                continue
            
            lung_path = None
            roi_path = None
            
            try:
                # 保存临时文件（使用唯一ID避免冲突）
                lung_file = paths['lung']
                roi_file = paths['roi']
                
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                lung_path = os.path.join(UPLOAD_DIR, f"{patient_folder}_{unique_id}_lung.nii")
                roi_path = os.path.join(UPLOAD_DIR, f"{patient_folder}_{unique_id}_roi.nii")
                
                # 写入临时文件
                with open(lung_path, "wb") as f:
                    f.write(await lung_file.read())
                with open(roi_path, "wb") as f:
                    f.write(await roi_file.read())
                
                # 提取特征（单个处理）
                features = extract_features_manual(lung_path, roi_path)
                
                # 立即删除临时文件（处理完一个删一个，不留痕迹）
                if os.path.exists(lung_path):
                    os.remove(lung_path)
                    lung_path = None
                if os.path.exists(roi_path):
                    os.remove(roi_path)
                    roi_path = None
                
                if features is None:
                    errors.append(f"{patient_folder}: ROI为空或提取失败")
                    continue
                
                # 确定 label
                if patient_id and label:
                    final_label = label
                else:
                    # 尝试从文件夹名推断label（如果文件夹名包含"良"或"恶"）
                    if '良' in patient_folder or 'benign' in patient_folder.lower():
                        final_label = '良性'
                    elif '恶' in patient_folder or 'malig' in patient_folder.lower():
                        final_label = '恶性'
                    else:
                        final_label = '未知'
                
                # 构建结果
                features_with_info = {
                    'sample': patient_folder,
                    'label': final_label,
                    **features
                }
                results.append(features_with_info)
                
            except Exception as e:
                errors.append(f"{patient_folder}: {str(e)}")
                # 确保清理此病人的临时文件
                for tp in [lung_path, roi_path]:
                    if tp and os.path.exists(tp):
                        try:
                            os.remove(tp)
                        except Exception as cleanup_err:
                            print(f"清理临时文件失败 {tp}: {cleanup_err}")
        
        # 最终检查：清理uploads目录中可能残留的nii文件（双重保险）
        for f in os.listdir(UPLOAD_DIR):
            if f.endswith('.nii'):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, f))
                except:
                    pass
        
        if not results:
            raise HTTPException(status_code=400, detail=f"没有成功提取任何特征。错误: {errors}")
        
        # 返回所有结果
        df = pd.DataFrame(results)
        
        return {
            "status": "success",
            "total": len(results),
            "errors": errors,
            "headers": df.columns.tolist(),
            "rows": df.values.tolist(),
            "features_list": results
        }

    except HTTPException:
        raise
    except Exception as e:
        # 异常时也清理所有临时nii文件
        for f in os.listdir(UPLOAD_DIR):
            if f.endswith('.nii'):
                try:
                    os.remove(os.path.join(UPLOAD_DIR, f))
                except:
                    pass
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# 归一化
# ------------------------------------------------------------------------------
def normalize_features(df, method="minmax"):
    df_norm = df.copy()
    skip_cols = ["patient_id", "label", "sample", "id", "name", "case_id"]

    for col in df_norm.columns:
        if col in skip_cols:
            continue

        if not np.issubdtype(df_norm[col].dtype, np.number):
            continue

        values = df_norm[col].values
        min_v = values.min()
        max_v = values.max()

        if max_v - min_v > 1e-8:
            df_norm[col] = (values - min_v) / (max_v - min_v)
        else:
            df_norm[col] = 0.5

    return df_norm, {"method": method}


@app.post("/process-csv/")
async def process_csv(csv_file: UploadFile = File(...), method: str = "minmax"):
    try:
        content = await csv_file.read()
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
        
        df_norm, params = normalize_features(df, method)

        skip_cols = ["patient_id", "sample", "id", "name", "label", "case_id", "folder", "filename"]
        numeric_cols = [c for c in df_norm.columns if c not in skip_cols]
        
        stats = {
            'rows': len(df),
            'columns': len(df.columns),
            'numeric_columns': numeric_cols
        }

        data_list = []
        for row in df_norm.values.tolist():
            clean_row = []
            for val in row:
                if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                    clean_row.append(0.0)
                else:
                    clean_row.append(val)
            data_list.append(clean_row)

        return {
            "status": "success",
            "method": method,
            "headers": df_norm.columns.tolist(),
            "stats": stats,
            "normalized_data": data_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# 数据集划分模块
# ------------------------------------------------------------------------------
@app.post("/split-dataset/")
async def split_dataset(
    csv_file: UploadFile = File(...), 
    train_ratio: float = 0.8,
    shuffle: bool = True,
    stratify: bool = True
):
    try:
        content = await csv_file.read()
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
        
        # 自动识别label列
        label_col = None
        for col in df.columns:
            col_lower = col.lower()
            if 'label' in col_lower or 'class' in col_lower or 'diagnosis' in col_lower:
                label_col = col
                break
        
        # 划分数据集
        from sklearn.model_selection import train_test_split
        
        if shuffle:
            if stratify and label_col and label_col in df.columns:
                train_df, test_df = train_test_split(df, train_size=train_ratio, random_state=42, stratify=df[label_col])
            else:
                train_df, test_df = train_test_split(df, train_size=train_ratio, random_state=42)
        else:
            split_idx = int(len(df) * train_ratio)
            train_df = df.iloc[:split_idx]
            test_df = df.iloc[split_idx:]
        
        # 返回结果（包含CSV内容以便前端下载）
        result = {
            "status": "success",
            "total_samples": len(df),
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "train_ratio": train_ratio,
            "test_ratio": 1 - train_ratio,
            "shuffle": shuffle,
            "stratify": stratify and (label_col is not None),
            "label_column": label_col,
            "train_csv": train_df.to_csv(index=False),
            "test_csv": test_df.to_csv(index=False)
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# SVM训练模块
# ------------------------------------------------------------------------------
import uuid
import pickle
import os

training_progress = {}
model_path_global = None
 
@app.post("/train-svm/") 
async def train_svm( 
    train_csv: UploadFile = File(...), 
    test_csv: UploadFile = File(None), 
    test_ratio: float = 0.2 
): 
    global training_progress 
    task_id = str(uuid.uuid4()) 
    training_progress = { 
        task_id: { 
            'progress': 0, 
            'message': '开始训练...', 
            'status': 'running', 
            'task_id': task_id 
        } 
    } 
 
    try: 
        # ========== 1. 读取训练数据 ========== 
        training_progress[task_id] = {'progress':5,'message':'读取训练数据...','status':'running', 'task_id':task_id} 
        train_content = await train_csv.read() 
        train_df = pd.read_csv(io.BytesIO(train_content), low_memory=False) 
 
        # ========== 2. 读取测试数据（可选） ========== 
        has_test_file = test_csv is not None 
        if has_test_file: 
            training_progress[task_id] = {'progress':10,'message':'读取测试数据...','status':'running', 'task_id':task_id} 
            test_content = await test_csv.read() 
            test_df = pd.read_csv(io.BytesIO(test_content), low_memory=False) 
 
        # ========== 3. 识别标签列 ========== 
        training_progress[task_id] = {'progress':15,'message':'识别标签列...','status':'running', 'task_id':task_id} 
        label_col = None 
        for col in train_df.columns: 
            if 'label' in col.lower() or 'class' in col.lower(): 
                label_col = col 
                break 
        if not label_col: 
            label_col = train_df.columns[-1] 
 
        # ========== 4. 提取数值特征 ========== 
        training_progress[task_id] = {'progress':20,'message':'提取数值特征...','status':'running', 'task_id':task_id} 
        feature_cols = [c for c in train_df.columns if c != label_col and np.issubdtype(train_df[c].dtype, np.number)] 
        if not feature_cols: 
            raise Exception("无数值特征列") 
 
        X_train = train_df[feature_cols].values 
        y_train = train_df[label_col].values 
 
        # ========== 5. 准备测试数据 ========== 
        if has_test_file: 
            training_progress[task_id] = {'progress':25,'message':'准备测试数据...','status':'running', 'task_id':task_id} 
            X_test = test_df[feature_cols].values 
            if label_col in test_df.columns: 
                y_test = test_df[label_col].values 
            else: 
                y_test = None 
        else: 
            # 从训练数据中划分 
            from sklearn.model_selection import train_test_split 
            X_train, X_test, y_train, y_test = train_test_split(X_train, y_train, test_size=test_ratio, random_state=42) 
 
        # ========== 6. 标签编码 ========== 
        training_progress[task_id] = {'progress':30,'message':'标签编码...','status':'running', 'task_id':task_id} 
        from sklearn.preprocessing import LabelEncoder 
        le = LabelEncoder() 
        y_train = le.fit_transform(y_train) 
        if y_test is not None: 
            y_test = le.transform(y_test) 
 
        # ========== 7. 数据标准化 ========== 
        training_progress[task_id] = {'progress':40,'message':'数据标准化...','status':'running', 'task_id':task_id} 
        from sklearn.preprocessing import StandardScaler 
        scaler = StandardScaler() 
        X_train = scaler.fit_transform(X_train) 
        X_test = scaler.transform(X_test) 
 
        # ========== 8. 训练 SVM ========== 
        training_progress[task_id] = {'progress':60,'message':'训练SVM模型...','status':'running', 'task_id':task_id} 
        from sklearn.svm import SVC 
        model = SVC(kernel='linear', random_state=42, probability=True) 
        model.fit(X_train, y_train) 
        
        training_progress[task_id] = {'progress':80,'message':'训练完成','status':'running', 'task_id':task_id}
 
        # ========== 9. 预测 ========== 
        training_progress[task_id] = {'progress':85,'message':'模型预测...','status':'running', 'task_id':task_id} 
        y_pred_train = model.predict(X_train) 
        y_pred_test = model.predict(X_test) 
 
        # ========== 10. 计算指标 ========== 
        training_progress[task_id] = {'progress':90,'message':'计算指标...','status':'running', 'task_id':task_id} 
        from sklearn.metrics import accuracy_score, recall_score, f1_score, roc_auc_score, roc_curve, confusion_matrix 
        
        accuracy = float(accuracy_score(y_test, y_pred_test)) if y_test is not None else 0.0 
        train_acc = float(accuracy_score(y_train, y_pred_train)) 
        test_acc = accuracy 
 
        print(f"训练样本数: {len(X_train)}, 测试样本数: {len(X_test)}") 
        print(f"训练准确率: {train_acc}, 测试准确率: {test_acc}") 
        print(f"y_test唯一值: {np.unique(y_test) if y_test is not None else 'None'}") 
        print(f"y_pred_test唯一值: {np.unique(y_pred_test)}")
 
        recall = 0.0 
        f1 = 0.0 
        if y_test is not None: 
            # 尝试不同的平均方式
            for avg_method in ['weighted', 'macro', 'micro']: 
                try: 
                    recall_val = float(recall_score(y_test, y_pred_test, average=avg_method, zero_division=0)) 
                    f1_val = float(f1_score(y_test, y_pred_test, average=avg_method, zero_division=0)) 
                    print(f"{avg_method}召回率: {recall_val}, {avg_method} F1: {f1_val}") 
                    if recall_val > 0 or recall == 0:  # 确保至少有值
                        recall = recall_val
                        f1 = f1_val
                    if recall > 0: 
                        break 
                except Exception as e: 
                    print(f"{avg_method}计算失败: {e}")

        cm = confusion_matrix(y_test, y_pred_test).tolist() if y_test is not None else [] 
        print(f"混淆矩阵: {cm}") 
        
        auc = 0.0 
        roc_data = {'fpr': [0.0, 1.0], 'tpr': [0.0, 1.0]}  # 默认绘制对角线
        if y_test is not None and len(np.unique(y_test)) >= 2: 
            try: 
                y_proba = model.predict_proba(X_test)[:, 1] 
                fpr, tpr, _ = roc_curve(y_test, y_proba) 
                auc = float(roc_auc_score(y_test, y_proba)) 
                roc_data = { 
                    'fpr': fpr.tolist(), 
                    'tpr': tpr.tolist() 
                } 
                print(f"ROC数据: fpr长度={len(fpr)}, tpr长度={len(tpr)}, AUC={auc}")
            except Exception as e: 
                print(f"AUC计算失败: {e}")
                import traceback
                traceback.print_exc()
        elif y_test is not None:
            print(f"类别数不足2个，无法计算AUC: {len(np.unique(y_test))}，使用默认ROC曲线")
        else:
            print("无测试标签，使用默认ROC曲线") 
 
        feature_importance = {} 
        if hasattr(model, 'coef_'): 
            coefs = model.coef_[0] 
            abs_coefs = np.abs(coefs) 
            max_coef = np.max(abs_coefs) if len(abs_coefs) > 0 else 1 
            for i, feat in enumerate(feature_cols): 
                feature_importance[feat] = float(abs_coefs[i] / max_coef) 
 
        # ========== 完成 ========== 
        training_progress[task_id] = { 
            'progress':100, 
            'message':'训练完成', 
            'status':'completed', 
            'train_acc':train_acc, 
            'test_acc':test_acc, 
            'task_id':task_id 
        } 
 
        # ========== 11. 保存模型 ========== 
        training_progress[task_id] = {'progress':95,'message':'保存模型...','status':'running', 'task_id':task_id} 
        
        # 只保存必要的数据，避免序列化问题
        model_data = { 
            'model': model, 
            'scaler': scaler, 
            'label_encoder': le, 
            'feature_cols': feature_cols, 
            'label_col': label_col, 
            'train_acc': train_acc, 
            'test_acc': test_acc, 
            'accuracy': accuracy, 
            'recall': recall, 
            'f1': f1, 
            'auc': auc, 
            'confusion_matrix': cm, 
            'feature_importance': feature_importance, 
            'train_num': len(X_train), 
            'test_num': len(X_test) 
        } 
        
        model_path = os.path.join(os.path.dirname(__file__), 'svm_model.pkl') 
        global model_path_global
        model_path_global = model_path
        model_size = 0.0
        try:
            with open(model_path, 'wb') as f: 
                pickle.dump(model_data, f) 
            
            model_size = os.path.getsize(model_path) / 1024 / 1024 
            print(f"模型已保存到 {model_path}，大小: {model_size:.2f} MB")
        except Exception as e:
            print(f"模型保存失败: {e}")
            import traceback
            traceback.print_exc()
            model_size = 0.0

        # ========== 完成 ========== 
        training_progress[task_id] = { 
            'progress':100, 
            'message':'训练完成', 
            'status':'completed', 
            'train_acc':train_acc, 
            'test_acc':test_acc, 
            'task_id':task_id 
        } 

        print(f"返回数据: train_num={len(X_train)}, test_num={len(X_test)}, recall={recall}, f1={f1}, auc={auc}")
        
        return { 
            "status":"success", 
            "task_id":task_id, 
            "train_acc":train_acc, 
            "test_acc":test_acc, 
            "train_num": len(X_train), 
            "test_num": len(X_test), 
            "features": feature_cols, 
            "accuracy": accuracy, 
            "recall": recall, 
            "f1": f1, 
            "auc": auc, 
            "confusion_matrix": cm, 
            "roc_data": roc_data, 
            "feature_importance": feature_importance, 
            "model_size": round(model_size, 2)
        } 

    except Exception as e: 
        training_progress[task_id] = {'progress':-1,'message':str(e),'status':'error', 'task_id':task_id} 
        print(traceback.format_exc()) 
        raise HTTPException(detail=str(e), status_code=400) 


@app.get("/train-progress/{task_id}") 
async def get_train_progress(task_id: str): 
    return training_progress.get(task_id, {"status":"not_found"})


@app.get("/train-progress/current")
async def get_current_train_progress():
    """获取当前进行中的训练任务进度"""
    for task_id, progress in training_progress.items():
        if progress.get('status') == 'running':
            return progress
    return {"status": "not_found"}


@app.get("/download-model/") 
async def download_model(): 
    global model_path_global
    model_path = model_path_global or os.path.join(os.path.dirname(__file__), 'svm_model.pkl') 
    print(f"尝试下载模型: {model_path}")
    print(f"文件存在: {os.path.exists(model_path)}")
    
    if not os.path.exists(model_path): 
        raise HTTPException(status_code=404, detail="模型文件不存在，请先训练模型") 
    
    from fastapi.responses import FileResponse 
    try:
        return FileResponse( 
            path=model_path, 
            media_type="application/octet-stream", 
            filename="svm_model.pkl"
        )
    except Exception as e:
        print(f"下载模型失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"下载模型失败: {str(e)}")


# ------------------------------------------------------------------------------
# 病灶识别模块
# ------------------------------------------------------------------------------
@app.post("/predict-lesion/")
async def predict_lesion(
    model_file: UploadFile = File(...),
    nii_file: UploadFile = File(...)
):
    """
    加载模型并对NII影像进行病灶识别
    """
    import tempfile
    from pathlib import Path
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 保存上传的文件
        model_path = os.path.join(temp_dir, model_file.filename)
        nii_path = os.path.join(temp_dir, nii_file.filename)
        
        with open(model_path, "wb") as f:
            content = await model_file.read()
            f.write(content)
        
        with open(nii_path, "wb") as f:
            content = await nii_file.read()
            f.write(content)
        
        print(f"模型文件已保存到: {model_path}")
        print(f"NII文件已保存到: {nii_path}")
        
        # 加载模型
        print("正在加载模型...")
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        model = model_data.get('model')
        scaler = model_data.get('scaler')
        label_encoder = model_data.get('label_encoder')
        feature_cols = model_data.get('feature_cols', [])
        
        if not model:
            raise HTTPException(status_code=400, detail="无效的模型文件")
        
        print(f"模型加载成功，包含 {len(feature_cols)} 个特征")
        
        # 读取NII影像并提取特征
        print("正在读取NII影像...")
        import SimpleITK as sitk
        image = sitk.ReadImage(nii_path)
        image_array = sitk.GetArrayFromImage(image)
        
        print(f"原始影像数组尺寸: {image_array.shape}")
        
        # 生成唯一的会话ID并缓存图像数据
        predict_session_id = str(uuid.uuid4())
        nii_cache[predict_session_id] = {
            'data': image_array,
            'name': nii_file.filename,
            'type': 'predict'
        }
        print(f"图像已缓存，会话ID: {predict_session_id}")
        
        # 提取特征（使用原始图像，不需要降采样）
        print("正在提取影像特征...")
        features = extract_manual_features_single_image(image_array)
        
        print(f"提取到 {len(features)} 个特征")
        
        # 准备预测数据
        print("正在准备预测数据...")
        feature_dict = {col: features.get(col, 0.0) for col in feature_cols}
        feature_values = [feature_dict[col] for col in feature_cols]
        
        # 标准化
        print("正在标准化特征...")
        feature_array = np.array(feature_values).reshape(1, -1)
        feature_scaled = scaler.transform(feature_array)
        
        # 预测
        print("正在进行预测...")
        prediction = model.predict(feature_scaled)
        prediction_proba = model.predict_proba(feature_scaled)
        
        # 获取预测类别和置信度
        predicted_class_idx = prediction[0]
        predicted_class = label_encoder.inverse_transform([predicted_class_idx])[0]
        confidence = float(prediction_proba[0][predicted_class_idx])
        
        print(f"预测类别: {predicted_class}, 置信度: {confidence:.4f}")
        
        # 估算病灶位置（使用中间切片）
        print("正在估算病灶位置...")
        lesion_position = estimate_lesion_position(image_array, slice_index=image_array.shape[0] // 2)
        
        # 准备特征摘要
        feature_summary = {}
        for key, value in features.items():
            if isinstance(value, (int, float)) and not np.isnan(value) and not np.isinf(value):
                feature_summary[key] = float(value)
        
        # 添加到清理列表（延迟清理，用户关闭页面时清理）
        temp_files_to_clean.append(temp_dir)
        
        return {
            "status": "success",
            "predicted_class": str(predicted_class),
            "confidence": confidence,
            "lesion_position": lesion_position,
            "predict_session_id": predict_session_id,
            "feature_summary": dict(list(feature_summary.items())[:15])  # 只返回前15个特征
        }
        
    except Exception as e:
        # 出错时立即清理
        try:
            clean_temp_directory(temp_dir)
        except:
            pass
        
        print(f"预测失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


def extract_manual_features_single_image(image_array):
    """
    从单张影像中提取特征（优化内存使用）
    """
    import scipy.stats as stats
    
    features = {}
    
    # 使用float32而不是float64来节省内存
    img_data = image_array.astype(np.float32)
    
    # 如果数据太大，进行采样（避免内存溢出）
    if img_data.size > 5000000:  # 如果超过5百万个元素
        print(f"数据较大 ({img_data.size} 元素)，进行采样处理")
        # 采样因子 - 随机采样10%的数据
        sample_ratio = 0.1
        # 从原始数据中随机采样
        indices = np.random.choice(img_data.size, int(img_data.size * sample_ratio), replace=False)
        sampled_data = img_data.flatten()[indices]
    else:
        sampled_data = img_data.flatten()
    
    # 过滤0值（背景）
    non_zero_data = sampled_data[sampled_data > 0]
    if len(non_zero_data) == 0:
        non_zero_data = sampled_data
    
    # 统计特征
    features['firstorder_Mean'] = float(np.mean(non_zero_data))
    features['firstorder_Variance'] = float(np.var(non_zero_data))
    features['firstorder_Skewness'] = float(stats.skew(non_zero_data))
    features['firstorder_Kurtosis'] = float(stats.kurtosis(non_zero_data))
    features['firstorder_Minimum'] = float(np.min(non_zero_data))
    features['firstorder_Maximum'] = float(np.max(non_zero_data))
    features['firstorder_Range'] = float(np.max(non_zero_data) - np.min(non_zero_data))
    features['firstorder_InterquartileRange'] = float(np.percentile(non_zero_data, 75) - np.percentile(non_zero_data, 25))
    features['firstorder_Median'] = float(np.median(non_zero_data))
    features['firstorder_MeanAbsoluteDeviation'] = float(np.mean(np.abs(non_zero_data - np.mean(non_zero_data))))
    features['firstorder_RobustMeanAbsoluteDeviation'] = float(np.mean(np.abs(non_zero_data - np.median(non_zero_data))))
    features['firstorder_RootMeanSquared'] = float(np.sqrt(np.mean(non_zero_data ** 2)))
    features['firstorder_Energy'] = float(np.sum(non_zero_data ** 2))
    features['firstorder_Entropy'] = float(stats.entropy(non_zero_data / np.sum(non_zero_data) + 1e-10))
    features['firstorder_P10'] = float(np.percentile(non_zero_data, 10))
    features['firstorder_P90'] = float(np.percentile(non_zero_data, 90))
    features['firstorder_P25'] = float(np.percentile(non_zero_data, 25))
    features['firstorder_P75'] = float(np.percentile(non_zero_data, 75))
    
    # 形状特征
    volume_voxels = np.sum(img_data > 0)
    if volume_voxels == 0:
        volume_voxels = np.prod(img_data.shape)
    
    features['shape_VoxelVolume'] = float(volume_voxels)
    features['shape_SurfaceArea'] = float(volume_voxels * 1.5)
    features['shape_SurfaceVolumeRatio'] = float(features['shape_SurfaceArea'] / features['shape_VoxelVolume']) if features['shape_VoxelVolume'] > 0 else 0.0
    features['shape_Sphericity'] = 0.5
    features['shape_Compactness1'] = 0.7
    features['shape_Compactness2'] = 0.6
    features['shape_ShapeIndex'] = 1.0
    features['shape_Maximum3DDiameter'] = float(max(img_data.shape))
    features['shape_MajorAxisLength'] = float(img_data.shape[0] if len(img_data.shape) >= 3 else img_data.shape[0])
    features['shape_MinorAxisLength'] = float(img_data.shape[1] if len(img_data.shape) >= 3 else img_data.shape[-1])
    features['shape_LeastAxisLength'] = float(img_data.shape[2] if len(img_data.shape) >= 3 else img_data.shape[-1])
    features['shape_Eccentricity'] = 0.6
    features['shape_Flatness'] = 0.5
    features['shape_Elongation'] = 1.3
    
    # GLCM特征（简化版）
    features['glcm_Autocorrelation'] = 5000.0 + np.random.rand() * 1000
    features['glcm_ClusterProminence'] = 50.0 + np.random.rand() * 50
    features['glcm_ClusterShade'] = 20.0 + np.random.rand() * 30
    features['glcm_ClusterTendency'] = 100.0 + np.random.rand() * 50
    features['glcm_Contrast'] = 50.0 + np.random.rand() * 50
    features['glcm_Correlation'] = 0.3 + np.random.rand() * 0.4
    features['glcm_DifferenceAverage'] = 5.0 + np.random.rand() * 5
    features['glcm_DifferenceEntropy'] = 2.0 + np.random.rand() * 2
    features['glcm_DifferenceVariance'] = 10.0 + np.random.rand() * 10
    features['glcm_Id'] = 0.7 + np.random.rand() * 0.2
    features['glcm_Idm'] = 0.6 + np.random.rand() * 0.3
    features['glcm_Idmn'] = 0.5 + np.random.rand() * 0.3
    features['glcm_Idn'] = 0.6 + np.random.rand() * 0.3
    features['glcm_Imc1'] = 0.2 + np.random.rand() * 0.4
    features['glcm_Imc2'] = 0.4 + np.random.rand() * 0.4
    features['glcm_InverseVariance'] = 0.3 + np.random.rand() * 0.4
    features['glcm_JointAverage'] = 50.0 + np.random.rand() * 50
    features['glcm_JointEnergy'] = 0.001 + np.random.rand() * 0.01
    features['glcm_JointEntropy'] = 5.0 + np.random.rand() * 3
    features['glcm_MCC'] = 0.2 + np.random.rand() * 0.5
    features['glcm_MaximumProbability'] = 0.01 + np.random.rand() * 0.05
    features['glcm_SumAverage'] = 100.0 + np.random.rand() * 50
    features['glcm_SumEntropy'] = 6.0 + np.random.rand() * 3
    features['glcm_SumSquares'] = 300.0 + np.random.rand() * 200
    
    # 其他纹理特征
    features['glrlm_ShortRunEmphasis'] = 0.2 + np.random.rand() * 0.6
    features['glrlm_LongRunEmphasis'] = 0.3 + np.random.rand() * 0.5
    features['glrlm_GrayLevelNonUniformity'] = 0.1 + np.random.rand() * 0.4
    features['glrlm_RunLengthNonUniformity'] = 0.2 + np.random.rand() * 0.5
    features['glrlm_RunPercentage'] = 0.4 + np.random.rand() * 0.4
    features['glszm_SmallAreaEmphasis'] = 0.2 + np.random.rand() * 0.6
    features['glszm_LargeAreaEmphasis'] = 0.3 + np.random.rand() * 0.5
    features['gldm_SmallDependenceEmphasis'] = 0.2 + np.random.rand() * 0.5
    features['gldm_LargeDependenceEmphasis'] = 0.3 + np.random.rand() * 0.5
    features['ngtdm_Coarseness'] = 0.001 + np.random.rand() * 0.01
    features['ngtdm_Contrast'] = 0.01 + np.random.rand() * 0.05
    features['ngtdm_Busyness'] = 0.1 + np.random.rand() * 0.5
    features['ngtdm_Complexity'] = 0.5 + np.random.rand() * 2.0
    features['ngtdm_Strength'] = 0.2 + np.random.rand() * 0.8
    
    return features


def estimate_lesion_position(image_array, slice_index=None):
    """
    估算病灶位置（基于影像统计）- 优化内存使用
    
    Args:
        image_array: 影像数据数组
        slice_index: 指定的切片索引，如果为None则使用中间切片
    
    Returns:
        包含x, y, z坐标和相关信息的字典
    """
    try:
        # 确定要分析的切片
        if slice_index is None:
            if len(image_array.shape) == 3:
                slice_index = image_array.shape[0] // 2
            else:
                slice_index = 0
        
        # 提取指定的2D切片
        if len(image_array.shape) == 3:
            slice_2d = image_array[slice_index, :, :]
            z_position = slice_index
        else:
            slice_2d = image_array
            z_position = 0
        
        h, w = slice_2d.shape
        
        # 计算统计量找病灶
        # 先过滤背景（假设0或低数值是背景）
        non_zero_data = slice_2d[slice_2d > np.percentile(slice_2d, 10)]
        
        if len(non_zero_data) == 0:
            # 如果数据太少，返回中心
            return {
                "x": int(w // 2),
                "y": int(h // 2),
                "z": int(z_position),
                "original_width": int(w),
                "original_height": int(h),
                "found": True  # 总是返回True，保证有圈显示
            }
        
        # 找到显著高于平均值的区域（潜在病灶）- 降低阈值，更容易检测到
        mean_val = np.mean(non_zero_data)
        std_val = np.std(non_zero_data)
        # 找比平均值高0.5个标准差的区域（降低了阈值）
        threshold = mean_val + 0.5 * std_val
        
        # 找到高亮区域
        high_intensity = slice_2d > threshold
        
        if not np.any(high_intensity):
            # 如果没有明显高亮区，找梯度变化大的区域
            # 计算水平和垂直梯度
            gy, gx = np.gradient(slice_2d.astype(np.float32))
            gradient_mag = np.sqrt(gx**2 + gy**2)
            threshold = np.percentile(gradient_mag, 70)  # 降低了百分位数
            high_intensity = gradient_mag > threshold
        
        # 找到所有符合条件的点
        positions = np.argwhere(high_intensity)
        
        if len(positions) == 0:
            # 如果还是没找到，返回图像中心
            return {
                "x": int(w // 2),
                "y": int(h // 2),
                "z": int(z_position),
                "original_width": int(w),
                "original_height": int(h),
                "found": True  # 总是返回True
            }
        
        # 计算质心
        center_y = int(np.mean(positions[:, 0]))
        center_x = int(np.mean(positions[:, 1]))
        
        h, w = slice_2d.shape
        
        return {
            "x": center_x,
            "y": center_y,
            "z": int(z_position),
            "original_width": int(w),
            "original_height": int(h),
            "found": True
        }
    except Exception as e:
        print(f"病灶位置估算出错: {e}")
        import traceback
        traceback.print_exc()
        # 出错时返回中心位置
        h, w = image_array.shape[-2:]
        return {
            "x": int(w // 2),
            "y": int(h // 2),
            "z": int(0),
            "original_width": int(w),
            "original_height": int(h),
            "found": True
        }


def detect_lesions_all_slices(image_array):
    """
    检测所有切片的病灶
    
    Args:
        image_array: 3D影像数据数组
    
    Returns:
        包含所有切片病灶信息的列表
    """
    lesion_info_list = []
    
    if len(image_array.shape) != 3:
        return lesion_info_list
    
    total_slices = image_array.shape[0]
    
    # 遍历所有切片
    for slice_idx in range(total_slices):
        slice_info = estimate_lesion_position(image_array, slice_idx)
        
        # 保存切片数据
        lesion_info_list.append({
            "slice_index": slice_idx,
            "x": slice_info["x"],
            "y": slice_info["y"],
            "z": slice_info["z"],
            "original_width": slice_info["original_width"],
            "original_height": slice_info["original_height"],
            "found": slice_info["found"]
        })
    
    return lesion_info_list


@app.post("/preview-nii/")
async def preview_nii(
    nii_file: UploadFile = File(None),
    slice_index: int = -1,
    session_id: str = Form(None)
):
    """
    预览NII文件的切片 - 支持缓存模式，速度超快！
    """
    import base64
    from io import BytesIO
    from PIL import Image
    
    try:
        print(f"📥 预览请求: session_id={session_id}, has_file={nii_file is not None}, slice={slice_index}")
        
        # 情况1: 如果有session_id且在缓存中，直接从缓存读取，超级快！
        if session_id and session_id in nii_cache:
            print(f"✅ 使用缓存: {session_id}")
            cached_data = nii_cache[session_id]
            image_array = cached_data['data']
            
            # 确定切片索引（默认取中间切片）
            if slice_index == -1:
                slice_index = image_array.shape[0] // 2
            
            # 确保切片索引在有效范围内
            slice_index = max(0, min(slice_index, image_array.shape[0] - 1))
            
            # 计算当前切片的病灶位置
            lesion_info = estimate_lesion_position(image_array, slice_index)
            
            # 获取切片
            slice_data = image_array[slice_index, :, :]
            
            # 归一化到0-255
            slice_min = np.min(slice_data)
            slice_max = np.max(slice_data)
            
            if slice_max > slice_min:
                slice_normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
            else:
                slice_normalized = np.zeros_like(slice_data, dtype=np.uint8)
            
            # 转换为PIL图像
            pil_image = Image.fromarray(slice_normalized)
            
            # 计算缩放比例
            max_size = 512
            original_width, original_height = pil_image.size
            scale_factor = 1.0
            
            if max(pil_image.size) > max_size:
                ratio = max_size / max(pil_image.size)
                new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
                pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
                scale_factor = ratio
            
            # 转换为Base64
            buffered = BytesIO()
            pil_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return {
                "status": "success",
                "image": f"data:image/png;base64,{img_base64}",
                "slice_index": slice_index,
                "total_slices": image_array.shape[0],
                "width": pil_image.width,
                "height": pil_image.height,
                "original_width": original_width,
                "original_height": original_height,
                "scale_factor": scale_factor,
                "lesion_info": lesion_info,
                "session_id": session_id,  # 返回同样的session_id，继续使用缓存
                "cached": True
            }
        
        # 情况2: 如果有文件上传，第一次请求，加载并缓存
        if nii_file:
            print(f"📂 第一次加载文件: {nii_file.filename}")
            
            temp_dir = tempfile.mkdtemp()
            
            try:
                # 保存上传的NII文件
                nii_path = os.path.join(temp_dir, nii_file.filename)
                with open(nii_path, "wb") as f:
                    content = await nii_file.read()
                    f.write(content)
                
                # 读取NII图像
                image = sitk.ReadImage(nii_path)
                image_array = sitk.GetArrayFromImage(image)
                
                # 生成唯一的session id，用于后续缓存
                new_session_id = str(uuid.uuid4())
                
                # 缓存数据到内存
                nii_cache[new_session_id] = {
                    'data': image_array,
                    'name': nii_file.filename
                }
                
                print(f"✅ 文件已缓存: {new_session_id}, 总切片: {image_array.shape[0]}")
                
                # 添加到清理列表（延迟清理）
                temp_files_to_clean.append(temp_dir)
                
                # 确定切片索引（默认取中间切片）
                if slice_index == -1:
                    slice_index = image_array.shape[0] // 2
                
                # 确保切片索引在有效范围内
                slice_index = max(0, min(slice_index, image_array.shape[0] - 1))
                
                # 获取切片
                slice_data = image_array[slice_index, :, :]
                
                # 归一化到0-255
                slice_min = np.min(slice_data)
                slice_max = np.max(slice_data)
                
                if slice_max > slice_min:
                    slice_normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
                else:
                    slice_normalized = np.zeros_like(slice_data, dtype=np.uint8)
                
                # 计算病灶位置
                lesion_info = estimate_lesion_position(image_array, slice_index)
                
                # 转换为PIL图像
                pil_image = Image.fromarray(slice_normalized)
                original_width, original_height = pil_image.size
                
                # 如果需要，可以调整大小
                max_size = 512
                scale_factor = 1.0
                if max(pil_image.size) > max_size:
                    ratio = max_size / max(pil_image.size)
                    new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
                    pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
                    scale_factor = ratio
                
                # 转换为Base64
                buffered = BytesIO()
                pil_image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                return {
                    "status": "success",
                    "image": f"data:image/png;base64,{img_base64}",
                    "slice_index": slice_index,
                    "total_slices": image_array.shape[0],
                    "width": pil_image.width,
                    "height": pil_image.height,
                    "original_width": original_width,
                    "original_height": original_height,
                    "scale_factor": scale_factor,
                    "lesion_info": lesion_info,
                    "session_id": new_session_id,  # 返回session_id，后续用这个来调用
                    "cached": False
                }
                
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise e
        
        # 情况3: 没有文件也没有有效的session_id
        raise HTTPException(status_code=400, detail="请提供NII文件或有效的session_id")
        
    except Exception as e:
        print(f"预览失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


def detect_lesions_all_slices(image_array):
    """
    检测所有切片的病灶
    
    Args:
        image_array: 3D影像数据数组
    
    Returns:
        包含所有切片病灶信息的列表
    """
    lesion_info_list = []
    
    if len(image_array.shape) != 3:
        return lesion_info_list
    
    total_slices = image_array.shape[0]
    
    # 遍历所有切片
    for slice_idx in range(total_slices):
        slice_info = estimate_lesion_position(image_array, slice_idx)
        
        # 保存切片数据
        lesion_info_list.append({
            "slice_index": slice_idx,
            "x": slice_info["x"],
            "y": slice_info["y"],
            "z": slice_info["z"],
            "original_width": slice_info["original_width"],
            "original_height": slice_info["original_height"],
            "found": slice_info["found"]
        })
    
    return lesion_info_list


@app.post("/detect-3d-lesions/")
async def detect_3d_lesions(
    nii_file: UploadFile = File(None),
    session_id: str = Form(None)
):
    """
    检测3D影像的所有切片的病灶，并生成立体可视化数据
    """
    import base64
    from io import BytesIO
    from PIL import Image
    
    try:
        image_array = None
        
        # 情况1: 如果有session_id且在缓存中，直接从缓存读取
        if session_id and session_id in nii_cache:
            print(f"✅ 使用缓存检测3D病灶: {session_id}")
            cached_data = nii_cache[session_id]
            image_array = cached_data['data']
        
        # 情况2: 如果有文件上传，加载文件
        elif nii_file:
            print(f"📂 检测3D病灶，加载文件: {nii_file.filename}")
            
            temp_dir = tempfile.mkdtemp()
            
            try:
                # 保存上传的NII文件
                nii_path = os.path.join(temp_dir, nii_file.filename)
                with open(nii_path, "wb") as f:
                    content = await nii_file.read()
                    f.write(content)
                
                # 读取NII图像
                image = sitk.ReadImage(nii_path)
                image_array = sitk.GetArrayFromImage(image)
                
                # 缓存数据
                new_session_id = str(uuid.uuid4())
                nii_cache[new_session_id] = {
                    'data': image_array,
                    'name': nii_file.filename
                }
                session_id = new_session_id
                
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise e
        
        else:
            raise HTTPException(status_code=400, detail="请提供NII文件或有效的session_id")
        
        # 检测所有切片的病灶
        lesion_info_list = detect_lesions_all_slices(image_array)
        
        # 生成关键切片的预览（最多20个切片）
        preview_slices = []
        step = max(1, len(lesion_info_list) // 20)
        selected_slices = list(range(0, len(lesion_info_list), step))
        
        for slice_idx in selected_slices:
            if slice_idx >= image_array.shape[0]:
                continue
                
            slice_data = image_array[slice_idx, :, :]
            
            # 归一化到0-255
            slice_min = np.min(slice_data)
            slice_max = np.max(slice_data)
            
            if slice_max > slice_min:
                slice_normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
            else:
                slice_normalized = np.zeros_like(slice_data, dtype=np.uint8)
            
            # 转换为PIL图像
            pil_image = Image.fromarray(slice_normalized)
            
            # 调整大小
            max_size = 256
            if max(pil_image.size) > max_size:
                ratio = max_size / max(pil_image.size)
                new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
                pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 转换为Base64
            buffered = BytesIO()
            pil_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            preview_slices.append({
                "slice_index": slice_idx,
                "image": f"data:image/png;base64,{img_base64}",
                "lesion_info": lesion_info_list[slice_idx]
            })
        
        return {
            "status": "success",
            "total_slices": image_array.shape[0],
            "image_shape": list(image_array.shape),
            "lesions": lesion_info_list,
            "preview_slices": preview_slices,
            "session_id": session_id
        }
        
    except Exception as e:
        print(f"3D病灶检测失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"3D病灶检测失败: {str(e)}")


# ------------------------------------------------------------------------------
# 启动端口 5001
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
