# 城投债会议纪要整理 Skill

这个 skill 用于把城投公司调研录音转写、会议要点或问答原文，整理成统一格式的 Word 调研纪要。

## 内容

- `SKILL.md`：触发条件、整理原则、分类规则和交付流程
- `references/classification-rules.md`：区域、业务、债务三类问答的分类细则
- `references/report-template.md`：纪要内容与格式参考
- `references/reference.docx`：生成 Word 文件时使用的版式基准模板
- `scripts/finalize_docx_from_reference.py`：将生成稿冻结到基准模板结构的校验脚本

## 使用说明

生成草稿时，必须将 `references/reference.docx` 作为 reference document；生成后运行冻结脚本，确认版式结构与模板一致。

本目录不包含任何具体公司会议录音、内部数据或个人信息。
