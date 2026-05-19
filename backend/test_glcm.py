import numpy as np
from skimage.feature import graycomatrix, graycoprops

# 生成测试数据
test_img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
test_mask = np.zeros((100, 100), dtype=bool)
test_mask[20:80, 20:80] = True

# 量化到16级灰度
roi_region = test_img[test_mask]
min_val, max_val = np.min(roi_region), np.max(roi_region)
quantized = ((roi_region - min_val) / (max_val - min_val) * 15).astype(np.uint8)

# 创建量化后的图像
temp_img = np.zeros_like(test_img, dtype=np.uint8)
temp_img[test_mask] = quantized

print(f"测试图像形状: {test_img.shape}")
print(f"ROI区域像素数: {np.sum(test_mask)}")
print(f"量化后唯一值数量: {len(np.unique(quantized))}")
print(f"量化值范围: {np.min(quantized)} - {np.max(quantized)}")

# 计算GLCM（使用mask参数）
glcm = graycomatrix(temp_img, distances=[1], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4], 
                    levels=16, symmetric=True, normed=True, mask=test_mask)

# 计算特征
contrast = float(graycoprops(glcm, 'contrast').mean())
correlation = float(graycoprops(glcm, 'correlation').mean())
homogeneity = float(graycoprops(glcm, 'homogeneity').mean())
dissimilarity = float(graycoprops(glcm, 'dissimilarity').mean())

print(f"\nGLCM特征值:")
print(f"Contrast: {contrast}")
print(f"Correlation: {correlation}")
print(f"Homogeneity: {homogeneity}")
print(f"Dissimilarity: {dissimilarity}")
