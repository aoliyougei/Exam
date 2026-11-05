import os
import json
import uuid
import sqlite3
import tempfile
import re
from contextlib import closing
import qrcode
from io import BytesIO
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template_string, redirect, url_for
import hashlib

app = Flask(__name__)

API_KEY = os.environ.get('API_KEY', 'exam_system_2024_secret_key')

os.makedirs('static/exams', exist_ok=True)
os.makedirs('static/qrcodes', exist_ok=True)

def verify_api_key(api_key):
    """验证API key"""
    return api_key == API_KEY

def generate_exam_html(exam_data):
    
    questions_html = ""
    for i, question in enumerate(exam_data['questions']):
        question_id = f"q{i}"
        
        if question['type'] == 'single':
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
            options_html = ""
            for j, option in enumerate(question['options']):
                options_html += f'''
                <div class="option">
                    <input type="checkbox" id="{question_id}_opt{j}" 
                           name="{question_id}" value="{j}">
                    <label for="{question_id}_opt{j}">{option}</label>
                </div>
                '''
            
            answer_json = json.dumps(question['answer']).replace('"', '&quot;')
            questions_html += f'''
            <div class="question multiple" id="question_{i}" data-index="{i}" 
                 data-type="multiple" data-answer='{answer_json}' data-score="{question['score']}">
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
            
            #questionCount::placeholder {{
                color: #888;
                opacity: 1;
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
            
            #wrongQuestionDetails {{ text-align: left; overflow-wrap: anywhere; }}
            #wrongQuestionDetails article {{ background: #f8f9fa; border-left: 4px solid #dc3545; padding: 16px; margin: 16px 0; border-radius: 8px; white-space: pre-wrap; }}
            #wrongQuestionDetails p {{ margin-top: 8px; }}
            .btn:disabled {{ opacity: 0.6; cursor: wait; }}

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
            <p>考试时间: {exam_data.get('duration', 60)}分钟 | 总分: <span id="examTotalScore">待开始</span>分</p>
        </div>
        
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
            <div class="form-group">
                <label for="questionCount">题目数量:</label>
                <input type="number" id="questionCount" min="1" max="{len(exam_data['questions'])}"
                       step="1" placeholder="如不填写则为全部考题" aria-describedby="countHelp">
            </div>
            <p id="countHelp" style="color: #666; font-size: 14px;">共 {len(exam_data['questions'])} 道题，填写后随机抽取。100 道以内总分 100，超过 100 道每题 1 分。</p>
            <button class="btn" onclick="startExam()">开始考试</button>
        </div>
        
        <div id="examContainer" class="exam-container">
            <div class="progress-bar">
                <div class="progress" id="progressBar"></div>
            </div>
            
            <div class="question-nav" id="questionNav">
            </div>
            
            <div id="questionsContainer">
                {questions_html}
            </div>
            
            <div class="controls">
                <button class="btn btn-secondary" onclick="previousQuestion()">上一题</button>
                <div class="timer" id="timer">剩余时间: {exam_data.get('duration', 60)}:00</div>
                <button class="btn" onclick="nextQuestion()" id="nextBtn">下一题</button>
            </div>
        </div>
        
        <div id="resultContainer" class="result-container">
            <h2>考试完成！</h2>
            <div class="score" id="finalScore">0</div>
            <p>总分: <span id="resultTotalScore">待开始</span>分</p>
            
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
                <button class="btn" id="saveScoreBtn" onclick="saveScoreImage()">保存成绩</button>
                <button class="btn" onclick="reviewWrongQuestions()">查看错题</button>
                <button class="btn btn-secondary" onclick="resetExam()">重置考试</button>
            </div>
            <section id="wrongQuestionDetails" hidden></section>
        </div>
        
        <script>
            const examData = {json.dumps(exam_data, ensure_ascii=False)};
            const questionBank = examData.questions.slice();
            const questionTemplates = Array.from(document.querySelectorAll('#questionsContainer .question'))
                .map(node => node.cloneNode(true));
            let totalQuestions = questionBank.length;
            let pendingAdvance;
            let startupTimeout;
            let currentQuestion = 0;
            let userAnswers = new Array(totalQuestions).fill(null);
            let userInfo = {{}};
            let timeLeft = examData.duration * 60 || 3600;
            let timerInterval;
            
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
            }}
            
            function updateNavStatus() {{
                const navItems = document.querySelectorAll('#questionNav .question-nav-item');
                navItems.forEach((item, index) => {{
                    item.classList.remove('current', 'answered', 'wrong');
                    
                    if (userAnswers[index] !== null) {{
                        const question = document.getElementById(`question_${{index}}`);
                        if (question) {{
                            const type = question.dataset.type;
                            const correctAnswer = question.dataset.answer;
                            const userAnswer = userAnswers[index];
                            let isCorrect = false;
                            
                            if (type === 'multiple') {{
                                if (!userAnswer || userAnswer.length === 0) {{
                                    item.classList.add('answered');
                                    item.classList.add('wrong');
                                    return;
                                }}
                                try {{
                                    const decodedAnswer = correctAnswer.replace(/&quot;/g, '"');
                                    const correctArray = JSON.parse(decodedAnswer).sort();
                                    isCorrect = JSON.stringify(userAnswer) === JSON.stringify(correctArray);
                                }} catch (e) {{
                                    console.error('Error parsing answer:', e);
                                    isCorrect = false;
                                }}
                            }} else {{
                                isCorrect = userAnswer === correctAnswer;
                            }}
                            
                            item.classList.add('answered');
                            
                            if (!isCorrect) {{
                                item.classList.add('wrong');
                            }}
                        }}
                    }}
                    
                    if (index === currentQuestion) {{
                        item.classList.add('current');
                    }}
                }});
                
                const resultNavItems = document.querySelectorAll('#resultQuestionNav .question-nav-item');
                resultNavItems.forEach((item, index) => {{
                    item.classList.remove('current', 'answered', 'wrong');
                    
                    if (userAnswers[index] !== null) {{
                        const question = document.getElementById(`question_${{index}}`);
                        if (question) {{
                            const type = question.dataset.type;
                            const correctAnswer = question.dataset.answer;
                            const userAnswer = userAnswers[index];
                            let isCorrect = false;
                            
                            if (type === 'multiple') {{
                                if (!userAnswer || userAnswer.length === 0) {{
                                    item.classList.add('answered');
                                    item.classList.add('wrong');
                                    return;
                                }}
                                try {{
                                    const decodedAnswer = correctAnswer.replace(/&quot;/g, '"');
                                    const correctArray = JSON.parse(decodedAnswer).sort();
                                    isCorrect = JSON.stringify(userAnswer) === JSON.stringify(correctArray);
                                }} catch (e) {{
                                    console.error('Error parsing answer:', e);
                                    isCorrect = false;
                                }}
                            }} else {{
                                isCorrect = userAnswer === correctAnswer;
                            }}
                            
                            item.classList.add('answered');
                            
                            if (!isCorrect) {{
                                item.classList.add('wrong');
                            }}
                        }}
                    }}
                    
                    if (index === currentQuestion) {{
                        item.classList.add('current');
                    }}
                }});
            }}
            
            function prepareAttempt() {{
                const field = document.getElementById('questionCount');
                const raw = field.value.trim();
                if (field.validity.badInput || (raw !== '' && !/^[0-9]+$/.test(raw))) {{
                    alert('请输入有效的正整数题目数量');
                    return false;
                }}
                const count = raw === '' ? questionBank.length : Number(raw);
                if (!Number.isSafeInteger(count) || count < 1 || count > questionBank.length) {{
                    alert(`题目数量必须在 1 至 ${{questionBank.length}} 之间`);
                    return false;
                }}
                const indices = questionBank.map((_, index) => index);
                if (raw !== '') {{
                    for (let i = indices.length - 1; i > 0; i--) {{
                        const j = Math.floor(Math.random() * (i + 1));
                        [indices[i], indices[j]] = [indices[j], indices[i]];
                    }}
                }}
                const selected = indices.slice(0, count);
                const total = count > 100 ? count : 100;
                const baseScore = count > 100 ? 1 : Math.floor(100 / count);
                const container = document.getElementById('questionsContainer');
                container.innerHTML = '';
                examData.questions = selected.map((sourceIndex, index) => {{
                    const score = index === count - 1 ? total - baseScore * (count - 1) : baseScore;
                    const node = questionTemplates[sourceIndex].cloneNode(true);
                    node.id = `question_${{index}}`;
                    node.dataset.index = index;
                    node.dataset.score = score;
                    node.querySelector('.question-number').textContent = `第${{index + 1}}题`;
                    node.querySelector('.question-score').textContent = `分值: ${{score}}分`;
                    node.querySelectorAll('input').forEach((input, optionIndex) => {{
                        const label = node.querySelector(`label[for="${{input.id}}"]`);
                        input.id = `q${{index}}_opt${{optionIndex}}`;
                        input.name = `q${{index}}`;
                        if (label) label.htmlFor = input.id;
                    }});
                    container.appendChild(node);
                    return {{...questionBank[sourceIndex], score}};
                }});
                examData.total_score = total;
                totalQuestions = count;
                currentQuestion = 0;
                userAnswers = new Array(count).fill(null);
                timeLeft = examData.duration * 60 || 3600;
                clearInterval(timerInterval);
                clearTimeout(pendingAdvance);
                clearTimeout(startupTimeout);
                document.getElementById('examTotalScore').textContent = total;
                document.getElementById('resultTotalScore').textContent = total;
                bindOptionEvents();
                return true;
            }}

            function scheduleAdvance() {{
                clearTimeout(pendingAdvance);
                const answeredIndex = currentQuestion;
                pendingAdvance = setTimeout(() => {{
                    if (currentQuestion !== answeredIndex || document.getElementById('examContainer').style.display !== 'block') return;
                    if (currentQuestion < totalQuestions - 1) nextQuestion();
                    else finishExam();
                }}, 1000);
            }}

            function startExam() {{
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
                
                if (!prepareAttempt()) return;
                document.getElementById('userInfoForm').style.display = 'none';
                document.getElementById('examContainer').style.display = 'block';
                
                initQuestionNav();
                
                requestAnimationFrame(() => {{
                    startupTimeout = setTimeout(() => {{
                        showQuestion(currentQuestion);
                        startTimer();
                    }}, 50);
                }});
            }}
            
            function showQuestion(index) {{
                document.querySelectorAll('.question').forEach(q => {{
                    q.classList.remove('active');
                }});
                
                const question = document.getElementById(`question_${{index}}`);
                if (!question) {{
                    console.error(`Question ${{index}} not found`);
                    return;
                }}
                
                question.classList.add('active');
                
                const progress = ((index + 1) / totalQuestions) * 100;
                document.getElementById('progressBar').style.width = progress + '%';
                
                updateNavStatus();
                
                if (userAnswers[index] !== null) {{
                    restoreAnswer(index);
                }}
            }}
            
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
                    let answerArray;
                    if (typeof answer === 'string') {{
                        try {{
                            answerArray = JSON.parse(answer);
                        }} catch (e) {{
                            console.error('Error parsing answer in restoreAnswer:', e);
                            answerArray = [];
                        }}
                    }} else if (Array.isArray(answer)) {{
                        answerArray = answer;
                    }} else {{
                        answerArray = [];
                    }}
                    
                    const inputs = question.querySelectorAll('input[type="checkbox"]');
                    inputs.forEach(input => {{
                        input.checked = answerArray.includes(input.value);
                    }});
                }}
            }}
            
            function checkAnswer(index, showFeedback = true) {{
                const question = document.getElementById(`question_${{index}}`);
                if (!question) {{
                    return false;
                }}
                
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
                        if (!userAnswer || userAnswer.length === 0) {{
                            feedback.style.display = 'none';
                            return false;
                        }}
                        try {{
                            const decodedAnswer = correctAnswer.replace(/&quot;/g, '"');
                            const correctArray = JSON.parse(decodedAnswer).sort();
                            isCorrect = JSON.stringify(userAnswer) === JSON.stringify(correctArray);
                        }} catch (e) {{
                            console.error('Error parsing answer:', e);
                            isCorrect = false;
                        }}
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
                    }} else {{
                        let correctText = correctAnswer;
                        if (type === 'multiple') {{
                            try {{
                                const decodedAnswer = correctAnswer.replace(/&quot;/g, '"');
                                const correctArray = JSON.parse(decodedAnswer);
                                correctText = correctArray.map(opt => examData.questions[index].options[opt]).join(', ');
                            }} catch (e) {{
                                console.error('Error parsing answer:', e);
                                correctText = '解析错误';
                            }}
                        }} else if (type === 'single') {{
                            correctText = examData.questions[index].options[correctAnswer];
                        }} else {{
                            correctText = correctAnswer === 'true' ? '正确' : '错误';
                        }}
                        
                        feedback.innerHTML = `<strong>✗ 回答错误！</strong><br>正确答案: ${{correctText}}`;
                    }}
                }}
                
                if (type === 'multiple') {{
                    if (!userAnswer || userAnswer.length === 0) {{
                        return false;
                    }}
                    try {{
                        const decodedAnswer = correctAnswer.replace(/&quot;/g, '"');
                        const correctArray = JSON.parse(decodedAnswer).sort();
                        return JSON.stringify(userAnswer) === JSON.stringify(correctArray);
                    }} catch (e) {{
                        console.error('Error parsing answer:', e);
                        return false;
                    }}
                }} else {{
                    return userAnswer === correctAnswer;
                }}
            }}
            
            function nextQuestion() {{
                clearTimeout(pendingAdvance);
                if (currentQuestion < totalQuestions - 1) {{
                    currentQuestion++;
                    showQuestion(currentQuestion);
                }} else {{
                    finishExam();
                }}
            }}
            
            function previousQuestion() {{
                clearTimeout(pendingAdvance);
                if (currentQuestion > 0) {{
                    currentQuestion--;
                    showQuestion(currentQuestion);
                }}
            }}
            
            function goToQuestion(index) {{
                clearTimeout(pendingAdvance);
                currentQuestion = index;
                showQuestion(index);
            }}
            
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
            
            function updateTimerDisplay() {{
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                document.getElementById('timer').textContent = 
                    `剩余时间: ${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}`;
            }}
            
            function finishExam() {{
                clearInterval(timerInterval);
                clearTimeout(pendingAdvance);
                clearTimeout(startupTimeout);
                
                let totalScore = 0;
                for (let i = 0; i < totalQuestions; i++) {{
                    if (checkAnswer(i, false)) {{
                        const question = document.getElementById(`question_${{i}}`);
                        totalScore += parseInt(question.dataset.score);
                    }}
                }}
                
                document.getElementById('examContainer').style.display = 'none';
                document.getElementById('resultContainer').style.display = 'block';
                
                document.getElementById('finalScore').textContent = totalScore;
                document.getElementById('resultCompany').textContent = userInfo.company;
                document.getElementById('resultEmployeeId').textContent = userInfo.employeeId;
                document.getElementById('resultDepartment').textContent = userInfo.department;
                document.getElementById('resultName').textContent = userInfo.name;
                updateNavStatus();
                renderWrongQuestionDetails();
            }}

            function getWrongQuestionDetails() {{
                const wrong = [];
                for (let i = 0; i < totalQuestions; i++) {{
                    if (checkAnswer(i, false)) continue;
                    const node = document.getElementById(`question_${{i}}`);
                    const selected = Array.from(node.querySelectorAll('input:checked')).map(input => {{
                        const label = node.querySelector(`label[for="${{input.id}}"]`);
                        const text = label ? label.textContent.trim() : input.value;
                        return node.dataset.type === 'judgment' ? text : `${{String.fromCharCode(65 + Number(input.value))}}. ${{text}}`;
                    }});
                    wrong.push({{number: i + 1, question: node.querySelector('.question-content').textContent.trim(),
                        selected: selected.length ? selected : ['未作答']}});
                }}
                return wrong;
            }}

            function renderWrongQuestionDetails() {{
                const container = document.getElementById('wrongQuestionDetails');
                const wrong = getWrongQuestionDetails();
                container.replaceChildren();
                container.hidden = wrong.length === 0;
                if (!wrong.length) return;
                const heading = document.createElement('h3');
                heading.textContent = '错题详情';
                container.appendChild(heading);
                wrong.forEach(item => {{
                    const card = document.createElement('article');
                    const title = document.createElement('strong');
                    title.textContent = `第${{item.number}}题：${{item.question}}`;
                    const answer = document.createElement('p');
                    answer.textContent = '你的选择：' + item.selected.join('；');
                    card.append(title, answer);
                    container.appendChild(card);
                }});
            }}

            async function saveScoreImage() {{
                const button = document.getElementById('saveScoreBtn');
                if (button.disabled) return;
                button.disabled = true;
                button.textContent = '正在生成图片…';
                try {{
                    if (document.fonts && document.fonts.ready) await document.fonts.ready;
                    // Draw locally instead of relying on a CDN or sending candidate data to a server.
                    const canvas = document.createElement('canvas');
                    canvas.width = 1000;
                    let ctx = canvas.getContext('2d');
                    if (!ctx) throw new Error('Canvas unavailable');
                    const commands = [];
                    let y = 20;
                    const text = (value, size = 22, color = '#333', center = false) => {{
                        ctx.font = `${{size}}px "Microsoft YaHei", sans-serif`;
                        let line = '';
                        const lines = [];
                        for (const char of String(value)) {{
                            if (char === '\\n') {{ lines.push(line); line = ''; continue; }}
                            if (line && ctx.measureText(line + char).width > 880) {{ lines.push(line); line = ''; }}
                            line += char;
                        }}
                        lines.push(line);
                        lines.forEach(content => {{
                            commands.push({{kind: 'text', content, size, color, center, y}});
                            y += Math.ceil(size * 1.6);
                        }});
                    }};
                    commands.push({{kind: 'header', y}});
                    y += 20;
                    text(document.querySelector('.header h1').textContent, 34, '#fff', true);
                    text(`考试时间: ${{examData.duration || 60}}分钟 | 总分: ${{examData.total_score}}分`, 20, '#fff', true);
                    y += 45;
                    text('考试完成！', 28, '#333', true);
                    y += 12;
                    text(document.getElementById('finalScore').textContent, 52, '#667eea', true);
                    text(`总分: ${{examData.total_score}}分`, 22, '#333', true);
                    y += 20;
                    text('考生信息', 26);
                    [['单位', userInfo.company], ['工号', userInfo.employeeId], ['部门', userInfo.department], ['姓名', userInfo.name]]
                        .forEach(([label, value]) => text(`${{label}}: ${{value || ''}}`));
                    y += 25;
                    text('答题情况', 26, '#333', true);
                    const wrong = getWrongQuestionDetails();
                    const wrongIndices = new Set(wrong.map(item => item.number));
                    for (let i = 0; i < totalQuestions; i++) {{
                        commands.push({{kind: 'circle', x: 80 + (i % 17) * 52, y: y + Math.floor(i / 17) * 54,
                            content: String(i + 1), color: wrongIndices.has(i + 1) ? '#dc3545' : '#28a745'}});
                    }}
                    y += Math.ceil(totalQuestions / 17) * 54 + 25;
                    if (wrong.length) {{
                        text('错题详情', 28);
                        wrong.forEach(item => {{
                            y += 18;
                            text(`第${{item.number}}题：${{item.question}}`, 22);
                            text('你的选择：' + item.selected.join('；'), 22, '#b02a37');
                        }});
                    }}
                    // Stay within common browser canvas limits; never silently clip wrong questions.
                    if (y + 40 > 30000) throw new Error('Image too tall');
                    canvas.height = Math.ceil(y + 40);
                    ctx = canvas.getContext('2d');
                    ctx.fillStyle = '#fff';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    commands.forEach(command => {{
                        if (command.kind === 'header') {{
                            const gradient = ctx.createLinearGradient(20, 0, 980, 0);
                            gradient.addColorStop(0, '#667eea'); gradient.addColorStop(1, '#764ba2');
                            ctx.fillStyle = gradient; ctx.fillRect(20, command.y, 960, 125);
                        }} else if (command.kind === 'circle') {{
                            ctx.fillStyle = command.color; ctx.beginPath();
                            ctx.arc(command.x, command.y + 20, 20, 0, Math.PI * 2); ctx.fill();
                            ctx.fillStyle = '#fff'; ctx.font = '18px sans-serif';
                            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                            ctx.fillText(command.content, command.x, command.y + 20);
                        }} else {{
                            ctx.fillStyle = command.color;
                            ctx.font = `${{command.size}}px "Microsoft YaHei", sans-serif`;
                            ctx.textAlign = command.center ? 'center' : 'left'; ctx.textBaseline = 'top';
                            ctx.fillText(command.content, command.center ? 500 : 60, command.y);
                        }}
                    }});
                    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
                    if (!blob) throw new Error('Image encoding failed');
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    const safeName = value => String(value).replace(/[\\\\/:*?"<>|\\x00-\\x1f]/g, '_').slice(0, 80);
                    link.download = `${{safeName(document.querySelector('.header h1').textContent)}}_${{safeName(userInfo.name)}}_成绩.png`;
                    link.href = url;
                    document.body.appendChild(link);
                    link.click(); link.remove();
                    setTimeout(() => URL.revokeObjectURL(url), 60000);
                }} catch (error) {{
                    alert('保存失败，可能是错题内容过长或浏览器不支持图片下载，请尝试浏览器长截图。');
                }} finally {{
                    button.disabled = false;
                    button.textContent = '保存成绩';
                }}
            }}
            
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
            
            function showResultQuestion(index) {{
                document.getElementById('resultContainer').style.display = 'none';
                document.getElementById('examContainer').style.display = 'block';
                currentQuestion = index;
                showQuestion(currentQuestion);
                
                const question = document.getElementById(`question_${{index}}`);
                question.querySelectorAll('input').forEach(input => {{
                    input.disabled = true;
                }});
            }}
            
            function resetExam() {{
                if (confirm('确定要重置考试吗？所有答案将被清空。')) {{
                    clearTimeout(pendingAdvance);
                    clearTimeout(startupTimeout);
                    document.getElementById('examTotalScore').textContent = '待开始';
                    document.getElementById('resultTotalScore').textContent = '待开始';
                    currentQuestion = 0;
                    userAnswers = new Array(totalQuestions).fill(null);
                    timeLeft = examData.duration * 60 || 3600;
                    
                    document.getElementById('company').value = '';
                    document.getElementById('employeeId').value = '';
                    document.getElementById('department').value = '';
                    document.getElementById('name').value = '';
                    
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
            
            function bindOptionEvents() {{
                document.querySelectorAll('.option').forEach(option => {{
                    option.onclick = function(event) {{
                        if (event.target.closest('input, label')) return;
                        const input = this.querySelector('input');
                        if (!input.disabled) input.click();
                    }};
                    option.onchange = function() {{
                        const question = this.closest('.question');
                        const inputs = question.querySelectorAll('input');
                        const type = question.dataset.type;
                        
                        if (type === 'multiple') {{
                            const input = this.querySelector('input');
                            const selected = Array.from(question.querySelectorAll('input[type="checkbox"]:checked')).map(inp => inp.value);
                            
                            const decodedAnswer = question.dataset.answer.replace(/&quot;/g, '"');
                            const correctArray = JSON.parse(decodedAnswer);
                            
                            const hasWrongOption = selected.some(val => !correctArray.includes(val));
                            
                            if (hasWrongOption) {{
                                inputs.forEach(inp => {{
                                    inp.disabled = true;
                                }});
                                
                                const feedback = question.querySelector('.answer-feedback');
                                feedback.style.display = 'block';
                                feedback.className = 'answer-feedback wrong';
                                
                                const correctText = correctArray.map(opt => examData.questions[currentQuestion].options[opt]).join(', ');
                                feedback.innerHTML = `<strong>✗ 回答错误！</strong><br>正确答案: ${{correctText}}`;
                                
                                userAnswers[currentQuestion] = selected.sort();
                                updateNavStatus();
                            }} else {{
                                const allCorrectSelected = correctArray.every(val => selected.includes(val));
                                
                                if (allCorrectSelected) {{
                                    inputs.forEach(inp => {{
                                        inp.disabled = true;
                                    }});
                                    
                                    const feedback = question.querySelector('.answer-feedback');
                                    feedback.style.display = 'block';
                                    feedback.className = 'answer-feedback correct';
                                    feedback.innerHTML = '<strong>✓ 回答正确！</strong>';
                                    
                                    userAnswers[currentQuestion] = selected.sort();
                                    updateNavStatus();
                                    
                                    scheduleAdvance();
                                }}
                            }}
                        }} else {{
                            if (Array.from(inputs).every(input => input.disabled)) return;
                            
                            const input = this.querySelector('input');
                            const isCorrect = checkAnswer(currentQuestion, true);
                            
                            inputs.forEach(inp => {{
                                inp.disabled = true;
                            }});
                            
                            if (isCorrect) {{
                                scheduleAdvance();
                            }}
                        }}
                    }};
                }});
            }}
            window.onload = bindOptionEvents;
        </script>
    </body>
    </html>
    '''
    
    return html_template

def generate_qrcode(url, exam_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    qr_path = f"static/qrcodes/{exam_id}.png"
    img.save(qr_path)
    
    return qr_path

def exam_registry():
    os.makedirs('storage', exist_ok=True)
    connection = sqlite3.connect('storage/exams.sqlite3', timeout=15)
    try:
        connection.execute('CREATE TABLE IF NOT EXISTS exams '
                           '(name TEXT PRIMARY KEY, filename TEXT NOT NULL)')
        connection.execute('CREATE TABLE IF NOT EXISTS exam_data '
                           '(filename TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    except Exception:
        connection.close()
        raise
    return connection


def valid_exam_name(name):
    return isinstance(name, str) and 1 <= len(name.strip()) <= 120


@app.route('/api/create_exam', methods=['POST'])
def create_exam():
    owned_paths = []
    try:
        exam_data = request.get_json(silent=True)
        if not isinstance(exam_data, dict):
            return jsonify({'error': 'Expected a JSON object'}), 400
        api_key = request.headers.get('X-API-Key') or exam_data.pop('api_key', None)
        if not verify_api_key(api_key):
            return jsonify({'error': 'Invalid API key'}), 401
        # Credentials and lookup names must never be embedded in the public HTML.
        exam_data.pop('api_key', None)
        has_name = 'exam_name' in exam_data
        exam_name = exam_data.pop('exam_name', None)
        if has_name and not valid_exam_name(exam_name):
            return jsonify({'error': 'exam_name must contain 1–120 characters'}), 400
        if has_name:
            exam_name = exam_name.strip()

        for field in ['title', 'questions']:
            if field not in exam_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        total_score = sum(q.get('score', 1) for q in exam_data['questions'])
        exam_data['total_score'] = total_score
        exam_data['duration'] = exam_data.get('duration', 60)
        exam_id = str(uuid.uuid4())[:8]
        html_filename = f'{exam_id}.html'
        html_path = f'static/exams/{html_filename}'
        qr_path = f'static/qrcodes/{exam_id}.png'
        exam_url = f'{request.host_url}exam/{html_filename}'

        with closing(exam_registry()) as connection:
            with connection:
                if has_name:
                    try:
                        connection.execute('INSERT INTO exams (name, filename) VALUES (?, ?)',
                                           (exam_name, html_filename))
                    except sqlite3.IntegrityError:
                        existing = connection.execute(
                            'SELECT filename FROM exams WHERE name = ?', (exam_name,)).fetchone()
                        return jsonify({'error': 'Exam name already exists',
                                        'exam_name': exam_name,
                                        'exam_id': existing[0][:-5]}), 409
                html_content = generate_exam_html(exam_data)
                with open(html_path, 'x', encoding='utf-8') as f:
                    owned_paths.append(html_path)
                    f.write(html_content)
                with open(qr_path, 'xb'):
                    owned_paths.append(qr_path)
                generate_qrcode(exam_url, exam_id)
                connection.execute('INSERT INTO exam_data (filename, payload) VALUES (?, ?)',
                                   (html_filename, json.dumps(exam_data, ensure_ascii=False)))

        result = {
            'success': True,
            'exam_id': exam_id,
            'exam_url': exam_url,
            'qr_url': f'{request.host_url}{qr_path}',
            'qr_path': qr_path,
            'total_score': total_score,
            'question_count': len(exam_data['questions'])
        }
        if has_name:
            result['exam_name'] = exam_name
        return jsonify(result)
    except Exception:
        for path in owned_paths:
            try:
                os.remove(path)
            except OSError:
                app.logger.exception('Failed to clean up generated exam file')
        app.logger.exception('Failed to create exam')
        return jsonify({'error': 'Failed to create exam'}), 500

def validate_replacement(data):
    if not isinstance(data, dict) or set(data) - {'title', 'duration', 'questions'}:
        return False
    if not isinstance(data.get('title'), str) or not data['title'].strip():
        return False
    duration = data.get('duration', 60)
    if type(duration) is not int or duration <= 0:
        return False
    questions = data.get('questions')
    if not isinstance(questions, list) or not questions:
        return False
    for question in questions:
        if not isinstance(question, dict):
            return False
        if not isinstance(question.get('question'), str) or not question['question'].strip():
            return False
        if type(question.get('score')) is not int or question['score'] <= 0:
            return False
        kind, answer = question.get('type'), question.get('answer')
        if kind == 'judgment':
            if answer not in ('true', 'false'):
                return False
        elif kind in ('single', 'multiple'):
            options = question.get('options')
            if not isinstance(options, list) or len(options) < 2 or any(
                    not isinstance(option, str) or not option.strip() for option in options):
                return False
            valid = {str(index) for index in range(len(options))}
            if kind == 'single':
                if not isinstance(answer, str) or answer not in valid:
                    return False
            elif (not isinstance(answer, list) or not answer
                  or any(not isinstance(value, str) or value not in valid for value in answer)
                  or len(set(answer)) != len(answer)):
                return False
        else:
            return False
    return True


@app.route('/api/exams/<exam_id>', methods=['PUT'])
def update_exam(exam_id):
    if not verify_api_key(request.headers.get('X-API-Key')):
        return jsonify({'error': 'Invalid API key'}), 401
    if not re.fullmatch(r'[0-9a-f]{8}', exam_id):
        return jsonify({'error': 'Exam not found'}), 404
    html_filename = f'{exam_id}.html'
    html_path = f'static/exams/{html_filename}'
    if not os.path.isfile(html_path):
        return jsonify({'error': 'Exam not found'}), 404
    data = request.get_json(silent=True)
    if not validate_replacement(data):
        return jsonify({'error': 'Expected title, optional positive integer duration, and valid nonempty questions; exam_name cannot be changed'}), 400
    temporary_path = None
    try:
        with closing(exam_registry()) as connection:
            row = connection.execute('SELECT name FROM exams WHERE filename = ?',
                                     (html_filename,)).fetchone()
        data['duration'] = data.get('duration', 60)
        data['total_score'] = sum(question['score'] for question in data['questions'])
        content = generate_exam_html(data)
        # Same-directory atomic replacement keeps the old exam intact on write failures.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir='static/exams',
                                         suffix='.tmp', delete=False) as output:
            temporary_path = output.name
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        with closing(exam_registry()) as connection:
            with connection:
                connection.execute('INSERT OR REPLACE INTO exam_data (filename, payload) VALUES (?, ?)',
                                   (html_filename, json.dumps(data, ensure_ascii=False)))
                os.replace(temporary_path, html_path)
                temporary_path = None
        qr_path = f'static/qrcodes/{exam_id}.png'
        result = {'success': True, 'exam_id': exam_id,
                  'exam_url': f'{request.host_url}exam/{html_filename}',
                  'qr_url': f'{request.host_url}{qr_path}', 'qr_path': qr_path,
                  'total_score': data['total_score'], 'question_count': len(data['questions'])}
        if row:
            result['exam_name'] = row[0]
        return jsonify(result)
    except Exception:
        app.logger.exception('Failed to update exam')
        return jsonify({'error': 'Failed to update exam'}), 500
    finally:
        if temporary_path is not None:
            try:
                os.remove(temporary_path)
            except OSError:
                app.logger.exception('Failed to clean up temporary exam file')


def exam_query_record(filename, name, payload, include_questions=False):
    data = json.loads(payload) if payload is not None else None
    exam_id = filename[:-5]
    record = {
        'exam_id': exam_id, 'exam_name': name,
        'title': data.get('title') if data else None,
        'duration': data.get('duration') if data else None,
        'question_count': len(data['questions']) if data else None,
        'total_score': data.get('total_score') if data else None,
        'data_available': data is not None,
        'file_exists': os.path.isfile(os.path.join('static/exams', filename)),
        'exam_url': f'{request.host_url}exam/{filename}',
        'qr_url': f'{request.host_url}static/qrcodes/{exam_id}.png',
    }
    if include_questions:
        record['questions'] = data['questions'] if data else None
    return record


@app.route('/api/exams', methods=['GET'])
def list_exams():
    if not verify_api_key(request.headers.get('X-API-Key')):
        return jsonify({'error': 'Invalid API key'}), 401
    try:
        with closing(exam_registry()) as connection:
            names = dict(connection.execute('SELECT filename, name FROM exams'))
            payloads = dict(connection.execute('SELECT filename, payload FROM exam_data'))
        filenames = set(names) | set(payloads)
        filenames.update(filename for filename in os.listdir('static/exams')
                         if re.fullmatch(r'[0-9a-f]{8}\.html', filename))
        records = [exam_query_record(filename, names.get(filename), payloads.get(filename))
                   for filename in sorted(filenames)]
        response = jsonify({'success': True, 'exams': records, 'count': len(records)})
        response.headers['Cache-Control'] = 'no-store'
        return response
    except Exception:
        app.logger.exception('Failed to list exams')
        return jsonify({'error': 'Failed to list exams'}), 500


@app.route('/api/exams/<exam_id>', methods=['GET'])
def get_exam(exam_id):
    if not verify_api_key(request.headers.get('X-API-Key')):
        return jsonify({'error': 'Invalid API key'}), 401
    if not re.fullmatch(r'[0-9a-f]{8}', exam_id):
        return jsonify({'error': 'Exam not found'}), 404
    filename = f'{exam_id}.html'
    try:
        with closing(exam_registry()) as connection:
            name = connection.execute('SELECT name FROM exams WHERE filename = ?', (filename,)).fetchone()
            payload = connection.execute('SELECT payload FROM exam_data WHERE filename = ?', (filename,)).fetchone()
        if name is None and payload is None and not os.path.isfile(os.path.join('static/exams', filename)):
            return jsonify({'error': 'Exam not found'}), 404
        record = exam_query_record(filename, name[0] if name else None,
                                   payload[0] if payload else None, include_questions=True)
        response = jsonify({'success': True, 'exam': record})
        response.headers['Cache-Control'] = 'no-store'
        return response
    except Exception:
        app.logger.exception('Failed to read exam')
        return jsonify({'error': 'Failed to read exam'}), 500


@app.route('/exam/<filename>')
def serve_exam(filename):
    try:
        html_path = f"static/exams/{filename}"
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except:
        return "Exam not found", 404

@app.route('/api/test_data', methods=['GET'])
def get_test_data():
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

def entry_page(error='', exam_name='', status=200):
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>考试入口</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Microsoft YaHei', sans-serif;
                line-height: 1.6; color: #333; max-width: 1000px;
                margin: 0 auto; padding: 20px; background-color: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 20px; border-radius: 10px;
                margin-bottom: 20px; text-align: center;
            }
            main { margin-top: clamp(0px, 5vh, 48px); }
            .header h1 { font-size: clamp(24px, 4vw, 32px); }
            .header p { margin-top: 8px; }
            .entry-card {
                background: white; padding: 25px; border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px;
            }
            .entry-content { max-width: 560px; margin: 0 auto; padding: 12px 0; }
            .entry-content h2 { color: #2c3e50; font-size: 22px; }
            .entry-intro { color: #555; margin-top: 8px; }
            .form-group { margin: 24px 0 15px; display: flex; align-items: center; }
            label { width: 80px; font-weight: bold; margin-right: 10px; flex-shrink: 0; }
            input {
                flex: 1; min-width: 0; padding: 8px 12px; border: 1px solid #ddd;
                border-radius: 5px; font: inherit; font-size: 14px;
            }
            .btn {
                background: #4CAF50; color: white; border: none; padding: 12px 24px;
                border-radius: 5px; cursor: pointer; font-size: 16px;
                margin: 10px 0; transition: background 0.3s;
            }
            .btn:hover { background: #45a049; }
            input:focus-visible, button:focus-visible, a:focus-visible {
                outline: 3px solid #667eea; outline-offset: 3px;
            }
            .error { color: #721c24; background: #f8d7da; border: 1px solid #f5c6cb;
                     border-radius: 8px; padding: 15px; margin: 15px 0; }
            .entry-help {
                margin-top: 20px; padding: 15px; background: #f8f9fa;
                border-radius: 8px; color: #555; font-size: 14px;
            }
            .entry-actions { padding-left: 90px; }
            .entry-actions .btn { width: 100%; }
            a { color: #4b4fa1; text-underline-offset: 3px; }
            a:hover { color: #764ba2; }
            @media (max-width: 768px) {
                body { padding: 10px; }
                .form-group { flex-direction: column; align-items: stretch; gap: 8px; }
                label { width: auto; margin-right: 0; }
                .btn { width: 100%; margin: 5px 0; }
                .entry-actions { padding-left: 0; }
                .entry-content { padding: 0; }
            }
        </style>
    </head>
    <body><main>
        <header class="header">
            <h1>考试入口</h1>
            <p>输入考试名称，开始答题</p>
        </header>
        <section class="entry-card" aria-labelledby="entryHeading">
            <div class="entry-content">
            <h2 id="entryHeading">进入考试</h2>
            <p class="entry-intro">请输入管理员提供的完整考试名称，进入后填写考生信息。</p>
            <form action="{{ url_for('enter_exam') }}" method="post">
                <div class="form-group">
                    <label for="examName">考试名称</label>
                    <input id="examName" name="exam_name" value="{{ exam_name }}"
                           maxlength="120" placeholder="请输入完整考试名称"
                           aria-describedby="entryHelp" required>
                </div>
                <div class="entry-actions">
                    <button class="btn" type="submit">进入考试</button>
                </div>
            </form>
            {% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
            <p id="entryHelp" class="entry-help">持有考试二维码？扫码即可直接进入，无需输入名称。<br>旧考试请使用原链接或二维码。</p>
            </div>
        </section>
    </main></body></html>
    ''', error=error, exam_name=exam_name), status


@app.route('/')
def index():
    return entry_page()


@app.route('/enter', methods=['POST'])
def enter_exam():
    name = request.form.get('exam_name', '')
    if not valid_exam_name(name):
        return entry_page('请输入 1–120 个字符的考试名称。', status=400)
    name = name.strip()
    try:
        with closing(exam_registry()) as connection:
            row = connection.execute('SELECT filename FROM exams WHERE name = ?', (name,)).fetchone()
    except sqlite3.Error:
        app.logger.exception('Failed to look up exam')
        return entry_page('考试查询暂不可用，请稍后再试。', name, 503)
    if row is None or not os.path.isfile(os.path.join('static/exams', row[0])):
        return entry_page('未找到该考试，请核对名称或联系管理员。', name, 404)
    return redirect(url_for('serve_exam', filename=row[0]))


@app.route('/admin')
def admin():
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
            .input-group { margin: 10px 0; }
            .input-group label { display: inline-block; width: 120px; font-weight: bold; }
            .input-group input { padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 300px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>考试系统管理后台</h1>
            
            <div class="card">
                <h2>API Key</h2>
                <div class="input-group">
                    <label>API Key:</label>
                    <input type="password" id="apiKey" placeholder="请输入API Key">
                </div>
            </div>
            
            <div class="card">
                <h2>1. 获取测试数据</h2>
                <button onclick="getTestData()">获取测试数据</button>
                <pre id="testData"></pre>
            </div>
            
            <div class="card">
                <h2>2. 创建考试</h2>
                <div class="input-group">
                    <label for="examName">考试名称:</label>
                    <input type="text" id="examName" maxlength="120" placeholder="请输入唯一考试名称" required>
                </div>
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
                const apiKey = document.getElementById('apiKey').value;
                const examName = document.getElementById('examName').value.trim();
                if (!examName || examName.length > 120) {
                    alert('请输入 1–120 个字符的考试名称');
                    return;
                }
                
                try {
                    const examData = JSON.parse(document.getElementById('examData').value);
                    examData.exam_name = examName;
                    const response = await fetch('/api/create_exam', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify(examData)
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
    # 开发环境
    #app.run(debug=True, port=5000)
    # 生产环境
    app.run(host='0.0.0.0', port=5000, debug=False)  # 生产环境设置 debug=False
