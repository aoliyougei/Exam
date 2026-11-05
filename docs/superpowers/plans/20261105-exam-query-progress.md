# 考试查询实施记录

需求：鉴权 GET /api/exams 列表及 GET /api/exams/<exam_id> 详情，新增结构化持久化，不逆向解析旧 HTML。

变更：app.py 新建私有 exam_data 表（不变更旧 exams 表），创建及 PUT 写入 JSON；列表合并名称映射、结构化记录和标准八位十六进制 ID HTML 文件；详情包含 questions，列表不含；成功响应 no-store。未知 ID 404，未授权 401，存储读取异常 500。

兼容：未命名考试名称 null；旧考试未知字段 null、data_available=false；缺失 HTML 考试保留可查询记录并 file_exists=false。旧考试通过一次完整 PUT 获得新结构化数据。列表一次全量返回，无分页；不是为大规模题库设计。

测试：先运行 4 个新查询用例，基线 1 failure、3 errors；实现后 Docker Python 3.9 中全部 22/22 测试通过（含原 18 项）。覆盖鉴权、空列表、列表/详情/更新一致、旧 schema、旧 HTML、缺失文件、秘密排除及 no-store。技能已更新查询规则、旧数据警示、读取不等于替换授权及避免重复转义。ZIP 在 Docker 生成，CRC 与源文件比较通过，已替换本地文件。

审查：本人静态复核。无独立 Agent 行为测试、浏览器验证或生产部署，未重建部署镜像；部署需自行重新构建。

已知边界：SQLite commit 与 HTML 原子替换不是跨资源事务，commit 失败或进程强杀可导致元数据与 HTML 不同步；正常 os.replace 失败会回滚元数据。备份须停止写入并成套备份。原创建接口的题目详细校验和 HTML 拼接风险未全面改造。
