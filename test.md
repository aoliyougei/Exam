# API 调用示例

## 考试名称入口（新增）

创建请求可加入 `"exam_name": "2026 年培训第一场"`，作为首页查找用的唯一名称，和 `title` 展示标题独立。去除首尾空白后为 1–120 个字符，精确匹配且区分大小写；非法名称返回 400，重名返回 409。成功响应会返回规范化后的 `exam_name`。

首页 `/` 输入名称进入，原管理页移至 `/admin`。API 省略名称仍兼容旧逻辑，原考试链接及二维码始终直接进入；旧考试不会自动补名称。

以下仅示例按名称进入，不携带密钥：

```bash
curl -i -X POST http://127.0.0.1:5000/enter \
  --data-urlencode 'exam_name=2026 年培训第一场'
```

匹配时返回 302，Location 指向 `/exam/<id>.html`；名称未知或文件丢失返回 404。新上传应使用技能约定的环境变量，在 HTTP 客户端内设置鉴权头，不在命令参数中展开真实密钥。下方为历史 curl 示例，示例密钥不应当作生产配置使用。

我来为您提供详细的curl调用示例。

## 1. 首先启动服务
```bash
# 安装依赖
pip install -r requirements.txt

# 启动Flask应用
python app.py
```

## 2. 获取测试数据示例
```bash
# 获取测试用的考试数据格式
curl -X GET http://127.0.0.1:5000/api/test_data \
  -H "Content-Type: application/json" \
  -H "X-API-Key: exam_system_2024_secret_key"
```

## 3. 创建考试示例（使用硬编码的JSON数据）

### 示例1：简单的考试
```bash
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -H "X-API-Key: exam_system_2024_secret_key" \
  -d '{
    "title": "员工入职考试",
    "duration": 30,
    "questions": [
      {
        "type": "single",
        "question": "公司的核心价值观是什么？",
        "options": ["创新、协作、诚信", "质量第一、客户至上", "安全、高效、卓越", "团结、拼搏、奉献"],
        "answer": "0",
        "score": 10
      },
      {
        "type": "multiple",
        "question": "下列哪些行为符合公司规定？",
        "options": ["准时上班", "着装整洁", "随意使用公司设备", "保持工作区域清洁"],
        "answer": ["0", "1", "3"],
        "score": 15
      },
      {
        "type": "judgment",
        "question": "工作中可以使用个人手机玩游戏。",
        "answer": "false",
        "score": 5
      }
    ]
  }'
```

### 示例2：包含更多题目的考试
```bash
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -H "X-API-Key: exam_system_2024_secret_key" \
  -d '{
    "title": "安全知识考核",
    "duration": 45,
    "questions": [
      {
        "type": "single",
        "question": "灭火器压力表指针在绿色区域表示什么？",
        "options": ["压力过高", "压力正常", "压力不足", "需要更换"],
        "answer": "1",
        "score": 10
      },
      {
        "type": "multiple",
        "question": "紧急疏散时需要注意什么？",
        "options": ["保持冷静", "使用电梯", "带好个人物品", "按照疏散路线走"],
        "answer": ["0", "3"],
        "score": 20
      },
      {
        "type": "judgment",
        "question": "电气设备着火时可以用水灭火。",
        "answer": "false",
        "score": 5
      },
      {
        "type": "single",
        "question": "发现安全隐患应该首先怎么做？",
        "options": ["自己处理", "立即上报", "忽略不管", "告诉同事"],
        "answer": "1",
        "score": 10
      },
      {
        "type": "multiple",
        "question": "高空作业时必须佩戴哪些防护用品？",
        "options": ["安全帽", "安全带", "安全网", "防滑鞋"],
        "answer": ["0", "1", "2"],
        "score": 15
      }
    ]
  }'
```

## 4. 从文件读取考试数据创建考试

### 步骤1：创建考试数据文件 `exam_data.json`
```json
{
  "title": "产品质量标准考试",
  "duration": 60,
  "questions": [
    {
      "type": "single",
      "question": "产品的A级质量标准要求是什么？",
      "options": [
        "无任何瑕疵",
        "允许微小瑕疵",
        "有明显瑕疵但可用",
        "重大瑕疵但能修复"
      ],
      "answer": "0",
      "score": 20
    },
    {
      "type": "multiple",
      "question": "质量检查包含哪些方面？",
      "options": [
        "外观检查",
        "尺寸测量",
        "功能测试",
        "包装检查"
      ],
      "answer": ["0", "1", "2", "3"],
      "score": 30
    },
    {
      "type": "judgment",
      "question": "不合格产品可以直接返工处理。",
      "answer": "false",
      "score": 10
    }
  ]
}
```

### 步骤2：使用curl从文件创建考试
```bash
# Windows PowerShell
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  --data-binary "@exam_data.json"

# Linux/Mac
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -d @exam_data.json
```

## 5. 格式化输出并保存结果

### 将结果保存到文件并格式化显示：
```bash
# 创建考试并将结果保存到文件
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -H "X-API-Key: exam_system_2024_secret_key" \
  -d '{
    "title": "紧急预案考试",
    "duration": 20,
    "questions": [
      {
        "type": "single",
        "question": "火灾报警电话是多少？",
        "options": ["110", "119", "120", "122"],
        "answer": "1",
        "score": 20
      }
    ]
  }' | python -m json.tool > result.json

# 查看保存的结果
cat result.json
```

### 使用jq格式化输出（需要先安装jq）：
```bash
# 如果安装了jq，可以使用以下命令获得更美观的输出
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -H "X-API-Key: exam_system_2024_secret_key" \
  -d '{
    "title": "设备操作规范考试",
    "duration": 25,
    "questions": [
      {
        "type": "judgment",
        "question": "设备运行中可以打开防护罩。",
        "answer": "false",
        "score": 10
      },
      {
        "type": "multiple",
        "question": "设备日常保养包括哪些内容？",
        "options": ["清洁表面", "检查螺丝", "添加润滑油", "更换配件"],
        "answer": ["0", "1", "2"],
        "score": 20
      }
    ]
  }' | jq '.'
```

## 6. 完整的创建和验证流程

### 步骤1：创建考试
```bash
# 创建考试并获取结果
RESULT=$(curl -s -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -H "X-API-Key: exam_system_2024_secret_key" \
  -d '{
    "title": "网络安全测试",
    "duration": 15,
    "questions": [
      {
        "type": "single",
        "question": "强密码应该包含什么？",
        "options": [
          "只包含数字",
          "大小写字母和数字",
          "只用常用单词",
          "与用户名相同"
        ],
        "answer": "1",
        "score": 10
      },
      {
        "type": "judgment",
        "question": "可以将公司密码告诉同事。",
        "answer": "false",
        "score": 5
      }
    ]
  }')

# 提取考试URL
EXAM_URL=$(echo $RESULT | python -c "import sys, json; data=json.load(sys.stdin); print(data['exam_url'])")
QR_URL=$(echo $RESULT | python -c "import sys, json; data=json.load(sys.stdin); print(data['qr_url'])")

echo "考试链接: $EXAM_URL"
echo "二维码链接: $QR_URL"
```

### 步骤2：验证考试链接是否有效
```bash
# 测试考试链接是否可以访问
curl -I $EXAM_URL

# 或者获取页面内容（前100个字符）
curl -s $EXAM_URL | head -c 100
```

## 7. 使用变量创建更复杂的考试

```bash
# 使用变量构建考试数据
EXAM_TITLE="季度考核测试"
DURATION=40
QUESTION_COUNT=3

curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -d "$(cat <<EOF
{
  "title": "$EXAM_TITLE",
  "duration": $DURATION,
  "questions": [
    {
      "type": "single",
      "question": "本季度的主要工作目标是什么？",
      "options": [
        "提高生产效率",
        "降低运营成本",
        "提升产品质量",
        "拓展市场份额"
      ],
      "answer": "2",
      "score": 30
    },
    {
      "type": "multiple",
      "question": "工作中需要遵守哪些安全规定？",
      "options": [
        "佩戴安全帽",
        "遵守操作规程",
        "及时报告隐患",
        "参加安全培训"
      ],
      "answer": ["0", "1", "2", "3"],
      "score": 40
    },
    {
      "type": "judgment",
      "question": "发现设备异常可以继续操作。",
      "answer": "false",
      "score": 10
    }
  ]
}
EOF
)"
```

## 8. 错误处理示例

### 测试缺少必要字段的情况：
```bash
# 缺少title字段
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -d '{
    "questions": [
      {
        "type": "single",
        "question": "测试题目",
        "options": ["A", "B"],
        "answer": "0",
        "score": 10
      }
    ]
  }'

# 格式错误的JSON
curl -X POST http://127.0.0.1:5000/api/create_exam \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试考试",
    "questions": [
      {
        "type": "invalid_type",  # 无效的题目类型
        "question": "测试题目",
        "options": ["A", "B"],
        "answer": "0",
        "score": 10
      }
    ]
  }'
```

## 9. 成功的返回结果示例

成功调用后，你会得到类似以下的响应：

```json
{
  "success": true,
  "exam_id": "a1b2c3d4",
  "exam_url": "http://127.0.0.1:5000/exam/a1b2c3d4.html",
  "qr_url": "http://127.0.0.1:5000/static/qrcodes/a1b2c3d4.png",
  "qr_path": "static/qrcodes/a1b2c3d4.png",
  "total_score": 45,
  "question_count": 3
}
```

## 10. 浏览器访问

创建成功后，你可以：
1. 直接在浏览器中打开 `exam_url` 进行考试
2. 扫描 `qr_url` 对应的二维码在手机上进行考试
3. 或者访问 `http://127.0.0.1:5000/` 使用网页管理界面

这些curl示例涵盖了各种使用场景，你可以根据实际需求选择合适的调用方式。





```bash
curl -X POST https://your-exam-service.example/api/create_exam \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <YOUR_API_KEY>" \
  -d '{
    "title": "员工入职考试",
    "duration": 30,
    "questions": [
      {
        "type": "single",
        "question": "公司的核心价值观是什么？",
        "options": ["创新、协作、诚信", "质量第一、客户至上", "安全、高效、卓越", "团结、拼搏、奉献"],
        "answer": "0",
        "score": 10
      },
      {
        "type": "multiple",
        "question": "下列哪些行为符合公司规定？",
        "options": ["准时上班", "着装整洁", "随意使用公司设备", "保持工作区域清洁"],
        "answer": ["0", "1", "3"],
        "score": 15
      },
      {
        "type": "judgment",
        "question": "工作中可以使用个人手机玩游戏。",
        "answer": "false",
        "score": 5
      }
    ]
  }'
```

