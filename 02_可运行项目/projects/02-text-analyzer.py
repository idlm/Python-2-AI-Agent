"""模块 2：文本分析工具最小实现。支持 Python 3.11+。"""


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def count_words(text: str) -> int:
    normalized = normalize_text(text)
    return 0 if not normalized else len(normalized.split(" "))


def analyze_text(text: str) -> dict[str, int]:
    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")
    return {"characters": len(text), "words": count_words(text), "lines": len(text.splitlines()) or 1}


def format_report(text: str) -> str:
    report = analyze_text(text)
    return f"字符数：{report['characters']}；词数：{report['words']}；行数：{report['lines']}"


if __name__ == "__main__":
    user_text = input("请输入要分析的文本：")
    print(format_report(user_text))
