# SPGA-backend
このプロジェクトはRaspberry Pi上で動作する土壌湿度を取得し植物に適切な水やりの通知を行うことができます。

## Getting started
pythonのライブラリ管理には[uv](https://docs.astral.sh/uv/)を使っています。
公式ページに沿ってuvのインストールを行い、以下のコマンドを入力します。
```bash
uv sync
```
このコマンドを実行することでライブラリをインストールします。

また、SSL通信を行うためにngrokを用いています。

## usage
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
ngrok http 8000
```

ngrokのURLが変わるのでLINE DevelopersのWebhook URLを変更する。
