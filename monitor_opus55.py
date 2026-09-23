import os

from common import get_band, load_previous_band, save_band, send_discord, describe_transition
from igx_api import fetch_model_state

MODEL = "claude-opus-5.5"
THRESHOLD = 80
STATE_PATH = "state_opus55.json"
DISCORD_WEBHOOK_URL = os.environ.get("OPUS55_ALARM")


def main():
    print(f"모니터링 시작: {MODEL}")
    score, tps, latency, measured_at, status = fetch_model_state(MODEL)
    print(f"현재 점수: {score}점 (TPS: {tps:.1f}, Latency: {latency:.0f}ms, {status}) - {measured_at}")

    prev_band = load_previous_band(STATE_PATH)
    new_band = get_band(score, THRESHOLD)
    emoji, headline = describe_transition(prev_band, new_band, THRESHOLD)

    if emoji:
        message = (
            f"{emoji} **{MODEL}** {headline}\n\n"
            f"📊 현재 점수: **{score}점** (구간: {new_band})\n"
            f"⚡ 속도: {tps:.1f} T/s\n"
            f"⏱ 응답 시간: {latency / 1000:.2f}초\n\n"
            f"확인하기: https://rs.igx.kr"
        )
        if DISCORD_WEBHOOK_URL:
            send_discord(DISCORD_WEBHOOK_URL, message)
        else:
            print("⚠️ OPUS55_ALARM 이 설정되어 있지 않습니다.")
    else:
        print(f"구간 변화 없음 (구간: {new_band}) → 알림 없음")

    save_band(STATE_PATH, new_band, score)


if __name__ == "__main__":
    main()
