# 贡献指南

先在 Issue 中提供中文词、当前英文、建议英文及一两个中文例句。英文提示需要短、常见，且不要把固定词的构词字义冒充整个词义。

词库修改：

1. 编辑 `data/vocabulary.json`，保持 `hanzi` 唯一。`annotation` 是实际绘制的 ASCII 小字。
2. 如需整词不标，将其从词库移出，并在 `data/protection.json` 添加 `annotation: ""` 的条目。
3. 运行 `npm run check`、`npm test`、`npm run build`，在 `npm run demo` 中检查实际效果。
4. 提交代码和数据变更，不提交 `dist/`、`.cache/`、下载底字、虚拟环境或字体压缩包。

构建会检查所有规则的实际排版、保护词和标注关闭，以及原底字的字符覆盖和 OpenType 功能。新增的复杂排版行为应增加相应检查。

贡献原创代码按 MIT 许可；词典派生修改遵循已有数据 CC BY-SA 4.0 许可。新增数据必须注明来源，不能把其他许可的数据重新标成 MIT。

见 `docs/releasing.md` 了解发布流程。
