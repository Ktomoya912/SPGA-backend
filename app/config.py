from logging import DEBUG, StreamHandler, basicConfig, getLogger, handlers


def set_logger():
    basicConfig(
        level=DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            StreamHandler(),
            handlers.RotatingFileHandler(
                "app.log",
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            ),
        ],
    )


logger = getLogger(__name__)
