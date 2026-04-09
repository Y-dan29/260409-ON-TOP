import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# [Context & Goal]
# 이 앱은 "고용센터 상담사"가 여러 기업의 채용공고 데이터를 빠르게 해석해
# 내담자 맞춤형 상담 인사이트를 만드는 목적의 데모 대시보드입니다.
# 단순 시각화가 아니라 "상담 의사결정"에 바로 쓰일 수 있도록 섹션을 구성합니다.

# [Tech Stack & Constraints]
# - Python, Streamlit, Pandas, Plotly 중심 경량 구성
# - 민감정보(API Key)는 하드코딩하지 않고 st.secrets / os.getenv 사용 원칙
# - 외부 의존성 실패 시 앱이 멈추지 않도록 예외 방어

st.set_page_config(page_title="온톱(On-Top) 채용 인사이트", page_icon="📈", layout="wide")


@dataclass
class ColumnMap:
    posting_date: str = "posting_date"
    company: str = "company"
    group: str = "group"
    industry: str = "industry"
    division: str = "division"
    job_category: str = "job_category"
    job_title: str = "job_title"
    required_skills: str = "required_skills"
    preferred_text: str = "preferred_text"
    education: str = "education"
    experience_years: str = "experience_years"


def inject_demo_data() -> pd.DataFrame:
    """해커톤 데모를 위한 샘플 데이터를 생성합니다."""
    rng = np.random.default_rng(42)
    years = [2023, 2024, 2025, 2026]
    industries = ["IT", "금융", "제조", "헬스케어", "유통"]
    divisions = ["플랫폼", "데이터", "서비스", "영업", "운영"]
    job_categories = ["백엔드", "프론트엔드", "데이터", "AI", "기획", "마케팅"]
    groups = ["Alpha그룹", "Beta그룹", "Gamma그룹", "Delta그룹"]

    skill_pool = {
        "백엔드": ["Python", "Java", "Spring", "SQL", "AWS", "Docker", "Kubernetes"],
        "프론트엔드": ["JavaScript", "TypeScript", "React", "Vue", "CSS", "Next.js"],
        "데이터": ["SQL", "Python", "Tableau", "Pandas", "ETL", "Spark"],
        "AI": ["Python", "PyTorch", "TensorFlow", "LLM", "MLOps", "데이터분석"],
        "기획": ["커뮤니케이션", "문제해결", "GA", "A/B테스트", "서비스기획"],
        "마케팅": ["콘텐츠", "퍼포먼스", "GA", "CRM", "데이터분석", "브랜딩"],
    }

    cert_tokens = ["정보처리기사", "SQLD", "ADsP", "PMP", "없음"]
    edu_tokens = ["학력무관", "학사", "석사", "박사"]

    rows = []
    for _ in range(700):
        y = int(rng.choice(years, p=[0.2, 0.25, 0.27, 0.28]))
        month = int(rng.integers(1, 13))
        day = int(rng.integers(1, 28))
        industry = str(rng.choice(industries))
        division = str(rng.choice(divisions))
        category = str(rng.choice(job_categories))
        group = str(rng.choice(groups))
        company = f"{group}-{industry}-{rng.integers(1, 25)}"

        base_skills = skill_pool[category]
        k = int(rng.integers(3, 6))
        skills = list(rng.choice(base_skills, size=k, replace=False))

        if y >= 2025 and category in ["AI", "데이터", "백엔드"] and rng.random() > 0.45:
            skills.append("Generative AI")
        if y >= 2026 and rng.random() > 0.55:
            skills.append("Agentic Workflow")

        cert = str(rng.choice(cert_tokens, p=[0.2, 0.22, 0.2, 0.1, 0.28]))
        edu = str(rng.choice(edu_tokens, p=[0.3, 0.45, 0.2, 0.05]))
        exp = int(rng.integers(0, 8))

        pref_fragments = [
            f"우대: {cert}",
            f"학력: {edu}",
            f"경력 {exp}년 이상",
        ]
        if y >= 2025 and rng.random() > 0.35:
            pref_fragments.append("AI/데이터 프로젝트 경험")
        if category == "AI" and rng.random() > 0.5:
            pref_fragments.append("머신러닝 모델 배포 경험")

        rows.append(
            {
                "posting_date": f"{y}-{month:02d}-{day:02d}",
                "company": company,
                "group": group,
                "industry": industry,
                "division": division,
                "job_category": category,
                "job_title": f"{category} 담당자",
                "required_skills": ", ".join(skills),
                "preferred_text": " / ".join(pref_fragments),
                "education": edu,
                "experience_years": exp,
            }
        )

    return pd.DataFrame(rows)


def safe_read_uploaded(file) -> pd.DataFrame:
    """CSV/XLSX 업로드를 안전하게 읽고 실패 시 빈 DF를 반환합니다."""
    if file is None:
        return pd.DataFrame()

    try:
        if file.name.lower().endswith(".csv"):
            return pd.read_csv(file)
        if file.name.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(file)
        st.warning("지원하지 않는 파일 형식입니다. CSV 또는 XLSX를 사용해주세요.")
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()


def standardize_columns(df: pd.DataFrame, cmap: ColumnMap) -> pd.DataFrame:
    """컬럼 누락에 대비해 기본 컬럼을 만들고 타입을 정리합니다."""
    out = df.copy()

    required = [
        cmap.posting_date,
        cmap.company,
        cmap.group,
        cmap.industry,
        cmap.division,
        cmap.job_category,
        cmap.job_title,
        cmap.required_skills,
        cmap.preferred_text,
        cmap.education,
        cmap.experience_years,
    ]

    for col in required:
        if col not in out.columns:
            out[col] = ""

    out[cmap.posting_date] = pd.to_datetime(out[cmap.posting_date], errors="coerce")
    out["year"] = out[cmap.posting_date].dt.year
    out["month"] = out[cmap.posting_date].dt.month
    out["half"] = np.where(out["month"].between(1, 6), "상반기", "하반기")

    out[cmap.experience_years] = pd.to_numeric(out[cmap.experience_years], errors="coerce")
    out[cmap.experience_years] = out[cmap.experience_years].fillna(0)

    text_cols = [
        cmap.company,
        cmap.group,
        cmap.industry,
        cmap.division,
        cmap.job_category,
        cmap.job_title,
        cmap.required_skills,
        cmap.preferred_text,
        cmap.education,
    ]

    for c in text_cols:
        out[c] = out[c].fillna("").astype(str)

    out = out.dropna(subset=["year"])
    out["year"] = out["year"].astype(int)
    out["month"] = out["month"].fillna(0).astype(int)

    return out


def tokenize_skills(series: pd.Series) -> List[str]:
    tokens: List[str] = []
    for txt in series.fillna("").astype(str):
        parts = re.split(r"[,/|;\n]", txt)
        for p in parts:
            t = p.strip()
            if not t:
                continue
            if len(t) <= 1:
                continue
            tokens.append(t)
    return tokens


def extract_skill_frame(df: pd.DataFrame, cmap: ColumnMap) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        parts = re.split(r"[,/|;\n]", str(r[cmap.required_skills]))
        for p in parts:
            s = p.strip()
            if s:
                rows.append(
                    {
                        "year": r["year"],
                        "industry": r[cmap.industry],
                        "job_category": r[cmap.job_category],
                        "skill": s,
                    }
                )
    return pd.DataFrame(rows)


def build_wordcloud(tokens: List[str]):
    """wordcloud 라이브러리가 없을 때는 None을 반환해 대체 UI를 사용합니다."""
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt

        freq = pd.Series(tokens).value_counts().to_dict()
        wc = WordCloud(width=1200, height=500, background_color="white").generate_from_frequencies(freq)
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        return fig
    except Exception:
        return None


def ai_data_preference_flag(text: str) -> int:
    pattern = r"(AI|인공지능|데이터|머신러닝|딥러닝|LLM)"
    return int(bool(re.search(pattern, str(text), flags=re.IGNORECASE)))


def education_bucket(text: str) -> str:
    t = str(text)
    if re.search(r"박사", t):
        return "박사"
    if re.search(r"석사", t):
        return "석사"
    if re.search(r"학사|대졸", t):
        return "학사"
    if re.search(r"무관", t):
        return "학력무관"
    return "기타"


def certifications_flag(text: str) -> int:
    return int(bool(re.search(r"(자격증|기사|SQLD|ADsP|PMP|license|cert)", str(text), re.IGNORECASE)))


def build_2026_outlook(df: pd.DataFrame, skill_df: pd.DataFrame, cmap: ColumnMap) -> str:
    latest_year = int(df["year"].max()) if not df.empty else 2026

    ai_rate_by_year = (
        df.groupby("year")["ai_data_pref"].mean().reset_index().sort_values("year") if not df.empty else pd.DataFrame()
    )
    ai_msg = "AI·데이터 우대 증가가 관찰되지 않았습니다."
    if len(ai_rate_by_year) >= 2:
        delta = (ai_rate_by_year.iloc[-1]["ai_data_pref"] - ai_rate_by_year.iloc[-2]["ai_data_pref"]) * 100
        if delta > 0:
            ai_msg = f"AI·데이터 우대 비중이 전년 대비 {delta:.1f}%p 상승했습니다."
        else:
            ai_msg = f"AI·데이터 우대 비중이 전년 대비 {abs(delta):.1f}%p 하락/정체했습니다."

    top_skills = "데이터 부족"
    if not skill_df.empty:
        recent = skill_df[skill_df["year"] == latest_year]
        if recent.empty:
            recent = skill_df
        top_skills = ", ".join(recent["skill"].value_counts().head(5).index.tolist())

    return (
        f"2026 전망: 최근 데이터 기준으로 기업의 채용 공고는 디지털/데이터 중심 역량을 계속 요구하는 흐름입니다. "
        f"{ai_msg} 특히 {top_skills} 역량의 우선순위가 높아, 구직자는 포트폴리오와 실무 프로젝트 증빙을 함께 준비하는 전략이 유효합니다."
    )


def recommend_adjacent_jobs(
    skill_df: pd.DataFrame,
    context_df: pd.DataFrame,
    target_job: str,
    latest_year: int,
    industry_weight: float = 0.25,
) -> List[Dict[str, str]]:
    """
    지원 직무와 공통 스킬이 많은 인접 직무를 1~3순위로 추천합니다.
    점수 = 스킬 유사도 + 산업군 일치 가중치.
    - 스킬 유사도: Jaccard(교집합/합집합) + 공통 스킬 수 보정
    - 산업군 일치도: 직무별 산업군 분포 코사인 유사도
    """
    if skill_df.empty:
        return []

    year_scope = skill_df[skill_df["year"] == latest_year].copy()
    if year_scope.empty:
        year_scope = skill_df.copy()

    job_skill_map: Dict[str, set] = (
        year_scope.groupby("job_category")["skill"].apply(lambda s: set(s.dropna().astype(str))).to_dict()
    )

    target_skills = job_skill_map.get(target_job, set())
    if not target_skills:
        target_skills = set(
            skill_df.loc[skill_df["job_category"] == target_job, "skill"].dropna().astype(str).tolist()
        )

    if not target_skills:
        return []

    # 산업군 일치도 계산용 데이터 구성
    ind_scope = context_df[context_df["year"] == latest_year].copy()
    if ind_scope.empty:
        ind_scope = context_df.copy()

    industry_sim_map: Dict[str, float] = {}
    if not ind_scope.empty and "job_category" in ind_scope.columns and "industry" in ind_scope.columns:
        ind_pivot = (
            ind_scope.groupby(["job_category", "industry"])
            .size()
            .reset_index(name="count")
            .pivot(index="job_category", columns="industry", values="count")
            .fillna(0)
        )

        if target_job in ind_pivot.index:
            target_vec = ind_pivot.loc[target_job].to_numpy(dtype=float)
            target_norm = float(np.linalg.norm(target_vec))
            for job in ind_pivot.index.tolist():
                cand_vec = ind_pivot.loc[job].to_numpy(dtype=float)
                cand_norm = float(np.linalg.norm(cand_vec))
                if target_norm == 0 or cand_norm == 0:
                    industry_sim_map[job] = 0.0
                else:
                    sim = float(np.dot(target_vec, cand_vec) / (target_norm * cand_norm))
                    industry_sim_map[job] = max(0.0, min(1.0, sim))

    scored: List[Tuple[str, float, List[str]]] = []
    for job, skills in job_skill_map.items():
        if job == target_job or not skills:
            continue
        inter = target_skills & skills
        union = target_skills | skills
        if not union:
            continue
        jaccard = len(inter) / len(union)
        skill_score = jaccard + (len(inter) * 0.01)
        industry_score = industry_sim_map.get(job, 0.0)
        final_score = (1.0 - industry_weight) * skill_score + industry_weight * industry_score
        scored.append((job, final_score, sorted(list(inter))[:5], industry_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top3 = scored[:3]
    result = []
    for rank, (job, score, common_skills, industry_score) in enumerate(top3, start=1):
        result.append(
            {
                "rank": f"{rank}순위",
                "job": job,
                "score": f"{score:.2f}",
                "industry_match": f"{industry_score:.2f}",
                "common_skills": ", ".join(common_skills) if common_skills else "-",
            }
        )
    return result


# [Step-by-step Logic]
# 1) 데이터 추출/정제 -> 2) 역량/우대 분석용 파생변수 생성 -> 3) 섹션별 시각화 -> 4) 상담 사용용 체크리스트 출력

def main() -> None:
    st.title("온톱(On-Top) 채용 인사이트 대시보드")
    st.caption("고용센터 상담사의 빠른 의사결정을 위한 채용 트렌드/역량 분석 데모")

    with st.sidebar:
        st.subheader("데이터 입력")
        uploaded = st.file_uploader("채용 공고 데이터 업로드 (CSV/XLSX)", type=["csv", "xlsx", "xls"])
        use_demo = st.toggle("샘플 데이터 사용", value=True)

        st.markdown("---")
        st.subheader("필터")

    raw = safe_read_uploaded(uploaded)
    if raw.empty and use_demo:
        raw = inject_demo_data()

    if raw.empty:
        st.warning("분석할 데이터가 없습니다. 파일을 업로드하거나 샘플 데이터를 켜주세요.")
        return

    cmap = ColumnMap()

    try:
        df = standardize_columns(raw, cmap)
    except Exception as e:
        st.error(f"데이터 정제 중 오류가 발생했습니다: {e}")
        return

    if df.empty:
        st.warning("유효한 날짜가 없어 분석할 수 없습니다. posting_date 컬럼을 확인해주세요.")
        return

    with st.sidebar:
        years = sorted(df["year"].dropna().unique().tolist())
        selected_years = st.multiselect("연도", years, default=years)

        inds = sorted(df[cmap.industry].unique().tolist())
        selected_inds = st.multiselect("산업군", inds, default=inds)

        jobs = sorted(df[cmap.job_category].unique().tolist())
        selected_jobs = st.multiselect("직무", jobs, default=jobs)

    fdf = df[
        (df["year"].isin(selected_years))
        & (df[cmap.industry].isin(selected_inds))
        & (df[cmap.job_category].isin(selected_jobs))
    ].copy()

    if fdf.empty:
        st.warning("필터 결과가 없습니다. 필터 조건을 완화해주세요.")
        return

    fdf["ai_data_pref"] = fdf[cmap.preferred_text].apply(ai_data_preference_flag)
    fdf["cert_flag"] = fdf[cmap.preferred_text].apply(certifications_flag)
    fdf["edu_bucket"] = fdf[cmap.education].apply(education_bucket)

    skill_df = extract_skill_frame(fdf, cmap)

    st.markdown("## 채용 트렌드 Overview")
    c1, c2 = st.columns(2)

    with c1:
        y_count = fdf.groupby("year").size().reset_index(name="count")
        fig = px.bar(y_count, x="year", y="count", text="count", title="연도별 채용 공고 수 변화")
        fig.update_layout(xaxis_title="연도", yaxis_title="공고 수")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        ind_share = fdf.groupby(["year", cmap.industry]).size().reset_index(name="count")
        total = ind_share.groupby("year")["count"].transform("sum")
        ind_share["share"] = ind_share["count"] / total
        fig = px.area(
            ind_share,
            x="year",
            y="share",
            color=cmap.industry,
            title="산업군별 채용 비중 추이",
            groupnorm="percent",
        )
        fig.update_layout(yaxis_title="비중(%)")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        half_div = fdf.groupby(["year", "half", cmap.division]).size().reset_index(name="count")
        fig = px.bar(
            half_div,
            x="year",
            y="count",
            color="half",
            barmode="group",
            facet_col=cmap.division,
            facet_col_wrap=3,
            title="연도별 상/하반기 사업부별 채용 추이",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        job_trend = fdf.groupby(["year", cmap.job_category]).size().reset_index(name="count")
        fig = px.line(job_trend, x="year", y="count", color=cmap.job_category, markers=True, title="직무 종류 변화 추이")
        st.plotly_chart(fig, use_container_width=True)

    season = fdf.groupby(["half", "month"]).size().reset_index(name="count")
    if not season.empty:
        pivot = season.pivot(index="half", columns="month", values="count").fillna(0)
        fig = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=[str(m) for m in pivot.columns.tolist()],
                y=pivot.index.tolist(),
                colorscale="Blues",
            )
        )
        fig.update_layout(title="상/하반기 채용 시즌 패턴", xaxis_title="월", yaxis_title="반기")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("## 직무별 요구 역량 분석")
    wc_col, top_col = st.columns([1.2, 1])

    all_tokens = tokenize_skills(fdf[cmap.required_skills])

    with wc_col:
        st.subheader("전체 공고 Top 키워드")
        wc_fig = build_wordcloud(all_tokens)
        if wc_fig is not None:
            st.pyplot(wc_fig, clear_figure=True)
        else:
            st.warning("워드클라우드 라이브러리 사용이 어려워 Top 키워드 막대그래프로 대체합니다.")
            top_keywords = pd.Series(all_tokens).value_counts().head(20).reset_index()
            top_keywords.columns = ["skill", "count"]
            fig = px.bar(top_keywords, x="skill", y="count", title="Top 키워드")
            st.plotly_chart(fig, use_container_width=True)

    with top_col:
        st.subheader("3년간 꾸준히 요구된 필수 스킬")
        if skill_df.empty:
            st.info("스킬 데이터가 부족합니다.")
        else:
            recent_years = sorted(skill_df["year"].unique())[-3:]
            yearly_sets = []
            for y in recent_years:
                yearly_sets.append(set(skill_df.loc[skill_df["year"] == y, "skill"].unique().tolist()))
            common_skills = set.intersection(*yearly_sets) if yearly_sets else set()
            if common_skills:
                common_df = (
                    skill_df[skill_df["skill"].isin(list(common_skills))]["skill"].value_counts().head(15).reset_index()
                )
                common_df.columns = ["skill", "count"]
                st.dataframe(common_df, use_container_width=True)
            else:
                st.info("최근 3년 공통 스킬이 없습니다.")

    st.subheader("연도별 신규 등장 / 사라진 스킬")
    if not skill_df.empty:
        years_sorted = sorted(skill_df["year"].unique().tolist())
        records = []
        for i in range(1, len(years_sorted)):
            py, cy = years_sorted[i - 1], years_sorted[i]
            prev_set = set(skill_df.loc[skill_df["year"] == py, "skill"].unique().tolist())
            curr_set = set(skill_df.loc[skill_df["year"] == cy, "skill"].unique().tolist())
            new_sk = ", ".join(sorted(list(curr_set - prev_set))[:10]) or "-"
            gone_sk = ", ".join(sorted(list(prev_set - curr_set))[:10]) or "-"
            records.append({"연도": cy, "신규 스킬(최대10)": new_sk, "사라진 스킬(최대10)": gone_sk})
        st.dataframe(pd.DataFrame(records), use_container_width=True)

    st.subheader("직무 카테고리별 요구 역량 비교표")
    if not skill_df.empty:
        comp = (
            skill_df.groupby(["job_category", "skill"]).size().reset_index(name="count").sort_values(["job_category", "count"], ascending=[True, False])
        )
        top_comp = comp.groupby("job_category").head(5)
        st.dataframe(top_comp, use_container_width=True)

    st.markdown("## 우대사항 트렌드")
    p1, p2 = st.columns(2)

    with p1:
        pref_year = fdf.groupby("year").agg(
            cert_rate=("cert_flag", "mean"),
            avg_exp=(cmap.experience_years, "mean"),
        ).reset_index()
        fig = px.line(pref_year, x="year", y=["cert_rate", "avg_exp"], markers=True, title="자격증/경력 연수 요구 변화")
        st.plotly_chart(fig, use_container_width=True)

        edu_year = fdf.groupby(["year", "edu_bucket"]).size().reset_index(name="count")
        fig2 = px.bar(edu_year, x="year", y="count", color="edu_bucket", barmode="stack", title="연도별 학력 요구 변화")
        st.plotly_chart(fig2, use_container_width=True)

    with p2:
        ind_pref = fdf.groupby(cmap.industry).agg(
            cert_rate=("cert_flag", "mean"),
            ai_data_rate=("ai_data_pref", "mean"),
            avg_exp=(cmap.experience_years, "mean"),
        ).reset_index()
        st.subheader("산업군별 우대사항 차이")
        st.dataframe(ind_pref, use_container_width=True)

        ai_year = fdf.groupby("year")["ai_data_pref"].mean().reset_index(name="rate")
        fig3 = px.bar(ai_year, x="year", y="rate", title="AI·데이터 관련 우대사항 급증 여부")
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("## 기업·산업군별 인사이트")
    i1, i2 = st.columns(2)

    with i1:
        st.subheader("대기업 그룹사별 채용 성향 비교")
        grp = fdf.groupby(cmap.group).agg(
            postings=(cmap.company, "count"),
            ai_pref_rate=("ai_data_pref", "mean"),
            avg_exp=(cmap.experience_years, "mean"),
        ).reset_index()
        grp = grp.sort_values("postings", ascending=False).head(10)
        st.dataframe(grp, use_container_width=True)

    with i2:
        st.subheader("산업군별 요구 스킬 히트맵")
        if skill_df.empty:
            st.info("스킬 데이터가 부족합니다.")
        else:
            top_skills = skill_df["skill"].value_counts().head(15).index.tolist()
            heat = (
                skill_df[skill_df["skill"].isin(top_skills)]
                .groupby(["industry", "skill"])
                .size()
                .reset_index(name="count")
            )
            pivot = heat.pivot(index="industry", columns="skill", values="count").fillna(0)
            fig = go.Figure(
                data=go.Heatmap(
                    z=pivot.values,
                    x=pivot.columns.tolist(),
                    y=pivot.index.tolist(),
                    colorscale="YlGnBu",
                )
            )
            fig.update_layout(xaxis_title="스킬", yaxis_title="산업군")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("## 구직자 실전 가이드")
    job_pick = st.selectbox("지원 직무 선택", sorted(fdf[cmap.job_category].unique().tolist()))
    industry_weight = st.slider(
        "추천 점수에서 산업군 일치 가중치",
        min_value=0.0,
        max_value=0.8,
        value=0.25,
        step=0.05,
        help="값이 높을수록 지원 직무와 산업군 분포가 유사한 직무를 더 우선 추천합니다.",
    )
    latest_year = int(fdf["year"].max())

    if not skill_df.empty:
        target = skill_df[(skill_df["job_category"] == job_pick) & (skill_df["year"] == latest_year)]
        if target.empty:
            target = skill_df[skill_df["job_category"] == job_pick]
        top5 = target["skill"].value_counts().head(5).index.tolist()
    else:
        top5 = []

    st.write(f"### {job_pick} 직무: 지금 준비해야 할 Top 5 스킬")
    if top5:
        for s in top5:
            st.checkbox(f"{s} 관련 포트폴리오/실습 완료", value=False, key=f"chk_{job_pick}_{s}")
    else:
        st.info("해당 직무의 스킬 데이터가 충분하지 않습니다.")

    recs = recommend_adjacent_jobs(
        skill_df=skill_df,
        context_df=fdf,
        target_job=job_pick,
        latest_year=latest_year,
        industry_weight=industry_weight,
    )
    st.write("### 지원가능한 직무 추천 순위")
    if recs:
        rec_df = pd.DataFrame(recs)
        one = rec_df.loc[rec_df["rank"] == "1순위", "job"].iloc[0] if (rec_df["rank"] == "1순위").any() else "-"
        two = rec_df.loc[rec_df["rank"] == "2순위", "job"].iloc[0] if (rec_df["rank"] == "2순위").any() else "-"
        three = rec_df.loc[rec_df["rank"] == "3순위", "job"].iloc[0] if (rec_df["rank"] == "3순위").any() else "-"

        summary_row = pd.DataFrame(
            [
                {
                    "지원 직무": job_pick,
                    "지원가능 직무 1순위": one,
                    "지원가능 직무 2순위": two,
                    "지원가능 직무 3순위": three,
                }
            ]
        )
        st.dataframe(summary_row, use_container_width=True)
        st.dataframe(
            rec_df.rename(
                columns={
                    "rank": "순위",
                    "job": "추천 직무",
                    "score": "종합 점수",
                    "industry_match": "산업군 일치도",
                    "common_skills": "공통 스킬",
                }
            ),
            use_container_width=True,
        )
    else:
        st.info("추천 가능한 유사 직무 데이터가 부족합니다.")

    st.info(build_2026_outlook(fdf, skill_df, cmap))

    st.markdown("## 참고: 원데이터 요약 테이블")
    summary = (
        fdf.groupby(["year", cmap.industry, cmap.job_category])
        .agg(
            공고수=(cmap.company, "count"),
            평균경력연수=(cmap.experience_years, "mean"),
            AI데이터우대비율=("ai_data_pref", "mean"),
        )
        .reset_index()
        .sort_values(["year", "공고수"], ascending=[False, False])
    )
    st.dataframe(summary, use_container_width=True)

    st.caption("보안 원칙: API 키 등 민감정보는 st.secrets 또는 환경변수(os.getenv)로 관리하세요.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # [Edge Case Handling] 데모 중 치명적 중단 방지
        st.error(f"앱 실행 중 예상치 못한 오류가 발생했습니다: {e}")
        st.warning("데이터 형식을 확인하거나 샘플 데이터로 다시 시도해주세요.")
