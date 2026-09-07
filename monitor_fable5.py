import os
import requests

from common import get_band, load_previous_band, save_band, send_discord, describe_transition

MODEL_ID = "fable5"
MODEL_LABEL = "Claude Fable 5"
API_URL = "https://claude-radiosonde.chyoyam.chatgpt.site/api/v1/status"
THRESHOLD = 80
STATE_PATH = "state_fable5.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_FABLE5")


def get_current_score():
    res = requests.get(API_URL, timeout=10)
    res.raise_for_status()
    data = res.json()

    models = data.get("models", [])
    target = next((m for m in models if m.get("id") == MODEL_ID), None)
    if target is None:
        raise ValueError(f"{MODEL_ID} 데이터 없음")

    score = target["experience_score"]["value"]
    tps = target["metrics"]["tps"]
    ttft_ms = target["metrics"]["ttft_ms"]
    measured_at = target.get("measured_at")
    return score, tps, ttft_ms, measured_at


def main():
    print(f"모니터링 시작: {MODEL_LABEL}")
    score, tps, ttft_ms, measured_at = get_current_score()
    print(f"현재 점수: {score}점 (TPS: {tps:.1f}, TTFT: {ttft_ms:.0f}ms) - {measured_at}")

    prev_band = load_previous_band(STATE_PATH)
    new_band = get_band(score, THRESHOLD)
    emoji, headline = describe_transition(prev_band, new_band, THRESHOLD)

    if emoji:
        message = (
            f"{emoji} **{MODEL_LABEL}** {headline}\n\n"
            f"📊 현재 점수: **{score}점** (구간: {new_band})\n"
            f"⚡ 속도: {tps:.1f} T/s\n"
            f"⏱ 첫 응답 시간: {ttft_ms / 1000:.2f}초\n\n"
            f"확인하기: https://claude-radiosonde.chyoyam.chatgpt.site"
        )
        if DISCORD_WEBHOOK_URL:
            send_discord(DISCORD_WEBHOOK_URL, message)
        else:
            print("⚠️ DISCORD_WEBHOOK_FABLE5 이 설정되어 있지 않습니다.")
    else:
        print(f"구간 변화 없음 (구간: {new_band}) → 알림 없음")

    save_band(STATE_PATH, new_band, score)


if __name__ == "__main__":
    main()
