from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.services.policy_service import to_detail


def export_excel(policies: list[Policy]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "政策列表"
    ws.append(
        [
            "政策ID",
            "标题",
            "发文机构",
            "发布时间",
            "生效时间",
            "政策层级",
            "分类",
            "原文链接",
            "抓取时间",
            "录入方式",
            "摘要",
        ]
    )
    for p in policies:
        cats = "、".join(sorted({c.category for c in p.categories}))
        ws.append(
            [
                p.id,
                p.title,
                p.issuing_org,
                p.publish_time.isoformat() if p.publish_time else "",
                p.effective_time.isoformat() if p.effective_time else "",
                p.policy_level,
                cats,
                p.original_url,
                p.crawl_time.isoformat() if p.crawl_time else "",
                p.ingest_method,
                p.summary,
            ]
        )
    ws2 = wb.create_sheet("合规摘要")
    ws2.append(["政策ID", "标题", "适用主体", "核心要求", "风险处罚", "行动建议", "模型", "生成时间", "原文链接"])
    for p in policies:
        analysis = p.analysis
        if not analysis:
            continue
        req = "；".join(_as_text(x) for x in (analysis.core_requirements or [])[:5])
        risk = "；".join(_as_text(x) for x in (analysis.risk_and_penalties or [])[:5])
        act = "；".join(_as_text(x) for x in (analysis.action_suggestions or [])[:5])
        ws2.append(
            [
                p.id,
                p.title,
                analysis.applicable_subjects,
                req,
                risk,
                act,
                analysis.model_name,
                analysis.generated_at.isoformat() if analysis.generated_at else "",
                p.original_url,
            ]
        )
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_pdf(session: Session, policy: Policy) -> bytes:
    detail = to_detail(policy)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=detail.title)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("cn_title", parent=styles["Heading1"], fontName="STSong-Light", fontSize=16, leading=22)
    h_style = ParagraphStyle("cn_h", parent=styles["Heading2"], fontName="STSong-Light", fontSize=12, leading=18)
    body = ParagraphStyle("cn_body", parent=styles["Normal"], fontName="STSong-Light", fontSize=9, leading=14)
    story = [
        Paragraph(_esc(detail.title), title_style),
        Spacer(1, 8),
        Paragraph(_esc(f"发文机构：{detail.issuing_org}"), body),
        Paragraph(_esc(f"发布时间：{detail.publish_time or '-'}  生效时间：{detail.effective_time or '-'}"), body),
        Paragraph(_esc(f"原文链接：{detail.original_url}"), body),
        Paragraph(_esc(f"抓取时间：{detail.crawl_time}  录入方式：{detail.ingest_method}"), body),
        Spacer(1, 10),
        Paragraph("结构化解析", h_style),
    ]
    if detail.structured:
        story.append(Paragraph(_esc(f"适用范围：{detail.structured.applicable_scope}"), body))
        story.append(Paragraph(_esc("主题：" + "、".join(detail.structured.themes)), body))
    if detail.analysis:
        story.append(Paragraph("合规影响分析（含推断与建议，不构成法律意见）", h_style))
        story.append(Paragraph(_esc(f"适用主体：{detail.analysis.applicable_subjects}"), body))
        for req in detail.analysis.core_requirements:
            story.append(Paragraph(_esc("· " + _as_text(req)), body))
        story.append(Paragraph("风险与处罚依据", h_style))
        for item in detail.analysis.risk_and_penalties:
            story.append(Paragraph(_esc("· " + _as_text(item)), body))
        story.append(Paragraph("通用行动建议", h_style))
        for item in detail.analysis.action_suggestions:
            story.append(Paragraph(_esc("· " + _as_text(item)), body))
    story.append(Paragraph("原文摘录", h_style))
    story.append(Paragraph(_esc(detail.content[:3500]), body))
    doc.build(story)
    return buf.getvalue()


def _as_text(value) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or value.get("quote") or "")
    return str(value)


def _esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def export_dir() -> Path:
    return Path("data/runtime/exports")
