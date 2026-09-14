# 독립 PNG 기반 숲 오브젝트 렌더링

## 원본과 공통 좌표

`src/frontend/assets/furniture-v153/`의 24개 PNG가 각각 한 오브젝트만 포함한다. 저장소 오브젝트 20종은 `ForestObjects.STORAGE_CODES` 순서의 256×256 프레임(5열×4행)을 유지한다. 장식 애니메이션 4종은 `ANIMATED_CODES` 순서의 128×128 프레임을 사용한다. 저장된 배치 좌표와 오브젝트 코드는 바뀌지 않는다.

`ForestObjects.INDIVIDUAL_ASSETS`가 파일명, 로더 키, 오브젝트 코드의 단일 목록이다. 서로 다른 오브젝트가 들어 있는 원본 스프라이트 시트에서 새 가구를 잘라내지 않는다.

## 잘림과 찌그러짐 방지

`alphaBounds`는 알파가 1 이상인 모든 픽셀을 포함하는 경계를 계산한다. 가구의 끝부분과 희미한 외곽선도 경계에서 제외하지 않는다. 이 경계를 원래 가로세로 비율로 맞추며, 256 프레임은 사방 최소 12픽셀, 128 프레임은 최소 6픽셀의 여백을 둔다. 발밑 기준선은 각각 244, 122이다. 정수 픽셀 반올림 외에는 가로와 세로 배율이 동일하다.

각 PNG는 전용 임시 타일에 먼저 그린 뒤 공통 아틀라스에 복사한다. 따라서 다른 오브젝트의 픽셀을 가져오거나 이웃 프레임으로 그림이 넘어갈 수 없다. `createIndividualTile(image, tileSize)`는 동일한 처리를 단일 오브젝트에도 제공한다.

## 로딩과 API

브라우저 초기화 시 `ForestObjects.loadIndividualAssets()`를 호출한다. 호출 즉시 일반 그리기 함수의 구형 아틀라스 대체 표시를 막고, 24개 파일이 모두 로드되어야 새 이미지 묶음을 등록한다. 로딩 오류는 Promise 거부로 전달되며 구형 그림으로 조용히 되돌아가지 않는다. 호출자는 오류 안내와 재시도/새로고침 경로를 제공해야 한다.

Phaser는 `INDIVIDUAL_ASSETS` 전체를 preload하고, create에서 `{ [code]: image }` 맵을 `registerIndividualImages`로 등록한다. 모든 PNG가 준비되지 않으면 등록이 실패한다.

- `createStorageAtlas(source)`와 `drawStorageItem(...)`: 등록된 독립 PNG의 공통 아틀라스를 사용한다.
- `createAnimatedAtlas(source)`와 `drawAnimatedItem(...)`: 등록된 독립 PNG의 고정 프레임을 사용한다.
- `createStorageAtlasFromImages(images)` / `createAnimatedAtlasFromImages(images)`: 주어진 이미지 맵을 직접 정규화한다.
- `individualReady`: 24개 PNG가 등록되었는지 확인한다.
- `createLegacyStorageAtlas(source)`: 기존 불꽃 추출처럼 명시적으로 허용한 구형 원본 처리에만 사용한다.

로딩 중 일반 아틀라스 함수는 `null`, 그리기 함수는 `false`를 반환한다. 직접 `drawImage` 또는 `ForestFire`에 아틀라스를 전달하는 호출자는 이를 확인해야 한다.

## 애니메이션과 모닥불

새 장식 원본은 한 장의 완전한 이미지다. 공통 아틀라스의 네 프레임은 동일한 타일을 반복하므로 분수 돌, 바람개비 받침 등 고정 부분이 프레임마다 이동하지 않는다. 물 효과, 날개 색 변화, 오리 몸의 작은 움직임은 Phaser의 분리된 효과만 사용한다. 새 바람개비 원본을 바꾸면 날개 분리 마스크를 실제 정규화된 이미지와 대조해야 한다.

새 `campfire.png`는 불이 꺼진 재·장작·돌 받침이다. `ForestFire`는 이 온전한 새 받침을 OFF와 모든 ON 프레임에 동일하게 사용한다. 불꽃은 별도의 구형 프레임에서 마스크로 추출한다. Phaser는 `ForestFire.install(scene, { flameAtlasKey: 'campfire-flame-atlas' })`로 그 원본을 명시한다. Canvas 경로에서도 `burningTile`의 첫 인수는 `createLegacyStorageAtlas` 결과여야 한다. 새 가구 아틀라스의 꺼진 모닥불에서 불꽃을 추출해서는 안 된다.

## 검증

`node --test tests/forest-objects.test.cjs tests/forest-fire.test.cjs tests/forest-object-motion.test.cjs`로 전체 알파 경계, 여백, 종횡비, 프레임 간 격리, 원본·캐시 공유, 전체 로딩 대기, 고정 모닥불 받침을 검증한다. 기존 구형 아틀라스 테스트는 불꽃 호환 경로의 회귀 방지를 위해 유지한다.

## 아바타 닉네임 기준점

닉네임은 224×288 합성 캔버스의 위쪽 경계가 아니라, 현재 LPC 프레임에서 알파 32 이상인 실제 불투명 영역의 위쪽에 붙인다. 스프라이트 원점·현재 배율·점프 이동량을 반영해 월드 좌표를 구한 다음 카메라로 투영한다. 닉네임 아랫변과 머리 사이 간격은 화면 높이로 환산한 고정 8 CSS 픽셀이므로 카메라 확대나 화면 리사이즈로 벌어지지 않는다. 관련 회귀 테스트는 `tests/forest-camera.test.cjs`에 있다.
