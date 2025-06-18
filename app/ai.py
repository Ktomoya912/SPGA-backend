import argparse
import json
import traceback
from io import BytesIO
from logging import getLogger
from pathlib import Path

import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

from app.config import set_logger
from app.utils import get_model

set_logger()
logger = getLogger(__name__)

MODEL_WEIGHTS_FILE = Path(__file__).parent.parent / "xp1_weights_best_acc.tar"
CLASS_NAMES_JSON_FILE = (
    Path(__file__).parent.parent / "plantnet300K_species_id_2_name.json"
)
MODEL_ARCHITECTURE = "resnet18"
NUM_CLASSES = 1081
IMAGE_INPUT_SIZE = 256
IMAGE_CROP_SIZE = 224
MODEL_INIT_PRETRAINED_FLAG = True
PREPROCESSING_USE_IMAGENET_NORM = True

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if not MODEL_WEIGHTS_FILE.exists():
    logger.error(
        f"モデルの重みファイルが見つかりません: {MODEL_WEIGHTS_FILE}. "
        "このファイルは、モデルの学習済み重みを含む必要があります。"
    )
    raise FileNotFoundError(MODEL_WEIGHTS_FILE)
if not CLASS_NAMES_JSON_FILE.exists():
    logger.error(
        f"クラス名のJSONファイルが見つかりません: {CLASS_NAMES_JSON_FILE}. "
        "このファイルは、モデルのクラスIDと名前をマッピングするために必要です。"
    )
    raise FileNotFoundError(CLASS_NAMES_JSON_FILE)

with open(CLASS_NAMES_JSON_FILE, "r", encoding="utf-8") as f:
    id_to_name_map: dict = json.load(f)

class_ids = list(id_to_name_map.keys())

args_for_get_model = argparse.Namespace(
    model=MODEL_ARCHITECTURE, pretrained=MODEL_INIT_PRETRAINED_FLAG
)

try:
    model = get_model(args_for_get_model, n_classes=NUM_CLASSES)
    logger.info(
        f"モデル '{MODEL_ARCHITECTURE}' を {NUM_CLASSES} クラスで初期化しました。"
    )
except Exception as e:
    logger.error(f"モデルの初期化中にエラー (get_model): {e}")
    logger.error(traceback.format_exc())

model.to(device)
model.eval()

try:
    checkpoint = torch.load(MODEL_WEIGHTS_FILE, map_location=device)
    state_dict_to_load = None
    if (
        isinstance(checkpoint, dict)
        and "model" in checkpoint
        and isinstance(checkpoint["model"], dict)
    ):
        state_dict_to_load = checkpoint["model"]
    elif isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict_to_load = checkpoint["model_state_dict"]
    elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        state_dict_to_load = checkpoint["state_dict"]
    elif isinstance(checkpoint, dict) and not any(
        key in ["epoch", "optimizer", "lr_scheduler", "model"]
        for key in checkpoint.keys()
    ):
        state_dict_to_load = checkpoint
    elif not isinstance(checkpoint, dict):
        state_dict_to_load = checkpoint

    if state_dict_to_load is None:
        logger.error("チェックポイントの構造が予期したものではありません。")
        logger.error(
            f"チェックポイントのトップレベルキー: {list(checkpoint.keys()) if isinstance(checkpoint, dict) else 'N/A'}"
        )

    incompatible_keys = model.load_state_dict(state_dict_to_load, strict=False)
    if not incompatible_keys.missing_keys and not incompatible_keys.unexpected_keys:
        logger.info(f"モデルの重みを '{MODEL_WEIGHTS_FILE}' から正常にロードしました。")
    else:
        logger.info(
            f"モデルの重みを '{MODEL_WEIGHTS_FILE}' からロードしました。一部互換性のないキーがありました:"
        )
        if incompatible_keys.missing_keys:
            logger.info(
                f"モデルに存在するがチェックポイントにないキー: {incompatible_keys.missing_keys}"
            )
        if incompatible_keys.unexpected_keys:
            logger.info(
                f"チェックポイントに存在するがモデルにないキー (無視されました): {incompatible_keys.unexpected_keys}"
            )
except Exception as e:
    logger.error(f"モデル重みのロード中にエラーが発生しました: {e}")
    logger.error(traceback.format_exc())

logger.info(f"デバイス '{device}' を使用します。")

if PREPROCESSING_USE_IMAGENET_NORM:
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    )
else:
    logger.warning(
        "ImageNet標準でない正規化を使用します。学習時のパラメータと一致しているか確認してください。"
    )
    normalize = transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])

preprocess = transforms.Compose(
    [
        transforms.Resize(IMAGE_INPUT_SIZE),
        transforms.CenterCrop(IMAGE_CROP_SIZE),
        transforms.ToTensor(),
        normalize,
    ]
)


def predict_minimal(
    image_binary: bytes = None,
):
    """
    指定された設定と重みファイルで単一画像を予測する最小限の関数。
    クラスIDとクラス名表示に対応。
    """

    # 画像の読み込み部分を修正
    try:
        img = Image.open(BytesIO(image_binary)).convert("RGB")
    except Exception as e:
        logger.error(f"画像 の読み込み中にエラー: {e}")
        return

    img_tensor = preprocess(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(img_tensor)
        probabilities = F.softmax(outputs, dim=1)
        confidence, predicted_idx_tensor = torch.max(probabilities, 1)

    predicted_class_index = predicted_idx_tensor.item()
    prediction_confidence = confidence.item()

    logger.info(f"--- 予測結果 ({NUM_CLASSES} クラス中) ---")
    logger.info(
        f"予測されたクラスインデックス: {predicted_class_index} (0 から {NUM_CLASSES - 1} の範囲)"
    )

    # ★★★ IDとクラス名表示の追加 ★★★
    predicted_id_str = "N/A"

    if class_ids and 0 <= predicted_class_index < len(class_ids):
        predicted_id_str = class_ids[predicted_class_index]

    if predicted_id_str != "N/A":
        logger.info(
            f"ID: {predicted_id_str} Name: {id_to_name_map.get(predicted_id_str)}"
        )

    logger.info(f"確信度 (Softmax確率): {prediction_confidence:.4f}")
    return predicted_id_str
