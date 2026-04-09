import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ==============================
# [Context & Goal]
# This app is designed for employment center counselors who need quick,
# reliable insights from hiring postings to guide job seekers.
# ==============================

st.set_page_config(page_title="온톱 (On-Top)", page_icon="📈", layout="wide")

st.title("온톱 (On-Top) - 채용 트렌드/역량 분석 대시보드")
st.caption("고용센터 상담사가 공고 데이터를 업로드하면 트렌드와 실전 컨설팅 인사이트를 즉시 확인할 수 있습니다.")


# ==============================
# [Tech Stack & Constraints]
# - Python / Streamlit / Pandas / Plotly
# - Optional: WordCloud
# - Sensitive values: use st.secrets or os.getenv (no hardcoded keys)
# ==============================

REQUIRED_COLUMNS_GUIDE = [
    "company",
    "group",
    "industry",
    "division",
    "job_category",
    "posting_date",
    "title",
    "description",
    "preferred",
]

DEFAULT_SKILL_DICT = [
    "python", "sql", "excel", "power bi", "tableau", "r", "java", "spring", "react", "node.js",
    "aws", "gcp", "azure", "docker", "kubernetes", "spark", "hadoop", "llm", "prompt",
    "머신러닝", "딥러닝", "데이터분석", "통계", "커뮤니케이션", "문제해결", "프로젝트관리",
    "영상편집", "마케팅", "영업", "회계", "재무", "인사", "총무", "생산관리", "품질관리",
    "c", "c++", "go", "typescript", "figma", "photoshop", "cad", "전기기사", "정보처리기사",
]

CERT_KEYWORDS = ["기사", "cert", "자격", "toeic", "opic", "cpa", "cfa", "정보처리", "adsp", "sqld"]
EDU_KEYWORDS = ["학사", "석사", "박사", "대졸", "전문학사", "고졸", "mba"]
AI_DATA_KEYWORDS = ["ai", "데이터", "머신러닝", "딥러닝", "llm", "analytics", "analysis", "ml"]
FREE_MAX_ROWS = 12000


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapper = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=mapper)

    alias_map = {
        "기업명": "company",
        "회사명": "company",
        "대기업그룹": "group",
        "산업군": "industry",
        "사업부": "division",
        "직무": "job_category",
        "채용일": "posting_date",
        "공고일": "posting_date",
        "공고제목": "title",
        "본문": "description",
        "우대사항": "preferred",
    }
    for k, v in alias_map.items():
        if k in df.columns and v not in df.columns:
            df[v] = df[k]

    return df


def parse_date_safe(value: object) -> Optional[pd.Timestamp]:
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value, errors="coerce")
    except Exception:
        return None


def infer_half(dt: pd.Timestamp) -> str:
    if pd.isna(dt):
        return "미상"
    return "상반기" if dt.month <= 6 else "하반기"


def extract_skills_from_text(text: str, skill_dict: List[str]) -> Set[str]:
    text_l = text.lower() if isinstance(text, str) else ""
    found = set()
    for skill in skill_dict:
        s = skill.lower()
        if s in text_l:
            found.add(skill)
    return found


def safe_ai_refine_skills(raw_text: str, initial_skills: Set[str]) -> Set[str]:
    """
    [Edge Case Handling]
    AI API is optional. If key or request fails, we return initial_skills.
    This prevents demo-breaking red screens.
    """
    provider = os.getenv("AI_PROVIDER", "") or st.secrets.get("AI_PROVIDER", "") if hasattr(st, "secrets") else ""
    _ = provider
    # Placeholder for Claude/Gemini integration. Intentionally no external call by default.
    try:
        return initial_skills
    except Exception:
        return initial_skills


@st.cache_data
def create_sample_data(n: int = 320) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    years = rng.choice([2022, 2023, 2024, 2025, 2026], size=n, p=[0.16, 0.18, 0.22, 0.24, 0.20])
    months = rng.integers(1, 13, size=n)

    companies = ["네오전자", "한빛금융", "스카이모빌리티", "휴먼바이오", "블루리테일", "퀀텀소프트"]
    groups = ["네오그룹", "한빛그룹", "스카이그룹", "휴먼그룹", "블루그룹", "퀀텀그룹"]
    industries = ["IT", "금융", "제조", "바이오", "유통", "모빌리티"]
    divisions = ["플랫폼", "데이터", "영업", "마케팅", "R&D", "운영"]
    jobs = ["데이터분석", "백엔드", "프론트엔드", "영업관리", "마케팅", "품질관리", "인사"]

    skill_templates = {
        "데이터분석": "Python SQL 데이터분석 통계 Tableau",
        "백엔드": "Java Spring SQL AWS Docker",
        "프론트엔드": "React TypeScript Figma 커뮤니케이션",
        "영업관리": "Excel 커뮤니케이션 문제해결 영업",
        "마케팅": "마케팅 데이터분석 Excel 커뮤니케이션",
        "품질관리": "품질관리 통계 Excel 문제해결",
        "인사": "인사 커뮤니케이션 Excel 프로젝트관리",
    }

    rows = []
    for i in range(n):
        job = rng.choice(jobs)
        y = int(years[i])
        m = int(months[i])
        d = int(rng.integers(1, 28))
        dt = datetime(y, m, d)

        c_idx = int(rng.integers(0, len(companies)))
        company = companies[c_idx]
        group = groups[c_idx]
        industry = industries[c_idx]

        base_desc = skill_templates[job]
        if y >= 2025 and rng.random() < 0.45:
            base_desc += " AI LLM"
        if y <= 2023 and rng.random() < 0.25:
            base_desc = base_desc.replace("LLM", "")

        preferred = "우대: "
        preferred += rng.choice([
            "정보처리기사 보유자", "석사 학위 보유", "경력 3년 이상", "TOEIC 800 이상",
            "AI 프로젝트 경험", "데이터 파이프라인 구축 경험", "관련 자격증 보유",
        ])

        rows.append(
            {
                "company": company,
                "group": group,
                "industry": industry,
                "division": rng.choice(divisions),
                "job_category": job,
                "posting_date": dt.strftime("%Y-%m-%d"),
                "title": f"[{company}] {job} 채용",
                "description": f"담당업무 및 자격요건: {base_desc}",
                "preferred": preferred,
            }
        )

    return pd.DataFrame(rows)


def prepare_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(raw_df.copy())

    for col in ["company", "group", "industry", "division", "job_category", "title", "description", "preferred"]:
        if col not in df.columns:
            df[col] = "미상"

    if "posting_date" not in df.columns:
        df["posting_date"] = pd.NaT

    df["posting_dt"] = df["posting_date"].apply(parse_date_safe)
    df = df[df["posting_dt"].notna()].copy()

    if df.empty:
        return df

    df["year"] = df["posting_dt"].dt.year.astype(int)
    df["month"] = df["posting_dt"].dt.month.astype(int)
    df["half"] = df["posting_dt"].apply(infer_half)

    full_text = (df["title"].fillna("") + " " + df["description"].fillna("") + " " + df["preferred"].fillna(""))
    df["skills"] = full_text.apply(lambda t: list(safe_ai_refine_skills(t, extract_skills_from_text(t, DEFAULT_SKILL_DICT))))

    def classify_pref(pref_text: str) -> Tuple[int, int, float, int]:
        t = pref_text.lower() if isinstance(pref_text, str) else ""
        cert = int(any(k in t for k in CERT_KEYWORDS))
        edu = int(any(k in t for k in EDU_KEYWORDS))
        ai_data = int(any(k in t for k in AI_DATA_KEYWORDS))

        exp_match = re.search(r"경력\s*(\d+)\s*년", t)
        exp_years = float(exp_match.group(1)) if exp_match else np.nan
        return cert, edu, exp_years, ai_data

    pref_features = df["preferred"].apply(classify_pref)
    df["pref_cert"], df["pref_edu"], df["pref_exp_years"], df["pref_ai_data"] = zip(*pref_features)

    return df


def skill_year_presence(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year", "skill", "count"])

    rows = []
    for _, r in df[["year", "skills"]].iterrows():
        skills = r["skills"] if isinstance(r["skills"], list) else []
        for s in skills:
            rows.append((r["year"], s))

    if not rows:
        return pd.DataFrame(columns=["year", "skill", "count"])

    out = pd.DataFrame(rows, columns=["year", "skill"])
    out = out.groupby(["year", "skill"], as_index=False).size().rename(columns={"size": "count"})
    return out


def render_wordcloud(skill_counts: pd.DataFrame) -> None:
    st.subheader("전체 공고 Top 키워드 (경량 바차트)")

    if skill_counts.empty:
        st.info("표시할 키워드가 없습니다.")
        return

    # Free-tier stability: avoid heavy image rendering dependencies.
    fig = px.bar(skill_counts.head(20), x="skill", y="count", title="Top Skill Keywords")
    st.plotly_chart(fig, use_container_width=True)


def section_overview(df: pd.DataFrame) -> None:
    st.header("1) 채용 트렌드 Overview")

    c1, c2 = st.columns(2)

    with c1:
        yearly = df.groupby("year", as_index=False).size().rename(columns={"size": "posting_count"})
        fig = px.bar(yearly, x="year", y="posting_count", title="연도별 채용 공고 수 변화")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        by_industry = df.groupby(["year", "industry"], as_index=False).size().rename(columns={"size": "cnt"})
        total_per_year = by_industry.groupby("year")["cnt"].transform("sum")
        by_industry["ratio"] = by_industry["cnt"] / total_per_year
        fig = px.area(by_industry, x="year", y="ratio", color="industry", groupnorm="fraction", title="산업군별 채용 비중 추이")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        yhd = df.groupby(["year", "half", "division"], as_index=False).size().rename(columns={"size": "cnt"})
        yhd["year_half"] = yhd["year"].astype(str) + "-" + yhd["half"]
        fig = px.bar(yhd, x="year_half", y="cnt", color="division", barmode="group", title="연도별 상/하반기 사업부별 채용 추이")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        job_trend = df.groupby(["year", "job_category"], as_index=False).size().rename(columns={"size": "cnt"})
        fig = px.line(job_trend, x="year", y="cnt", color="job_category", markers=True, title="직무 종류 변화 추이")
        st.plotly_chart(fig, use_container_width=True)

    season = df.groupby(["half", "month"], as_index=False).size().rename(columns={"size": "cnt"})
    fig = px.bar(season, x="month", y="cnt", color="half", barmode="group", title="상/하반기 채용 시즌 패턴")
    st.plotly_chart(fig, use_container_width=True)


def section_skill_analysis(df: pd.DataFrame) -> None:
    st.header("2) 직무별 요구 역량 분석")

    sy = skill_year_presence(df)
    total_skill = sy.groupby("skill", as_index=False)["count"].sum().sort_values("count", ascending=False)
    render_wordcloud(total_skill)

    st.subheader("3년간 꾸준히 요구된 필수 스킬")
    years = sorted(df["year"].unique().tolist())
    if len(years) >= 3:
        recent3 = years[-3:]
        each_year_skills = []
        for y in recent3:
            skills_y = set(sy[sy["year"] == y]["skill"].tolist())
            each_year_skills.append(skills_y)
        core_skills = set.intersection(*each_year_skills) if each_year_skills else set()
        st.write(f"최근 3개년 ({recent3[0]}-{recent3[-1]}) 공통 스킬: {', '.join(sorted(core_skills)) if core_skills else '없음'}")
    else:
        st.info("3개년 데이터가 부족하여 꾸준한 스킬 분석이 제한됩니다.")

    st.subheader("연도별 신규 등장 / 사라진 스킬")
    new_dead_rows = []
    for i in range(1, len(years)):
        prev_y, curr_y = years[i - 1], years[i]
        prev_skills = set(sy[sy["year"] == prev_y]["skill"])
        curr_skills = set(sy[sy["year"] == curr_y]["skill"])
        new_skills = sorted(curr_skills - prev_skills)
        dead_skills = sorted(prev_skills - curr_skills)
        new_dead_rows.append(
            {
                "기준연도": curr_y,
                "신규 등장 스킬": ", ".join(new_skills[:20]) if new_skills else "-",
                "사라진 스킬": ", ".join(dead_skills[:20]) if dead_skills else "-",
            }
        )
    st.dataframe(pd.DataFrame(new_dead_rows), use_container_width=True)

    st.subheader("직무 카테고리별 요구 역량 비교표")
    rows = []
    for _, r in df[["job_category", "skills"]].iterrows():
        for s in r["skills"]:
            rows.append((r["job_category"], s))
    if rows:
        tmp = pd.DataFrame(rows, columns=["job_category", "skill"])
        piv = tmp.groupby(["job_category", "skill"], as_index=False).size().rename(columns={"size": "cnt"})
        piv = piv.pivot(index="job_category", columns="skill", values="cnt").fillna(0).astype(int)
        st.dataframe(piv, use_container_width=True)
    else:
        st.info("스킬 비교를 위한 데이터가 부족합니다.")


def section_preferred(df: pd.DataFrame) -> None:
    st.header("3) 우대사항 트렌드")

    c1, c2 = st.columns(2)

    with c1:
        trend = df.groupby("year", as_index=False).agg(
            cert_ratio=("pref_cert", "mean"),
            edu_ratio=("pref_edu", "mean"),
            exp_years=("pref_exp_years", "mean"),
        )
        trend_long = trend.melt(id_vars=["year"], var_name="metric", value_name="value")
        fig = px.line(trend_long, x="year", y="value", color="metric", markers=True, title="자격증 / 학력 / 경력 연수 요구 변화")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        by_ind = df.groupby("industry", as_index=False).agg(
            cert_ratio=("pref_cert", "mean"),
            edu_ratio=("pref_edu", "mean"),
            ai_data_ratio=("pref_ai_data", "mean"),
        )
        show = by_ind.melt(id_vars=["industry"], var_name="metric", value_name="ratio")
        fig = px.bar(show, x="industry", y="ratio", color="metric", barmode="group", title="산업군별 우대사항 차이")
        st.plotly_chart(fig, use_container_width=True)

    ai_trend = df.groupby("year", as_index=False)["pref_ai_data"].mean().rename(columns={"pref_ai_data": "ai_data_preferred_ratio"})
    fig = px.bar(ai_trend, x="year", y="ai_data_preferred_ratio", title='"AI·데이터" 관련 우대사항 급증 여부')
    st.plotly_chart(fig, use_container_width=True)


def section_company_insight(df: pd.DataFrame) -> None:
    st.header("4) 기업·산업군별 인사이트")

    st.subheader("대기업 그룹사별 채용 성향 비교")
    group_profile = df.groupby(["group", "job_category"], as_index=False).size().rename(columns={"size": "cnt"})
    fig = px.bar(group_profile, x="group", y="cnt", color="job_category", title="그룹사별 직무 집중도")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("산업군별 요구 스킬 히트맵")
    rows = []
    for _, r in df[["industry", "skills"]].iterrows():
        for s in r["skills"]:
            rows.append((r["industry"], s))
    if rows:
        tmp = pd.DataFrame(rows, columns=["industry", "skill"])
        hm = tmp.groupby(["industry", "skill"], as_index=False).size().rename(columns={"size": "cnt"})
        top_skills = hm.groupby("skill")["cnt"].sum().sort_values(ascending=False).head(20).index.tolist()
        hm = hm[hm["skill"].isin(top_skills)]
        piv = hm.pivot(index="industry", columns="skill", values="cnt").fillna(0)
        fig = px.imshow(piv, title="산업군별 상위 스킬 히트맵", aspect="auto", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("히트맵을 그릴 스킬 데이터가 없습니다.")


def section_jobseeker_guide(df: pd.DataFrame) -> None:
    st.header("5) 구직자 실전 가이드")

    current_year = int(df["year"].max())
    st.subheader(f"직무별 지금 준비해야 할 Top 5 스킬 ({current_year}년 기준)")

    jobs = sorted(df["job_category"].dropna().unique().tolist())
    selected_job = st.selectbox("직무 선택", jobs)

    rows = []
    sub = df[(df["job_category"] == selected_job) & (df["year"] == current_year)]
    for _, r in sub[["skills"]].iterrows():
        for s in r["skills"]:
            rows.append(s)

    if rows:
        freq = pd.Series(rows).value_counts().head(5)
        for skill, cnt in freq.items():
            st.checkbox(f"{skill} (언급 {cnt}회)", value=False, key=f"check_{selected_job}_{skill}")
    else:
        st.info("선택한 직무의 최신 연도 스킬 데이터가 부족합니다.")

    st.subheader("2026 채용 전망")
    ai_ratio_2026 = df[df["year"] == 2026]["pref_ai_data"].mean() if (df["year"] == 2026).any() else np.nan
    top_industry = (
        df[df["year"] == current_year].groupby("industry").size().sort_values(ascending=False).index[0]
        if not df.empty
        else "미상"
    )

    if pd.isna(ai_ratio_2026):
        전망 = (
            "현재 데이터 기준으로 2026년은 AI/데이터 역량을 요구하는 공고가 계속 증가할 가능성이 높습니다. "
            f"특히 {top_industry} 산업군 중심으로 데이터 활용형 직무가 확대될 것으로 보입니다."
        )
    else:
        전망 = (
            f"2026년 데이터에서 AI/데이터 우대 비중은 {ai_ratio_2026:.1%}로 집계되었습니다. "
            "상담 시 기초 데이터 리터러시 + 직무 특화 툴 역량을 함께 준비하도록 안내하는 것이 효과적입니다."
        )

    st.info(전망)


def section_raw_summary(df: pd.DataFrame) -> None:
    st.header("6) 원데이터 요약 테이블")
    base_cols = ["company", "group", "industry", "division", "job_category", "posting_date", "half", "title", "preferred"]
    show_cols = [c for c in base_cols if c in df.columns]
    st.dataframe(df[show_cols].sort_values("posting_date", ascending=False), use_container_width=True, height=360)


def sidebar_controls() -> Dict[str, object]:
    st.sidebar.header("데이터 입력")
    mode = st.sidebar.radio("데이터 소스", ["샘플 데이터", "파일 업로드"], index=0)

    uploaded = None
    if mode == "파일 업로드":
        uploaded = st.sidebar.file_uploader("CSV 파일", type=["csv"])

    st.sidebar.markdown("---")
    st.sidebar.caption("권장 컬럼")
    st.sidebar.code(", ".join(REQUIRED_COLUMNS_GUIDE), language="text")
    st.sidebar.caption(f"무료 버전 권장: 최대 {FREE_MAX_ROWS:,}행")

    return {"mode": mode, "uploaded": uploaded}


# ==============================
# [Step-by-step Logic]
# 1) 데이터 입력 (샘플 또는 업로드)
# 2) 컬럼 표준화 + 날짜/반기/스킬/우대사항 파생
# 3) 섹션별 시각화 임시 출력
# 4) 추후 승인 시 구글시트 적재/API 확장 가능
# ==============================


controls = sidebar_controls()

raw_df = pd.DataFrame()
if controls["mode"] == "샘플 데이터":
    raw_df = create_sample_data()
else:
    up = controls["uploaded"]
    if up is None:
        st.warning("파일을 업로드해주세요.")
    else:
        try:
            raw_df = pd.read_csv(up)
        except Exception as e:
            st.error(f"파일을 읽는 중 문제가 발생했습니다: {e}")

if raw_df.empty:
    st.info("표시할 데이터가 없습니다. 샘플 데이터를 사용하거나 파일을 업로드해주세요.")
    st.stop()

# Free-tier memory guard: sample too-large data to keep the app responsive.
if len(raw_df) > FREE_MAX_ROWS:
    st.warning(f"업로드 데이터가 {len(raw_df):,}행으로 커서 상위 {FREE_MAX_ROWS:,}행만 분석합니다.")
    raw_df = raw_df.head(FREE_MAX_ROWS).copy()

try:
    df = prepare_df(raw_df)
except Exception as e:
    st.error(f"데이터 전처리 중 오류가 발생했습니다: {e}")
    st.stop()

if df.empty:
    st.warning("유효한 날짜(posting_date)를 가진 데이터가 없어 분석을 진행할 수 없습니다.")
    st.info("예: 2026-04-09 형식의 posting_date 컬럼을 확인해주세요.")
    st.stop()

# Global filters
st.sidebar.header("분석 필터")
years = sorted(df["year"].unique().tolist())
selected_years = st.sidebar.multiselect("연도 선택", years, default=years)
industries = sorted(df["industry"].dropna().unique().tolist())
selected_industries = st.sidebar.multiselect("산업군 선택", industries, default=industries)

fdf = df[df["year"].isin(selected_years) & df["industry"].isin(selected_industries)].copy()
if fdf.empty:
    st.warning("필터 결과가 비어 있습니다. 필터를 조정해주세요.")
    st.stop()

section_overview(fdf)
section_skill_analysis(fdf)
section_preferred(fdf)
section_company_insight(fdf)
section_jobseeker_guide(fdf)
section_raw_summary(fdf)

st.success("분석 완료: 상담사 보고/설명용 대시보드가 준비되었습니다.")
