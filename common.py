import json
import os
import requests


def get_band(score, threshold):
    """점수에 대한 구간 라벨을 반환한다.

    - score < threshold  -> "below" (하나의 구간, 세분화하지 않음)
    - score >= threshold -> 5점 단위 구간 (예: 60-64, 65-69, ... 95-99, "100")
    """
    if score < threshold:
        return "below"
    if score >= 100:
        return "100"
    bucket_start = (score // 5) * 5
    return f"{bucket_start}-{bucket_start + 4}"


def load_previous_band(state_path):
    """직전 실행에서 저장한 구간 라벨을 읽어온다. 파일이 없으면 None (최초 실행)."""
    if not os.path.exists(state_path):
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("band")
    except (json.JSONDecodeError, OSError):
        return None


def save_band(state_path, band, score):
    """이번 실행의 구간/점수를 파일에 저장한다. (워크플로가 이 파일을 git commit)"""
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"band": band, "score": score}, f, ensure_ascii=False, indent=2)


def send_discord(webhook_url, content):
    res = requests.post(webhook_url, json={"content": content}, timeout=10)
    ok = res.status_code in (200, 204)
    print(f"디스코드 응답: {res.status_code}")
    if not ok:
        print(res.text)
    return ok


def describe_transition(prev_band, new_band, threshold):
    """구간 전환 상황을 설명하는 (emoji, headline)을 반환한다.
    알림이 필요 없으면 (None, None)을 반환한다.
    """
    if prev_band is None:
        # 최초 실행: 비교 대상이 없으므로 알림 없이 상태만 저장
        return None, None
    if prev_band == new_band:
        return None, None

    was_below = prev_band == "below"
    now_below = new_band == "below"

    if was_below and not now_below:
        return "✅", f"{threshold}점 이상으로 회복했습니다"
    if not was_below and now_below:
        return "🔻", f"{threshold}점 아래로 떨어졌습니다"

    # 양쪽 다 임계값 이상인데 5점 구간이 바뀐 경우
    try:
        prev_start = int(prev_band.split("-")[0]) if "-" in prev_band else int(prev_band)
        new_start = int(new_band.split("-")[0]) if "-" in new_band else int(new_band)
    except ValueError:
        return None, None

    if new_start > prev_start:
        return "📈", "점수 구간이 상승했습니다"
    return "📉", "점수 구간이 하락했습니다"
