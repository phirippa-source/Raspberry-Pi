import os
import joblib
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)

# =========================================================
# 사용자 설정
# =========================================================
INPUT_CSV = "./dataset/processed/gestures_wide.csv"
MODEL_OUT = "./dataset/processed/knn_gesture_model.joblib"

TEST_SIZE = 0.30
RANDOM_STATE = 42
N_NEIGHBORS = 5   # 3 또는 5부터 시작 추천

# =========================================================
# CSV 읽기
# =========================================================
df = pd.read_csv(INPUT_CSV)

if "sample_id" not in df.columns or "label" not in df.columns:
    raise ValueError("gestures_wide.csv 에 sample_id, label 컬럼이 있어야 합니다.")

feature_cols = [c for c in df.columns if c not in ["sample_id", "label"]]

X = df[feature_cols].astype(float)
y = df["label"].astype(str)

print("전체 샘플 수 =", len(df))
print("입력 차원   =", X.shape[1])
print("\n클래스별 샘플 수")
print(y.value_counts())

# =========================================================
# train / test 분할
# =========================================================
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y
    )
except ValueError:
    print("\n[경고] 클래스별 샘플 수가 적어서 stratify를 적용하지 못했습니다.")
    print("일반 random split으로 진행합니다.\n")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE
    )

print("학습 샘플 수 =", len(X_train))
print("테스트 샘플 수 =", len(X_test))

# =========================================================
# 모델 구성
# =========================================================
model = Pipeline([
    ("scaler", StandardScaler()),
    ("knn", KNeighborsClassifier(n_neighbors=N_NEIGHBORS))
])

# =========================================================
# 학습
# =========================================================
model.fit(X_train, y_train)

# =========================================================
# 예측 및 평가
# =========================================================
y_pred = model.predict(X_test)

acc = accuracy_score(y_test, y_pred)
print("\n테스트 정확도 =", round(acc, 4))

print("\n[Classification Report]")
print(classification_report(y_test, y_pred))

labels_sorted = sorted(y.unique())
cm = confusion_matrix(y_test, y_pred, labels=labels_sorted)

print("[Confusion Matrix]")
print(pd.DataFrame(cm, index=labels_sorted, columns=labels_sorted))

disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels_sorted)
disp.plot(cmap="Blues", values_format="d")
plt.title(f"kNN Gesture Classification (k={N_NEIGHBORS})")
plt.tight_layout()
plt.show()

# =========================================================
# 모델 저장
# =========================================================
os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)

joblib.dump(
    {
        "model": model,
        "feature_columns": feature_cols,
        "class_labels": labels_sorted,
        "n_neighbors": N_NEIGHBORS
    },
    MODEL_OUT
)

print("\n모델 저장 완료:", MODEL_OUT)
