# S3 모델 Artifact 레지스트리

실제 모델 바이너리는 Git에 포함하지 않는다. 이 문서는 배포 환경이 읽을 수 있는
S3 위치, 버전과 무결성 기준만 기록한다. S3 객체는 비공개로 유지하고, EC2에는
해당 두 객체만 `GetObject` 가능한 IAM 역할을 부여한다.

| 모델 | 버전 | S3 URI | SHA-256 | S3 Version ID | ETag |
| --- | --- | --- | --- | --- | --- |
| 오늘이: 현재 당뇨 신호 선별 | `knhanes-shared8-waist-sk180-research-v1` | `s3://ah05-model-artifacts-20260915-019fdc6f/오늘이8.joblib` | `aceafb1011afed055da727f63c996f1e35a711e0e01f3a38c349360d2f3ee8fc` | `B4HZrfZOo_nZ6lCZRpMjUVtsyzUFD8ct` | `b199a54e0d3389b271175d93bf03d1a7` |
| 내일이: 미래 신규 당뇨 발병 위험 | `rf25-tuned-spec40-v1` | `s3://ah05-model-artifacts-20260915-019fdc6f/내일이25.joblib` | `e5067dacd50006b8d7681ef9e558a2a3488913ae1db58d15632c842623c05bf8` | `sqVF_Lyh9X6x5DZEBCaH.gmAK._._Trs` | `edc86585ec2d71cdd5aff12f16d73b69` |

## 배포 설정

```dotenv
CURRENT_SCREENING_RUNTIME=shared8-waist
TOMORROW_RUNTIME=rf25
ML_SHARED8_MODEL_URI=s3://ah05-model-artifacts-20260915-019fdc6f/오늘이8.joblib
ML_RF25_MODEL_URI=s3://ah05-model-artifacts-20260915-019fdc6f/내일이25.joblib
MODEL_CACHE_DIR=/app/storage/cache
```

`ai-worker`는 시작 전에 S3에서 파일을 내려받고 SHA-256을 검증한다. 이 단계가
실패하면 `/tmp/ai-worker-ready`를 만들지 않으므로 컨테이너 health check도 통과하지
않는다. 두 모델은 `research_candidate_only` 상태를 유지하며 개인 진단·처방 또는
공개 발병확률로 사용하지 않는다.
