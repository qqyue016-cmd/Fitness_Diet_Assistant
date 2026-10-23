import csv
import re

from pathlib import Path
from langchain_chroma import Chroma
from utils.path_tool import get_abs_path
from utils.config_tool import config_chroma
from utils.logger_tool import logger
from ai.client import embedding_model
from langchain_core.documents import Document

class VectorStoreService:
    def __init__(self):
        self.chroma = Chroma(
            collection_name=config_chroma['collection_name'],
            persist_directory=get_abs_path(config_chroma['persist_directory']),
            embedding_function=embedding_model,
            collection_metadata=config_chroma['collection_metadata']
        )

    def load_documents(self) -> list[Document]:
        """读 data/knowledge/*.csv，按二级标题切分为 Document 列表。"""
        data_dir = Path(get_abs_path(config_chroma['data_path']))
        csv_files = sorted(data_dir.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"知识库目录下没有 CSV 文件：{data_dir}")

        documents = []
        for path in csv_files:
            with open(path,"r",encoding="utf-8-sig")as fh:
                for row in csv.DictReader(fh):
                    documents.extend(self._split_row(row))

        logger.info(f"[知识库] {len(csv_files)} 篇文档 → {len(documents)} 个 chunk")
        return documents


    @staticmethod
    def _split_row(row: dict) ->list[Document]:
        """把一篇 CSV 的一行切成多个 chunk。"""
        doc_id = f"{int(row["篇号"]):02d}"
        full_tittle = row["文章标题"].strip()
        short_tittle = full_tittle.split("：")[0]

        parts = [
            p.strip()
            for p in re.split(r"(?=^## )",row["正文内容"],flags=re.M)\
            if p.strip()
        ]

        docs = []
        for idx, part in enumerate(parts,1):
            section = re.sub(
                r"^\d+[.、]\s*",
                "",
                re.sub(r"^#+\s*", "", part.splitlines()[0]),
            ).strip()

            chunk_id = f"{doc_id}_s{idx}"
            docs.append(Document(
                page_content=f"【{short_tittle} > {section}】\n{part}",
                metadata={
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "doc_title": full_tittle,
                    "section": section,
                    "category": row["主题类别"].strip(),
                    "tags": row["主题标签/核心关键词"].strip(),
                    "source": row["参考来源"].strip(),
                },
            ))

        return docs

    def build(self) -> int:
        """建库。可重复执行——固定 ids 保证幂等。"""
        docs = self.load_documents()
        self.chroma.add_documents(docs, ids=[d.metadata["chunk_id"] for d in docs])
        count = self.chroma._collection.count()
        logger.info(f"[知识库] 入库完成，当前 {count} 条")
        return count

    def get_retriever(self):
        return self.chroma.as_retriever(search_kwargs={"k": config_chroma['k']})

if __name__ == '__main__':
    v = VectorStoreService()
    print("建库:", v.build())  # 期望 35
    print("再建:", v.build())  # 期望还是 35
    for d, s in v.chroma.similarity_search_with_score("减脂期蛋白质吃多少", k=3):
        print(f"{s:.4f}  {d.metadata['chunk_id']}  {d.metadata['section']}")

