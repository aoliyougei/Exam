# 考试系统

我将为您设计一个完整的Flask考试系统，无需数据库，所有数据都存储在生成的HTML文件中。

## 项目结构
```
exam_system/
├── app.py
├── templates/
│   └── exam_template.html
├── static/
│   ├── qrcodes/         # 存储生成的二维码
│   └── exams/           # 存储生成的HTML考试文件
└── requirements.txt
```

## 1. 安装依赖
创建 `requirements.txt`:
```txt
Flask==2.3.3
qrcode[pil]==7.4.2
Pillow==10.0.0
```

## 2. Flask应用主文件 `app.py`

```python
import os
import json
import uuid
import qrcode
from io import BytesIO
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template_string
import hashlib

app = Flask(__name__)

# 创建必要的目录
os.makedirs('static/exams', exist_ok=True)
os.makedirs('static/qrcodes', exist_ok=True)

def generate_exam_html(exam_data):
    """生成考试HTML页面"""
    
    questions_html = ""
    for i, question in enumerate(exam_data['questions']):
        question_id = f"q{i}"
        
        if question['type'] == 'single':
            # 单选题
            options_html = ""
            for j, option in enumerate(question['options']):
                options_html += f'''
                <div class="option">
                    <input type="radio" id="{question_id}_opt{j}" 
                           name="{question_id}" value="{j}">
                    <label for="{question_id}_opt{j}">{option}</label>
                </div>
                '''
            
            questions_html += f'''
            <div class="question single" id="question_{i}" data-index="{i}" 
                 data-type="single" data-answer="{question['answer']}" data-score="{question['score']}">
                <div class="question-header">
                    <span class="question-number">第{i+1}题</span>
                    <span class="question-type">【单选题】</span>
                    <span class="question-score">分值: {question['score']}分</span>
                </div>
                <div class="question-content">
                    <p>{question['question']}</p>
                </div>
                <div class="options">
                    {options_html}
                </div>
                <div class="answer-feedback"></div>
            </div>
            '''
        
        elif question['type'] == 'multiple':
            # 多选题
            options_html = ""
            for j, option in enumerate(question['options']):
                options_html += f'''
                <div class="option">
                    <input type="checkbox" id="{question_id}_opt{j}" 
                           name="{question_id}" value="{j}">
                    <label for="{question_id}_opt{j}">{option}</label>
                </div>
                '''
            
            questions_html += f'''
            <div class="question multiple" id="question_{i}" data-index="{i}" 
                 data-type="multiple" data-answer="{json.dumps(question['answer'])}" data-score="{question['score']}">
                <div class="question-header">
                    <span class="question-number">第{i+1}题</span>
                    <span class="question-type">【多选题】</span>
                    <span class="question-score">分值: {question['score']}分</span>
                </div>
                <div class="question-content">
                    <p>{question['question']}</p>
                </div>
                <div class="options">
                    {options_html}
                </div>
                <div class="answer-feedback"></div>
            </div>
            '''
        
        elif question['type'] == 'judgment':
            # 判断题
            questions_html += f'''
            <div class="question judgment" id="question_{i}" data-index="{i}" 
                 data-type="judgment" data-answer="{question['answer']}" data-score="{question['score']}">
                <div class="question-header">
                    <span class="question-number">第{i+1}题</span>
                    <span class="question-type">【判断题】</span>
                    <span class="question-score">分值: {question['score']}分</span>
                </div>
                <div class="question-content">
                    <p>{question['question']}</p>
                </div>
                <div class="options">
                    <div class="option">
                        <input type="radio" id="{question_id}_true" 
                               name="{question_id}" value="true">
                        <label for="{question_id}_true">正确</label>
                    </div>
                    <div class="option">
                        <input type="radio" id="{question_id}_false" 
                               name="{question_id}" value="false">
                        <label for="{question_id}_false">错误</label>
                    </div>
                </div>
                <div class="answer-feedback"></div>
            </div>
            '''
    
    # 生成HTML模板
    html_template = f'''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{exam_data['title']}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Microsoft YaHei', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }}
            
            .user-info-form {{
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            
            .form-group {{
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            
            .form-group label {{
                width: 80px;
                font-weight: bold;
                margin-right: 10px;
            }}
            
            .form-group input {{
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }}
            
            .btn {{
                background: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px 5px;
                transition: background 0.3s;
            }}
            
            .btn:hover {{
                background: #45a049;
            }}
            
            .btn-secondary {{
                background: #6c757d;
            }}
            
            .btn-secondary:hover {{
                background: #5a6268;
            }}
            
            .exam-container {{
                display: none;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            
            .question {{
                padding: 25px;
                border-bottom: 1px solid #eee;
                display: none;
            }}
            
            .question.active {{
                display: block;
                animation: fadeIn 0.5s;
            }}
            
            .question-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #f0f0f0;
            }}
            
            .question-content {{
                font-size: 16px;
                margin-bottom: 20px;
                color: #2c3e50;
            }}
            
            .options {{
                margin: 20px 0;
            }}
            
            .option {{
                margin: 12px 0;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s;
            }}
            
            .option:hover {{
                border-color: #667eea;
                background: #f8f9fa;
            }}
            
            .option input:checked + label {{
                color: #667eea;
                font-weight: bold;
            }}
            
            .option input:checked ~ .option {{
                border-color: #667eea;
                background: #f0f4ff;
            }}
            
            .answer-feedback {{
                margin-top: 20px;
                padding: 15px;
                border-radius: 8px;
                display: none;
            }}
            
            .correct {{
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .wrong {{
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .progress-bar {{
                height: 6px;
                background: #e0e0e0;
                margin-bottom: 20px;
                border-radius: 3px;
                overflow: hidden;
            }}
            
            .progress {{
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                width: 0%;
                transition: width 0.5s;
            }}
            
            .question-nav {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            
            .question-nav-item {{
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                background: #6c757d;
                color: white;
                cursor: pointer;
                transition: all 0.3s;
            }}
            
            .question-nav-item.answered {{
                background: #28a745;
            }}
            
            .question-nav-item.current {{
                background: #007bff;
                transform: scale(1.1);
            }}
            
            .question-nav-item.wrong {{
                background: #dc3545;
            }}
            
            .result-container {{
                display: none;
                padding: 30px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            
            .score {{
                font-size: 48px;
                font-weight: bold;
                color: #667eea;
                margin: 20px 0;
            }}
            
            .user-info-display {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: left;
            }}
            
            .controls {{
                display: flex;
                justify-content: space-between;
                padding: 20px;
                background: #f8f9fa;
                border-top: 1px solid #eee;
            }}
            
            .timer {{
                font-size: 18px;
                font-weight: bold;
                color: #dc3545;
                padding: 10px;
                background: white;
                border-radius: 5px;
                border: 2px solid #dc3545;
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            @media (max-width: 768px) {{
                body {{
                    padding: 10px;
                }}
                
                .question-header {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
                
                .question-nav-item {{
                    width: 35px;
                    height: 35px;
                }}
                
                .controls {{
                    flex-direction: column;
                    gap: 10px;
                }}
                
                .btn {{
                    width: 100%;
                    margin: 5px 0;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{exam_data['title']}</h1>
            <p>考试时间: {exam_data.get('duration', 60)}分钟 | 总分: {exam_data['total_score']}分</p>
        </div>
        
        <!-- 用户信息输入 -->
        <div id="userInfoForm" class="user-info-form">
            <h2>考生信息</h2>
            <div class="form-group">
                <label for="company">单位:</label>
                <input type="text" id="company" placeholder="请输入单位名称">
            </div>
            <div class="form-group">
                <label for="employeeId">工号:</label>
                <input type="text" id="employeeId" placeholder="请输入工号">
            </div>
            <div class="form-group">
                <label for="department">部门:</label>
                <input type="text" id="department" placeholder="请输入部门">
            </div>
            <div class="form-group">
                <label for="name">姓名:</label>
                <input type="text" id="name" placeholder="请输入姓名">
            </div>
            <button class="btn" onclick="startExam()">开始考试</button>
        </div>
        
        <!-- 考试容器 -->
        <div id="examContainer" class="exam-container">
            <div class="progress-bar">
                <div class="progress" id="progressBar"></div>
            </div>
            
            <div class="question-nav" id="questionNav">
                <!-- 题号导航将通过JS生成 -->
            </div>
            
            <div id="questionsContainer">
                {questions_html}
            </div>
            
            <div class="controls">
                <button class="btn btn-secondary" onclick="previousQuestion()">上一题</button>
                <div class="timer" id="timer">剩余时间: 60:00</div>
                <button class="btn" onclick="nextQuestion()" id="nextBtn">下一题</button>
            </div>
        </div>
        
        <!-- 结果页面 -->
        <div id="resultContainer" class="result-container">
            <h2>考试完成！</h2>
            <div class="score" id="finalScore">0</div>
            <p>总分: {exam_data['total_score']}分</p>
            
            <div class="user-info-display">
                <h3>考生信息</h3>
                <p><strong>单位:</strong> <span id="resultCompany"></span></p>
                <p><strong>工号:</strong> <span id="resultEmployeeId"></span></p>
                <p><strong>部门:</strong> <span id="resultDepartment"></span></p>
                <p><strong>姓名:</strong> <span id="resultName"></span></p>
            </div>
            
            <div id="questionReview" style="margin: 30px 0;">
                <h3>答题情况</h3>
                <div class="question-nav" id="resultQuestionNav"></div>
            </div>
            
            <div style="margin: 20px 0;">
                <button class="btn" onclick="reviewWrongQuestions()">查看错题</button>
                <button class="btn btn-secondary" onclick="resetExam()">重置考试</button>
            </div>
        </div>
        
        <script>
            // 考试数据
            const examData = {json.dumps(exam_data, ensure_ascii=False)};
            const totalQuestions = examData.questions.length;
            let currentQuestion = 0;
            let userAnswers = new Array(totalQuestions).fill(null);
            let userInfo = {{}};
            let timeLeft = examData.duration * 60 || 3600;
            let timerInterval;
            
            // 初始化导航
            function initQuestionNav() {{
                const navContainer = document.getElementById('questionNav');
                const resultNavContainer = document.getElementById('resultQuestionNav');
                navContainer.innerHTML = '';
                resultNavContainer.innerHTML = '';
                
                for (let i = 0; i < totalQuestions; i++) {{
                    const navItem = document.createElement('div');
                    navItem.className = 'question-nav-item';
                    navItem.textContent = i + 1;
                    navItem.onclick = () => goToQuestion(i);
                    
                    const resultNavItem = navItem.cloneNode(true);
                    resultNavItem.onclick = () => {{
                        if (userAnswers[i] !== null) {{
                            showResultQuestion(i);
                        }}
                    }};
                    
                    navContainer.appendChild(navItem);
                    resultNavContainer.appendChild(resultNavItem);
                }}
                
                updateNavStatus();
            }}
            
            // 更新导航状态
            function updateNavStatus() {{
                const navItems = document.querySelectorAll('.question-nav-item');
                navItems.forEach((item, index) => {{
                    item.classList.remove('current', 'answered', 'wrong');
                    
                    if (index === currentQuestion) {{
                        item.classList.add('current');
                    }}
                    
                    if (userAnswers[index] !== null) {{
                        const question = document.getElementById(`question_${{index}}`);
                        const isCorrect = checkAnswer(index, false);
                        item.classList.add('answered');
                        
                        if (!isCorrect) {{
                            item.classList.add('wrong');
                        }}
                    }}
                }});
            }}
            
            // 开始考试
            function startExam() {{
                // 获取用户信息
                userInfo = {{
                    company: document.getElementById('company').value,
                    employeeId: document.getElementById('employeeId').value,
                    department: document.getElementById('department').value,
                    name: document.getElementById('name').value
                }};
                
                if (!userInfo.name || !userInfo.employeeId) {{
                    alert('请填写姓名和工号');
                    return;
                }}
                
                document.getElementById('userInfoForm').style.display = 'none';
                document.getElementById('examContainer').style.display = 'block';
                
                initQuestionNav();
                showQuestion(currentQuestion);
                startTimer();
            }}
            
            // 显示题目
            function showQuestion(index) {{
                // 隐藏所有题目
                document.querySelectorAll('.question').forEach(q => {{
                    q.classList.remove('active');
                }});
                
                // 显示当前题目
                const question = document.getElementById(`question_${{index}}`);
                question.classList.add('active');
                
                // 更新进度条
                const progress = ((index + 1) / totalQuestions) * 100;
                document.getElementById('progressBar').style.width = progress + '%';
                
                // 更新导航
                updateNavStatus();
                
                // 恢复已选择的答案
                if (userAnswers[index] !== null) {{
                    restoreAnswer(index);
                }}
            }}
            
            // 恢复答案
            function restoreAnswer(index) {{
                const question = document.getElementById(`question_${{index}}`);
                const answer = userAnswers[index];
                const type = question.dataset.type;
                
                if (type === 'single' || type === 'judgment') {{
                    const inputs = question.querySelectorAll('input[type="radio"]');
                    inputs.forEach(input => {{
                        input.checked = input.value === answer;
                    }});
                }} else if (type === 'multiple') {{
                    const answerArray = JSON.parse(answer);
                    const inputs = question.querySelectorAll('input[type="checkbox"]');
                    inputs.forEach(input => {{
                        input.checked = answerArray.includes(input.value);
                    }});
                }}
            }}
            
            // 检查答案
            function checkAnswer(index, showFeedback = true) {{
                const question = document.getElementById(`question_${{index}}`);
                const type = question.dataset.type;
                const correctAnswer = question.dataset.answer;
                let userAnswer;
                
                if (type === 'single' || type === 'judgment') {{
                    const selected = question.querySelector('input[type="radio"]:checked');
                    userAnswer = selected ? selected.value : null;
                }} else if (type === 'multiple') {{
                    const selected = question.querySelectorAll('input[type="checkbox"]:checked');
                    userAnswer = Array.from(selected).map(input => input.value).sort();
                }}
                
                userAnswers[index] = userAnswer;
                
                if (showFeedback) {{
                    const feedback = question.querySelector('.answer-feedback');
                    let isCorrect = false;
                    
                    if (type === 'multiple') {{
                        const correctArray = JSON.parse(correctAnswer).sort();
                        isCorrect = JSON.stringify(userAnswer) === JSON.stringify(correctArray);
                    }} else {{
                        isCorrect = userAnswer === correctAnswer;
                    }}
                    
                    if (userAnswer === null) {{
                        feedback.style.display = 'none';
                        return false;
                    }}
                    
                    feedback.style.display = 'block';
                    feedback.className = 'answer-feedback ' + (isCorrect ? 'correct' : 'wrong');
                    
                    if (isCorrect) {{
                        feedback.innerHTML = '<strong>✓ 回答正确！</strong>';
                        setTimeout(() => {{
                            if (currentQuestion < totalQuestions - 1) {{
                                nextQuestion();
                            }} else {{
                                finishExam();
                            }}
                        }}, 1000);
                    }} else {{
                        let correctText = correctAnswer;
                        if (type === 'multiple') {{
                            const correctArray = JSON.parse(correctAnswer);
                            correctText = correctArray.map(opt => examData.questions[index].options[opt]).join(', ');
                        }} else if (type === 'single') {{
                            correctText = examData.questions[index].options[correctAnswer];
                        }} else {{
                            correctText = correctAnswer === 'true' ? '正确' : '错误';
                        }}
                        
                        feedback.innerHTML = `<strong>✗ 回答错误！</strong><br>正确答案: ${{correctText}}`;
                    }}
                }}
                
                updateNavStatus();
                
                if (type === 'multiple') {{
                    const correctArray = JSON.parse(correctAnswer).sort();
                    return JSON.stringify(userAnswer) === JSON.stringify(correctArray);
                }} else {{
                    return userAnswer === correctAnswer;
                }}
            }}
            
            // 下一题
            function nextQuestion() {{
                // 先检查当前题目
                const isCorrect = checkAnswer(currentQuestion, true);
                
                // 如果答错，等待手动点击
                if (!isCorrect && userAnswers[currentQuestion] !== null) {{
                    return;
                }}
                
                if (currentQuestion < totalQuestions - 1) {{
                    currentQuestion++;
                    showQuestion(currentQuestion);
                }} else {{
                    finishExam();
                }}
            }}
            
            // 上一题
            function previousQuestion() {{
                if (currentQuestion > 0) {{
                    currentQuestion--;
                    showQuestion(currentQuestion);
                }}
            }}
            
            // 跳转到指定题目
            function goToQuestion(index) {{
                currentQuestion = index;
                showQuestion(index);
            }}
            
            // 开始计时器
            function startTimer() {{
                updateTimerDisplay();
                timerInterval = setInterval(() => {{
                    timeLeft--;
                    updateTimerDisplay();
                    
                    if (timeLeft <= 0) {{
                        clearInterval(timerInterval);
                        finishExam();
                    }}
                }}, 1000);
            }}
            
            // 更新计时器显示
            function updateTimerDisplay() {{
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                document.getElementById('timer').textContent = 
                    `剩余时间: ${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
            }}
            
            // 完成考试
            function finishExam() {{
                clearInterval(timerInterval);
                
                // 计算总分
                let totalScore = 0;
                for (let i = 0; i < totalQuestions; i++) {{
                    if (checkAnswer(i, false)) {{
                        const question = document.getElementById(`question_${{i}}`);
                        totalScore += parseInt(question.dataset.score);
                    }}
                }}
                
                // 显示结果
                document.getElementById('examContainer').style.display = 'none';
                document.getElementById('resultContainer').style.display = 'block';
                
                document.getElementById('finalScore').textContent = totalScore;
                document.getElementById('resultCompany').textContent = userInfo.company;
                document.getElementById('resultEmployeeId').textContent = userInfo.employeeId;
                document.getElementById('resultDepartment').textContent = userInfo.department;
                document.getElementById('resultName').textContent = userInfo.name;
            }}
            
            // 查看错题
            function reviewWrongQuestions() {{
                const wrongQuestions = [];
                for (let i = 0; i < totalQuestions; i++) {{
                    if (!checkAnswer(i, false)) {{
                        wrongQuestions.push(i);
                    }}
                }}
                
                if (wrongQuestions.length === 0) {{
                    alert('没有错题！');
                    return;
                }}
                
                document.getElementById('resultContainer').style.display = 'none';
                document.getElementById('examContainer').style.display = 'block';
                currentQuestion = wrongQuestions[0];
                showQuestion(currentQuestion);
            }}
            
            // 显示结果中的题目
            function showResultQuestion(index) {{
                document.getElementById('resultContainer').style.display = 'none';
                document.getElementById('examContainer').style.display = 'block';
                currentQuestion = index;
                showQuestion(currentQuestion);
                
                // 禁用选项
                const question = document.getElementById(`question_${{index}}`);
                question.querySelectorAll('input').forEach(input => {{
                    input.disabled = true;
                }});
            }}
            
            // 重置考试
            function resetExam() {{
                if (confirm('确定要重置考试吗？所有答案将被清空。')) {{
                    currentQuestion = 0;
                    userAnswers = new Array(totalQuestions).fill(null);
                    timeLeft = examData.duration * 60 || 3600;
                    
                    // 清空输入
                    document.getElementById('company').value = '';
                    document.getElementById('employeeId').value = '';
                    document.getElementById('department').value = '';
                    document.getElementById('name').value = '';
                    
                    // 重置所有选项
                    document.querySelectorAll('.question').forEach(question => {{
                        question.querySelectorAll('input').forEach(input => {{
                            input.checked = false;
                            input.disabled = false;
                        }});
                        question.querySelector('.answer-feedback').style.display = 'none';
                    }});
                    
                    document.getElementById('resultContainer').style.display = 'none';
                    document.getElementById('examContainer').style.display = 'none';
                    document.getElementById('userInfoForm').style.display = 'block';
                    
                    clearInterval(timerInterval);
                }}
            }}
            
            // 初始化
            window.onload = function() {{
                // 添加选项点击事件
                document.querySelectorAll('.option').forEach(option => {{
                    option.onclick = function() {{
                        const input = this.querySelector('input');
                        if (input.type === 'radio') {{
                            input.checked = true;
                        }} else {{
                            input.checked = !input.checked;
                        }}
                        
                        // 触发检查答案
                        checkAnswer(currentQuestion, true);
                    }};
                }});
            }};
        </script>
    </body>
    </html>
    '''
    
    return html_template

def generate_qrcode(url, exam_id):
    """生成二维码并保存"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 保存二维码图片
    qr_path = f"static/qrcodes/{exam_id}.png"
    img.save(qr_path)
    
    return qr_path

@app.route('/api/create_exam', methods=['POST'])
def create_exam():
    """创建新的考试"""
    try:
        exam_data = request.json
        
        # 验证数据
        required_fields = ['title', 'questions']
        for field in required_fields:
            if field not in exam_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # 计算总分
        total_score = sum(q.get('score', 1) for q in exam_data['questions'])
        exam_data['total_score'] = total_score
        exam_data['duration'] = exam_data.get('duration', 60)
        
        # 生成唯一ID
        exam_id = str(uuid.uuid4())[:8]
        
        # 生成HTML内容
        html_content = generate_exam_html(exam_data)
        
        # 保存HTML文件
        html_filename = f"{exam_id}.html"
        html_path = f"static/exams/{html_filename}"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 生成考试链接
        exam_url = f"{request.host_url}exam/{html_filename}"
        
        # 生成二维码
        qr_path = generate_qrcode(exam_url, exam_id)
        qr_url = f"{request.host_url}{qr_path}"
        
        return jsonify({
            'success': True,
            'exam_id': exam_id,
            'exam_url': exam_url,
            'qr_url': qr_url,
            'qr_path': qr_path,
            'total_score': total_score,
            'question_count': len(exam_data['questions'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/exam/<filename>')
def serve_exam(filename):
    """提供考试页面"""
    try:
        html_path = f"static/exams/{filename}"
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except:
        return "Exam not found", 404

@app.route('/api/test_data', methods=['GET'])
def get_test_data():
    """提供测试用的考试数据"""
    test_data = {
        "title": "安全生产知识考试",
        "duration": 30,
        "questions": [
            {
                "type": "single",
                "question": "安全生产的方针是什么？",
                "options": ["安全第一，预防为主", "生产第一，安全第二", "安全为主，生产为辅", "预防第一，安全第二"],
                "answer": "0",
                "score": 10
            },
            {
                "type": "multiple",
                "question": "下列哪些属于安全三宝？",
                "options": ["安全帽", "安全带", "安全网", "安全鞋"],
                "answer": ["0", "1", "2"],
                "score": 15
            },
            {
                "type": "judgment",
                "question": "高处作业必须系好安全带。",
                "answer": "true",
                "score": 5
            },
            {
                "type": "single",
                "question": "灭火器压力表指针在哪个区域表示正常？",
                "options": ["红色", "黄色", "绿色", "白色"],
                "answer": "2",
                "score": 10
            },
            {
                "type": "multiple",
                "question": "以下哪些情况必须停止高处作业？",
                "options": ["六级以上大风", "暴雨", "大雾", "夜间照明不足"],
                "answer": ["0", "1", "2", "3"],
                "score": 20
            },
            {
                "type": "judgment",
                "question": "可以用水扑灭电气火灾。",
                "answer": "false",
                "score": 5
            }
        ]
    }
    
    return jsonify(test_data)

@app.route('/')
def index():
    """主页"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>考试系统管理后台</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 5px; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .qr-code { margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>考试系统管理后台</h1>
            
            <div class="card">
                <h2>1. 获取测试数据</h2>
                <button onclick="getTestData()">获取测试数据</button>
                <pre id="testData"></pre>
            </div>
            
            <div class="card">
                <h2>2. 创建考试</h2>
                <p>将上面的考试数据复制到下面的JSON编辑器中，然后点击创建考试</p>
                <textarea id="examData" rows="10" cols="80" placeholder="请输入考试JSON数据..."></textarea>
                <br><br>
                <button onclick="createExam()">创建考试</button>
                <div id="result"></div>
                <div id="qrCode" class="qr-code"></div>
            </div>
        </div>
        
        <script>
            async function getTestData() {
                const response = await fetch('/api/test_data');
                const data = await response.json();
                document.getElementById('testData').textContent = JSON.stringify(data, null, 2);
                document.getElementById('examData').value = JSON.stringify(data, null, 2);
            }
            
            async function createExam() {
                const examData = document.getElementById('examData').value;
                try {
                    const response = await fetch('/api/create_exam', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: examData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        document.getElementById('result').innerHTML = `
                            <h3>创建成功！</h3>
                            <p><strong>考试ID:</strong> ${result.exam_id}</p>
                            <p><strong>考试链接:</strong> <a href="${result.exam_url}" target="_blank">${result.exam_url}</a></p>
                            <p><strong>二维码链接:</strong> <a href="${result.qr_url}" target="_blank">${result.qr_url}</a></p>
                            <p><strong>题目数量:</strong> ${result.question_count}</p>
                            <p><strong>总分:</strong> ${result.total_score}</p>
                        `;
                        
                        document.getElementById('qrCode').innerHTML = `
                            <p><strong>二维码:</strong></p>
                            <img src="${result.qr_url}" alt="QR Code" style="width: 200px; height: 200px;">
                        `;
                    } else {
                        document.getElementById('result').innerHTML = `<p style="color: red;">创建失败: ${result.error}</p>`;
                    }
                } catch (error) {
                    document.getElementById('result').innerHTML = `<p style="color: red;">请求失败: ${error}</p>`;
                }
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

## 3. 使用说明

### 启动服务：
```bash
pip install -r requirements.txt
python app.py
```

### 创建考试的API调用示例：
```python
import requests
import json

# 考试数据格式
exam_data = {
    "title": "员工安全知识考试",
    "duration": 60,  # 考试时长（分钟）
    "questions": [
        {
            "type": "single",  # 单选题
            "question": "安全生产的方针是什么？",
            "options": ["安全第一，预防为主", "生产第一，安全第二", "安全为主，生产为辅"],
            "answer": "0",  # 正确答案的索引
            "score": 10
        },
        {
            "type": "multiple",  # 多选题
            "question": "下列哪些属于安全三宝？",
            "options": ["安全帽", "安全带", "安全网", "安全鞋"],
            "answer": ["0", "1", "2"],  # 正确答案索引数组
            "score": 15
        },
        {
            "type": "judgment",  # 判断题
            "question": "高处作业必须系好安全带。",
            "answer": "true",  # true/false
            "score": 5
        }
    ]
}

# 调用API创建考试
response = requests.post(
    "http://localhost:5000/api/create_exam",
    json=exam_data,
    headers={"Content-Type": "application/json"}
)

result = response.json()
print(f"考试链接: {result['exam_url']}")
print(f"二维码链接: {result['qr_url']}")
```

## 4. 特性说明

### 后端功能：
- **生成HTML考试页面**：根据传入的考试数据动态生成完整的HTML文件
- **无数据库存储**：所有考试数据嵌入HTML文件中
- **二维码生成**：自动生成考试链接的二维码图片
- **固定文件存储**：生成的HTML文件保存在服务器上，可通过链接直接访问

### 考试页面功能：
- **响应式设计**：支持PC端和移动端
- **考生信息录入**：单位、工号、部门、姓名
- **智能答题**：单选、多选、判断题支持
- **即时反馈**：答对自动跳转，答错显示正确答案
- **进度跟踪**：实时显示答题进度和剩余时间
- **结果统计**：显示总分和考生信息
- **错题回顾**：可查看所有错题
- **考试重置**：支持重新开始考试

## 5. 扩展建议

1. **安全性增强**：添加考试密码保护
2. **考试记录**：虽然不用数据库，但可以生成考试结果文件
3. **题目随机**：支持题目顺序随机
4. **考试时间限制**：支持时间到自动交卷
5. **导出功能**：导出考试结果为PDF或Excel

这个系统完全满足您的需求，无需数据库，所有数据都存储在HTML文件中，通过接口创建考试后即可获得可直接访问的链接和二维码。

