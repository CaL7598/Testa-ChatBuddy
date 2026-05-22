"""Generate PNG structure diagrams from DEEPSEEK_API_DOCUMENTATION.md (matplotlib)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

INDIGO = "#4f46e5"
VIOLET = "#7c3aed"
SLATE = "#334155"
LIGHT = "#eef2ff"
WHITE = "#ffffff"
BLUE_CLOUD = "#dbeafe"
BLUE_BORDER = "#2563eb"
LOCAL_BG = "#ecfdf5"
LOCAL_BORDER = "#059669"

Side = Literal["top", "bottom", "left", "right"]


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    label: str
    facecolor: str = WHITE
    edgecolor: str = INDIGO
    fontsize: int = 9
    bold: bool = False

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def anchor(self, side: Side, along: float = 0.5) -> tuple[float, float]:
        """along: 0..1 position along that edge (for bottom/top: left→right)."""
        if side == "top":
            return (self.x + self.w * along, self.y + self.h)
        if side == "bottom":
            return (self.x + self.w * along, self.y)
        if side == "left":
            return (self.x, self.y + self.h * along)
        return (self.x + self.w, self.y + self.h * along)

    def draw(self, ax) -> None:
        ax.add_patch(
            FancyBboxPatch(
                (self.x, self.y),
                self.w,
                self.h,
                boxstyle="round,pad=0.02,rounding_size=0.06",
                linewidth=1.6,
                edgecolor=self.edgecolor,
                facecolor=self.facecolor,
            )
        )
        ax.text(
            self.cx,
            self.cy,
            self.label,
            ha="center",
            va="center",
            fontsize=self.fontsize,
            fontweight="bold" if self.bold else "normal",
            color=SLATE,
        )


def _arrow(
    ax,
    src: Box,
    dst: Box,
    src_side: Side,
    dst_side: Side,
    *,
    color: str = SLATE,
    label: str | None = None,
    dashed: bool = False,
    src_along: float = 0.5,
    dst_along: float = 0.5,
) -> None:
    p1, p2 = src.anchor(src_side, src_along), dst.anchor(dst_side, dst_along)
    style = "]-[,widthB=1.0" if dashed else "-|>"
    ax.add_patch(
        FancyArrowPatch(
            p1,
            p2,
            arrowstyle=style,
            mutation_scale=14,
            linewidth=1.5,
            color=color,
            linestyle="--" if dashed else "-",
            shrinkA=3,
            shrinkB=3,
        )
    )
    if label:
        ax.text(
            (p1[0] + p2[0]) / 2,
            (p1[1] + p2[1]) / 2 + 0.14,
            label,
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=SLATE,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85),
        )


def _arrow_elbow(
    ax,
    src: Box,
    dst: Box,
    *,
    y_lane: float,
    color: str = SLATE,
    label: str | None = None,
    dashed: bool = False,
) -> None:
    """Route above boxes: up from src, across, down into dst."""
    x1, x2 = src.cx, dst.cx
    y1, y2 = src.y + src.h, dst.y + dst.h
    verts = [(x1, y1), (x1, y_lane), (x2, y_lane), (x2, y2)]
    ax.add_patch(
        PathPatch(
            MplPath(verts, [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.LINETO]),
            fill=False,
            edgecolor=color,
            linewidth=1.5,
            linestyle="--" if dashed else "-",
        )
    )
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x2, y_lane),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5),
    )
    if label:
        ax.text((x1 + x2) / 2, y_lane + 0.12, label, ha="center", va="bottom", fontsize=7.5, color=SLATE)


def architecture_diagram() -> Path:
    """§2 mermaid: UI→V, V→U, U→E, U→F, U→C, V→C, C→OR→DS, E→F, F-.->U."""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(
        "DeepSeek API Integration — High-Level Architecture\n(Testa StudyBuddy)",
        fontsize=14,
        fontweight="bold",
        color=INDIGO,
        pad=14,
    )

    user = Box(4.8, 8.55, 4.4, 0.8, "User (browser)\nDjango templates + AJAX", LIGHT, INDIGO, bold=True)
    views = Box(0.5, 6.7, 3.4, 0.85, "views.py\nstudy_assistant_views.py", WHITE, INDIGO)
    utils = Box(5.05, 6.7, 3.4, 0.85, "utils.py\nRAG + generators", WHITE, INDIGO)
    client = Box(9.6, 6.7, 3.4, 0.85, "bytez_client.py\nBytezClient", WHITE, INDIGO, bold=True)

    embed = Box(0.5, 4.0, 3.2, 0.95, "EmbeddingClient\nsentence-transformers", LOCAL_BG, LOCAL_BORDER, 8)
    faiss = Box(4.1, 4.0, 3.2, 0.95, "FAISS vector index\nfaiss_index/", LOCAL_BG, LOCAL_BORDER, 8)
    openrouter = Box(8.8, 4.0, 2.5, 0.95, "OpenRouter API\nchat/completions", BLUE_CLOUD, BLUE_BORDER, 8, True)
    deepseek = Box(11.5, 4.0, 2.2, 0.95, "DeepSeek\ndeepseek-chat", BLUE_CLOUD, BLUE_BORDER, 8, True)

    ax.text(7, 7.75, "Django application", ha="center", fontsize=10, fontweight="bold", color=VIOLET)
    ax.text(2.1, 5.25, "Local (no API)", ha="center", fontsize=9, fontweight="bold", color=LOCAL_BORDER)
    ax.text(11.1, 5.25, "Cloud API", ha="center", fontsize=9, fontweight="bold", color=BLUE_BORDER)

    for b in (user, views, utils, client, embed, faiss, openrouter, deepseek):
        b.draw(ax)

    _arrow(ax, user, views, "bottom", "top", color=INDIGO, label="UI → views")
    _arrow(ax, views, utils, "right", "left", color=SLATE, label="views → utils")
    _arrow_elbow(ax, views, client, y_lane=7.85, color=SLATE, label="views → BytezClient")
    _arrow(ax, utils, embed, "bottom", "top", color=LOCAL_BORDER, label="utils → embeddings",
           src_along=0.25, dst_along=0.5)
    _arrow(ax, utils, faiss, "bottom", "top", color=LOCAL_BORDER, label="utils → FAISS",
           src_along=0.55, dst_along=0.5)
    _arrow(ax, utils, client, "right", "left", color=INDIGO, label="utils → BytezClient")
    _arrow(ax, embed, faiss, "right", "left", color=LOCAL_BORDER, label="vectors → index")
    # FAISS returns chunks to utils (horizontal between local row and django row)
    _arrow(ax, faiss, utils, "right", "left", color=LOCAL_BORDER, dashed=True,
           label="similarity_search", src_along=0.65, dst_along=0.35)
    _arrow(ax, client, openrouter, "bottom", "top", color=BLUE_BORDER, label="HTTPS POST JSON")
    _arrow(ax, openrouter, deepseek, "right", "left", color=BLUE_BORDER, label="routes to")

    ax.text(
        0.45,
        2.4,
        "Q&A paths:\n"
        "1. RAG: question → FAISS (k=3) → BytezClient + context → DeepSeek\n"
        "2. Direct: no context → BytezClient + system prompt → DeepSeek\n"
        "3. Fallback: API fail → BeautifulSoup scrape (optional)",
        fontsize=8.5,
        color=SLATE,
        va="top",
        linespacing=1.35,
    )

    out = ASSETS / "deepseek_api_architecture.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def class_structure_diagram() -> Path:
    """§3.2: BytezClient→OpenRouter; EmbeddingClient→SentenceTransformer; callers→BytezClient."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title(
        "DeepSeek Client — Software Structure (bytez_client.py)",
        fontsize=14,
        fontweight="bold",
        color=INDIGO,
        pad=14,
    )

    bytez = Box(
        3.2, 2.5, 5.6, 3.0,
        "BytezClient\napi_key, model\n+ chat(messages) → str\n+ generate_text(...)\n+ answer_question(...)\nget_bytez_client() • HTTP retries",
        LIGHT, INDIGO, 8, True,
    )
    embed = Box(
        0.6, 2.5, 2.3, 3.0,
        "EmbeddingClient\n+ embed_text\n+ embed_documents",
        LOCAL_BG, LOCAL_BORDER, 8, True,
    )
    st = Box(0.35, 6.0, 2.55, 0.85, "SentenceTransformer\nall-MiniLM-L6-v2", LOCAL_BG, LOCAL_BORDER, 8)
    or_box = Box(4.0, 6.0, 2.2, 0.75, "OpenRouter", BLUE_CLOUD, BLUE_BORDER, 9, True)
    ds = Box(6.4, 6.0, 2.0, 0.75, "DeepSeek", BLUE_CLOUD, BLUE_BORDER, 9, True)
    callers = Box(
        3.0, 0.35, 6.0, 1.0,
        "Callers → BytezClient:\nutils.py  •  views.py  •  study_assistant_views.py",
        "#f8fafc", SLATE, 8,
    )

    for b in (bytez, embed, st, or_box, ds, callers):
        b.draw(ax)

    _arrow(ax, embed, st, "top", "bottom", color=LOCAL_BORDER, label="local CPU")
    _arrow(ax, bytez, or_box, "top", "bottom", color=INDIGO, label="HTTPS POST")
    _arrow(ax, or_box, ds, "right", "left", color=BLUE_BORDER, label="inference")
    _arrow(ax, callers, bytez, "top", "bottom", color=SLATE, label="invokes")

    ax.text(0.5, 7.0, "DEFAULT_MODEL = deepseek/deepseek-chat", fontsize=8, color="#64748b", style="italic")

    out = ASSETS / "deepseek_api_class_structure.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def sequence_rag_diagram() -> Path:
    """§4.4 sequenceDiagram — horizontal messages on lifeline x positions."""
    fig, ax = plt.subplots(figsize=(14, 7.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7.5)
    ax.axis("off")
    ax.set_title(
        "Sequence: Question Answering with RAG + DeepSeek",
        fontsize=14,
        fontweight="bold",
        color=INDIGO,
        pad=14,
    )

    specs = [
        ("User", 1.0),
        ("views.py", 3.1),
        ("FAISS +\nembeddings", 5.6),
        ("BytezClient", 8.1),
        ("OpenRouter", 10.3),
        ("DeepSeek", 12.2),
    ]
    y_top, y_bot = 6.6, 1.1
    actors: list[Box] = []
    for name, cx in specs:
        w = 1.65
        b = Box(cx - w / 2, y_top - 0.55, w, 0.6, name, WHITE, SLATE, 8, True)
        b.draw(ax)
        actors.append(b)
        ax.plot([cx, cx], [y_top - 0.55, y_bot], color="#cbd5e1", lw=1.2, ls="--", zorder=0)

    def lifeline_msg(i_from: int, i_to: int, text: str, y: float, *, response: bool = False) -> None:
        x1, x2 = actors[i_from].cx, actors[i_to].cx
        color = SLATE if response else INDIGO
        style = "]-[,widthB=1.0" if response else "-|>"
        ax.add_patch(
            FancyArrowPatch(
                (x1, y),
                (x2, y),
                arrowstyle=style,
                mutation_scale=14,
                linewidth=1.5,
                color=color,
                linestyle="--" if response else "-",
                shrinkA=0,
                shrinkB=0,
            )
        )
        ax.text((x1 + x2) / 2, y + 0.11, text, ha="center", va="bottom", fontsize=7.5, color=SLATE)

    y = 5.55
    lifeline_msg(0, 1, "POST question", y)
    y -= 0.52
    lifeline_msg(1, 2, "similarity_search(question, k=3)", y)
    y -= 0.52
    lifeline_msg(2, 1, "top 3 text chunks", y, response=True)
    y -= 0.52
    lifeline_msg(1, 3, "answer_question(question, context)", y)
    y -= 0.52
    lifeline_msg(3, 4, "POST /v1/chat/completions", y)
    y -= 0.52
    lifeline_msg(4, 5, "forward request", y)
    y -= 0.52
    lifeline_msg(5, 4, "completion", y, response=True)
    y -= 0.52
    lifeline_msg(4, 3, "choices[0].message.content", y, response=True)
    y -= 0.52
    lifeline_msg(3, 1, "answer string", y, response=True)
    y -= 0.52
    lifeline_msg(1, 0, "JSON response", y, response=True)

    ax.text(0.4, 0.3, "Payload: model=deepseek/deepseek-chat • temperature=0.3 • max_tokens=768",
            fontsize=8, color="#64748b", style="italic")
    ax.text(10.5, 0.3, "solid → request    dashed → response", fontsize=8, color=SLATE)

    out = ASSETS / "deepseek_api_sequence_rag.png"
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def main() -> None:
    for path in (architecture_diagram(), class_structure_diagram(), sequence_rag_diagram()):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
