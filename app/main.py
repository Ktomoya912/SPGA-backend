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
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import ImageMessageContent, MessageEvent

from app.ai import predict_minimal

load_dotenv()
SAVE_DIR = "images"
os.makedirs(SAVE_DIR, exist_ok=True)
app = FastAPI()

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
# 画像保存用ディレクトリ作成


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
    reply_text = f"受け取ったメッセージ: {text}"

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
    message_id = event.message.id
    response = line_bot_api_blob.get_message_content(message_id)

    line_bot_api.reply_message_with_http_info(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(
                    text="画像を受け取りました。現在画像の処理を行っています..."
                )
            ],
        )
    )

    result = predict_minimal(response)
    line_bot_api.push_message_with_http_info(
        push_message_request=PushMessageRequest(
            to=event.source.user_id,
            messages=[TextMessage(text=f"予測結果: (ID: {result})")],
        )
    )


if __name__ == "__main__":
    pass
