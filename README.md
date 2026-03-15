# 문제 복습 웹사이트

Streamlit 기반 로컬 웹앱입니다.

## 주요 기능
- `problems` 폴더의 과목별 JSON 파일 자동 로드
- 과목별 문제 풀이
- 과목별 현재 문제 위치 저장
- 랜덤 섞기 / 원래 순서 복원
- 슬라이더 바를 이용한 문제 이동
- 정답/오답과 관계없이 제출 후 해설 표시
- 틀린 문제의 과목별 복습 문제 누적 저장
- 문제별 누적 오답 횟수 표시
- 복습 페이지에서 오답 횟수별 필터 후 특정 문제 하나만 다시 풀이 가능

## 폴더 구조
```text
review_quiz_app/
├─ app.py
├─ requirements.txt
├─ problems/
│  ├─ machine_learning.json
│  ├─ statistics.json
│  └─ problem_schema_example.json
└─ data/
   ├─ user_state.json
   └─ review_bucket/
```

## 실행 방법
### 1) 가상환경 생성
macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) 의존성 설치
```bash
pip install -r requirements.txt
```

### 3) 실행
```bash
streamlit run app.py
```

### 4) 접속
브라우저에서 보통 아래 주소를 엽니다.
```text
http://localhost:8501
```

## 문제 파일 형식
기본 형식은 `problems/problem_schema_example.json`을 따르면 됩니다.

- `subject`: 과목명
- `questions`: 문제 배열
- 각 문제는 보기 `choices`가 정확히 5개여야 함
- `answer`는 1~5 정수여야 함
- `choice_explanations`도 5개여야 함

## 저장 방식
- 사용자 진행 상태: `data/user_state.json`
- 복습 문제 파일: `data/review_bucket/all_review_questions.json`
- 과목별 복습 문제 파일: `data/review_bucket/<과목명>.json`

## 주의
- 같은 `id`를 가진 문제가 여러 파일에 있으면 에러가 납니다.
- 문제 파일을 수정한 뒤 앱을 새로고침하면 반영됩니다.
