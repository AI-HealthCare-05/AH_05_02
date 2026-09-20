# 움직이는 펫 목록 유지 — 2026-09-08

사용자 정정에 따라 **이미 자연스럽게 움직이던 펫만** 유지합니다. LPC 보행
3종과 Last tick 고양이 4종, `없음`을 포함해 총 **8개 선택지**입니다.
이전에 복구 대상으로 잘못 해석했던 정지 일러스트 6종은 메뉴와 렌더러에서
제외했습니다. 해당 원본 PNG 파일 자체는 삭제하거나 수정하지 않았습니다.

| 분류 | ID | 표시 이름 | 실제 동작 자산 |
| --- | --- | --- | --- |
| 기존 LPC | `lpc_white_cat` | 흰 고양이 · 보행 | 4방향 × 보행 3프레임 |
| 기존 LPC | `lpc_orange_cat` | 주황 고양이 · 보행 | 4방향 × 보행 3프레임 |
| 기존 LPC | `lpc_brown_dog` | 갈색 강아지 · 보행 | 4방향 × 보행 3프레임 |
| 신규 고양이 | `last_tick_white` | 눈꽃 고양이 | 원본 대기·보행·먹기·앞발 |
| 신규 고양이 | `last_tick_gray` | 구름 고양이 | 원본 대기·보행·먹기·앞발 |
| 신규 고양이 | `last_tick_ginger` | 살구 고양이 | 원본 대기·보행·먹기·앞발 |
| 신규 고양이 | `last_tick_ribbon` | 리본 고양이 | 흰 고양이 + 동기화된 원본 리본 |

## 기존 저장값 호환

저장된 펫 ID·코디·프리셋은 마이그레이션하거나 초기화하지 않습니다.
프리셋 3~6의 신규 고양이도 그대로입니다. 오래된 ID는 표시할 때만 다음과 같이
해석하며 메뉴에 별도 중복 카드를 만들지 않습니다.

- `white_pup`, `brown_pup` → `lpc_brown_dog`
- `cat` → `lpc_white_cat`
- `fox` → `lpc_orange_cat`
- `blue_eyes_white_cat` → `last_tick_white`
- `gold_eyes_orange_cat` → `last_tick_ginger`

꾸미기 선택 카드와 미리보기 역시 같은 호환 규칙을 사용합니다. 메뉴를 열었다는
이유로 기존 저장값을 `none`으로 바꾸거나 alias를 저장값에 덮어쓰지 않습니다.
이전 `white_pup`에 대응했던 LPC 원본은 실제로 갈색 개였습니다.

## 동작과 검증

LPC 3종은 네 방향으로 걷고, 별도 앉기·먹기·앞발 프레임은 없으므로 정지 시
멈춘 보행 프레임을 사용합니다. Last tick 4종은 검증된 원본 대기·보행·먹기·
앞발 동작을 유지합니다. 새 그림·늘이기·재색칠·가짜 애니메이션은 추가하지 않습니다.

`forest-pet-restoration.test.cjs`, `forest-pet-preview.test.cjs`,
`forest-pet-runtime.test.cjs`, `forest-kitten-pack.test.cjs`에서 목록 8개,
애니메이션 프레임·정지 그림 제외·저장 ID 호환·선택 카드·미리보기·상태 보존·
포획 중복 방지·없음 선택을 확인합니다.
