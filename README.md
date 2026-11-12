# 维语词光 · Uyghur Word Atlas

维吾尔语学习网站，**以 [designfuchen/word-atlas](https://github.com/designfuchen/word-atlas) 的真实开源 React/WebGL2/FSRS 程序为底座**，通过 GitHub Actions 自动取回原版源码并应用维语补丁。

## 构建状态

- GitHub Actions 已实现：获取原版源码 → 替换维语数据 → 禁用英语语音后备 → 测试 → 编译 → 上传静态网站
- 代码编译通过、原版 21 项自动测试通过
- GitHub Pages 发布需要仓库所有者在 **Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**
- 启用 Pages 后，在 **Actions** 中重新运行失败的发布作业
- 也可以从 Actions 的成功构建中下载 **uyghur-atlas-website**，部署到其它静态网页服务（Github Pages 构建的资源路径为 /uyghur-word-atlas/，直接部署到网站根目录前需调整基础路径）

## 重要学习提示

当前只含 **46 条初筛维语词汇**，尚未经母语专家逐词审校，不是适用于高校辅导员面试的完整词库。请不要把待核实词当作确定的考试标准词。未配置真正维吾尔语音源，因此自动禁用听音题，也不会使用英语语音合成器朗读维文。词条插画及完整例句尚未提供，原版没有删掉视觉和记忆算法代码，但功能受素材缺失限制。

## 原作者及许可证

软件基于 [Word Atlas](https://github.com/designfuchen/word-atlas)，原版代码遵循 MIT License；原版数据和媒体受 CC BY 4.0 等授权条款约束，具体见原仓库 LICENSE 和 CONTENT_LICENSE.md。不要将原项目的插画和发音误称为本版原创维吾尔语素材。
