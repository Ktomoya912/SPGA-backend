import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import ImageMessageContent, MessageEvent
from sqlmodel import Session, select

from app import db, models
from app.ai import predict_minimal


def register(db: Session, plant_id: int, device_id: int = None):
    registed = db.exec(
        select(models.Registed).where(
            models.Registed.plant_id == plant_id,
            models.Registed.device_id == device_id if device_id else None,
        )
    ).first()
    if registed is None:
        new_registed = models.Registed(plant_id=plant_id, device_id=device_id)
        db.add(new_registed)
        db.commit()
        return True
    else:
        return False


class RequestState:
    def __init__(self):
        self.start_registing = False
        self.predict_result = None

    def parse_message(self, message: str):
        with Session(db.engine) as session:
            if "登録" in message:
                return self.start_regist()
            elif self.predict_result:
                return self.regist_plant(message, session)

    def start_regist(self):
        if not self.start_registing:
            self.start_registing = True
            return {"error": False, "text": "画像を送信してください。"}
        else:
            return {
                "error": True,
                "text": "すでに登録を開始しています。画像を送信してください。",
            }

    def regist_plant(self, message: str, db: Session):
        if "はい" in message or "yes" == message.lower():
            self.start_registing = False
            # ここで予測結果を登録する処理を実行
            if not register(db, self.predict_result):
                self.predict_result = None
                return {
                    "error": True,
                    "text": "登録に失敗しました。もう一度送信してください。",
                }
            self.predict_result = None
            return {
                "error": False,
                "text": "登録が完了しました。",
            }
        elif "いいえ" in message or "no" == message.lower():
            self.start_registing = False
            self.predict_result = None
            return {
                "error": False,
                "text": "登録をキャンセルしました。",
            }
        else:
            return {
                "error": True,
                "text": "登録の確認ができませんでした。もう一度送信してください。",
            }


async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    yield


load_dotenv()
app = FastAPI(lifespan=lifespan)

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
rs = RequestState()


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
    text = event.message.text
    reply_text = rs.parse_message(text)

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
        message_id = event.message.id
        content = line_bot_api_blob.get_message_content(message_id)

        result = predict_minimal(content)
        db_plant = session.exec(
            select(models.Plant).where(models.Plant.id == int(result))
        ).first()
        if db_plant is None:
            reply_msg = "予測結果の植物がデータベースに存在しません。"
        else:
            rs.predict_result = db_plant.id
            reply_msg = f"予測結果: {db_plant.name_jp}\n登録する場合は「はい」と送信してください。登録しない場合は「いいえ」と送信してください。"

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_msg)],
            )
        )
    # line_bot_api.push_message_with_http_info(
    #     push_message_request=PushMessageRequest(
    #         to=event.source.user_id,
    #         messages=[TextMessage(text=f"予測結果: (ID: {result})")],
    #     )
    # )
