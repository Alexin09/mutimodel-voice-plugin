"""后处理 Pipeline 单元测试"""

import pytest
from mutimodel_voice_plugin.processors.base import ProcessorResult
from mutimodel_voice_plugin.processors.filler_filter import FillerFilterProcessor
from mutimodel_voice_plugin.processors.dictionary_replace import DictionaryReplaceProcessor
from mutimodel_voice_plugin.processors.pipeline import ProcessorPipeline


@pytest.mark.asyncio
async def test_filler_filter_zh():
    """测试中文填充词过滤"""
    processor = FillerFilterProcessor()
    result = ProcessorResult(text="嗯那个就是说我们下周三开会讨论一下")
    result = await processor.process(result)
    assert "嗯" not in result.text
    assert "那个" not in result.text
    assert "就是说" not in result.text
    assert "开会" in result.text


@pytest.mark.asyncio
async def test_filler_filter_preserves_content():
    """填充词过滤不应删除有意义的内容"""
    processor = FillerFilterProcessor()
    result = ProcessorResult(text="请把文件发给我")
    result = await processor.process(result)
    assert result.text == "请把文件发给我"


@pytest.mark.asyncio
async def test_dictionary_replace():
    """测试词典替换"""
    processor = DictionaryReplaceProcessor(replacements={"欧克二": "OKR", "皮皮迪": "PPT"})
    result = ProcessorResult(text="我们来讨论一下欧克二和皮皮迪")
    result = await processor.process(result)
    assert "OKR" in result.text
    assert "PPT" in result.text
    assert "欧克二" not in result.text


@pytest.mark.asyncio
async def test_pipeline_chain():
    """测试 Pipeline 链式执行"""
    pipeline = ProcessorPipeline()
    pipeline.add(FillerFilterProcessor())
    pipeline.add(DictionaryReplaceProcessor(replacements={"欧克二": "OKR"}))

    result = await pipeline.run("嗯那个我们来讨论一下欧克二")
    assert "嗯" not in result.text
    assert "那个" not in result.text
    assert "OKR" in result.text


@pytest.mark.asyncio
async def test_pipeline_empty_text():
    """空文本不应崩溃"""
    pipeline = ProcessorPipeline()
    pipeline.add(FillerFilterProcessor())
    result = await pipeline.run("")
    assert result.text == ""
