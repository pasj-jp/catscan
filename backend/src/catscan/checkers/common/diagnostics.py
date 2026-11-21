import re

_JAPANESE = re.compile(r"[\u3040-\u30ff\u4e00-\u9faf]")


def localized_message(message: str) -> dict[str, str]:
    japanese, separator, english = message.partition(" / ")
    if separator and _JAPANESE.search(japanese):
        return {"message": english.strip(), "message_ja": japanese.strip()}
    return {"message": message.strip()}
