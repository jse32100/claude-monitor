"""IGX Radiosonde V2 API 공통 조회 모듈.

/api/v2/simple/{model} 이 status/latency/tps/score 를 모두 계산해서 주므로
클라이언트에서 점수를 따로 계산하지 않는다.
"""
import requests

API_BASE = "https://rs.igx.kr/api/v2/simple/"


def fetch_model_state(model):
    """모델의 최신 상태를 반환한다.

    returns: (score, tps, latency_ms, measured_at, status)
    """
    res = requests.get(API_BASE + model, timeout=10)
    res.raise_for_status()
    payload = res.json()

    if not payload.get("success"):
        raise ValueError(f"{model} 조회 실패: {payload.get('message')}")

    data = payload["data"]
    score = data["score"]
    tps = data["tps"]
    latency = data["latency"]
    measured_at = data.get("measuredAt")
    status = data.get("status")

    if score is None or tps is None or latency is None:
        raise ValueError(f"{model} 유효한 데이터 없음")

    return int(round(score)), float(tps), float(latency), measured_at, status
