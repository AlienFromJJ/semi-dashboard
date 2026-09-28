# 반도체 사이클 대시보드

국내외 주요 반도체 종목, 메모리 현물가, 괴리율·상대강도, 반도체 경기 온도계를 한 페이지에서 보는 정적 웹사이트입니다.
서버 없이 **GitHub Actions가 30분마다 데이터를 수집해 GitHub Pages에 자동 배포**합니다.

## 구성
| 경로 | 설명 |
| --- | --- |
| `index.html`, `assets/` | 화면 (uPlot 차트 라이브러리 포함, 외부 CDN 불필요) |
| `scripts/update_data.py` | 데이터 수집·지표 계산 스크립트 |
| `data/` | 수집 결과 JSON (`summary.json`, `prices/*.json`, `memory.json`, `macro.json`) |
| `.github/workflows/update.yml` | 자동 업데이트·배포 스케줄 |

## 배포 (최초 1회, 약 5분)
1. GitHub에서 새 저장소를 만들고 이 폴더 전체를 업로드합니다. (브랜치: `main`)
2. 저장소 **Settings → Pages → Source**를 **GitHub Actions**로 선택합니다.
3. **Actions** 탭 → `데이터 자동 업데이트 & 배포` → **Run workflow**를 누릅니다.
4. 완료되면 `https://<계정>.github.io/<저장소>/` 에서 사이트가 열립니다. 이후 평일 30분마다 자동으로 갱신됩니다.

> 저장소는 Public이면 Actions가 무료·무제한입니다. Private은 월 2,000분 무료 한도가 있으므로 cron을 `0 * * * 1-5`(1시간)로 늘리는 것을 권장합니다.

Notion 페이지에는 배포된 주소를 `/embed` 블록으로 넣으면 됩니다.

## 로컬 실행
```bash
pip install beautifulsoup4
python scripts/update_data.py
python -m http.server 8000   # http://localhost:8000
```

## 종목·지표 수정
`scripts/update_data.py` 상단의 `UNIVERSE` 목록에 한 줄을 추가하면 됩니다.
- 국내: `("종목코드", "이름", "naver", "종목코드", "KR", "분류", "KRW")`
- 해외: `("티커", "이름", "yahoo", "야후 티커", "GLOBAL", "분류", "USD")`

## 데이터 출처
- 국내 종목: 네이버 금융 일봉 · 해외 종목/지수/환율/원자재: Yahoo Finance
- 메모리 현물가: DRAMeXchange(TrendForce) — 공개 이력이 없어 **실행할 때마다 누적 저장**합니다.
- 실물 지표: FRED (미국 반도체 산업생산, 반도체 PPI, 전자제품 신규주문)

본 사이트는 정보 제공 목적이며 투자 권유가 아닙니다.
