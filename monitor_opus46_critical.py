import os

from common import load_previous_band, save_band, send_discord
from igx_api import fetch_model_state

MODEL = "claude-opus-4.6"
CRITICAL = 30
STATE_PATH = "state_opus46_critical.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_OPUS46_CRITICAL")


def get_crit_band(score):
    """30점 기준 밴드. 30점 이상은 "normal" 하나로 취급하고,
    30점 미만은 10점 단위로 나눈다 (crit-20-29, crit-10-19, crit-0-9)."""
    if score >= CRITICAL:
        return "normal"
    bucket_start = (score // 10) * 10
    return f"crit-{bucket_start}-{bucket_start + 9}"


def crit_rank(band):
    """crit 밴드끼리 상대적인 높낮이를 비교하기 위한 값. 낮을수록 더 심각함."""
    return int(band.split("-")[1])


def describe_transition(prev_band, new_band):
    """비대칭 알림 로직:
    - normal -> crit : 하락 알림
    - crit -> normal : 회복 알림 (1회)
    - crit -> 더 낮은 crit : 추가 하락 알림
    - crit -> 더 높은 crit (여전히 30점 밑) : 알림 없음 (상태만 갱신)
    """
    if prev_band is None or prev_band == new_band:
        return None, None

    if prev_band == "normal" and new_band != "normal":
        return "🚨", f"{CRITICAL}점 이하로 떨어졌습니다"
    if prev_band != "normal" and new_band == "normal":
        return "✅", f"{CRITICAL}점 이상으로 회복했습니다"

    if crit_rank(new_band) < crit_rank(prev_band):
        return "📉", "위험 구간에서 점수가 추가로 하락했습니다"

    return None, None


def main():
    print(f"위험 구간 모니터링 시작: {MODEL} (기준 {CRITICAL}점)")
    score, tps, latency, measured_at, status = fetch_model_state(MODEL)
    print(f"현재 점수: {score}점 (TPS: {tps:.1f}, Latency: {latency:.0f}ms, {status}) - {measured_at}")

    prev_band = load_previous_band(STATE_PATH)
    new_band = get_crit_band(score)
    emoji, headline = describe_transition(prev_band, new_band)

    if emoji:
        message = (
            f"{emoji} **{MODEL}** {headline}\n\n"
            f"📊 현재 점수: **{score}점**\n"
            f"⚡ 속도: {tps:.1f} T/s\n"
            f"⏱ 응답 시간: {latency / 1000:.2f}초\n\n"
            f"확인하기: https://rs.igx.kr"
        )
        if DISCORD_WEBHOOK_URL:
            send_discord(DISCORD_WEBHOOK_URL, message)
        else:
            print("⚠️ DISCORD_WEBHOOK_OPUS46_CRITICAL 이 설정되어 있지 않습니다.")
    else:
        print(f"알림 없음 (밴드: {new_band})")

    save_band(STATE_PATH, new_band, score)


if __name__ == "__main__":
    main()
