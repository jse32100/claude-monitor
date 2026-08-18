# Claude Score Monitor (Discord 버전)

## 파일 구성
```
.github/workflows/monitor_opus46.yml   # opus4.6용 워크플로
.github/workflows/monitor_opus5.yml    # opus5용 워크플로
common.py                              # 공통 로직 (구간 계산, 상태 저장, 디스코드 전송)
monitor_opus46.py                      # rs.igx.kr / claude-opus-4.6, 임계값 60점
monitor_opus5.py                       # claude-radiosonde / opus5, 임계값 80점
```
실행되면 각 스크립트가 `state_opus46.json`, `state_opus5.json`을 저장하고,
워크플로가 이 파일을 레포에 커밋해서 다음 실행 때 "직전 구간"으로 사용합니다.
(최초 1회 실행 시에는 비교 대상이 없어 알림 없이 상태만 저장됩니다.)

## 1. 기존 카카오 관련 정리
- 기존 `monitor.py`, 기존 `monitor.yml` (카카오용)은 삭제하거나 두 파일로 교체하세요.
- 기존 Secrets(`KAKAO_REST_API_KEY`, `KAKAO_CLIENT_SECRET`, `KAKAO_REFRESH_TOKEN`)는 더 이상 필요 없으니 삭제해도 됩니다.

## 2. 디스코드 웹훅 만들기
채널 설정 → 연동(Integrations) → 웹후크(Webhooks) → 새 웹후크 만들기 → URL 복사.
(opus4.6용, opus5용 채널 2개에 각각 하나씩 만드세요)

## 3. GitHub Secrets 등록
레포 Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 |
|---|---|
| `DISCORD_WEBHOOK_OPUS46` | opus4.6 채널 웹훅 URL |
| `DISCORD_WEBHOOK_OPUS5` | opus5 채널 웹훅 URL |

## 4. cron-job.org 설정 (기존 것 대신 2개로)
기존에 `monitor.yml`을 1분마다 workflow_dispatch로 호출하던 cron job을 **2개**로 나눠야 합니다.
각 cron job이 GitHub API의 workflow dispatch 엔드포인트를 호출하도록 설정하세요:

```
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/monitor_opus46.yml/dispatches
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/monitor_opus5.yml/dispatches
```
- Header: `Authorization: Bearer <PAT>` (repo 권한 있는 Personal Access Token), `Accept: application/vnd.github+json`
- Body: `{"ref":"main"}` (기본 브랜치명에 맞게)

기존에 이미 이런 방식으로 카카오 버전을 돌리고 계셨다면, 같은 PAT을 재사용하고 URL의 워크플로 파일명만 두 개로 나누면 됩니다.

## 5. 알림 로직 요약
- 임계값 미만 구간은 "below" 하나로 취급 (세분화 없음)
- 임계값 이상은 5점 단위로 구간을 나눔 (예: opus5는 80-84, 85-89, ... 100)
- **직전 구간과 이번 구간이 다르면** 무조건 알림 (오르든 내리든)
  - 미만 → 이상: ✅ 회복 알림
  - 이상 → 미만: 🔻 하락 알림
  - 이상 구간 사이 이동: 📈 상승 / 📉 하락 알림
- 같은 구간이 유지되는 동안은 알림 없음

## 6. 동시 실행 주의사항
1분마다 트리거되기 때문에, 만약 이전 실행이 아직 끝나지 않은 상태로 다음 실행이 겹치면
`state_*.json` 커밋 시 충돌이 날 수 있습니다. 워크플로에 `git pull --rebase`를 넣어뒀지만,
스크립트 실행 자체가 보통 몇 초 내로 끝나므로 실사용에서는 거의 문제되지 않습니다.
