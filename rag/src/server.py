"""
server.py — RAG HTTP 服务

基于 FastAPI，提供 6 个端点：
- POST /retrieve — 混合检索
- POST /reindex — 重建索引
- GET  /health — 健康检查
- POST /explain-retrieval — 检索解释（含详细分数分解）
- GET  /stats — 索引统计
- GET  /routes — 任务路由定义
"""

import json
import os
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from . import indexer
from . import router as router_mod
from . import context_pack as context_pack_mod
from .storage import sqlite_store
from .storage import vector_store
from .retriever import hybrid_retrieve

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ====== Pydantic 模型 ======

class RetrieveRequest(BaseModel):
    query: str = Field(..., description="检索查询文本")
    task_type: str | None = Field(None, description="任务类型（可选，自动路由）")
    project_hint: str | None = Field(None, description="项目提示（保留字段）")
    top_k: int = Field(5, description="返回结果数量", ge=1, le=20)


class ReindexResponse(BaseModel):
    status: str
    documents: int
    chunks: int
    vectors: int
    elapsed_seconds: float


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    sqlite: bool
    vectors: bool


class ExplainRequest(BaseModel):
    query: str = Field(..., description="检索查询文本")
    task_type: str | None = Field(None, description="任务类型")


# ====== 应用 ======

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时：自动初始化数据库
    sqlite_store.initialize()
    print(f"[server] RAG 服务启动，SQLite 状态: {sqlite_store.get_stats()}")
    yield
    # 关闭时
    sqlite_store.close()


app = FastAPI(
    title="novel-harness RAG Service",
    version="1.0.0",
    description="轻量混合 RAG 知识层 — 面向 Agent 消费的写作知识检索服务",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====== 端点 ======

@app.get("/health", response_model=HealthResponse)
def health_check():
    """健康检查"""
    from datetime import datetime
    stats = sqlite_store.get_stats()
    vec_count = vector_store.get_vector_count()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
        sqlite=stats["documents"] > 0,
        vectors=vec_count > 0,
    )


@app.post("/retrieve")
def retrieve(request: RetrieveRequest):
    """混合检索入口"""
    result = hybrid_retrieve(
        query=request.query,
        task_type=request.task_type,
        top_k=request.top_k,
    )

    context_pack = context_pack_mod.build_context_pack(
        query=request.query,
        retrieval_result=result,
        task_type=request.task_type,
        project_hint=request.project_hint,
    )
    context_text = context_pack_mod.context_pack_to_text(context_pack)

    return {
        "context_pack": context_pack,
        "context_text": context_text,
    }


@app.post("/reindex", response_model=ReindexResponse)
def reindex():
    """重建索引"""
    import time
    start = time.time()
    stats = indexer.build_full_index()
    elapsed = time.time() - start
    return ReindexResponse(
        status="ok",
        documents=stats["documents"],
        chunks=stats["chunks"],
        vectors=stats["vectors"],
        elapsed_seconds=round(elapsed, 2),
    )


@app.post("/explain-retrieval")
def explain_retrieval(request: ExplainRequest):
    """检索解释（含详细分数分解）"""
    from .retriever import hybrid_retrieve

    # 路由分析
    route_result = router_mod.route_query(request.query) if not request.task_type else {
        "task_type": request.task_type,
        **router_mod.get_route(request.task_type),
    }

    # 检索
    result = hybrid_retrieve(
        query=request.query,
        task_type=request.task_type,
        top_k=5,
    )

    return {
        "query": request.query,
        "route_analysis": {
            "task_type": route_result.get("task_type"),
            "categories": route_result.get("categories", []),
            "stages": route_result.get("stages", []),
            "confidence": route_result.get("confidence", 0),
        },
        "retrieval": result,
    }


@app.get("/stats")
def stats():
    """索引统计"""
    sqlite_stats = sqlite_store.get_stats()
    vec_count = vector_store.get_vector_count()
    return {
        "sqlite": sqlite_stats,
        "vectors": vec_count,
    }


@app.get("/routes")
def routes():
    """任务路由定义"""
    routes_path = PROJECT_ROOT / "rag" / "config" / "task-routes.json"
    try:
        with open(routes_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500, detail=str(e))
