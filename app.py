from __future__ import annotations

import json
import random
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
PROBLEMS_DIR = BASE_DIR / "problems"
DATA_DIR = BASE_DIR / "data"
USER_STATE_PATH = DATA_DIR / "user_state.json"
REVIEW_BUCKET_DIR = DATA_DIR / "review_bucket"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REVIEW_BUCKET_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="문제 복습 웹사이트", page_icon="📝", layout="wide")


# def inject_global_style() -> None:
#     st.markdown(
#         """
#         <style>
#         html, body, [class*="css"] {
#             font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
#         }
#         .main-title {
#             font-size: 2rem;
#             font-weight: 800;
#             margin-bottom: 0.2rem;
#         }
#         .sub-title {
#             color: #666;
#             margin-bottom: 1rem;
#             line-height: 1.7;
#         }
#         .question-card {
#             padding: 1.25rem 1.25rem 0.75rem 1.25rem;
#             border: 1px solid rgba(120,120,120,0.22);
#             border-radius: 16px;
#             background: rgba(250,250,250,0.82);
#             margin-bottom: 1rem;
#         }
#         .choice-box {
#             padding: 0.7rem 0.85rem;
#             border-radius: 12px;
#             border: 1px solid rgba(120,120,120,0.22);
#             background: white;
#             margin-bottom: 0.6rem;
#             line-height: 1.8;
#             font-size: 1.02rem;
#         }
#         .explanation-box {
#             padding: 1rem;
#             border-radius: 12px;
#             background: rgba(0, 128, 255, 0.06);
#             border: 1px solid rgba(0, 128, 255, 0.15);
#             line-height: 1.8;
#         }
#         .small-muted {
#             color: #666;
#             font-size: 0.92rem;
#         }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )


def inject_global_style() -> None:
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
        }
        .main-title {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
            color: #111827;
        }
        .sub-title {
            color: #4B5563;
            margin-bottom: 1rem;
            line-height: 1.7;
        }
        .question-card {
            padding: 1.25rem 1.25rem 0.75rem 1.25rem;
            border: 1px solid #D1D5DB;
            border-radius: 16px;
            background: #FFFFFF;
            margin-bottom: 1rem;
            color: #111827;
        }
        .choice-box {
            padding: 0.7rem 0.85rem;
            border-radius: 12px;
            border: 1px solid #D1D5DB;
            background: #FFFFFF;
            margin-bottom: 0.6rem;
            line-height: 1.8;
            font-size: 1.02rem;
            color: #111827;
        }
        .explanation-box {
            padding: 1rem;
            border-radius: 12px;
            background: #F8FAFC;
            border: 1px solid #CBD5E1;
            line-height: 1.8;
            color: #0F172A;
        }
        .small-muted {
            color: #4B5563;
            font-size: 0.92rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_key(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text) or "default"



def safe_filename(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text).strip("_") or "unknown"



def normalize_question(raw: dict[str, Any], default_subject: str | None = None) -> dict[str, Any]:
    required_fields = ["id", "unit", "topic", "difficulty", "question", "choices", "answer", "explanation"]
    for field in required_fields:
        if field not in raw:
            raise ValueError(f"문제에 필수 필드가 없습니다: {field}")

    subject = raw.get("subject", default_subject)
    if not subject:
        raise ValueError(f"문제 {raw.get('id', '<unknown>')}에 subject가 없습니다.")

    choices = raw["choices"]
    if not isinstance(choices, list) or len(choices) != 5:
        raise ValueError(f"문제 {raw.get('id', '<unknown>')}의 choices는 반드시 5개여야 합니다.")

    answer = raw["answer"]
    if not isinstance(answer, int) or not 1 <= answer <= 5:
        raise ValueError(f"문제 {raw.get('id', '<unknown>')}의 answer는 1~5 정수여야 합니다.")

    choice_explanations = raw.get("choice_explanations", [""] * 5)
    if not isinstance(choice_explanations, list) or len(choice_explanations) != 5:
        raise ValueError(f"문제 {raw.get('id', '<unknown>')}의 choice_explanations는 반드시 5개여야 합니다.")

    return {
        "id": str(raw["id"]),
        "subject": str(subject),
        "unit": str(raw["unit"]),
        "topic": str(raw["topic"]),
        "difficulty": int(raw["difficulty"]),
        "question": str(raw["question"]),
        "choices": [str(choice) for choice in choices],
        "answer": int(answer),
        "explanation": str(raw["explanation"]),
        "choice_explanations": [str(item) for item in choice_explanations],
        "formula": str(raw.get("formula", "")),
        "tags": [str(item) for item in raw.get("tags", [])],
        "source": str(raw.get("source", "")),
    }


@st.cache_data(show_spinner=False)
def load_questions() -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in sorted(PROBLEMS_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)

        default_subject = path.stem
        if isinstance(loaded, dict) and "questions" in loaded:
            default_subject = str(loaded.get("subject", default_subject))
            items = loaded["questions"]
        elif isinstance(loaded, list):
            items = loaded
        else:
            raise ValueError(f"{path.name} 형식이 올바르지 않습니다. list 또는 {{'questions': [...]}} 이어야 합니다.")

        for item in items:
            question = normalize_question(item, default_subject=default_subject)
            if question["id"] in seen_ids:
                raise ValueError(f"중복 문제 ID가 있습니다: {question['id']}")
            seen_ids.add(question["id"])
            questions.append(question)

    questions.sort(key=lambda q: (q["subject"], q["id"]))
    return questions



def create_default_question_state() -> dict[str, Any]:
    return {
        "attempts": 0,
        "correct": 0,
        "wrong": 0,
        "last_result": None,
        "last_selected": None,
        "last_seen_at": None,
    }



def create_default_subject_session(question_ids: list[str]) -> dict[str, Any]:
    return {
        "order": list(question_ids),
        "current_index": 0,
        "is_shuffled": False,
    }



def create_default_review_session() -> dict[str, Any]:
    return {
        "subject_filter": "전체",
        "wrong_filter": "전체",
        "order": [],
        "current_index": 0,
        "is_shuffled": False,
    }



def get_questions_by_subject(questions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        grouped[question["subject"]].append(question)
    for subject in grouped:
        grouped[subject].sort(key=lambda q: q["id"])
    return dict(grouped)



def load_user_state(questions: list[dict[str, Any]]) -> dict[str, Any]:
    if USER_STATE_PATH.exists():
        with USER_STATE_PATH.open("r", encoding="utf-8") as file:
            state = json.load(file)
    else:
        state = {}

    state.setdefault("per_question", {})
    state.setdefault("subject_sessions", {})
    state.setdefault("history", [])
    state.setdefault("review_session", create_default_review_session())

    grouped = get_questions_by_subject(questions)
    all_question_ids = {question["id"] for question in questions}

    for question_id in all_question_ids:
        state["per_question"].setdefault(question_id, create_default_question_state())

    state["per_question"] = {
        question_id: state["per_question"].get(question_id, create_default_question_state())
        for question_id in sorted(all_question_ids)
    }

    migrated_sessions: dict[str, dict[str, Any]] = {}
    for subject, subject_questions in grouped.items():
        expected_ids = [question["id"] for question in subject_questions]
        previous = state["subject_sessions"].get(subject, {})
        previous_order = previous.get("order", [])
        kept_order = [question_id for question_id in previous_order if question_id in expected_ids]
        missing_ids = [question_id for question_id in expected_ids if question_id not in kept_order]
        order = kept_order + missing_ids
        if not order:
            order = list(expected_ids)

        current_index = int(previous.get("current_index", 0)) if previous else 0
        current_index = max(0, min(current_index, len(order) - 1))

        migrated_sessions[subject] = {
            "order": order,
            "current_index": current_index,
            "is_shuffled": bool(previous.get("is_shuffled", False)),
        }

    state["subject_sessions"] = migrated_sessions

    review_session = state.get("review_session", create_default_review_session())
    state["review_session"] = {
        "subject_filter": str(review_session.get("subject_filter", "전체")),
        "wrong_filter": review_session.get("wrong_filter", "전체"),
        "order": list(review_session.get("order", [])),
        "current_index": int(review_session.get("current_index", 0)),
        "is_shuffled": bool(review_session.get("is_shuffled", False)),
    }

    state["history"] = state["history"][-3000:]
    return state



def save_user_state(state: dict[str, Any]) -> None:
    with USER_STATE_PATH.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)



def get_review_question_ids(questions: list[dict[str, Any]], state: dict[str, Any], subject: str | None = None) -> list[str]:
    filtered: list[str] = []
    for question in questions:
        if subject is not None and question["subject"] != subject:
            continue
        if state["per_question"][question["id"]]["wrong"] > 0:
            filtered.append(question["id"])
    return filtered



def sync_review_bucket(questions: list[dict[str, Any]], state: dict[str, Any]) -> None:
    for path in REVIEW_BUCKET_DIR.glob("*.json"):
        path.unlink()

    all_review_items: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for question in questions:
        progress = state["per_question"][question["id"]]
        if progress["wrong"] <= 0:
            continue
        item = deepcopy(question)
        item["progress"] = deepcopy(progress)
        all_review_items.append(item)
        grouped[question["subject"]].append(item)

    with (REVIEW_BUCKET_DIR / "all_review_questions.json").open("w", encoding="utf-8") as file:
        json.dump(all_review_items, file, ensure_ascii=False, indent=2)

    for subject, items in grouped.items():
        filename = f"{safe_filename(subject)}.json"
        with (REVIEW_BUCKET_DIR / filename).open("w", encoding="utf-8") as file:
            json.dump(items, file, ensure_ascii=False, indent=2)



def reset_all_data(questions: list[dict[str, Any]]) -> dict[str, Any]:
    if USER_STATE_PATH.exists():
        USER_STATE_PATH.unlink()
    for path in REVIEW_BUCKET_DIR.glob("*.json"):
        path.unlink()
    state = load_user_state(questions)
    save_user_state(state)
    sync_review_bucket(questions, state)
    return state



def format_question_short(question: dict[str, Any]) -> str:
    text = question["question"].replace("\n", " ").strip()
    if len(text) > 45:
        text = text[:45] + "..."
    return f"[{question['id']}] {question['topic']} | {text}"



def format_review_label(question: dict[str, Any], wrong_count: int) -> str:
    return f"오답 {wrong_count}회 | {question['id']} | {question['topic']} | {format_question_short(question)}"



def bump_subject_slider_nonce(subject: str) -> None:
    nonce_key = f"solve_slider_nonce_{safe_key(subject)}"
    st.session_state[nonce_key] = int(st.session_state.get(nonce_key, 0)) + 1



def get_subject_slider_key(subject: str) -> str:
    nonce_key = f"solve_slider_nonce_{safe_key(subject)}"
    nonce = int(st.session_state.get(nonce_key, 0))
    return f"solve_slider_{safe_key(subject)}_{nonce}"



def bump_review_slider_nonce() -> None:
    st.session_state["review_slider_nonce"] = int(st.session_state.get("review_slider_nonce", 0)) + 1



def get_review_slider_key() -> str:
    nonce = int(st.session_state.get("review_slider_nonce", 0))
    return f"review_slider_{nonce}"



def set_subject_index(state: dict[str, Any], subject: str, new_index: int) -> None:
    session = state["subject_sessions"][subject]
    max_index = len(session["order"]) - 1
    session["current_index"] = max(0, min(new_index, max_index))
    save_user_state(state)
    bump_subject_slider_nonce(subject)



def clear_solve_feedback(subject: str) -> None:
    st.session_state[f"solve_feedback_{safe_key(subject)}"] = None



def clear_review_feedback() -> None:
    st.session_state["review_feedback"] = None



def sync_review_session(
    state: dict[str, Any],
    filtered_ids: list[str],
    selected_subject: str,
    selected_wrong_count: str | int,
) -> dict[str, Any]:
    session = state["review_session"]
    previous_order = list(session.get("order", []))
    previous_current_id = None
    if previous_order:
        previous_index = max(0, min(int(session.get("current_index", 0)), len(previous_order) - 1))
        previous_current_id = previous_order[previous_index]

    filter_changed = (
        session.get("subject_filter") != selected_subject
        or session.get("wrong_filter") != selected_wrong_count
    )

    kept_order = [question_id for question_id in previous_order if question_id in filtered_ids]
    missing_ids = [question_id for question_id in filtered_ids if question_id not in kept_order]
    new_order = kept_order + missing_ids

    if filter_changed or len(new_order) != len(previous_order):
        if set(new_order) != set(filtered_ids) or len(new_order) != len(filtered_ids):
            new_order = list(filtered_ids)
            session["is_shuffled"] = False

    if not new_order:
        session["order"] = []
        session["current_index"] = 0
        session["subject_filter"] = selected_subject
        session["wrong_filter"] = selected_wrong_count
        save_user_state(state)
        return session

    if filter_changed and previous_current_id in new_order:
        current_index = new_order.index(previous_current_id)
    else:
        current_index = min(int(session.get("current_index", 0)), len(new_order) - 1)
        current_index = max(0, current_index)

    session["order"] = new_order
    session["current_index"] = current_index
    session["subject_filter"] = selected_subject
    session["wrong_filter"] = selected_wrong_count
    save_user_state(state)
    return session



def set_review_index(state: dict[str, Any], new_index: int) -> None:
    session = state["review_session"]
    max_index = len(session["order"]) - 1
    session["current_index"] = max(0, min(new_index, max_index))
    save_user_state(state)
    bump_review_slider_nonce()



def initialize_radio_value(page_name: str, question: dict[str, Any], last_selected: int | None) -> str:
    radio_key = f"{page_name}_choice_{question['id']}"
    options = [f"{idx}. {choice}" for idx, choice in enumerate(question["choices"], start=1)]
    if radio_key not in st.session_state:
        if isinstance(last_selected, int) and 1 <= last_selected <= 5:
            st.session_state[radio_key] = options[last_selected - 1]
        else:
            st.session_state[radio_key] = options[0]
    return radio_key



def record_attempt(
    state: dict[str, Any],
    questions_by_id: dict[str, dict[str, Any]],
    questions: list[dict[str, Any]],
    question_id: str,
    selected_answer: int,
    mode: str,
) -> bool:
    question = questions_by_id[question_id]
    progress = state["per_question"][question_id]
    is_correct = selected_answer == question["answer"]

    progress["attempts"] += 1
    progress["last_selected"] = selected_answer
    progress["last_seen_at"] = datetime.now().isoformat(timespec="seconds")
    progress["last_result"] = "correct" if is_correct else "wrong"

    if is_correct:
        progress["correct"] += 1
    else:
        progress["wrong"] += 1

    state["history"].append(
        {
            "question_id": question_id,
            "subject": question["subject"],
            "selected_answer": selected_answer,
            "correct_answer": question["answer"],
            "is_correct": is_correct,
            "mode": mode,
            "answered_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    state["history"] = state["history"][-3000:]

    save_user_state(state)
    sync_review_bucket(questions, state)
    return is_correct



def render_question_box(question: dict[str, Any], progress: dict[str, Any], current_number: int, total_count: int) -> None:
    header = " / ".join([question["subject"], question["unit"], question["topic"]])
    st.markdown(
        (
            f"<div class='question-card'>"
            f"<div><strong>{header}</strong> · 난이도 {question['difficulty']} · {current_number}/{total_count}</div>"
            f"<div class='small-muted'>문제 ID: {question['id']} | 누적 오답: {progress['wrong']}회 | 총 시도: {progress['attempts']}회</div>"
            f"<br><div style='font-size:1.14rem; line-height:1.85;'>{question['question']}</div>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )



def render_result_block(question: dict[str, Any], selected_answer: int, is_correct: bool, progress: dict[str, Any]) -> None:
    if is_correct:
        st.success(f"정답입니다. 정답은 {question['answer']}번입니다.")
    else:
        st.error(f"오답입니다. 정답은 {question['answer']}번입니다. 누적 오답이 {progress['wrong']}회로 증가했습니다.")

    st.markdown("### 해설")
    st.markdown(f"<div class='explanation-box'>{question['explanation']}</div>", unsafe_allow_html=True)

    if question.get("formula"):
        st.markdown("### 공식")
        st.code(question["formula"])

    st.markdown("### 보기별 해설")
    for idx, choice in enumerate(question["choices"], start=1):
        prefix = "✅" if idx == question["answer"] else "•"
        selected_label = " (내가 선택)" if idx == selected_answer else ""
        st.markdown(f"**{prefix} {idx}번{selected_label}**")
        st.markdown(f"- 보기: {choice}")
        explanation = question["choice_explanations"][idx - 1] or "보기별 해설이 없습니다."
        st.markdown(f"- 해설: {explanation}")

    col1, col2, col3 = st.columns(3)
    col1.metric("누적 오답", progress["wrong"])
    col2.metric("누적 정답", progress["correct"])
    col3.metric("총 시도", progress["attempts"])



def render_home(questions: list[dict[str, Any]], state: dict[str, Any]) -> None:
    review_ids = get_review_question_ids(questions, state)
    total_attempts = sum(item["attempts"] for item in state["per_question"].values())
    total_correct = sum(item["correct"] for item in state["per_question"].values())
    accuracy = round((total_correct / total_attempts) * 100, 1) if total_attempts else 0.0

    st.markdown("<div class='main-title'>문제 복습 웹사이트</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-title'>problems 폴더에 과목별 JSON 파일을 넣으면 과목별로 문제를 풀 수 있습니다. 틀린 문제는 과목별 복습 문제로 누적 저장되며, 과목을 바꿨다가 돌아와도 이전에 보던 문제부터 이어집니다.</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("전체 문제", len(questions))
    col2.metric("복습 문제", len(review_ids))
    col3.metric("총 시도", total_attempts)
    col4.metric("정답률", f"{accuracy}%")

    st.markdown("### 핵심 동작")
    st.markdown(
        """
        - `problems/*.json` 파일을 자동 로드합니다.
        - 과목별 현재 문제 위치와 셔플 순서를 저장합니다.
        - 정답/오답과 무관하게 제출 후 해설이 항상 표시됩니다.
        - 틀린 문제는 복습 문제에서 사라지지 않고 누적 오답 횟수만 증가합니다.
        - 복습 페이지에서 **오답 n회 문제만 필터링한 뒤 한 문제씩 연속으로 복습할 수 있습니다.**
        """
    )

    st.markdown("### 과목별 복습 문제 수")
    subject_counts: dict[str, int] = defaultdict(int)
    for question in questions:
        if state["per_question"][question["id"]]["wrong"] > 0:
            subject_counts[question["subject"]] += 1
    if subject_counts:
        st.bar_chart(subject_counts)
    else:
        st.info("아직 복습 문제가 없습니다.")



def render_solve_page(questions: list[dict[str, Any]], questions_by_id: dict[str, dict[str, Any]], state: dict[str, Any]) -> None:
    st.markdown("## 문제 풀이")

    grouped = get_questions_by_subject(questions)
    subjects = sorted(grouped.keys())
    if not subjects:
        st.warning("문제가 없습니다.")
        return

    subject = st.selectbox("과목", subjects, key="solve_subject_select")
    subject_questions = grouped[subject]
    session = state["subject_sessions"][subject]

    sorted_ids = [question["id"] for question in subject_questions]
    ordered_ids = [question_id for question_id in session["order"] if question_id in set(sorted_ids)]
    if len(ordered_ids) != len(sorted_ids):
        ordered_ids = sorted_ids
        session["order"] = ordered_ids
        session["current_index"] = 0
        session["is_shuffled"] = False
        save_user_state(state)

    current_index = session["current_index"]
    current_index = max(0, min(current_index, len(ordered_ids) - 1))
    session["current_index"] = current_index
    save_user_state(state)

    slider_key = get_subject_slider_key(subject)
    current_display_index = current_index + 1
    progress_ratio = current_display_index / max(1, len(ordered_ids))
    st.progress(progress_ratio, text=f"{subject} 진행: {current_display_index}/{len(ordered_ids)}")

    if len(ordered_ids) > 1:
        slider_value = st.slider(
            "문제 이동",
            min_value=1,
            max_value=len(ordered_ids),
            value=current_display_index,
            key=slider_key,
        )
        if slider_value - 1 != current_index:
            set_subject_index(state, subject, slider_value - 1)
            clear_solve_feedback(subject)
            st.rerun()
    else:
        st.caption("문제 이동: 현재 과목에 문제 1개")

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1.2])
    disable_nav = len(ordered_ids) <= 1
    if col1.button("이전", key=f"solve_prev_{safe_key(subject)}", disabled=disable_nav):
        set_subject_index(state, subject, current_index - 1)
        clear_solve_feedback(subject)
        st.rerun()
    if col2.button("다음", key=f"solve_next_{safe_key(subject)}", disabled=disable_nav):
        set_subject_index(state, subject, current_index + 1)
        clear_solve_feedback(subject)
        st.rerun()
    if col3.button("랜덤 섞기", key=f"solve_shuffle_{safe_key(subject)}", disabled=disable_nav):
        current_question_id = ordered_ids[current_index]
        new_order = list(ordered_ids)
        random.shuffle(new_order)
        session["order"] = new_order
        session["current_index"] = new_order.index(current_question_id)
        session["is_shuffled"] = True
        save_user_state(state)
        bump_subject_slider_nonce(subject)
        clear_solve_feedback(subject)
        st.rerun()
    if col4.button("원래 순서", key=f"solve_reset_order_{safe_key(subject)}", disabled=disable_nav):
        current_question_id = ordered_ids[current_index]
        session["order"] = list(sorted_ids)
        session["current_index"] = session["order"].index(current_question_id)
        session["is_shuffled"] = False
        save_user_state(state)
        bump_subject_slider_nonce(subject)
        clear_solve_feedback(subject)
        st.rerun()
    col5.caption("현재 순서: 랜덤" if session["is_shuffled"] else "현재 순서: 기본")

    question_id = session["order"][session["current_index"]]
    question = questions_by_id[question_id]
    progress = state["per_question"][question_id]
    render_question_box(question, progress, session["current_index"] + 1, len(session["order"]))

    st.caption(f"현재 문제 누적 오답: {progress['wrong']}회")

    radio_key = initialize_radio_value("solve", question, progress.get("last_selected"))
    options = [f"{idx}. {choice}" for idx, choice in enumerate(question["choices"], start=1)]
    st.radio("보기를 선택하세요.", options=options, key=radio_key)

    feedback_key = f"solve_feedback_{safe_key(subject)}"
    feedback = st.session_state.get(feedback_key)

    if st.button("정답 제출", type="primary", key=f"solve_submit_{question_id}"):
        selected_label = st.session_state[radio_key]
        selected_answer = options.index(selected_label) + 1
        is_correct = record_attempt(state, questions_by_id, questions, question_id, selected_answer, mode="solve")
        st.session_state[feedback_key] = {
            "question_id": question_id,
            "selected_answer": selected_answer,
            "is_correct": is_correct,
        }
        st.rerun()

    feedback = st.session_state.get(feedback_key)
    if feedback and feedback.get("question_id") == question_id:
        render_result_block(question, feedback["selected_answer"], feedback["is_correct"], state["per_question"][question_id])



def render_review_page(questions: list[dict[str, Any]], questions_by_id: dict[str, dict[str, Any]], state: dict[str, Any]) -> None:
    st.markdown("## 오답 복습")

    all_review_ids = get_review_question_ids(questions, state)
    if not all_review_ids:
        st.success("복습할 문제가 없습니다.")
        return

    subjects = ["전체"] + sorted({questions_by_id[question_id]["subject"] for question_id in all_review_ids})
    review_session = state["review_session"]
    default_subject = review_session.get("subject_filter", "전체")
    if default_subject not in subjects:
        default_subject = "전체"

    selected_subject = st.selectbox(
        "과목",
        subjects,
        index=subjects.index(default_subject),
        key="review_subject_select",
    )

    available_ids = [
        question_id
        for question_id in all_review_ids
        if selected_subject == "전체" or questions_by_id[question_id]["subject"] == selected_subject
    ]

    wrong_counts = sorted({state["per_question"][question_id]["wrong"] for question_id in available_ids})
    wrong_count_options: list[str | int] = ["전체"] + wrong_counts
    default_wrong = review_session.get("wrong_filter", "전체")
    if default_wrong not in wrong_count_options:
        default_wrong = "전체"

    selected_wrong_count = st.selectbox(
        "오답 횟수 필터",
        wrong_count_options,
        index=wrong_count_options.index(default_wrong),
        key="review_wrong_count_filter",
    )

    filtered_ids = [
        question_id
        for question_id in available_ids
        if selected_wrong_count == "전체" or state["per_question"][question_id]["wrong"] == selected_wrong_count
    ]

    if not filtered_ids:
        st.warning("해당 조건의 복습 문제가 없습니다.")
        return

    review_rows = []
    for question_id in filtered_ids:
        question = questions_by_id[question_id]
        progress = state["per_question"][question_id]
        review_rows.append(
            {
                "문제 ID": question_id,
                "과목": question["subject"],
                "단원": question["unit"],
                "주제": question["topic"],
                "오답 횟수": progress["wrong"],
                "총 시도": progress["attempts"],
                "최근 결과": progress["last_result"] or "-",
                "문제": question["question"],
            }
        )
    st.dataframe(review_rows, use_container_width=True, hide_index=True)

    session = sync_review_session(state, filtered_ids, selected_subject, selected_wrong_count)
    ordered_ids = session["order"]
    current_index = max(0, min(session["current_index"], len(ordered_ids) - 1))
    session["current_index"] = current_index
    save_user_state(state)

    slider_key = get_review_slider_key()
    current_display_index = current_index + 1
    progress_ratio = current_display_index / max(1, len(ordered_ids))
    st.progress(progress_ratio, text=f"복습 진행: {current_display_index}/{len(ordered_ids)}")

    if len(ordered_ids) > 1:
        slider_value = st.slider(
            "복습 문제 이동",
            min_value=1,
            max_value=len(ordered_ids),
            value=current_display_index,
            key=slider_key,
        )
        if slider_value - 1 != current_index:
            set_review_index(state, slider_value - 1)
            clear_review_feedback()
            st.rerun()
    else:
        st.caption("복습 문제 이동: 현재 필터에 문제 1개")

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1.2])
    disable_nav = len(ordered_ids) <= 1
    if col1.button("이전", key="review_prev", disabled=disable_nav):
        set_review_index(state, current_index - 1)
        clear_review_feedback()
        st.rerun()
    if col2.button("다음", key="review_next", disabled=disable_nav):
        set_review_index(state, current_index + 1)
        clear_review_feedback()
        st.rerun()
    if col3.button("랜덤 섞기", key="review_shuffle", disabled=disable_nav):
        current_question_id = ordered_ids[current_index]
        new_order = list(ordered_ids)
        random.shuffle(new_order)
        session["order"] = new_order
        session["current_index"] = new_order.index(current_question_id)
        session["is_shuffled"] = True
        save_user_state(state)
        bump_review_slider_nonce()
        clear_review_feedback()
        st.rerun()
    if col4.button("원래 순서", key="review_reset_order", disabled=disable_nav):
        current_question_id = ordered_ids[current_index]
        session["order"] = list(filtered_ids)
        session["current_index"] = session["order"].index(current_question_id)
        session["is_shuffled"] = False
        save_user_state(state)
        bump_review_slider_nonce()
        clear_review_feedback()
        st.rerun()
    col5.caption("현재 순서: 랜덤" if session["is_shuffled"] else "현재 순서: 기본")

    question_id = session["order"][session["current_index"]]
    question = questions_by_id[question_id]
    progress = state["per_question"][question_id]
    render_question_box(question, progress, session["current_index"] + 1, len(session["order"]))

    radio_key = initialize_radio_value("review", question, progress.get("last_selected"))
    review_options = [f"{idx}. {choice}" for idx, choice in enumerate(question["choices"], start=1)]
    st.radio("보기를 선택하세요.", options=review_options, key=radio_key)

    if st.button("복습 답안 제출", type="primary", key=f"review_submit_{question_id}"):
        selected_label = st.session_state[radio_key]
        selected_answer = review_options.index(selected_label) + 1
        is_correct = record_attempt(state, questions_by_id, questions, question_id, selected_answer, mode="review")
        st.session_state["review_feedback"] = {
            "question_id": question_id,
            "selected_answer": selected_answer,
            "is_correct": is_correct,
        }
        st.rerun()

    feedback = st.session_state.get("review_feedback")
    if feedback and feedback.get("question_id") == question_id:
        render_result_block(question, feedback["selected_answer"], feedback["is_correct"], state["per_question"][question_id])


def render_progress_page(questions: list[dict[str, Any]], state: dict[str, Any]) -> None:
    st.markdown("## 진행 현황")

    rows = []
    for question in questions:
        progress = state["per_question"][question["id"]]
        rows.append(
            {
                "문제 ID": question["id"],
                "과목": question["subject"],
                "단원": question["unit"],
                "주제": question["topic"],
                "총 시도": progress["attempts"],
                "정답": progress["correct"],
                "오답": progress["wrong"],
                "최근 결과": progress["last_result"] or "-",
                "최근 본 시각": progress["last_seen_at"] or "-",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("### 과목별 오답 누적")
    subject_wrong: dict[str, int] = defaultdict(int)
    for question in questions:
        subject_wrong[question["subject"]] += state["per_question"][question["id"]]["wrong"]
    st.bar_chart(subject_wrong)

    st.markdown("### 과목별 현재 위치")
    subject_position_rows = []
    grouped = get_questions_by_subject(questions)
    for subject, subject_questions in grouped.items():
        session = state["subject_sessions"].get(subject, create_default_subject_session([q["id"] for q in subject_questions]))
        total = len(session["order"])
        current = session["current_index"] + 1 if total else 0
        subject_position_rows.append(
            {
                "과목": subject,
                "현재 위치": f"{current}/{total}",
                "랜덤 순서 여부": "Y" if session.get("is_shuffled") else "N",
            }
        )
    st.dataframe(subject_position_rows, use_container_width=True, hide_index=True)



def render_problem_file_page() -> None:
    st.markdown("## 문제 파일 미리보기")

    files = sorted(PROBLEMS_DIR.glob("*.json"))
    if not files:
        st.warning("problems 폴더에 문제 파일이 없습니다.")
        return

    selected_path = st.selectbox("파일 선택", files, format_func=lambda path: path.name)
    st.code(selected_path.read_text(encoding="utf-8"), language="json")



def render_settings_page(questions: list[dict[str, Any]], state: dict[str, Any]) -> None:
    st.markdown("## 설정")
    st.warning("아래 버튼은 학습 기록과 복습 누적을 모두 초기화합니다.")
    if st.button("전체 학습 기록 초기화", type="secondary"):
        new_state = reset_all_data(questions)
        st.session_state["review_feedback"] = None
        for subject in get_questions_by_subject(questions).keys():
            st.session_state[f"solve_feedback_{safe_key(subject)}"] = None
        st.success("초기화가 완료되었습니다. 필요하면 한 번 더 새로고침하십시오.")
        st.write(new_state)

    st.markdown("### 저장 파일")
    st.code(str(USER_STATE_PATH))
    st.code(str(REVIEW_BUCKET_DIR))



def main() -> None:
    inject_global_style()

    questions = load_questions()
    if not questions:
        st.error("문제 파일을 찾지 못했습니다. problems 폴더에 JSON 파일을 넣어주세요.")
        st.stop()

    questions_by_id = {question["id"]: question for question in questions}
    state = load_user_state(questions)
    save_user_state(state)
    sync_review_bucket(questions, state)

    review_count = len(get_review_question_ids(questions, state))

    with st.sidebar:
        st.markdown("## 메뉴")
        page = st.radio("이동", ["홈", "문제 풀이", "오답 복습", "진행 현황", "문제 파일 미리보기", "설정"])
        st.divider()
        st.caption(f"문제 수: {len(questions)}")
        st.caption(f"복습 문제 수: {review_count}")
        st.caption(f"review bucket: {REVIEW_BUCKET_DIR}")

    if page == "홈":
        render_home(questions, state)
    elif page == "문제 풀이":
        render_solve_page(questions, questions_by_id, state)
    elif page == "오답 복습":
        render_review_page(questions, questions_by_id, state)
    elif page == "진행 현황":
        render_progress_page(questions, state)
    elif page == "문제 파일 미리보기":
        render_problem_file_page()
    elif page == "설정":
        render_settings_page(questions, state)


if __name__ == "__main__":
    main()
