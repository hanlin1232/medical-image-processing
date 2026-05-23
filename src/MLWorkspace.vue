<template>
  <div class="ml-workspace">
    <header class="header">
      <h1>医学影像特征提取工作台</h1>
      <div class="header-actions">
        <button @click="resetWorkspace" class="btn-reset">重置</button>
        <button @click="checkBackend" class="btn-check" :disabled="isChecking">
          {{ isChecking ? '检测中...' : '🔍 检测后端' }}
        </button>
      </div>
    </header>

    <nav class="top-nav">
      <div class="nav-inner">
        <a href="#nii-upload" class="nav-link" :class="{ active: activeNavSection === 'nii-upload' }"
          @click.prevent="scrollTo('nii-upload')">
          <span class="nav-icon">📁</span><span class="nav-text">NII上传</span>
        </a>
        <a href="#feature-info" class="nav-link" :class="{ active: activeNavSection === 'feature-info' }"
          @click.prevent="scrollTo('feature-info')">
          <span class="nav-icon">📋</span><span class="nav-text">特征说明</span>
        </a>
        <a href="#csv-normalize" class="nav-link" :class="{ active: activeNavSection === 'csv-normalize' }"
          @click.prevent="scrollTo('csv-normalize')">
          <span class="nav-icon">⚡</span><span class="nav-text">CSV归一化</span>
        </a>
        <a href="#dataset-split" class="nav-link" :class="{ active: activeNavSection === 'dataset-split' }"
          @click.prevent="scrollTo('dataset-split')">
          <span class="nav-icon">📊</span><span class="nav-text">数据集划分</span>
        </a>
        <a href="#svm-train" class="nav-link" :class="{ active: activeNavSection === 'svm-train' }"
          @click.prevent="scrollTo('svm-train')">
          <span class="nav-icon">🧠</span><span class="nav-text">SVM训练</span>
        </a>
        <a href="#lesion-detect" class="nav-link" :class="{ active: activeNavSection === 'lesion-detect' }"
          @click.prevent="scrollTo('lesion-detect')">
          <span class="nav-icon">🔍</span><span class="nav-text">病灶识别</span>
        </a>
      </div>
    </nav>

    <main class="main-content">
      <section class="nii-upload-section" id="nii-upload">
        <h2>📁 NII文件上传</h2>

        <!-- 上传方式切换 -->
        <div class="upload-mode-switch">
          <button @click="uploadMode = 'files'" class="mode-btn" :class="{ active: uploadMode === 'files' }">
            📁 分别上传文件
          </button>
          <button @click="uploadMode = 'folder'" class="mode-btn" :class="{ active: uploadMode === 'folder' }">
            📂 上传NII文件夹
          </button>
        </div>

        <!-- 文件夹上传模式 -->
        <div v-if="uploadMode === 'folder'" class="folder-upload">
          <div class="upload-area folder-area" @dragover.prevent @drop.prevent="handleFolderDrop">
            <input type="file" ref="folderInput" @change="handleFolderSelect" webkitdirectory directory
              accept=".nii,.nii.gz" />
            <div class="upload-hint">
              <span class="upload-icon">{{ folderFiles.length > 0 ? '✓' : '📂' }}</span>
              <p>{{ folderFiles.length > 0 ? `已选择 ${folderFiles.length} 个文件` : '拖拽文件夹或点击选择' }}</p>
              <p class="upload-formats">选择包含 lung 和 ROI 文件的文件夹</p>
            </div>
          </div>

          <!-- 自动识别文件 -->
          <div v-if="folderFiles.length > 0" class="file-detection">
            <h3>📋 文件识别结果</h3>
            <div class="detected-files">
              <div class="detected-item">
                <span class="detected-label">肺部影像:</span>
                <div class="detected-value-wrapper">
                  <span :class="['detected-value', imageFile ? 'success' : 'warning']">
                    {{ imageFile ? imageFile.name : '未找到' }}
                  </span>
                  <button @click="showImageSelector = !showImageSelector" class="btn-select-file">
                    {{ showImageSelector ? '✕' : '🔄' }}
                  </button>
                </div>
                <!-- 手动选择影像文件 -->
                <div v-if="showImageSelector" class="file-selector">
                  <select v-model="selectedImageIndex" @change="selectImageFile">
                    <option value="">请选择影像文件</option>
                    <option v-for="(file, index) in niiFiles" :key="index" :value="index">
                      {{ file.name }}
                    </option>
                  </select>
                </div>
              </div>
              <div class="detected-item">
                <span class="detected-label">ROI掩码:</span>
                <div class="detected-value-wrapper">
                  <span :class="['detected-value', roiFile ? 'success' : 'warning']">
                    {{ roiFile ? roiFile.name : '未找到' }}
                  </span>
                  <button @click="showRoiSelector = !showRoiSelector" class="btn-select-file">
                    {{ showRoiSelector ? '✕' : '🔄' }}
                  </button>
                </div>
                <!-- 手动选择ROI文件 -->
                <div v-if="showRoiSelector" class="file-selector">
                  <select v-model="selectedRoiIndex" @change="selectRoiFile">
                    <option value="">请选择ROI文件</option>
                    <option v-for="(file, index) in niiFiles" :key="index" :value="index">
                      {{ file.name }}
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 显示所有NII文件列表（可折叠） -->
            <div class="nii-files-list">
              <h4 @click="showNiiFileList = !showNiiFileList" class="collapsible-header">
                <span class="collapse-arrow">{{ showNiiFileList ? '▼' : '▶' }}</span>
                📁 找到的NII文件 ({{ niiFiles.length }})
              </h4>
              <ul v-if="showNiiFileList">
                <li v-for="(file, index) in niiFiles" :key="index">
                  {{ file.name }}
                  <span v-if="imageFile && imageFile.name === file.name" class="file-tag image-tag">影像</span>
                  <span v-if="roiFile && roiFile.name === file.name" class="file-tag roi-tag">ROI</span>
                </li>
              </ul>
            </div>
          </div>
          <!-- 批量患者检测结果 -->
          <div v-if="detectedPatients.length > 0" class="detected-patients-section">
            <h3>检测到 {{ detectedPatients.length }} 个患者</h3>
            <div class="patients-table-wrapper">
              <table class="patients-table">
                <thead>
                  <tr>
                    <th><input type="checkbox" @click.stop="toggleSelectAllPatients" :checked="allPatientsSelected"
                        title="全选" /></th>
                    <th>患者ID</th>
                    <th>标签文件夹</th>
                    <th>映射标签</th>
                    <th>Lung文件</th>
                    <th>ROI文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(p, idx) in detectedPatients" :key="idx"
                    :class="{ 'selected-row': selectedPatientIndex === idx }" @click="selectBatchPatient(idx)">
                    <td><input type="checkbox" :checked="selectedPatientIndices.includes(idx)"
                        @click.stop="togglePatientSelect(idx)" /></td>
                    <td>{{ p.patientId }}</td>
                    <td>{{ p.label }}</td>
                    <td>{{ detectedLabelMap[p.label] || p.label }}</td>
                    <td :class="p.lung ? 'file-ok' : 'file-missing'">{{ p.lung ? p.lung.name : '缺失' }}</td>
                    <td :class="p.roi ? 'file-ok' : 'file-missing'">{{ p.roi ? p.roi.name : '缺失' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="patient-actions">
              <button @click="useSelectedPatient" :disabled="selectedPatientIndex < 0" class="btn-extract">
                使用选中患者提取特征
              </button>
              <button @click="batchExtractAllPatients" :disabled="isExtracting" class="btn-download">
                批量提取全部患者
              </button>
            </div>
          </div>
        </div>

        <!-- 单独文件上传模式 -->
        <div v-else class="upload-container">
          <div class="upload-box">
            <h3>🩻 肺部影像文件 (Image)</h3>
            <div class="upload-area" :class="{ 'has-file': imageFile }" @dragover.prevent
              @drop.prevent="(e) => handleFileDrop(e, 'image')">
              <input type="file" ref="imageInput" @change="(e) => handleFileSelect(e, 'image')" accept=".nii,.nii.gz" />
              <div class="upload-hint">
                <span class="upload-icon">{{ imageFile ? '✓' : '📁' }}</span>
                <p>{{ imageFile ? imageFile.name : '拖拽或点击选择NII文件' }}</p>
                <p class="upload-formats">支持 .nii 或 .nii.gz 格式</p>
              </div>
            </div>
          </div>

          <div class="upload-box">
            <h3>🎯 ROI掩码文件 (Mask)</h3>
            <div class="upload-area" :class="{ 'has-file': roiFile }" @dragover.prevent
              @drop.prevent="(e) => handleFileDrop(e, 'roi')">
              <input type="file" ref="roiInput" @change="(e) => handleFileSelect(e, 'roi')" accept=".nii,.nii.gz" />
              <div class="upload-hint">
                <span class="upload-icon">{{ roiFile ? '✓' : '📁' }}</span>
                <p>{{ roiFile ? roiFile.name : '拖拽或点击选择ROI掩码' }}</p>
                <p class="upload-formats">支持 .nii 或 .nii.gz 格式</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 患者信息 -->
        <div class="patient-info-row">
          <div class="patient-input-group">
            <label>患者ID</label>
            <input type="text" v-model="patientId" placeholder="例: P00173278" class="patient-input" />
          </div>
          <div class="patient-input-group">
            <label>标签</label>
            <select v-model="patientLabel" class="patient-input">
              <option value="">请选择</option>
              <option value="0">0</option>
              <option value="1">1</option>
            </select>
          </div>
        </div>

        <!-- 单独文件模式的提取按钮 -->
        <button v-if="uploadMode === 'files'" @click="extractFeatures" class="btn-extract"
          :disabled="!imageFile || !roiFile || isExtracting">
          {{ isExtracting ? '提取中...' : '提取影像组学特征' }}
        </button>

        <!-- 后端状态提示 -->
        <div v-if="backendStatus" :class="['backend-status', backendStatus.status]">
          <span class="status-icon">{{ backendStatus.status === 'success' ? '✓' : '⚠' }}</span>
          <span>{{ backendStatus.message }}</span>
        </div>

        <!-- 影像预览区域 -->
        <div v-if="niiFiles.length > 0 || imageFile" class="feature-preview-section">
          <h3>🖼️ 影像预览</h3>
          <div class="preview-controls">
            <select v-model="selectedPreviewFileIndex" @change="previewSelectedFile" class="file-select">
              <option value="">选择要预览的文件</option>
              <option v-for="(file, index) in getPreviewableFiles()" :key="index" :value="index">
                {{ file.name }}
              </option>
            </select>
          </div>
          <div class="preview-display">
            <div v-if="featurePreviewImage" class="preview-image-container">
              <img :src="featurePreviewImage.image" alt="NII Preview" class="preview-nii-image" />
            </div>
            <div v-else class="preview-placeholder">
              <span>选择文件后预览</span>
            </div>
          </div>
          <div v-if="featurePreviewImage" class="preview-slider-controls">
            <div class="preview-slider-container">
              <span class="slice-label">切片</span>
              <input type="range" :min="0" :max="featurePreviewImage.total_slices - 1" v-model="featurePreviewSlice"
                @input="updatePreviewSlice" class="slice-slider" />
              <span class="slice-info">{{ featurePreviewSlice + 1 }} / {{ featurePreviewImage.total_slices }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="feature-info-section" id="feature-info">
        <h2>📋 特征类别说明</h2>
        <div class="info-cards">
          <div class="info-card" v-for="(desc, key) in featureCategories" :key="key">
            <h4>{{ getCategoryIcon(key) }} {{ key.toUpperCase() }}</h4>
            <p>{{ desc }}</p>
          </div>
        </div>
      </section>

      <!-- 归一化模块 -->
      <section class="csv-section" id="csv-normalize">
        <h2>⚡ CSV归一化</h2>
        <div class="csv-upload-area">
          <input type="file" ref="normCsvFile" id="norm-csv" @change="handleNormCsvSelect" accept=".csv"
            class="csv-input" />
          <label for="norm-csv" class="csv-upload-btn">
            📁 上传CSV文件
          </label>
          <span v-if="normCsvFileName" class="csv-file-name">{{ normCsvFileName }}</span>
        </div>

        <div v-if="normCsvLoaded" class="norm-controls">
          <button @click="normalizeCsv" class="btn-process">🔄 开始归一化</button>
        </div>

        <div v-if="normProgressValue > 0" class="progress-container">
          <div class="progress-bar-wrapper">
            <div class="progress-bar" :style="{ width: normProgressValue + '%' }"></div>
          </div>
          <span class="progress-text">{{ normProgressMessage }}</span>
        </div>

        <div v-if="normResult" class="norm-result">
          <h3>归一化结果</h3>
          <div class="result-stats">
            <div class="stat-item">
              <span class="stat-label">行数:</span>
              <span class="stat-value">{{ normResult.rows }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">列数:</span>
              <span class="stat-value">{{ normResult.columns }}</span>
            </div>
          </div>
          <button @click="downloadNormalizedCsv" class="btn-download">💾 下载归一化CSV</button>
        </div>
      </section>

      <!-- 数据集划分模块 -->
      <section class="csv-section" id="dataset-split">
        <h2>📊 数据集划分</h2>
        <div class="csv-upload-area">
          <input type="file" ref="splitCsvFile" id="split-csv" @change="handleSplitCsvSelect" accept=".csv"
            class="csv-input" />
          <label for="split-csv" class="csv-upload-btn">
            📁 上传CSV文件
          </label>
          <span v-if="splitCsvFileName" class="csv-file-name">{{ splitCsvFileName }}</span>
        </div>

        <div v-if="splitCsvLoaded" class="split-controls">
          <div class="split-slider">
            <label>训练集比例: {{ splitRatio * 100 }}%</label>
            <input type="range" v-model.number="splitRatio" min="0.5" max="0.9" step="0.05" class="ratio-slider" />
          </div>
          <button @click="splitDataset" class="btn-process">🔀 开始划分</button>
        </div>

        <div v-if="splitResult" class="split-result">
          <div class="result-summary">
            <div class="summary-card">
              <span class="summary-label">总样本数</span>
              <span class="summary-value">{{ splitResult.total }}</span>
            </div>
            <div class="summary-card">
              <span class="summary-label">训练集</span>
              <span class="summary-value">{{ splitResult.train_count }}</span>
            </div>
            <div class="summary-card">
              <span class="summary-label">测试集</span>
              <span class="summary-value">{{ splitResult.test_count }}</span>
            </div>
          </div>
          <div class="result-actions">
            <button @click="downloadTrainSet" class="btn-download">💾 下载训练集</button>
            <button @click="downloadTestSet" class="btn-download">💾 下载测试集</button>
          </div>
        </div>
      </section>

      <!-- SVM训练模块 -->
      <section class="svm-section" id="svm-train">
        <h2>🧠 SVM分类器训练</h2>

        <div class="svm-upload">
          <input type="file" ref="svmTrainFile" id="svm-train-file" @change="handleSvmTrainFileSelect" accept=".csv"
            class="csv-input" />
          <label for="svm-train-file" class="csv-upload-btn">
            📁 上传训练CSV
          </label>
          <span v-if="svmTrainFileName" class="csv-file-name">{{ svmTrainFileName }}</span>
        </div>

        <div class="svm-upload">
          <input type="file" ref="svmTestFile" id="svm-test-file" @change="handleSvmTestFileSelect" accept=".csv"
            class="csv-input" />
          <label for="svm-test-file" class="csv-upload-btn">
            📁 上传测试CSV（可选）
          </label>
          <span v-if="svmTestFileName" class="csv-file-name">{{ svmTestFileName }}</span>
        </div>

        <div v-if="svmTrainLoaded" class="svm-controls">
          <button @click="trainSvm" class="btn-process btn-train" :disabled="isTrainingSvm">
            {{ isTrainingSvm ? '训练中...' : '🚀 开始训练' }}
          </button>
        </div>

        <div v-if="svmProgressValue > 0 && isTrainingSvm" class="progress-container">
          <div class="progress-bar-wrapper">
            <div class="progress-bar" :style="{ width: svmProgressValue + '%' }"></div>
          </div>
          <span class="progress-text">{{ svmProgressMessage }} ({{ svmProgressValue }}%)</span>
        </div>

        <div v-if="svmResult" class="svm-result">
          <h3>📊 模型评估结果</h3>

          <div class="metrics-grid">
            <div class="metric-card">
              <span class="metric-icon">🎯</span>
              <span class="metric-label">测试准确率</span>
              <span class="metric-value">{{ formatPercent(svmResult.test_acc) }}</span>
            </div>
            <div class="metric-card">
              <span class="metric-icon">📚</span>
              <span class="metric-label">训练准确率</span>
              <span class="metric-value">{{ formatPercent(svmResult.train_acc) }}</span>
            </div>
            <div class="metric-card">
              <span class="metric-icon">📏</span>
              <span class="metric-label">召回率</span>
              <span class="metric-value">{{ formatPercent(svmResult.recall) }}</span>
            </div>
            <div class="metric-card">
              <span class="metric-icon">⚖️</span>
              <span class="metric-label">F1分数</span>
              <span class="metric-value">{{ formatPercent(svmResult.f1) }}</span>
            </div>
            <div class="metric-card">
              <span class="metric-icon">📈</span>
              <span class="metric-label">AUC值</span>
              <span class="metric-value">{{ formatAuc(svmResult.auc) }}</span>
            </div>
          </div>

          <div v-if="svmResult.confusion_matrix && svmResult.confusion_matrix.length === 2" class="confusion-matrix">
            <h4>🔢 混淆矩阵</h4>
            <div class="matrix-container">
              <div class="matrix-row">
                <div class="matrix-cell tn">{{ svmResult.confusion_matrix[0][0] }}<span class="cell-label">TN</span></div>
                <div class="matrix-cell fp">{{ svmResult.confusion_matrix[0][1] }}<span class="cell-label">FP</span></div>
              </div>
              <div class="matrix-row">
                <div class="matrix-cell fn">{{ svmResult.confusion_matrix[1][0] }}<span class="cell-label">FN</span></div>
                <div class="matrix-cell tp">{{ svmResult.confusion_matrix[1][1] }}<span class="cell-label">TP</span></div>
              </div>
            </div>
            <div class="matrix-labels">
              <span>行=真实 / 列=预测</span>
            </div>
          </div>

          <div v-show="svmResult.roc_data" class="roc-chart">
            <h4>📉 ROC曲线</h4>
            <div class="chart-container">
              <canvas ref="rocCanvas" width="400" height="300"></canvas>
            </div>
          </div>

          <div v-if="svmResult.feature_importance" class="feature-heatmap">
            <h4>🔥 特征重要性</h4>
            <div class="heatmap-container">
              <div class="heatmap-row" v-for="(importance, name) in svmResult.feature_importance" :key="name">
                <span class="heatmap-label">{{ name }}</span>
                <div class="heatmap-bar" :style="{ width: (importance * 100) + '%' }"></div>
                <span class="heatmap-value">{{ (importance * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>

          <div class="basic-info">
            <div class="info-item">
              <span class="info-label">训练样本数</span>
              <span class="info-value">{{ svmResult.train_num }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">测试样本数</span>
              <span class="info-value">{{ svmResult.test_num }}</span>
            </div>
            <div v-if="svmResult.model_size" class="info-item">
              <span class="info-label">模型大小</span>
              <span class="info-value">{{ svmResult.model_size }} MB</span>
            </div>
          </div>

          <div v-if="svmResult" class="model-download">
            <button @click="downloadModel" class="btn-process btn-download">
              📥 下载模型 (svm_model.pkl)
            </button>
          </div>
        </div>
      </section>

      <section class="predict-section" id="lesion-detect">
        <h2>🔍 病灶识别</h2>

        <div class="predict-content">
          <!-- 左侧：上传控件 + 识别结果 -->
          <div class="predict-left">
            <div class="predict-upload">
              <div class="upload-item">
                <input type="file" ref="modelFile" id="predict-model" @change="handleModelSelect" accept=".pkl"
                  class="pkl-input" />
                <label for="predict-model" class="predict-upload-btn">
                  📦 上传模型文件 (.pkl)
                </label>
                <span v-if="modelFileName" class="csv-file-name">{{ modelFileName }}</span>
              </div>

              <div class="upload-item">
                <input type="file" ref="niiImageFile" id="predict-nii" @change="handleNiiImageSelect"
                  accept=".nii,.nii.gz" class="nii-input" />
                <label for="predict-nii" class="predict-upload-btn">
                  🩺 上传NII影像文件
                </label>
                <span v-if="niiImageFileName" class="csv-file-name">{{ niiImageFileName }}</span>
              </div>
            </div>

            <!-- 操作按钮区 -->
            <div v-if="modelLoaded && niiImageLoaded" class="predict-controls">
              <button @click="predictLesion" class="btn-process btn-predict" :disabled="isPredicting">
                {{ isPredicting ? '识别中...' : '🚀 开始识别' }}
              </button>
            </div>

            <!-- 进度条 -->
            <div v-if="predictProgress > 0 && isPredicting" class="progress-container">
              <div class="progress-bar-wrapper">
                <div class="progress-bar" :style="{ width: predictProgress + '%' }"></div>
              </div>
              <span class="progress-text">{{ predictProgressMessage }} ({{ predictProgress }}%)</span>
            </div>

            <!-- 识别结果 -->
            <div v-if="predictResult" class="predict-result">
              <h3>📋 识别结果</h3>

              <!-- 判断是否有病灶 -->
              <div class="result-status">
                <div v-if="!hasLesion" class="no-lesion-message">
                  <span class="no-lesion-icon">✅</span>
                  <h4>未检测到病灶</h4>
                  <p>该影像未检测出明显的病灶特征</p>
                </div>
                <div v-else class="has-lesion-message">
                  <span class="has-lesion-icon">⚠️</span>
                  <h4>检测到病灶</h4>
                </div>
              </div>

              <div class="result-metrics">
                <div class="result-card">
                  <span class="result-icon">🎯</span>
                  <span class="result-label">预测类别</span>
                  <span class="result-value">{{ predictResult.predicted_class }}</span>
                </div>
                <div class="result-card">
                  <span class="result-icon">📊</span>
                  <span class="result-label">置信度</span>
                  <span class="result-value">{{ (predictResult.confidence * 100).toFixed(2) }}%</span>
                </div>
              </div>

              <!-- 只在有病灶时显示位置 -->
              <div v-if="hasLesion && predictResult.lesion_position" class="lesion-position">
                <h4>📍 病灶位置</h4>
                <div class="position-info">
                  <p><strong>X坐标:</strong> {{ predictResult.lesion_position.x }}</p>
                  <p><strong>Y坐标:</strong> {{ predictResult.lesion_position.y }}</p>
                  <p><strong>Z坐标:</strong> {{ predictResult.lesion_position.z }}</p>
                </div>
              </div>

              <div v-if="predictResult.feature_summary" class="feature-summary">
                <h4>📈 特征摘要</h4>
                <div class="summary-grid">
                  <div v-for="(value, key) in predictResult.feature_summary" :key="key" class="summary-item">
                    <span class="summary-key">{{ key }}:</span>
                    <span class="summary-value">{{ typeof value === 'number' ? value.toFixed(4) : value }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：2D影像预览 -->
          <div class="predict-right">
            <!-- 2D影像预览 -->
            <div class="nii-preview">
              <h3>🖼️ 影像预览</h3>
              <div v-if="niiPreview" class="image-container" ref="imageContainerRef">
                <div class="image-wrapper" :class="{ 'has-lesion': hasLesion }">
                  <img :src="niiPreview.image" alt="NII Preview" class="nii-image" ref="niiImageRef"
                    @load="onImageLoad" />
                  <!-- 只在有病灶时显示轮廓标注 -->
                  <svg v-if="hasLesion" class="lesion-overlay" :width="overlayWidth" :height="overlayHeight">
                    <path v-if="lesionContourPath" :d="lesionContourPath" fill="rgba(255, 68, 68, 0.25)"
                      stroke="#ff4444" stroke-width="2.5" />
                    <rect v-if="lesionBBox" :x="lesionBBox.x" :y="lesionBBox.y" :width="lesionBBox.width"
                      :height="lesionBBox.height" fill="none" stroke="#ffeb3b" stroke-width="1.5"
                      stroke-dasharray="6,4" />
                    <circle v-if="!lesionContourPath" :cx="overlayWidth / 2" :cy="overlayHeight / 2"
                      :r="Math.min(overlayWidth, overlayHeight) * 0.15" fill="none" stroke="#ff4444" stroke-width="3"
                      stroke-dasharray="6,4" />
                  </svg>
                  <!-- 如果没有病灶，显示安全提示 -->
                  <div v-if="!hasLesion && predictResult" class="no-lesion-overlay">
                    <span class="check-icon">✓</span>
                    <span>未检测到病灶</span>
                  </div>
                </div>
              </div>
              <div v-else-if="isLoadingPreview" class="image-placeholder loading">
                <div class="loading-spinner-small"></div>
                <span>正在加载预览...</span>
              </div>
              <div v-else class="image-placeholder">
                <span>请上传NII文件以预览</span>
              </div>

              <div v-if="niiPreview" class="slice-controls">
                <div class="slice-slider-container">
                  <span class="slice-label">切片</span>
                  <input type="range" :min="0" :max="niiPreview.total_slices - 1" :value="currentSlice"
                    @input="onSliceInput" class="slice-slider" />
                  <span class="slice-info">{{ currentSlice + 1 }} / {{ niiPreview.total_slices }}</span>
                </div>
              </div>
            </div>

          </div> <!-- 闭合 predict-right -->
        </div> <!-- 闭合 predict-content -->
      </section>
    </main>

    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>{{ loadingMessage }}</p>
    </div>

    <div v-if="error" class="error-toast">
      {{ error }}
      <button @click="error = null" class="close-error">✕</button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';

// 后端API地址
const API_BASE = '/api';

export default {
  name: 'MLWorkspace',
  setup() {
    // CSV值转义：包含逗号、引号或换行符时用双引号包裹
    const quoteCsvValue = (val) => {
      const s = String(val ?? '');
      if (s.includes(',') || s.includes('"') || s.includes('\n') || s.includes('\r')) {
        return '"' + s.replace(/"/g, '""') + '"';
      }
      return s;
    };

    // 正确解析一行CSV（处理引号内的逗号）
    const parseCsvLine = (line) => {
      const result = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
            current += '"';
            i++;
          } else {
            inQuotes = !inQuotes;
          }
        } else if (char === ',' && !inQuotes) {
          result.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      result.push(current.trim());
      return result;
    };

    const imageInput = ref(null);
    const roiInput = ref(null);
    const folderInput = ref(null);

    const uploadMode = ref('files'); // 'files' or 'folder'
    const folderFiles = ref([]);
    const niiFiles = ref([]); // 存储所有NII文件
    const patientId = ref('');
    const patientLabel = ref('');
    const imageFile = ref(null);
    const roiFile = ref(null);
    const features = ref(null);
    const isExtracting = ref(false);
    const loading = ref(false);
    const loadingMessage = ref('');
    const error = ref(null);
    const backendStatus = ref(null);
    const isChecking = ref(false);

    // 特征提取模块的影像预览
    const featurePreviewImage = ref(null);
    const featurePreviewSlice = ref(0);
    const selectedPreviewFileIndex = ref('');
    const featurePreviewSessionId = ref(null);
    const previewingFile = ref(null);
    // 手动选择相关变量
    const showImageSelector = ref(false);
    const showRoiSelector = ref(false);
    const selectedImageIndex = ref('');
    const selectedRoiIndex = ref('');
    const showNiiFileList = ref(true);

    // 数据集划分
    const splitCsvFile = ref(null);
    const splitCsvFileName = ref('');
    const splitCsvLoaded = ref(false);
    const splitRatio = ref(0.8);
    const splitResult = ref(null);
    const isSplitting = ref(false);
    let splitTrainData = null;
    let splitTestData = null;

    // 归一化
    const normCsvFile = ref(null);
    const normCsvFileName = ref('');
    const normCsvLoaded = ref(false);
    const normResult = ref(null);
    const normProgressValue = ref(0);
    const normProgressMessage = ref('');
    const isNormalizing = ref(false);

    // SVM训练
    const svmTrainFile = ref(null);
    const svmTrainFileName = ref('');
    const svmTrainLoaded = ref(false);
    const svmTestFile = ref(null);
    const svmTestFileName = ref('');
    const svmTestLoaded = ref(false);
    const svmResult = ref(null);
    const svmProgressValue = ref(0);
    const svmProgressMessage = ref('');
    const isTrainingSvm = ref(false);
    const rocCanvas = ref(null);

    const featureCategories = ref({
      "shape": "形状特征 - 描述ROI的几何形状（体积、表面积、球形度等）",
      "firstorder": "一阶统计特征 - 描述图像强度分布（均值、方差、偏度、峰度等）",
      "glcm": "灰度共生矩阵 - 4方向GLCM纹理特征（对比度、相关性、同质性、能量等）"
    });

    const detectedPatients = ref([]);
    const detectedLabelMap = ref({});
    const selectedPatientIndex = ref(-1);
    const selectedPatientIndices = ref([]);
    const activeNavSection = ref('nii-upload');

    const allPatientsSelected = computed(() => {
      const patients = detectedPatients.value;
      return patients.length > 0 && selectedPatientIndices.value.length === patients.length;
    });

    const toggleSelectAllPatients = () => {
      if (allPatientsSelected.value) {
        selectedPatientIndices.value = [];
      } else {
        selectedPatientIndices.value = detectedPatients.value.map((_, i) => i);
      }
    };

    const togglePatientSelect = (idx) => {
      const arr = selectedPatientIndices.value;
      const pos = arr.indexOf(idx);
      if (pos >= 0) {
        arr.splice(pos, 1);
      } else {
        arr.push(idx);
      }
    };

    // 导航平滑滚动
    const scrollTo = (id) => {
      const el = document.getElementById(id);
      if (el) {
        const navHeight = 70;
        const top = el.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    };

    const updateActiveNav = () => {
      const sections = ['nii-upload', 'feature-info', 'csv-normalize', 'dataset-split', 'svm-train', 'lesion-detect'];
      const scrollPos = window.scrollY + 120;
      let active = sections[0];
      for (const id of sections) {
        const el = document.getElementById(id);
        if (el && el.offsetTop <= scrollPos) {
          active = id;
        }
      }
      activeNavSection.value = active;
    };

    onMounted(() => {
      window.addEventListener('scroll', updateActiveNav, { passive: true });
    });

    onUnmounted(() => {
      window.removeEventListener('scroll', updateActiveNav);
    });


    // 检测后端服务
    const checkBackend = async () => {
      isChecking.value = true;
      try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
          const data = await response.json();
          backendStatus.value = {
            status: 'success',
            message: '后端服务连接正常',
            has_pyradiomics: data.has_pyradiomics
          };
        } else {
          backendStatus.value = {
            status: 'warning',
            message: '后端服务不可用，将使用模拟数据',
            has_pyradiomics: false
          };
        }
      } catch {
        backendStatus.value = {
          status: 'warning',
          message: '无法连接后端服务，将使用模拟数据',
          has_pyradiomics: false
        };
      }
      isChecking.value = false;
    };

    // 处理文件夹选择
    const handleFolderSelect = (event) => {
      const files = Array.from(event.target.files);
      processFolderFiles(files);
    };

    // 处理文件夹拖拽
    const handleFolderDrop = (event) => {
      const files = Array.from(event.dataTransfer.files);
      processFolderFiles(files);
    };

    // 处理文件夹文件 — 解析目录结构提取患者信息和标签
    const processFolderFiles = (files) => {
      folderFiles.value = files;
      error.value = null;

      const foundNiiFiles = files.filter(f => f.name.endsWith('.nii') || f.name.endsWith('.nii.gz'));
      niiFiles.value = foundNiiFiles;

      if (foundNiiFiles.length === 0) {
        imageFile.value = null;
        roiFile.value = null;
        detectedPatients.value = [];
        return;
      }

      // 解析目录结构: ... / label_folder / patient_folder / file.nii
      // webkitRelativePath 是相对于选中文件夹的路径
      const patientMap = {};
      const labelFolderNames = new Set();
      const allLabelCandidates = [];

      for (const f of foundNiiFiles) {
        const relPath = f.webkitRelativePath || f.name;
        const parts = relPath.replace(/\\/g, '/').split('/').filter(p => p && p !== '.');

        let patientKey, patientId, labelFolder;
        const n = parts.length;

        if (n >= 3) {
          // 倒数第3层 = label, 倒数第2层 = patient, 最后 = filename
          labelFolder = parts[n - 3];
          patientId = parts[n - 2];
          patientKey = labelFolder + '/' + patientId;
        } else if (n === 2) {
          // 2层: 可能是 label/file.nii 或 patient/file.nii
          const first = parts[0];
          if (/^[01]$/.test(first) || first.length <= 3) {
            // 短名称 → 可能是 label 文件夹
            labelFolder = first;
            patientId = first + '_patient';  // 没有真实患者ID，用label代替
            patientKey = labelFolder + '/' + patientId;
          } else {
            // 长名称 → 可能是 patient 文件夹，但没有 label 信息
            labelFolder = '__nested__';
            patientId = first;
            patientKey = patientId;
          }
        } else {
          // 只有文件名，无法解析
          patientKey = f.name;
          patientId = f.name.replace(/\.(nii|nii\.gz)$/i, '');
          labelFolder = '__single__';
        }

        labelFolderNames.add(labelFolder);
        allLabelCandidates.push(labelFolder);

        if (!patientMap[patientKey]) {
          patientMap[patientKey] = { label: labelFolder, patientId, lung: null, roi: null };
        }

        const lungPatterns = ['lung', 'image', 'ct', 'scan', 'volume', 'img', 'original', 'tissue', 'chest'];
        const roiPatterns = ['roi', 'mask', 'label', 'segmentation', 'seg', 'mask_roi', 'roi_mask', 'annotation', 'region'];
        const fname = f.name.toLowerCase();
        const isLung = lungPatterns.some(p => fname.includes(p)) && !roiPatterns.some(p => fname.includes(p));
        const isRoi = roiPatterns.some(p => fname.includes(p));

        if (isLung || (!isRoi && !patientMap[patientKey].lung)) {
          if (!patientMap[patientKey].lung) patientMap[patientKey].lung = f;
        }
        if (isRoi || (!isLung && patientMap[patientKey].lung && !patientMap[patientKey].roi)) {
          if (!patientMap[patientKey].roi || isRoi) patientMap[patientKey].roi = f;
        }
      }

      // 确保每个患者都有 roi（回退策略）
      for (const key of Object.keys(patientMap)) {
        const p = patientMap[key];
        if (!p.roi && p.lung) {
          const patientFiles = foundNiiFiles.filter(f => {
            const rp = (f.webkitRelativePath || f.name).replace(/\\/g, '/');
            return rp.includes(p.patientId);
          });
          const altRoi = patientFiles.find(f => f !== p.lung);
          if (altRoi) p.roi = altRoi;
        }
      }

      // 转换为数组
      const patients = Object.values(patientMap);
      detectedPatients.value = patients;
      selectedPatientIndices.value = [];

      // 标签文件夹名称 → 标签映射 (输出0或1)
      const labelMap = {};
      const realFolders = [...labelFolderNames].filter(n => !n.startsWith('__'));
      if (realFolders.length === 2) {
        const sorted = realFolders.sort();
        labelMap[sorted[0]] = '0';
        labelMap[sorted[1]] = '1';
      } else {
        for (const name of realFolders) {
          const lower = name.toLowerCase();
          if (name === '0' || lower === 'malignant' || name.includes('恶')) {
            labelMap[name] = '0';
          } else if (name === '1' || lower === 'benign' || name.includes('良')) {
            labelMap[name] = '1';
          } else {
            labelMap[name] = name;
          }
        }
      }
      // 内部标记回退
      if (labelFolderNames.has('__nested__')) labelMap['__nested__'] = '未知';
      if (labelFolderNames.has('__single__')) labelMap['__single__'] = '未知';
      detectedLabelMap.value = labelMap;

      // 单患者: 自动填充
      if (patients.length === 1) {
        const p = patients[0];
        imageFile.value = p.lung;
        roiFile.value = p.roi;
        // 如果 patientId 是合成的（如 '1_patient'），只用 label 信息
        patientId.value = p.patientId.endsWith('_patient') ? '' : p.patientId;
        patientLabel.value = labelMap[p.label] || p.label;
        console.log('检测到单患者:', { patientId: p.patientId, labelFolder: p.label, mapped: patientLabel.value });
      } else if (patients.length > 1) {
        console.log('检测到多患者:', patients.length, patients.map(p => `${p.patientId}[${p.label}]`));
        imageFile.value = null;
        roiFile.value = null;
        patientId.value = '';
        patientLabel.value = '';
      }

      // 重置选择器
      showImageSelector.value = false;
      showRoiSelector.value = false;
      selectedImageIndex.value = '';
      selectedRoiIndex.value = '';

      console.log('NII文件列表:', foundNiiFiles.map(f => f.name));
      console.log('识别到的患者:', patients.map(p => `${p.patientId} [${p.label}]`));
    };

    // 选中某个患者
    const selectBatchPatient = (idx) => {
      selectedPatientIndex.value = idx;
    };

    // 使用选中的患者填充并提取特征
    const useSelectedPatient = async () => {
      const p = detectedPatients.value[selectedPatientIndex.value];
      if (!p) return;
      imageFile.value = p.lung;
      roiFile.value = p.roi;
      patientId.value = p.patientId;
      patientLabel.value = detectedLabelMap.value[p.label] || p.label;
      console.log('选中患者:', { patientId: p.patientId, label: patientLabel.value });
      await extractFeatures();
    };

    // 批量提取患者特征（优先使用勾选的患者，无勾选时提取全部）
    const batchExtractAllPatients = async () => {
      const allPatients = detectedPatients.value;
      if (allPatients.length === 0) return;

      const selectedIndices = selectedPatientIndices.value;
      const targets = selectedIndices.length > 0
        ? selectedIndices.map(i => allPatients[i])
        : allPatients;

      isExtracting.value = true;
      loading.value = true;
      loadingMessage.value = `正在批量提取 ${targets.length} 个患者的特征...`;
      error.value = null;

      try {
        const allResults = [];
        const allErrors = [];

        for (let i = 0; i < targets.length; i++) {
          const p = targets[i];
          if (!p.lung || !p.roi) {
            allErrors.push(`${p.patientId}: 缺少lung或ROI文件`);
            continue;
          }

          loadingMessage.value = `正在处理 ${i + 1}/${targets.length}: ${p.patientId}...`;

          const formData = new FormData();
          formData.append('image_file', p.lung);
          formData.append('roi_file', p.roi);
          formData.append('patient_id', p.patientId);
          formData.append('label', detectedLabelMap.value[p.label] || p.label);

          try {
            const response = await fetch(`${API_BASE}/extract-features/`, {
              method: 'POST',
              body: formData
            });

            if (response.ok) {
              const data = await response.json();
              allResults.push(data.features);
            } else {
              const errData = await response.json();
              allErrors.push(`${p.patientId}: ${errData.detail || '提取失败'}`);
            }
          } catch (e) {
            allErrors.push(`${p.patientId}: ${e.message}`);
          }
        }

        if (allResults.length > 0) {
          // 合并所有结果并导出CSV
          const allFeatureKeys = new Set();
          for (const r of allResults) {
            for (const k of Object.keys(r)) {
              if (k !== 'sample' && k !== 'label') allFeatureKeys.add(k);
            }
          }
          const featureKeys = [...allFeatureKeys];

          const csvHeaders = ['sample', 'label', ...featureKeys].map(quoteCsvValue).join(',');
          const csvRows = allResults.map(r => {
            const row = [String(r.sample || ''), String(r.label || '')];
            for (const k of featureKeys) {
              const v = r[k];
              row.push(typeof v === 'number' ? v.toFixed(6) : String(v ?? ''));
            }
            return row.map(quoteCsvValue).join(',');
          });

          const csvContent = [csvHeaders, ...csvRows].join('\n');
          const blob = new Blob(['﻿' + csvContent], { type: 'text/csv;charset=utf-8;' });
          const link = document.createElement('a');
          link.href = URL.createObjectURL(blob);
          const now = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
          link.download = `radiomics_batch_${allResults.length}patients_${now}.csv`;
          link.click();

          loadingMessage.value = `完成! 成功提取 ${allResults.length} 个患者，${allErrors.length} 个失败`;
        } else {
          loadingMessage.value = '所有患者提取均失败';
        }

        if (allErrors.length > 0) {
          console.error('批量提取错误:', allErrors);
        }
      } catch (err) {
        error.value = err.message;
        console.error('批量提取失败:', err);
      } finally {
        isExtracting.value = false;
        loading.value = false;
      }
    };

    // 获取可预览的文件列表
    const getPreviewableFiles = () => {
      if (niiFiles.value.length > 0) {
        return niiFiles.value;
      }
      const files = [];
      if (imageFile.value) files.push(imageFile.value);
      if (roiFile.value && (!imageFile.value || roiFile.value.name !== imageFile.value.name)) {
        files.push(roiFile.value);
      }
      return files;
    };

    // 预览选中的文件
    const previewSelectedFile = async () => {
      if (selectedPreviewFileIndex.value === '') {
        featurePreviewImage.value = null;
        return;
      }

      const files = getPreviewableFiles();
      const file = files[selectedPreviewFileIndex.value];
      if (!file) return;

      previewingFile.value = file;
      featurePreviewSessionId.value = null;
      await loadFeaturePreview(file);
    };

    // 加载影像预览
    const loadFeaturePreview = async (file, sliceIndex = -1) => {
      try {
        const formData = new FormData();

        if (featurePreviewSessionId.value && previewingFile.value === file) {
          formData.append('session_id', featurePreviewSessionId.value);
        } else if (file) {
          formData.append('nii_file', file);
        }

        const url = sliceIndex !== -1
          ? `${API_BASE}/preview-nii/?slice_index=${sliceIndex}`
          : `${API_BASE}/preview-nii/`;

        const response = await fetch(url, {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          if (featurePreviewSessionId.value && file) {
            featurePreviewSessionId.value = null;
            return await loadFeaturePreview(file, sliceIndex);
          }
          const errData = await response.json();
          throw new Error(errData.detail || '预览失败');
        }

        const result = await response.json();
        featurePreviewImage.value = result;
        featurePreviewSlice.value = result.slice_index;

        if (result.session_id) {
          featurePreviewSessionId.value = result.session_id;
        }
      } catch (err) {
        console.error('预览失败:', err);
        error.value = '预览失败: ' + err.message;
      }
    };

    // 更新预览切片
    const updatePreviewSlice = async () => {
      if (previewingFile.value) {
        await loadFeaturePreview(previewingFile.value, featurePreviewSlice.value);
      }
    };

    // 手动选择影像文件
    const selectImageFile = () => {
      if (selectedImageIndex.value !== '' && niiFiles.value[selectedImageIndex.value]) {
        imageFile.value = niiFiles.value[selectedImageIndex.value];
        showImageSelector.value = false;
        selectedImageIndex.value = '';
      }
    };

    // 手动选择ROI文件
    const selectRoiFile = () => {
      if (selectedRoiIndex.value !== '' && niiFiles.value[selectedRoiIndex.value]) {
        roiFile.value = niiFiles.value[selectedRoiIndex.value];
        showRoiSelector.value = false;
        selectedRoiIndex.value = '';
      }
    };

    const handleFileSelect = (event, type) => {
      const file = event.target.files[0];
      if (file) {
        if (type === 'image') {
          imageFile.value = file;
        } else {
          roiFile.value = file;
        }
        error.value = null;

        // 默认预览第一个上传的文件
        if (imageFile.value && !featurePreviewImage.value) {
          selectedPreviewFileIndex.value = '0';
          previewSelectedFile();
        }
      }
    };

    const handleFileDrop = (event, type) => {
      const file = event.dataTransfer.files[0];
      if (file && (file.name.endsWith('.nii') || file.name.endsWith('.nii.gz'))) {
        if (type === 'image') {
          imageFile.value = file;
        } else {
          roiFile.value = file;
        }
        error.value = null;

        // 默认预览第一个上传的文件
        if (imageFile.value && !featurePreviewImage.value) {
          selectedPreviewFileIndex.value = '0';
          previewSelectedFile();
        }
      }
    };

    const extractFeatures = async () => {
      if (!imageFile.value || !roiFile.value) return;

      isExtracting.value = true;
      loading.value = true;
      loadingMessage.value = '正在提取特征...';
      error.value = null;

      try {
        // 检查后端是否可用
        let useBackend = false;
        if (backendStatus.value?.status === 'success') {
          useBackend = true;
        } else {
          // 尝试连接后端
          try {
            const response = await fetch(`${API_BASE}/health`);
            if (response.ok) {
              const data = await response.json();
              backendStatus.value = {
                status: 'success',
                message: '后端服务连接正常',
                has_pyradiomics: data.has_pyradiomics
              };
              useBackend = true;
            }
          } catch {
            useBackend = false;
          }
        }

        if (useBackend) {
          // 使用后端API提取特征
          loadingMessage.value = '正在上传文件并提取特征...';

          const formData = new FormData();
          formData.append('image_file', imageFile.value);
          formData.append('roi_file', roiFile.value);
          if (patientId.value) formData.append('patient_id', patientId.value);
          if (patientLabel.value) formData.append('label', patientLabel.value);

          const response = await fetch(`${API_BASE}/extract-features/`, {
            method: 'POST',
            body: formData
          });

          if (response.ok) {
            features.value = await response.json();
          } else {
            const errData = await response.json();
            throw new Error(errData.detail || '特征提取失败');
          }
        } else {
          // 使用前端模拟数据
          loadingMessage.value = '使用模拟数据生成特征...';
          await new Promise(resolve => setTimeout(resolve, 1000));

          const mockFeatures = generateMockFeatures();
          features.value = {
            status: 'success',
            features: mockFeatures,
            feature_count: Object.keys(mockFeatures).filter(k => k !== 'sample' && k !== 'label').length,
            is_real: false,
            has_pyradiomics: false
          };
        }
      } catch (err) {
        error.value = err.message;
        console.error('特征提取失败:', err);
      } finally {
        isExtracting.value = false;
        loading.value = false;
      }
    };

    const getCategoryIcon = (category) => {
      const icons = {
        'shape': '📐',
        'firstorder': '📊',
        'glcm': '🔗',
        'glrlm': '📏',
        'glszm': '⬜',
        'gldm': '📈',
        'ngtdm': '🔄'
      };
      return icons[category] || '📝';
    };

    const resetWorkspace = () => {
      imageFile.value = null;
      roiFile.value = null;
      folderFiles.value = [];
      features.value = null;
      activeTab.value = 'shape';
      error.value = null;
      if (imageInput.value) imageInput.value.value = '';
      if (roiInput.value) roiInput.value.value = '';
      if (folderInput.value) folderInput.value.value = '';
    };

    // 数据集划分
    const handleSplitCsvSelect = (event) => {
      const file = event.target.files[0];
      if (file) {
        splitCsvFileName.value = file.name;
        splitCsvLoaded.value = true;
      }
    };

    const splitDataset = async () => {
      if (isSplitting.value) return;
      isSplitting.value = true;

      const inputElement = splitCsvFile.value;
      if (!inputElement || !inputElement.files || inputElement.files.length === 0) {
        error.value = '请先选择CSV文件';
        isSplitting.value = false;
        return;
      }
      const file = inputElement.files[0];

      try {
        const text = await file.text();
        const lines = text.trim().split('\n').filter(l => l.trim());
        const headers = parseCsvLine(lines[0]);
        const data = lines.slice(1).map(line => parseCsvLine(line)).filter(r => r.length === headers.length);

        for (let i = data.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [data[i], data[j]] = [data[j], data[i]];
        }

        const splitIdx = Math.floor(data.length * splitRatio.value);
        splitTrainData = [headers, ...data.slice(0, splitIdx)];
        splitTestData = [headers, ...data.slice(splitIdx)];

        splitResult.value = {
          total: data.length,
          train_count: splitTrainData.length - 1,
          test_count: splitTestData.length - 1
        };

        setTimeout(() => {
          downloadTrainSet();
          setTimeout(() => {
            downloadTestSet();
          }, 300);
        }, 500);

      } catch (err) {
        error.value = '划分失败: ' + err.message;
      } finally {
        isSplitting.value = false;
      }
    };

    const downloadTrainSet = () => {
      if (!splitTrainData) return;
      downloadCsv(splitTrainData, 'train_set.csv');
    };

    const downloadTestSet = () => {
      if (!splitTestData) return;
      downloadCsv(splitTestData, 'test_set.csv');
    };

    const downloadCsv = (data, filename) => {
      const csv = data.map(row => row.map(quoteCsvValue).join(',')).join('\n');
      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    // 归一化
    const handleNormCsvSelect = (event) => {
      const file = event.target.files[0];
      if (file) {
        normCsvFileName.value = file.name;
        normCsvLoaded.value = true;
      }
    };

    const normalizeCsv = async () => {
      if (isNormalizing.value) return;
      isNormalizing.value = true;

      const inputElement = normCsvFile.value;
      if (!inputElement || !inputElement.files || inputElement.files.length === 0) {
        error.value = '请先选择CSV文件';
        isNormalizing.value = false;
        return;
      }
      const file = inputElement.files[0];

      normProgressValue.value = 10;
      normProgressMessage.value = '读取数据...';

      try {
        const text = await file.text();
        const lines = text.trim().split('\n').filter(l => l.trim());

        const headers = parseCsvLine(lines[0]);
        const data = lines.slice(1).map(line => {
          const values = parseCsvLine(line);
          return headers.map((_, idx) => {
            const val = values[idx]?.trim();
            const valLower = val.toLowerCase();

            if (valLower === 'inf' || valLower === '+inf') {
              return Infinity;
            } else if (valLower === '-inf') {
              return -Infinity;
            }

            const num = parseFloat(val);
            return isNaN(num) ? val : num;
          });
        });

        normProgressValue.value = 30;
        normProgressMessage.value = '识别特征列...';

        const skipKeywords = ['patient_id', 'label', 'sample', 'simple', 'id', 'name', 'case_id'];
        const featureCols = [];
        for (let i = 0; i < headers.length; i++) {
          const headerLower = headers[i].toLowerCase().trim();
          const containsSkipWord = skipKeywords.some(keyword => headerLower.includes(keyword));
          if (containsSkipWord) {
            continue;
          }
          if (typeof data[0][i] === 'number') {
            featureCols.push(i);
          }
        }

        normProgressValue.value = 50;
        normProgressMessage.value = '归一化处理...';

        for (const colIdx of featureCols) {
          const colData = data.map(row => row[colIdx]).filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v));

          if (colData.length === 0) continue;

          const minVal = Math.min(...colData);
          const maxVal = Math.max(...colData);

          if (maxVal - minVal > 1e-8) {
            data.forEach(row => {
              const val = row[colIdx];
              if (typeof val === 'number' && !isNaN(val) && isFinite(val)) {
                const normalized = (val - minVal) / (maxVal - minVal);
                row[colIdx] = isFinite(normalized) ? normalized : 0.5;
              }
            });
          }
        }

        for (let i = 0; i < data.length; i++) {
          for (let j = 0; j < data[i].length; j++) {
            const val = data[i][j];
            if (typeof val === 'number') {
              if (!isFinite(val) || isNaN(val)) {
                data[i][j] = 0.5;
              }
            }
          }
        }

        normProgressValue.value = 80;
        normProgressMessage.value = '生成结果...';

        normResult.value = {
          rows: data.length,
          columns: headers.length,
          headers: headers,
          data: data
        };

        normProgressValue.value = 100;
        normProgressMessage.value = '归一化完成！';

        setTimeout(() => {
          normProgressValue.value = 0;
          normProgressMessage.value = '';
        }, 2000);

      } catch (err) {
        error.value = '归一化失败: ' + err.message;
        normProgressValue.value = 0;
        normProgressMessage.value = '';
      } finally {
        isNormalizing.value = false;
      }
    };

    const downloadNormalizedCsv = () => {
      if (!normResult.value) return;
      const data = [normResult.value.headers, ...normResult.value.data];
      downloadCsv(data, 'normalized_features.csv');
    };

    // SVM训练
    const handleSvmTrainFileSelect = (event) => {
      const file = event.target.files[0];
      if (file) {
        svmTrainFileName.value = file.name;
        svmTrainLoaded.value = true;
      }
    };

    const handleSvmTestFileSelect = (event) => {
      const file = event.target.files[0];
      if (file) {
        svmTestFileName.value = file.name;
        svmTestLoaded.value = true;
      } else {
        svmTestFileName.value = '';
        svmTestLoaded.value = false;
      }
    };

    const getMatrixColor = (value) => {
      const maxVal = Math.max(...svmResult.value.confusion_matrix.flat());
      const ratio = value / maxVal;
      if (ratio > 0.7) return '#4CAF50';
      if (ratio > 0.4) return '#FFC107';
      return '#F44336';
    };

    const getHeatmapColor = (value) => {
      const hue = 240 - (value * 240);
      return `hsla(${hue}, 70%, 60%, 0.8)`;
    };

    const formatPercent = (value) => {
      if (value === undefined || value === null || isNaN(value)) {
        return '0.00%';
      }
      return (value * 100).toFixed(2) + '%';
    };

    const formatAuc = (value) => {
      if (value === undefined || value === null || isNaN(value)) {
        return '0.0000';
      }
      return value.toFixed(4);
    };

    const drawRocCurve = () => {
      if (!rocCanvas.value || !svmResult.value?.roc_data) return;

      const canvas = rocCanvas.value;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const { fpr, tpr } = svmResult.value.roc_data;

      if (!fpr || !tpr || fpr.length === 0 || tpr.length === 0) {
        console.log('ROC data is empty');
        canvas.width = 400;
        canvas.height = 300;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#999';
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('无法绘制ROC曲线', canvas.width / 2, canvas.height / 2);
        ctx.textAlign = 'left';
        return;
      }

      canvas.width = 400;
      canvas.height = 300;

      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = '#e0e0e0';
      ctx.lineWidth = 1;
      for (let i = 0; i <= 10; i++) {
        const x = (i / 10) * canvas.width;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();

        const y = ((10 - i) / 10) * canvas.height;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      ctx.strokeStyle = '#cccccc';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(0, canvas.height);
      ctx.lineTo(canvas.width, 0);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.strokeStyle = '#667eea';
      ctx.lineWidth = 3;
      ctx.beginPath();
      for (let i = 0; i < fpr.length; i++) {
        const x = fpr[i] * canvas.width;
        const y = canvas.height - (tpr[i] * canvas.height);
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      ctx.fillStyle = '#667eea';
      ctx.beginPath();
      ctx.arc(fpr[fpr.length - 1] * canvas.width, canvas.height - (tpr[tpr.length - 1] * canvas.height), 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#333';
      ctx.font = '12px Arial';
      ctx.fillText('FPR', canvas.width / 2 - 20, canvas.height - 5);
      ctx.save();
      ctx.translate(10, canvas.height / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText('TPR', 0, 0);
      ctx.restore();

      ctx.fillStyle = '#667eea';
      ctx.font = 'bold 14px Arial';
      const auc = svmResult.value.auc || 0;
      ctx.fillText(`AUC = ${auc.toFixed(4)}`, canvas.width - 100, 25);
    };

    const trainSvm = async () => {
      const trainInput = svmTrainFile.value;
      if (!trainInput || !trainInput.files || trainInput.files.length === 0) {
        error.value = '请先选择训练CSV文件';
        return;
      }
      const trainFile = trainInput.files[0];

      isTrainingSvm.value = true;
      svmProgressValue.value = 0;
      svmProgressMessage.value = '准备训练...';

      try {
        const formData = new FormData();
        formData.append('train_csv', trainFile);

        const testInput = svmTestFile.value;
        if (testInput && testInput.files && testInput.files.length > 0) {
          formData.append('test_csv', testInput.files[0]);
        }

        svmProgressValue.value = 10;
        svmProgressMessage.value = '发送请求...';

        // 先发送训练请求
        const responsePromise = fetch(`${API_BASE}/train-svm/`, {
          method: 'POST',
          body: formData
        });

        // 同时模拟进度更新
        let currentProgress = 10;
        const progressSteps = [
          { value: 20, message: '读取数据...', delay: 300 },
          { value: 35, message: '处理标签...', delay: 400 },
          { value: 55, message: '训练模型...', delay: 600 },
          { value: 80, message: '评估指标...', delay: 400 },
          { value: 95, message: '生成报告...', delay: 300 },
        ];

        for (const step of progressSteps) {
          await new Promise(resolve => setTimeout(resolve, step.delay));
          svmProgressValue.value = step.value;
          svmProgressMessage.value = step.message;
        }

        // 等待训练完成
        const response = await responsePromise;

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || '训练失败');
        }

        const result = await response.json();
        svmProgressValue.value = 100;
        svmProgressMessage.value = '训练完成！';

        svmResult.value = result;

        // 等待DOM渲染完成后绘制ROC曲线
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              drawRocCurve();
            });
          });
        });

        setTimeout(() => {
          svmProgressValue.value = 0;
          svmProgressMessage.value = '';
          isTrainingSvm.value = false;
        }, 2000);

      } catch (err) {
        error.value = '训练失败: ' + err.message;
        svmProgressValue.value = 0;
        svmProgressMessage.value = '';
        isTrainingSvm.value = false;
      }
    };

    const downloadModel = async () => {
      try {
        const response = await fetch(`${API_BASE}/download-model/`);
        if (!response.ok) {
          let errorMsg = '下载失败';
          try {
            const errData = await response.json();
            if (errData.detail) {
              errorMsg = errData.detail;
            }
          } catch (e) {
            // 如果无法解析JSON，使用默认错误信息
          }
          throw new Error(errorMsg);
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'svm_model.pkl';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } catch (err) {
        error.value = '下载模型失败: ' + err.message;
      }
    };

    // ========== 病灶识别模块 ==========
    const modelFile = ref(null);
    const modelObj = ref(null);
    const modelFileName = ref('');
    const modelLoaded = ref(false);
    const niiImageFile = ref(null); // 这个是 ref 指向 input 元素
    const niiImageObj = ref(null); // 这个是保存选中的文件对象
    const niiImageFileName = ref('');
    const niiImageLoaded = ref(false);
    const isPredicting = ref(false);
    const predictProgress = ref(0);
    const predictProgressMessage = ref('');
    const predictResult = ref(null);
    const niiPreview = ref(null);
    const currentSlice = ref(0);
    const isLoadingPreview = ref(false);
    const niiSessionId = ref(null); // 用来缓存session id
    const imageContainerRef = ref(null);
    const niiImageRef = ref(null);
    const overlayWidth = ref(0);
    const overlayHeight = ref(0);

    // 病灶标记计算属性
    const lesionContourPath = computed(() => {
      const lesionPos = predictResult.value?.lesion_position;
      if (!lesionPos || !lesionPos.contour_points || lesionPos.contour_points.length === 0) return '';

      const originalWidth = lesionPos.original_width || 512;
      const originalHeight = lesionPos.original_height || 512;
      const displayWidth = niiPreview.value?.width || overlayWidth.value || 512;
      const displayHeight = niiPreview.value?.height || overlayHeight.value || 512;
      const scaleX = displayWidth / originalWidth;
      const scaleY = displayHeight / originalHeight;

      const points = lesionPos.contour_points[0];
      if (!points || points.length < 3) return '';

      const scaled = points.map(p => `${(p[0] * scaleX).toFixed(1)},${(p[1] * scaleY).toFixed(1)}`);
      return 'M ' + scaled.join(' L ') + ' Z';
    });

    const lesionBBox = computed(() => {
      const lesionPos = predictResult.value?.lesion_position;
      if (!lesionPos || !lesionPos.bounding_box) return null;

      const bb = lesionPos.bounding_box;
      const originalWidth = lesionPos.original_width || 512;
      const originalHeight = lesionPos.original_height || 512;
      const displayWidth = niiPreview.value?.width || overlayWidth.value || 512;
      const displayHeight = niiPreview.value?.height || overlayHeight.value || 512;
      const scaleX = displayWidth / originalWidth;
      const scaleY = displayHeight / originalHeight;

      return {
        x: bb.x_min * scaleX,
        y: bb.y_min * scaleY,
        width: (bb.x_max - bb.x_min) * scaleX,
        height: (bb.y_max - bb.y_min) * scaleY
      };
    });

    // 判断是否有病灶的计算属性
    const hasLesion = computed(() => {
      const lesionPos = predictResult.value?.lesion_position;
      if (!lesionPos) return false;
      if (lesionPos.found === false) return false;
      if (lesionPos.area_pixels !== undefined && lesionPos.area_pixels < 10) return false;
      return true;
    });

    // 图片加载完成后更新覆盖层尺寸
    const onImageLoad = () => {
      if (niiImageRef.value) {
        // 使用图片的实际显示尺寸
        overlayWidth.value = niiImageRef.value.clientWidth || niiImageRef.value.naturalWidth || 512;
        overlayHeight.value = niiImageRef.value.clientHeight || niiImageRef.value.naturalHeight || 512;

        console.log('onImageLoad called:');
        console.log('  overlayWidth:', overlayWidth.value);
        console.log('  overlayHeight:', overlayHeight.value);
      }
    };

    const handleModelSelect = (event) => {
      const file = event.target.files[0];
      if (file) {
        modelObj.value = file;
        modelFileName.value = file.name;
        modelLoaded.value = true;
      }
    };

    const handleNiiImageSelect = async (event) => {
      const file = event.target.files[0];
      if (file) {
        niiImageFileName.value = file.name;
        niiImageObj.value = file; // 保存文件对象
        niiImageLoaded.value = true;
        niiSessionId.value = null; // 清除旧的session
        niiPreview.value = null; // 清除旧预览

        // 上传后立即预览
        console.log('📤 开始加载NII预览:', file.name);
        await loadNiiPreview(file);
      }
    };

    const loadNiiPreview = async (file, sliceIndex = -1) => {
      isLoadingPreview.value = true;
      try {
        console.log('📤 加载预览:', { file: file?.name, sliceIndex, hasSession: !!niiSessionId.value });

        const formData = new FormData();

        // 简化逻辑：每次都优先重新上传文件，避免缓存问题
        if (file) {
          formData.append('nii_file', file);
          console.log('📂 上传文件预览');
        } else if (niiSessionId.value) {
          formData.append('session_id', niiSessionId.value);
          console.log('🚀 使用缓存预览');
        } else {
          console.error('❌ 没有文件也没有session_id');
          throw new Error('请先上传NII文件');
        }

        let url = `${API_BASE}/preview-nii/`;
        if (sliceIndex !== -1) {
          url += `?slice_index=${sliceIndex}`;
        }

        console.log('🔗 请求URL:', url);

        const response = await fetch(url, {
          method: 'POST',
          body: formData,
          headers: {
            'Accept': 'application/json'
          }
        });

        console.log('📊 响应状态:', response.status, response.statusText);

        if (!response.ok) {
          let errMessage = `请求失败: ${response.status}`;
          try {
            const errData = await response.json();
            errMessage = errData.detail || errMessage;
          } catch (e) {
            console.error('无法解析错误响应:', e);
          }
          throw new Error(errMessage);
        }

        const result = await response.json();
        console.log('📋 响应数据:', {
          status: result.status,
          hasImage: !!result.image,
          sliceIndex: result.slice_index,
          totalSlices: result.total_slices
        });

        if (result.status !== 'success') {
          throw new Error('服务返回失败');
        }

        niiPreview.value = result;
        currentSlice.value = result.slice_index;

        if (result.session_id) {
          niiSessionId.value = result.session_id;
        }

        console.log('✅ 预览加载成功');
      } catch (err) {
        console.error('❌ 预览加载失败:', err.message);
        error.value = '预览失败: ' + err.message;
        niiPreview.value = null;
      } finally {
        isLoadingPreview.value = false;
      }
    };

    const prevSlice = async () => {
      if (currentSlice.value > 0 && niiImageObj.value) {
        await loadNiiPreview(niiImageObj.value, currentSlice.value - 1);
      }
    };

    const nextSlice = async () => {
      if (niiPreview.value && currentSlice.value < niiPreview.value.total_slices - 1 && niiImageObj.value) {
        await loadNiiPreview(niiImageObj.value, currentSlice.value + 1);
      }
    };

    const onSliceInput = async (event) => {
      // 直接更新当前值
      const newSlice = parseInt(event.target.value);
      currentSlice.value = newSlice;

      // 简单直接地加载切片
      if (niiImageObj.value) {
        await loadNiiPreview(niiImageObj.value, newSlice);
      }
    };

    const predictLesion = async () => {
      if (!modelObj.value || !niiImageObj.value) {
        error.value = '请先选择模型和NII影像文件';
        return;
      }

      isPredicting.value = true;
      predictProgress.value = 10;
      predictProgressMessage.value = '准备数据...';
      predictResult.value = null;

      try {
        const formData = new FormData();
        formData.append('model_file', modelObj.value);
        formData.append('nii_file', niiImageObj.value);

        predictProgress.value = 30;
        predictProgressMessage.value = '发送请求...';

        const response = await fetch(`${API_BASE}/predict-lesion/`, {
          method: 'POST',
          body: formData
        });

        predictProgress.value = 70;
        predictProgressMessage.value = '处理结果...';

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || '预测失败');
        }
        const result = await response.json();
        predictResult.value = result;

        predictProgress.value = 100;
        predictProgressMessage.value = '识别完成！';

        setTimeout(() => {
          predictProgress.value = 0;
          predictProgressMessage.value = '';
          isPredicting.value = false;
        }, 2000);

      } catch (err) {
        error.value = '识别失败: ' + err.message;
        predictProgress.value = 0;
        predictProgressMessage.value = '';
        isPredicting.value = false;
      }
    };

    onMounted(() => {
      // 初始化时检测后端状态
      checkBackend();
    });

    // 清理临时文件的函数
    const cleanupTempFiles = async () => {
      try {
        console.log('🧹 正在清理临时文件...');
        const response = await fetch(`${API_BASE}/cleanup-temp/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        if (response.ok) {
          const result = await response.json();
          console.log('✅ 清理完成:', result);
        }
      } catch (err) {
        console.warn('⚠️  清理请求失败（可能网络问题）:', err);
      }
    };

    // 页面关闭/刷新时清理
    const handleBeforeUnload = (e) => {
      // 尝试发送清理请求（使用 sendBeacon 提高成功率）
      if (navigator.sendBeacon) {
        navigator.sendBeacon(`${API_BASE}/cleanup-temp/`);
      } else {
        // 降级方案：使用同步 XMLHttpRequest
        cleanupTempFiles();
      }
    };

    onMounted(() => {
      // 添加页面关闭/刷新事件监听
      window.addEventListener('beforeunload', handleBeforeUnload);
      window.addEventListener('unload', handleBeforeUnload);
    });

    onUnmounted(() => {
      // 组件卸载时也清理
      cleanupTempFiles();
      // 移除事件监听
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleBeforeUnload);
    });

    return {
      imageInput,
      roiInput,
      folderInput,
      uploadMode,
      folderFiles,
      niiFiles,
      patientId,
      patientLabel,
      detectedPatients,
      detectedLabelMap,
      selectedPatientIndex,
      selectedPatientIndices,
      activeNavSection,
      scrollTo,
      allPatientsSelected,
      toggleSelectAllPatients,
      togglePatientSelect,
      selectBatchPatient,
      useSelectedPatient,
      batchExtractAllPatients,
      imageFile,
      roiFile,
      features,
      isExtracting,
      loading,
      loadingMessage,
      error,
      backendStatus,
      isChecking,
      // 特征提取模块的影像预览
      featurePreviewImage,
      featurePreviewSlice,
      selectedPreviewFileIndex,
      getPreviewableFiles,
      previewSelectedFile,
      updatePreviewSlice,
      showNiiFileList,
      showImageSelector,
      showRoiSelector,
      selectedImageIndex,
      selectedRoiIndex,
      featureCategories,
      checkBackend,
      handleFolderSelect,
      handleFolderDrop,
      handleFileSelect,
      handleFileDrop,
      extractFeatures,
      selectImageFile,
      selectRoiFile,
      getCategoryIcon,
      resetWorkspace,
      // 数据集划分
      splitCsvFile,
      splitCsvFileName,
      splitCsvLoaded,
      splitRatio,
      splitResult,
      handleSplitCsvSelect,
      splitDataset,
      downloadTrainSet,
      downloadTestSet,
      // 归一化
      normCsvFile,
      normCsvFileName,
      normCsvLoaded,
      normResult,
      normProgressValue,
      normProgressMessage,
      handleNormCsvSelect,
      normalizeCsv,
      downloadNormalizedCsv,
      // SVM训练
      svmTrainFile,
      svmTrainFileName,
      svmTrainLoaded,
      svmTestFile,
      svmTestFileName,
      svmTestLoaded,
      svmResult,
      svmProgressValue,
      svmProgressMessage,
      isTrainingSvm,
      handleSvmTrainFileSelect,
      handleSvmTestFileSelect,
      trainSvm,
      downloadModel,
      getMatrixColor,
      getHeatmapColor,
      formatPercent,
      formatAuc,
      // 病灶识别
      modelFile,
      modelObj,
      modelFileName,
      modelLoaded,
      niiImageFile,
      niiImageObj,
      niiImageFileName,
      niiImageLoaded,
      isPredicting,
      predictProgress,
      predictProgressMessage,
      predictResult,
      niiPreview,
      currentSlice,
      isLoadingPreview,
      niiSessionId,
      imageContainerRef,
      niiImageRef,
      overlayWidth,
      overlayHeight,
      lesionContourPath,
      lesionBBox,
      hasLesion,
      onImageLoad,
      handleModelSelect,
      handleNiiImageSelect,
      loadNiiPreview,
      prevSlice,
      nextSlice,
      onSliceInput,
      predictLesion
    };
  }
};
</script>

<style scoped>
.ml-workspace {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  min-height: 100vh;
  background: #f0f2f5;
  background-image:
    radial-gradient(ellipse at 20% 50%, rgba(102, 126, 234, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(118, 75, 162, 0.04) 0%, transparent 50%);
  padding: 20px;
}

.header {
  background: white;
  border-radius: 16px;
  padding: 20px 30px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.header h1 {
  margin: 0;
  color: #333;
  font-size: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn-reset {
  background: #6c757d;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-reset:hover {
  background: #5a6268;
}

.btn-check {
  background: #17a2b8;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-check:hover:not(:disabled) {
  background: #138496;
}

.btn-check:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 顶部导航栏 */
.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: 14px;
  padding: 4px;
  margin-bottom: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(102, 126, 234, 0.1);
}

.nav-inner {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 11px;
  text-decoration: none;
  color: #555;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.25s ease;
  white-space: nowrap;
}

.nav-link:hover {
  background: rgba(102, 126, 234, 0.08);
  color: #667eea;
}

.nav-link.active {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.nav-icon {
  font-size: 15px;
}

@media (max-width: 768px) {
  .nav-text {
    display: none;
  }

  .nav-link {
    padding: 10px 12px;
  }
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

/* 统一卡片样式 */
.nii-upload-section,
.feature-info-section,
.csv-section,
.svm-section,
.predict-section {
  background: linear-gradient(145deg, #ffffff 0%, #fafbfc 100%);
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), 0 1px 4px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(102, 126, 234, 0.08);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  scroll-margin-top: 90px;
  animation: sectionEnter 0.5s ease-out backwards;
}

.nii-upload-section:hover,
.feature-info-section:hover,
.csv-section:hover,
.svm-section:hover,
.predict-section:hover {
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.1), 0 2px 8px rgba(0, 0, 0, 0.06);
  border-color: rgba(102, 126, 234, 0.2);
}

/* 统一区块标题样式 */
.nii-upload-section h2,
.feature-info-section h2,
.csv-section h2,
.svm-section h2,
.predict-section h2 {
  margin: 0 0 28px 0;
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  padding-bottom: 14px;
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
}

.nii-upload-section h2::after,
.feature-info-section h2::after,
.csv-section h2::after,
.svm-section h2::after,
.predict-section h2::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 60px;
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(90deg, #667eea, #764ba2);
}

@keyframes sectionEnter {
  from {
    opacity: 0;
    transform: translateY(24px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

h2 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 18px;
  border-bottom: 2px solid #667eea;
  padding-bottom: 10px;
}

h3 {
  margin: 15px 0 10px 0;
  color: #444;
  font-size: 15px;
}

/* 上传模式切换 */
.upload-mode-switch {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.mode-btn {
  flex: 1;
  padding: 12px 20px;
  border: 2px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.mode-btn:hover {
  border-color: #667eea;
}

.mode-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: #667eea;
}

/* 文件夹上传区域 */
.folder-upload {
  margin-bottom: 10px;
}

.folder-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  position: relative;
  transition: all 0.3s;
}

.folder-area:hover {
  border-color: #667eea;
  background: #f0f4ff;
}

.folder-area.has-files {
  border-color: #28a745;
  background: #f0fff0;
}

.folder-area input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

/* 文件检测结果 */
.file-detection {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
  margin-top: 15px;
}

.detected-files {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detected-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detected-label {
  font-weight: 500;
  color: #666;
}

.detected-value {
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 13px;
}

.detected-value.success {
  background: #d4edda;
  color: #155724;
}

.detected-value.warning {
  background: #fff3cd;
  color: #856404;
}

.detected-value-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-select-file {
  background: #667eea;
  color: white;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-select-file:hover {
  background: #764ba2;
}

/* 特征提取模块影像预览 */
.feature-preview-section {
  margin-top: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
}

.feature-preview-section h3 {
  margin: 0 0 15px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.preview-controls {
  margin-bottom: 15px;
}

.file-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.file-select:hover {
  border-color: #667eea;
}

.file-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.preview-display {
  background: white;
  border-radius: 10px;
  padding: 15px;
  margin-bottom: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image-container {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-nii-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: 6px;
  image-rendering: pixelated;
}

.preview-placeholder {
  color: #999;
  font-size: 14px;
}

.preview-slider-controls {
  padding: 10px 0;
}

.preview-slider-container {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

/* 通用滑块样式 */
.slice-slider {
  -webkit-appearance: none;
  appearance: none;
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, #667eea, #764ba2);
  outline: none;
  opacity: 0.85;
  transition: opacity 0.2s;
  cursor: pointer;
}

.slice-slider:hover {
  opacity: 1;
}

.slice-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
  border: 3px solid #667eea;
  transition: all 0.2s ease;
}

.slice-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6);
}

.slice-slider::-moz-range-thumb {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
  border: 3px solid #667eea;
  transition: all 0.2s ease;
}

.slice-slider::-moz-range-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6);
}

.slice-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
}

.slice-info {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  min-width: 100px;
  text-align: right;
  white-space: nowrap;
}

.file-selector {
  margin-top: 10px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
}

.file-selector select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.nii-files-list {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed #ddd;
}

.nii-files-list h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #666;
}

.nii-files-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nii-files-list li {
  padding: 6px 10px;
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: 13px;
  color: #555;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nii-files-list li:hover {
  background: #f0f4ff;
}

.file-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.file-tag.image-tag {
  background: #d4edda;
  color: #155724;
}

.file-tag.roi-tag {
  background: #cce5ff;
  color: #004085;
}

.upload-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-box {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 25px;
  text-align: center;
  cursor: pointer;
  position: relative;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #667eea;
  background: #f0f4ff;
}

.upload-area.has-file {
  border-color: #28a745;
  background: #f0fff0;
}

.upload-area input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.upload-icon {
  font-size: 36px;
}

.upload-hint p {
  margin: 10px 0 5px 0;
  color: #666;
  font-size: 14px;
}

.upload-formats {
  font-size: 12px;
  color: #999;
}

/* 后端状态 */
.backend-status {
  padding: 12px 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.backend-status.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.backend-status.warning {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeeba;
}

.status-icon {
  font-weight: bold;
}

.pyradiomics-badge {
  background: #28a745;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: auto;
}

.btn-extract {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 15px 30px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  margin-top: 20px;
  width: 100%;
  font-weight: 600;
}

.btn-extract:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-extract:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.note-box {
  background: #fff3cd;
  border: 1px solid #ffeeba;
  border-radius: 8px;
  padding: 12px;
  margin-top: 15px;
  font-size: 13px;
  color: #856404;
}

.note-box strong {
  color: #856404;
}

.summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 40px;
  border-radius: 10px;
  text-align: center;
}

.summary-label {
  display: block;
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 5px;
}

.summary-value {
  font-size: 32px;
  font-weight: bold;
}

.btn-download {
  background: #28a745;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  flex: 1;
}

.btn-download:hover {
  background: #218838;
}

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.info-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.info-card h4 {
  margin: 0 0 10px 0;
  color: #667eea;
  font-size: 14px;
}

.info-card p {
  margin: 0;
  font-size: 12px;
  color: #666;
  line-height: 1.5;
}

.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-overlay p {
  color: white;
  margin-top: 15px;
  font-size: 16px;
}

.error-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #dc3545;
  color: white;
  padding: 15px 25px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 1001;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.close-error {
  background: none;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
}

/* CSV/SVM 内部组件样式 */
.csv-upload-area,
.svm-upload {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.csv-input {
  display: none;
}

.csv-upload-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.csv-upload-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.csv-file-name {
  font-size: 14px;
  color: #555;
  background: #f8f9fa;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px dashed #ddd;
}

.split-controls,
.norm-controls,
.svm-controls {
  margin-top: 20px;
}

.split-slider {
  margin-bottom: 20px;
  padding: 20px;
  background: linear-gradient(145deg, #f8f9fa, #ffffff);
  border-radius: 12px;
  border: 1px solid #e9ecef;
}

.split-slider label {
  display: block;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #444;
}

.ratio-slider {
  width: 100%;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(90deg, #e0e0e0, #f5f5f5);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}

.ratio-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.4);
  transition: all 0.2s ease;
}

.ratio-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.5);
}

.btn-process {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 14px 32px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.btn-process:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.btn-train {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3);
}

.btn-train:hover:not(:disabled) {
  box-shadow: 0 8px 25px rgba(240, 147, 251, 0.4);
}

.btn-process:disabled {
  background: linear-gradient(135deg, #ccc, #ddd);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* SVM 指标卡片网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.metric-card {
  background: linear-gradient(145deg, #f8f9fa, #ffffff);
  border-radius: 12px;
  padding: 18px 16px;
  text-align: center;
  border: 1px solid #e9ecef;
  transition: all 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.12);
  border-color: rgba(102, 126, 234, 0.3);
}

.metric-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.metric-label {
  font-size: 12px;
  color: #888;
  font-weight: 500;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

/* 混淆矩阵 */
.confusion-matrix {
  margin-top: 20px;
}

.confusion-matrix h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.matrix-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
}

.matrix-row {
  display: flex;
  gap: 4px;
}

.matrix-cell {
  width: 80px;
  height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  border-radius: 8px;
  color: white;
}
.cell-label {
  font-size: 10px;
  font-weight: 500;
  opacity: 0.8;
  margin-top: 2px;
}

.matrix-cell.tp {
  background: linear-gradient(135deg, #43e97b, #38f9d7);
  color: #1a1a2e;
}

.matrix-cell.fp {
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

.matrix-cell.fn {
  background: linear-gradient(135deg, #fa709a, #fee140);
  color: #1a1a2e;
}

.matrix-cell.tn {
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  color: #1a1a2e;
}

.matrix-labels {
  display: flex;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: #888;
  margin-top: 8px;
}

.matrix-labels span {
  background: #f0f0f0;
  padding: 4px 10px;
  border-radius: 4px;
}

/* ROC 曲线 */
.roc-chart {
  margin-top: 20px;
}

.roc-chart h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.chart-container {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  justify-content: center;
}

/* 特征重要性热力图 */
.feature-heatmap {
  margin-top: 20px;
}

.feature-heatmap h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.heatmap-container {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.heatmap-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.heatmap-label {
  width: 100px;
  font-size: 11px;
  color: #666;
  text-align: right;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.heatmap-bar {
  height: 20px;
  border-radius: 4px;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.4s ease;
  min-width: 4px;
}

.heatmap-value {
  width: 40px;
  font-size: 11px;
  font-weight: 600;
  color: #333;
  flex-shrink: 0;
}

/* 基本信息与模型下载 */
.basic-info {
  margin-top: 20px;
  padding: 16px;
  background: linear-gradient(145deg, #f8f9fa, #ffffff);
  border-radius: 12px;
  border: 1px solid #e9ecef;
}

.model-download {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.progress-container {
  margin-top: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
}

.progress-bar-wrapper {
  height: 12px;
  background: #e9ecef;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
  border-radius: 6px;
  transition: width 0.5s ease;
  position: relative;
  overflow: hidden;
}

.progress-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg,
      transparent,
      rgba(255, 255, 255, 0.3),
      transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(100%);
  }
}

.progress-text {
  display: block;
  margin-top: 12px;
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.split-result,
.norm-result,
.svm-result {
  margin-top: 24px;
  padding: 24px;
  background: linear-gradient(145deg, #f8f9fa, #ffffff);
  border-radius: 16px;
  border: 1px solid #e9ecef;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.split-result h3,
.norm-result h3,
.svm-result h3 {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}

.result-summary .summary-card {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.result-summary .summary-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.result-stats {
  display: flex;
  gap: 32px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
}

.stat-item {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stat-label {
  font-weight: 600;
  color: #666;
  font-size: 14px;
}

.stat-value {
  color: #667eea;
  font-weight: 700;
  font-size: 18px;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.result-actions .btn-download {
  flex: 1;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
  border: none;
  padding: 14px 24px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
}

.result-actions .btn-download:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(17, 153, 142, 0.4);
}

@media (max-width: 900px) {
  .main-content {
    max-width: 100%;
    gap: 16px;
    padding: 0 8px;
  }

  .nii-upload-section,
  .feature-info-section,
  .csv-section,
  .svm-section,
  .predict-section {
    padding: 20px;
  }

  .header {
    flex-direction: column;
    gap: 12px;
    text-align: center;
  }

  .header h1 {
    font-size: 20px;
  }

  .result-summary {
    flex-direction: column;
  }

  .top-nav {
    overflow-x: auto;
  }

  .nav-inner {
    flex-wrap: nowrap;
  }
}

@media (max-width: 768px) {
  .predict-content {
    flex-direction: column;
  }

  .predict-left,
  .predict-right {
    width: 100%;
  }
}

/* 病灶识别模块内部组件样式 */
.predict-upload {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.upload-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pkl-input,
.nii-input {
  display: none;
}

.predict-upload-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.predict-upload-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.predict-controls {
  margin-top: 10px;
}

.predict-content {
  display: flex;
  gap: 24px;
}

.predict-left {
  flex: 1;
  min-width: 0;
}

.predict-right {
  flex: 1;
  min-width: 0;
}

.nii-preview {
  background: #f8f9fa;
  border-radius: 16px;
  padding: 20px;
  height: fit-content;
  position: sticky;
  top: 20px;
}

.nii-preview h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
}

.image-container {
  background: white;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nii-image {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 8px;
  image-rendering: pixelated;
}

.image-placeholder {
  background: white;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-size: 14px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.slice-controls {
  display: flex;
  align-items: center;
  justify-content: center;
}

.slice-slider-container {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 8px 0;
}

.slice-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
}

.slice-slider {
  -webkit-appearance: none;
  appearance: none;
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, #667eea, #764ba2);
  outline: none;
  opacity: 0.85;
  transition: opacity 0.2s;
  cursor: pointer;
}

.slice-slider:hover {
  opacity: 1;
}

.slice-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
  border: 3px solid #667eea;
  transition: all 0.2s ease;
}

.slice-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6);
}

.slice-slider::-moz-range-thumb {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
  border: 3px solid #667eea;
  transition: all 0.2s ease;
}

.slice-slider::-moz-range-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6);
}

.slice-info {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  min-width: 100px;
  text-align: right;
  white-space: nowrap;
}

/* 病灶标记样式 */
.image-wrapper {
  position: relative;
  display: inline-block;
  width: 100%;
  overflow: hidden;
  border-radius: 8px;
}

.image-wrapper.has-lesion {
  border: 2px solid rgba(255, 68, 68, 0.3);
}

.lesion-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 10;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.7;
  }
}

/* 结果状态样式 */
.result-status {
  margin-bottom: 20px;
}

.no-lesion-message {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border: 2px solid #81c784;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.no-lesion-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 10px;
}

.no-lesion-message h4 {
  margin: 0 0 8px 0;
  color: #2e7d32;
  font-size: 18px;
}

.no-lesion-message p {
  margin: 0;
  color: #388e3c;
  font-size: 14px;
}

.has-lesion-message {
  background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
  border: 2px solid #ef5350;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.has-lesion-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 10px;
}

.has-lesion-message h4 {
  margin: 0;
  color: #c62828;
  font-size: 18px;
}

/* 无病灶覆盖层 */
.no-lesion-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(76, 175, 80, 0.15);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  pointer-events: none;
  z-index: 10;
  border-radius: 8px;
}

.no-lesion-overlay .check-icon {
  font-size: 48px;
  color: #4caf50;
  animation: checkPop 0.5s ease-out;
}

.no-lesion-overlay span:last-child {
  font-size: 16px;
  font-weight: 600;
  color: #2e7d32;
  background: rgba(255, 255, 255, 0.9);
  padding: 6px 16px;
  border-radius: 20px;
}

@keyframes checkPop {
  0% {
    transform: scale(0.5);
    opacity: 0;
  }

  50% {
    transform: scale(1.2);
  }

  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.predict-result {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 2px solid #e0e0e0;
}

.predict-result h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
}

.result-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.result-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.result-card:hover {
  transform: translateY(-3px);
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.result-icon {
  font-size: 32px;
}

.result-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.result-value {
  font-size: 20px;
  font-weight: bold;
  color: #667eea;
}

.lesion-position,
.feature-summary {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.lesion-position h4,
.feature-summary h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.position-info p {
  margin: 8px 0;
  font-size: 14px;
  color: #555;
}

.position-info strong {
  color: #333;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  transition: all 0.2s ease;
}

.summary-item:hover {
  border-color: #667eea;
  background: #f0f4ff;
}

.summary-key {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.summary-value {
  font-size: 14px;
  font-weight: bold;
  color: #667eea;
}

/* 加载状态样式 */
.image-placeholder.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.loading-spinner-small {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.patient-info-row {
  display: flex;
  gap: 16px;
  margin: 12px 0;
}

.patient-input-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.patient-input-group label {
  font-size: 13px;
  font-weight: 600;
  color: #8892b0;
}

.patient-input {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: #e6f1ff;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.patient-input:focus {
  border-color: #64ffda;
}

.detected-patients-section {
  margin: 16px 0;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
}

.detected-patients-section h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #64ffda;
}

.patients-table-wrapper {
  max-height: 300px;
  overflow-y: auto;
  margin: 8px 0;
}

.patients-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.patients-table th {
  text-align: left;
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #8892b0;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.patients-table td {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #ccd6f6;
}

.patients-table .selected-row {
  background: rgba(100, 255, 218, 0.08);
}

.patients-table .selected-row td {
  color: #64ffda;
}

.patients-table .file-ok {
  color: #64ffda;
}

.patients-table .file-missing {
  color: #ff6b6b;
}

.patient-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}
</style>
