import importlib
from pathlib import Path


SOURCE_DIR = Path("knowledge_base/sources")


def test_retrieves_power_and_water_balance_page() -> None:
    knowledge = importlib.import_module("dispatch_assistant.knowledge")
    index = knowledge.build_knowledge_index(SOURCE_DIR)
    evidence = index.retrieve("功率平衡和水量平衡约束是什么", top_k=3)

    matched = [item for item in evidence if item.source_id == "KB-002" and item.page == 10]
    assert matched
    assert "功率平衡" not in matched[0].quote
    assert "Power balance" in matched[0].quote
    assert "Water balance" in matched[0].quote


def test_retrieves_complementarity_pages_for_chinese_query() -> None:
    knowledge = importlib.import_module("dispatch_assistant.knowledge")
    index = knowledge.build_knowledge_index(SOURCE_DIR)
    evidence = index.retrieve("水电怎样补偿风电和光伏波动", top_k=4)

    assert any(item.source_id == "KB-002" and item.page in {7, 9, 16} for item in evidence)


def test_returns_empty_for_unrelated_query() -> None:
    knowledge = importlib.import_module("dispatch_assistant.knowledge")
    index = knowledge.build_knowledge_index(SOURCE_DIR)

    assert index.retrieve("蛋白质折叠与药物分子动力学", min_score=0.05) == []
