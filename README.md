# 考试系统

一个基于 Flask 的在线考试系统，支持单选题、多选题和判断题。无需外部数据库服务，试卷内容存于 HTML，名称映射存于本地 SQLite。

## 考试名称入口

- 首页 `/` 输入完整考试名称，点击“进入考试”后进入原有考生信息和答题页面；管理后台移至 `/admin`。
- `POST /api/create_exam` 新增可选字段 `exam_name`，与展示标题 `title` 独立。去除首尾空白后须为 1–120 个字符，精确匹配、区分大小写；重复名称返回 HTTP 409，不覆盖原考试。空名称、非字符串或超长名称返回 400。
- 省略 `exam_name` 仍可创建考试，但只能通过原链接或二维码进入。旧考试不自动补名称。
- 首页以表单 `POST /enter` 提交 `exam_name`；非法名称返回 400，名称未知或文件丢失返回 404，数据库不可用返回 503。
- 原 `exam_url` 和二维码目标不变，扫码直接进入，不经过首页。名称不是密码，不构成访问控制，不提供公开考试列表。

请求示例（通过 HTTP 客户端从环境读取密钥设置 `X-API-Key`，不要把密钥放进 JSON）：

```json
{
  "exam_name": "2026 年安全培训第一场",
  "title": "安全生产知识考试",
  "duration": 30,
  "questions": [
    {
      "type": "single",
      "question": "火灾报警电话是多少？",
      "options": ["110", "119", "120"],
      "answer": "1",
      "score": 10
    }
  ]
}
```

带名称的成功响应额外返回去除首尾空白后的 `exam_name`。名称不嵌入公开试卷 HTML。链接仍根据创建请求的主机地址生成，请通过考生可访问的域名调用。

## 考生自选题数与随机抽题

新生成的试卷在考生信息末尾提供“题目数量”，灰色提示“如不填写则为全部考题”。留空按原顺序使用全部题目；填写正整数 N 则从全部题型中随机抽取 N 道、不重复，不保证题型比例。超过题库数量、0、负数或小数均阻止开始。

作答计分按实际题数重新分配整数分：

- 1–100 道总分 100，前 N−1 题各 floor(100/N) 分，最后一题补足。例如 6 道为 16、16、16、16、16、20 分。
- 超过 100 道每题 1 分，总分等于题数，例如 120 道总分 120。

抽取、编号、导航、题面分值及结果总分只在当前浏览器生效，服务器题库、API 返回的原始分值、考试时长及二维码不变。重置返回信息填写页，重新开始时重新抽取；不增加服务端成绩持久化或防作弊能力。

### 考试二维码

考生信息页的“进入考试”和“二维码”按钮并排居中。点击“二维码”会弹窗放大展示当前考试已有的二维码，并提供“下载二维码”和关闭按钮；支持 Escape 关闭，不清空已填写的考生信息。下载在当前站点内获取 PNG，不需要 API Key；无法下载时可尝试长按图片保存。二维码仅在正式的 `/exam/<考试ID>.html` 页面可用，沿用服务端已生成图片，不会重新生成或改变其编码地址。此功能也仅对新版生成的试卷页面生效。

### 保存成绩图片

考试完成页的“保存成绩”按钮可在浏览器本地生成 PNG 长图，包含考试标题、时长、当前试卷总分、得分、考生信息和答题情况。下方自动追加错题题干及考生所选选项（含选项字母）；判断题显示所选“正确/错误”，未作答显示“未作答”，全部答对时不显示错题区域。完成页也会直接显示这些错题详情。

图片生成不调用外部服务，不上传考生信息，也不保存到服务器。文件名为“考试标题_考生姓名_成绩.png”，下载位置由浏览器决定。极长内容超过图片尺寸上限、浏览器不支持或生成失败时，会显示提示且恢复按钮，不静默截断错题；可改用浏览器长截图。手机内置浏览器的下载和相册保存能力需在实际设备上验证。

此功能仅影响使用新版代码生成的试卷 HTML。已生成的静态考试页面不会自动更新，需要先部署新版，再通过已授权的考试更新接口重新生成页面；保留考试 ID、链接和二维码。

**历史静态 HTML 不会因升级镜像自动获得此功能。** 需用原始试题通过 PUT 重新生成，保留原链接和二维码；没有结构化数据的旧考试须先取得原题。本次不自动批量覆盖历史试卷。

DOM 回归测试需在隔离容器内安装 Node 和 jsdom@24（仅测试依赖），从项目根目录运行：

```bash
PYTHONPATH=. python tests/generate_browser_fixture.py
NODE_PATH=/app/node_modules node tests/test_random_questions.cjs
python -m unittest discover -s tests -v
```

`NODE_PATH` 按容器实际依赖安装位置配置，不属于应用运行依赖。

## 查询现有考试

以下接口均要求 `X-API-Key` 请求头，成功响应设置 `Cache-Control: no-store`，不公开答案。

- `GET /api/exams`：返回 `{"success": true, "count": 1, "exams": [...]}`。每项包括 `exam_id`、`exam_name`、`title`、`duration`、`question_count`、`total_score`、`exam_url`、`qr_url`、`data_available`、`file_exists`，不包含题目或答案。当前一次返回全部考试，按 ID 排序，不提供分页或名称过滤。
- `GET /api/exams/<exam_id>`：返回 `{"success": true, "exam": {...}}`，在上述字段基础上增加 `questions`，包含正确答案，仅供可信管理客户端使用。未知 ID 返回 404；鉴权失败返回 401；读取异常返回 500。

升级后创建或更新的考试会将结构化试卷保存到私有 SQLite 的 `exam_data` 表，更新时同步替换。字段是当时提交的内容（含调用方已做的 HTML 转义），不是从 HTML 逆向还原的原始资料。

升级前的考试也会列出（根据名称映射及标准 ID 的 HTML 文件），但无法可靠恢复的标题、题数、总分和题目为 `null`，`data_available=false`；详情仍返回 200 并明确标记。提交一次完整 PUT 更新后可获得结构化数据。文件已丢失但仍有数据库记录时继续列出，`file_exists=false`，不会假装链接可用。未命名考试的 `exam_name=null`。

SQLite 与 HTML 不是跨资源事务，异常终止或提交失败极端情况下可能不同步；备份请停止写入并成套保存 `static/` 与 `storage/`。不自动修复或从 HTML 猜测还原数据。

## 更新同一场考试

```http
PUT /api/exams/<exam_id>
Content-Type: application/json
X-API-Key: <从安全环境读取>
```

请求体只允许 `title`、`duration`、`questions`，整体替换试卷，不支持增量编辑或改名。标题和非空题目数组必填；时长为正整数，省略默认 60；每题须有非空题干、正整数分值及合法题型/字符串答案，选择题至少两个非空选项。成功响应格式与创建一致。

更新保留 ID、名称映射、原考试路径及二维码文件。未授权返回 401，数据非法返回 400，目标不存在返回 404，写入异常返回 500。使用同目录临时文件和原子替换，正常写入失败保留旧试卷；不提供版本历史或回滚接口。并发更新以最后成功写入为准，请协调编辑者。

创建重名仍返回 409，现额外返回已有 `exam_id` 和 `exam_name`（仅鉴权后）。技能会询问“换名新建”或“更新原考试”，不会自动覆盖。旧版无名称试卷也可按 ID 更新，但不会自动获得名称。

**已打开的页面不会自动更新，重新打开/刷新才会加载新题，刷新会丢失当前作答。请尽量在考试开始前修改。** 原二维码不重新生成；响应中的域名仍由当前请求的 Host 决定，调用时沿用原服务基础地址。

## 功能特性

- 支持单选题、多选题、判断题
- 实时答题反馈（答对自动跳转，答错显示正确答案）
- 响应式设计，支持PC和移动端
- 自动生成考试链接和二维码
- API Key鉴权
- Docker容器化部署

## 快速开始

### 使用Docker（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>

# 2. 进入项目目录
cd exam_system

# 3. 配置API Key（可选）
cp .env.example .env
# 编辑.env文件，设置API_KEY=your_secret_key

# 4. 构建并启动容器
docker-compose up -d

# 5. 访问管理后台
open http://localhost:5000/admin
```

### 使用Python直接运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置API Key环境变量（可选）
export API_KEY=exam_system_2024_secret_key

# 3. 启动服务
python app.py

# 4. 访问管理后台
open http://localhost:5000/admin
```

## API使用

### 创建考试

```bash
curl -X POST http://localhost:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -H "X-API-Key: exam_system_2024_secret_key" \
  -d '{
    "title": "安全生产知识考试",
    "duration": 30,
    "questions": [
      {
        "type": "single",
        "question": "安全生产的方针是什么？",
        "options": ["安全第一，预防为主", "生产第一，安全第二", "安全为主，生产为辅"],
        "answer": "0",
        "score": 10
      }
    ]
  }'
```

### Python示例

```python
import requests

headers = {
    'Content-Type': 'application/json',
    'X-API-Key': 'exam_system_2024_secret_key'
}

exam_data = {
    "title": "安全生产知识考试",
    "duration": 30,
    "questions": [
        {
            "type": "single",
            "question": "安全生产的方针是什么？",
            "options": ["安全第一，预防为主", "生产第一，安全第二", "安全为主，生产为辅"],
            "answer": "0",
            "score": 10
        }
    ]
}

response = requests.post(
    "http://localhost:5000/api/create_exam",
    json=exam_data,
    headers=headers
)

result = response.json()
print(f"考试链接: {result['exam_url']}")
print(f"二维码链接: {result['qr_url']}")
```

## 配置说明

### API Key配置

默认API Key: `exam_system_2024_secret_key`

#### 方法1：环境变量（推荐）

创建 `.env` 文件：
```
API_KEY=your_custom_secret_key
```

#### 方法2：Docker环境变量

在 `docker-compose.yml` 中设置：
```yaml
environment:
  - API_KEY=${API_KEY:-exam_system_2024_secret_key}
```

#### 方法3：请求头

在API请求时通过 `X-API-Key` 头传递：
```bash
-H "X-API-Key: your_secret_key"
```

## 数据持久化

### 名称映射存储

`storage/exams.sqlite3` 使用标准库 SQLite 保存名称到 HTML 文件名的映射，无需数据库服务，不通过静态目录公开。默认相对工作目录创建，运行用户须有目录写权限。Compose 已配置 `./storage:/app/storage` 持久化。

备份时停止服务写入，成套备份并恢复 `static/` 和 `storage/`，避免映射与文件不一致。升级保留静态文件即可继续使用旧链接，新名称仅对新增命名考试生效。

### 静态文件存储

- `static/exams/` - 存储生成的HTML考试文件
- `static/qrcodes/` - 存储生成的二维码图片

### Docker卷挂载

```yaml
volumes:
  - ./static:/app/static
  - ./storage:/app/storage
```

通过Docker卷挂载，生成的HTML文件和二维码会持久化存储在宿主机的 `./static` 目录中。

## 目录结构

```
exam_system/
├── app.py                  # Flask应用主文件
├── requirements.txt         # Python依赖
├── Dockerfile              # Docker镜像构建文件
├── docker-compose.yml       # Docker编排文件
├── .dockerignore          # Docker忽略文件
├── .env                   # 环境变量配置
├── static/                # 静态文件目录
│   ├── exams/          # 生成的HTML考试文件
│   └── qrcodes/        # 生成的二维码图片
└── README.md              # 项目说明文档
```

## 考试数据格式

### 单选题
```json
{
  "type": "single",
  "question": "题目内容",
  "options": ["选项A", "选项B", "选项C", "选项D"],
  "answer": "0",
  "score": 10
}
```

### 多选题
```json
{
  "type": "multiple",
  "question": "题目内容",
  "options": ["选项A", "选项B", "选项C", "选项D"],
  "answer": ["0", "1", "2"],
  "score": 15
}
```

### 判断题
```json
{
  "type": "judgment",
  "question": "题目内容",
  "answer": "true",
  "score": 5
}
```

## 端口说明

- `5000` - Flask应用端口
- 暴露端口：`5000:5000`

## 常见问题

### 如何更换API Key？

编辑 `.env` 文件，修改 `API_KEY` 的值，然后重启容器：
```bash
docker-compose restart
```

### 如何查看生成的考试文件？

生成的HTML文件存储在 `static/exams/` 目录中，可以直接访问或分享。

### 如何备份数据？

停止服务写入后成套备份 `static/` 和 `storage/`，试卷内容在 HTML 中，名称映射在 SQLite 中。

## 安全建议

1. 定期更换API Key
2. 使用HTTPS部署（生产环境）
3. 限制API Key的访问频率
4. 定期备份 `static/` 目录
5. 使用防火墙限制容器访问

## 许可证

MIT License
