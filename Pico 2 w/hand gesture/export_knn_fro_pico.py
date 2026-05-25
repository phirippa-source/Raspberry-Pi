import os
import joblib
import numpy as np

# =========================================================
# 사용자 설정
# =========================================================
MODEL_PATH = "./dataset/processed/knn_gesture_model.joblib"
PICO_OUT_DIR = "./pico_export"
PICO_MODEL_FILE = os.path.join(PICO_OUT_DIR, "knn_model_data.py")

# 소수점 자리수
# 너무 크게 잡으면 Pico에 올릴 파일이 커집니다.
FLOAT_DECIMALS = 6


# =========================================================
# Python 코드 파일에 넣기 좋은 형태로 리스트 변환
# =========================================================
def format_float(v):
    return f"{float(v):.{FLOAT_DECIMALS}f}"


def format_1d_float_list(values, indent=""):
    items = [format_float(v) for v in values]
    return "[" + ", ".join(items) + "]"


def format_2d_float_list(matrix, indent="    "):
    lines = ["["]
    for row in matrix:
        row_text = format_1d_float_list(row)
        lines.append(indent + row_text + ",")
    lines.append("]")
    return "\n".join(lines)


def format_str_list(values):
    items = [repr(str(v)) for v in values]
    return "[" + ", ".join(items) + "]"


# =========================================================
# 모델 로드
# =========================================================
saved = joblib.load(MODEL_PATH)

model = saved["model"]
feature_columns = saved["feature_columns"]
class_labels = saved["class_labels"]
n_neighbors = saved["n_neighbors"]

print("모델 로드 완료")
print("클래스 목록 =", class_labels)
print("입력 feature 수 =", len(feature_columns))
print("k =", n_neighbors)

# =========================================================
# Pipeline 내부 객체 꺼내기
# =========================================================
scaler = model.named_steps["scaler"]
knn = model.named_steps["knn"]

# StandardScaler 정보
mean = scaler.mean_
scale = scaler.scale_

# kNN이 실제로 기억하고 있는 학습 데이터
# 주의: Pipeline 구조이므로 knn._fit_X는 이미 scaler를 통과한 데이터입니다.
train_x_scaled = knn._fit_X

# kNN 내부 label
# scikit-learn KNeighborsClassifier는 label을 내부적으로 숫자로 인코딩할 수 있습니다.
knn_classes = list(knn.classes_)
raw_y = knn._y

train_y = []
for y in raw_y:
    # y가 숫자 인덱스이면 classes_를 이용해 원래 label로 복원
    if isinstance(y, (int, np.integer)):
        train_y.append(str(knn_classes[int(y)]))
    else:
        # 혹시 문자열 그대로 들어있는 경우
        train_y.append(str(y))

feature_count = len(feature_columns)
train_count = len(train_x_scaled)

print("Scaler mean 개수 =", len(mean))
print("Scaler scale 개수 =", len(scale))
print("kNN 학습 샘플 수 =", train_count)
print("kNN 학습 샘플 feature 수 =", train_x_scaled.shape[1])

if len(mean) != feature_count:
    raise ValueError("mean 개수와 feature 개수가 맞지 않습니다.")

if len(scale) != feature_count:
    raise ValueError("scale 개수와 feature 개수가 맞지 않습니다.")

if train_x_scaled.shape[1] != feature_count:
    raise ValueError("kNN 학습 샘플의 feature 수가 맞지 않습니다.")

if len(train_y) != train_count:
    raise ValueError("학습 샘플 수와 label 수가 맞지 않습니다.")

# =========================================================
# Pico용 Python 파일 생성
# =========================================================
os.makedirs(PICO_OUT_DIR, exist_ok=True)

with open(PICO_MODEL_FILE, "w", encoding="utf-8") as f:
    f.write("# Auto-generated file for MicroPython kNN inference\n")
    f.write("# Do not edit manually unless you know what you are doing.\n\n")

    f.write(f"K = {int(n_neighbors)}\n")
    f.write(f"FEATURE_COUNT = {int(feature_count)}\n")
    f.write(f"TRAIN_COUNT = {int(train_count)}\n")
    f.write("CHANNEL_ORDER = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']\n\n")

    f.write("CLASS_LABELS = ")
    f.write(format_str_list(class_labels))
    f.write("\n\n")

    f.write("# StandardScaler mean values\n")
    f.write("MEAN = ")
    f.write(format_1d_float_list(mean))
    f.write("\n\n")

    f.write("# StandardScaler scale values\n")
    f.write("SCALE = ")
    f.write(format_1d_float_list(scale))
    f.write("\n\n")

    f.write("# kNN training samples after StandardScaler transform\n")
    f.write("TRAIN_X = ")
    f.write(format_2d_float_list(train_x_scaled))
    f.write("\n\n")

    f.write("# Labels for TRAIN_X\n")
    f.write("TRAIN_Y = ")
    f.write(format_str_list(train_y))
    f.write("\n")

print()
print("Pico용 모델 데이터 파일 생성 완료:")
print(PICO_MODEL_FILE)
