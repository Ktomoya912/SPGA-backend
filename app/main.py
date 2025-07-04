import os
import sys
from logging import getLogger

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    ImageMessage,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import ImageMessageContent, MessageEvent
from sqlmodel import Session, select

from app import db, models
from app.ai import predict_minimal
from app.crud.utils import get_create_user, plant_regist


async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    yield


load_dotenv()
app = FastAPI(lifespan=lifespan)
logger = getLogger("uvicorn.error")
channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
line_bot_api_blob = MessagingApiBlob(api_client)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(channel_secret)


@app.post("/callback")
async def handle_callback(request: Request):
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = await request.body()
    body = body.decode("utf-8")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"


@handler.add(MessageEvent)
def handle_message(event: MessageEvent):
    # テキストメッセージを受け取ったときの処理
    # rs = req_dict.get(event.source.user_id, RequestState())
    text: str = event.message.text
    with Session(db.engine) as session:
        user = get_create_user(session, event.source.user_id)
        if "登録" in text:
            reply_text = "登録を開始します。画像を送信してください。"
        elif "一覧" in text:
            # 登録済みの植物一覧を取得
            registed_plants = session.exec(
                select(models.Registed).where(models.Registed.user_id == user.id)
            ).all()
            if not registed_plants:
                reply_text = "登録済みの植物はありません。"
            else:
                reply_text = "登録済みの植物一覧:\n"
                for registed in registed_plants:
                    plant = session.exec(
                        select(models.Plant).where(models.Plant.id == registed.plant_id)
                    ).first()
                    reply_text += f"- {plant.name_jp} (ID: {plant.id})\n"
        elif user.current_predict:
            if "はい" in text or "yes" == text.lower():
                if not plant_regist(session, user.current_predict, user.id):
                    reply_text = "すでに登録済みの植物です。"
                else:
                    reply_text = "登録が完了しました。"
            elif "いいえ" in text or "no" == text.lower():
                reply_text = "登録をキャンセルしました。"
            else:
                reply_text = (
                    "登録の確認ができませんでした。もう一度写真を送信してください。"
                )
            user.current_predict = None
            session.commit()
        else:
            reply_text = (
                "画像を送信してください。植物の予測を行います。\n"
                "または「一覧」と送信すると、登録済みの植物一覧を表示します。"
            )

    # LINEに返信
    line_bot_api.reply_message_with_http_info(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply_text)],
        )
    )


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    # 画像を保存
    with Session(db.engine) as session:
        user = get_create_user(session, event.source.user_id)
        message_id = event.message.id
        content = line_bot_api_blob.get_message_content(message_id)

        result, prediction_confidence = predict_minimal(content)
        db_plant = session.exec(
            select(models.Plant).where(models.Plant.id == int(result))
        ).first()
        if prediction_confidence < 0.85:
            reply_msg = (
                f"予測結果の植物の確信度が低いため、再度画像を送信してください。\n"
                f"確信度: {prediction_confidence:.2f}"
            )
            messages = [
                TextMessage(text=reply_msg),
            ]
        elif db_plant is None:
            all_plant = session.exec(select(models.Plant)).all()
            logger.warning(
                f"予測結果の植物ID {result} がデータベースに存在しません。登録されている植物: {[plant.id for plant in all_plant]}"
            )
            reply_msg = "予測結果の植物がデータベースに存在しません。"
            messages = [
                TextMessage(text=reply_msg),
            ]
        else:
            user.current_predict = db_plant.id
            session.add(user)
            session.commit()
            reply_msg = f"予測結果: {db_plant.name_jp}\n登録する場合は「はい」と送信してください。登録しない場合は「いいえ」と送信してください。"
            messages = [
                TextMessage(text=reply_msg),
                ImageMessage(
                    previewImageUrl=db_plant.previewImageUrl,
                    originalContentUrl=db_plant.originalContentUrl,
                ),
            ]

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages,
            )
        )
    # line_bot_api.push_message_with_http_info(
    #     push_message_request=PushMessageRequest(
    #         to=event.source.user_id,
    #         messages=[TextMessage(text=f"予測結果: (ID: {result})")],
    #     )
    # )
