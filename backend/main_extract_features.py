# ------------------------------------------------------------------------------
# 提取特征接口
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
