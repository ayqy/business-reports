from pypdf import PdfReader


def extract(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


if __name__ == "__main__":
    for pdf in ["/tmp/37-2024-audit.pdf", "/tmp/37-2024-report.pdf", "/tmp/37-2023-report.pdf"]:
        print(f"FILE: {pdf}")
        text = extract(pdf)
        for keyword in [
            "网页游戏",
            "移动游戏",
            "互联网流量费用",
            "AI",
            "小游戏",
            "营业收入",
        ]:
            pos = text.find(keyword)
            if pos != -1:
                print(f"\nKEYWORD: {keyword}")
                print(text[max(0, pos - 300):pos + 1500])
        print("\n" + "=" * 80 + "\n")
