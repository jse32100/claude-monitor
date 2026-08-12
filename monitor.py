import requests
import json
import os
import re

MODEL = "claude-opus-4.6"
BADGE_URL = f"https://rs.igx.kr/badge/{MODEL}"

KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN")

TPS_BEST   = 33.0
TPS_NORMAL = 17.5
TPS_WORST  = 10.0
LAT_BEST   = 2000
LAT_NORMAL = 3500
LAT_WORST  = 7000


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


def fetch_score_from_badge():
    res = requests.get(BADGE_URL, timeout=10)
    if res.status_code != 200:
        raise ValueError(f"뱃지 요청 실패: {res.status_code}")
    svg = res.text
    latency_match = re.search(r'대기\s*([\d.]+)초', svg)
    tps_match = re.search(r'([\d.]+)토큰/초', svg)
    if not latency_match or not tps_match:
        raise ValueError(f"파싱 실패. SVG 내용: {svg[:200]}")
    latency_ms = float(latency_match.group(1)) * 1000
    tps = float(tps_match.group(1))
    return tps, latency_ms


def refresh_access_token():
    """리프레시 토큰으로 새 액세스 토큰 발급"""
    res = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_API_KEY,
            "client_secret": KAKAO_CLIENT_SECRET,
            "refresh_token": KAKAO_REFRESH_TOKEN,
        },
        timeout=10
    )
    if res.status_code != 200:
        raise ValueError(f"토큰 갱신 실패: {res.status_code} {res.text}")

    data = res.json()
    access_token = data["access_token"]
    new_refresh_token = data.get("refresh_token")  # 갱신되면 같이 옴 (없을 수도 있음)

    if new_refresh_token:
        print("⚠️ 새 리프레시 토큰 발급됨! GitHub Secret KAKAO_REFRESH_TOKEN 업데이트 필요:")
        print(new_refresh_token)

    return access_token


def send_kakao(access_token, message):
    template = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": "https://rs.igx.kr",
            "mobile_web_url": "https://rs.igx.kr"
        }
    }
    res = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)}
    )
    print(f"카카오 응답: {res.status_code} {res.text}")
    return res.status_code == 200


def get_label(score):
    if score >= 70:
        return "🔥", "70점 이상"
    elif score >= 65:
        return "✅", "65점 이상"
    elif score >= 60:
        return "📊", "60점 이상"
    else:
        return None, None


def main():
    print(f"모니터링 시작: {MODEL}")
    tps, latency = fetch_score_from_badge()
    score = calc_score(tps, latency)
    print(f"현재 점수: {score}점 (TPS: {tps:.1f}, Latency: {latency:.0f}ms)")

    emoji, label = get_label(score)

    if emoji:
        access_token = refresh_access_token()
        message = (
            f"{emoji} {MODEL} 성능 알림\n\n"
            f"📊 현재 점수: {score}점 ({label})\n"
            f"⚡ 속도: {tps:.1f} T/s\n"
            f"⏱ 응답 시간: {latency / 1000:.2f}초\n\n"
            f"확인하기: https://rs.igx.kr"
        )
        send_kakao(access_token, message)
    else:
        print(f"60점 미만 → 알림 없음")


if __name__ == "__main__":
    main()
