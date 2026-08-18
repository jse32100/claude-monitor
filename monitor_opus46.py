import os
import requests

from common import get_band, load_previous_band, save_band, send_discord, describe_transition

MODEL = "claude-opus-4.6"
API_URL = "https://rs.igx.kr/api/statistics"
THRESHOLD = 40
STATE_PATH = "state_opus46.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_OPUS46")

TPS_BEST, TPS_NORMAL, TPS_WORST = 33.0, 17.5, 10.0
LAT_BEST, LAT_NORMAL, LAT_WORST = 2000, 3500, 7000


def map_val(v, i_min, i_max, o_min, o_max):
    return (v - i_min) * (o_max - o_min) / (i_max - i_min) + o_min


def calc_score(tps, latency):
    if tps is None or latency is None:
        return 0
    if latency <= LAT_BEST:
        l_score = 50
    elif latency <= LAT_NORMAL:
        l_score = map_val(latency, LAT_BEST, LAT_NORMAL, 50, 30)
    elif latency <= LAT_WORST:
        l_score = map_val(latency, LAT_NORMAL, LAT_WORST, 30, 0)
    else:
        l_score = 0
    if tps >= TPS_BEST:
        t_score = 50
    elif tps >= TPS_NORMAL:
        t_score = map_val(tps, TPS_NORMAL, TPS_BEST, 30, 50)
    elif tps >= TPS_WORST:
        t_score = map_val(tps, TPS_WORST, TPS_NORMAL, 10, 30)
    else:
        t_score = map_val(tps, 0, TPS_WORST, 0, 10)
    total = l_score + t_score
    if latency > LAT_WORST or tps < TPS_WORST:
        return int(min(40, total))
    return int(min(100, max(0, total)))


def get_current_score():
    res = requests.get(API_URL, timeout=10)
    res.raise_for_status()
    data = res.json()

    model_data = data.get(MODEL, [])
    if not model_data:
        raise ValueError(f"{MODEL} 데이터 없음")

    valid = [
        e for e in model_data
        if not e.get("failure") and e.get("tps") is not None and e.get("latency") is not None
    ]
    if not valid:
        raise ValueError("유효한 데이터 없음")

    latest = sorted(valid, key=lambda e: e["time"])[-1]
    tps = latest["tps"]
    latency = latest["latency"]
    score = calc_score(tps, latency)
    return score, tps, latency, latest["time"]


def main():
    print(f"모니터링 시작: {MODEL}")
    score, tps, latency, time_str = get_current_score()
    print(f"현재 점수: {score}점 (TPS: {tps:.1f}, Latency: {latency:.0f}ms) - {time_str}")

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
            print("⚠️ DISCORD_WEBHOOK_OPUS46 이 설정되어 있지 않습니다.")
    else:
        print(f"구간 변화 없음 (구간: {new_band}) → 알림 없음")

    save_band(STATE_PATH, new_band, score)


if __name__ == "__main__":
    main()
