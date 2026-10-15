# 发布字体

1. 确认词义修订、来源署名和许可完整，更新 `package.json` 与 `font.config.json` 的版本，保持一致。
2. 本地执行 `npm ci && npm run check && npm test`，准备 Python 依赖后执行 `npm run font:fetch && npm run build && npm run package`。
3. 检查 `dist/validation.json`，人工检查 `npm run demo` 中的样例、长词和长释义。
4. 提交 main 的源码变更，创建与配置一致的版本标签，例如 `v0.2.0`，并推送标签。
5. `.github/workflows/release.yml` 自动构建并验证，再发布 OTF、完整 WOFF2、含许可的 ZIP 和校验值到 GitHub Releases。

CI 的普通 main/PR 构建仅上传 Actions 构建附件，不创建公开 Release。标签推送才触发发布。工作流已配置，但首次远端运行仍需要验证 GitHub runner、网络和仓库 Actions 权限。

`dist/` 不进入 Git 历史。单独的字体下载仍需遵守 OFL，并保留对应的数据许可与署名；推荐下载含许可说明的 ZIP。

## 初版历史整理

本地旧初始提交已备份为 `.cache/pre-refactor.bundle`，并将 main 整理成只包含源码的新初始提交。备份不进入 Git，也不会随 main 推送。原字体仍保留在忽略跟踪的 `dist/`。

本次没有远端强推。若 GitHub 已接收旧初始提交，新本地 main 会与远端产生不同历史；普通 push 被拒绝时，先检查远端状态并协调，不要直接使用 `--force`。

需要恢复旧提交时，可用 `git fetch .cache/pre-refactor.bundle main:backup/original` 导入一个恢复分支，而不覆盖当前 main。
