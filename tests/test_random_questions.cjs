// Run in Docker after generate_browser_fixture.py; jsdom is test-only.
const { JSDOM } = require('jsdom');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const html = fs.readFileSync('/tmp/exam-browser.html', 'utf8');
function setup() {
  const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true });
  const w = dom.window;
  const alerts = [];
  w.alert = message => alerts.push(message);
  w.confirm = () => true;
  w.requestAnimationFrame = callback => callback();
  // Execute startup immediately; do not auto-advance while inspecting questions.
  w.setTimeout = (callback, delay) => { if (delay === 50) callback(); return 1; };
  w.clearTimeout = () => {};
  w.document.getElementById('name').value = '测试考生';
  w.document.getElementById('employeeId').value = '001';
  assert.equal(w.document.getElementById('questionCount').placeholder, '如不填写则为全部考题');
  return { dom, w, alerts };
}
for (const count of [1, 5, 6, 100, 120, '']) {
  const {dom, w, alerts} = setup();
  w.document.getElementById('questionCount').value = String(count);
  w.startExam();
  assert.equal(alerts.length, 0);
  const n = count === '' ? 120 : count;
  const nodes = [...w.document.querySelectorAll('#questionsContainer .question')];
  assert.equal(nodes.length, n);
  assert.equal(w.document.querySelectorAll('#questionNav .question-nav-item').length, n);
  assert.equal(new Set(nodes.map(node => node.querySelector('.question-content').textContent)).size, n);
  const scores = nodes.map(node => Number(node.dataset.score));
  assert.equal(scores.reduce((a,b) => a+b,0), n > 100 ? n : 100);
  assert.equal(scores[0], n > 100 ? 1 : Math.floor(100/n));
  if (n === 6) assert.equal(scores[5], 20);
  for (const [i, node] of nodes.entries()) {
    assert.equal(node.id, `question_${i}`);
    assert.equal(node.querySelector('.question-number').textContent, `第${i+1}题`);
    for (const input of node.querySelectorAll('input')) {
      assert.equal(input.name, `q${i}`);
      assert.ok(node.querySelector(`label[for="${input.id}"]`));
      const answers = node.dataset.type === 'multiple' ? JSON.parse(node.dataset.answer) : [node.dataset.answer];
      input.checked = answers.includes(input.value);
    }
  }
  w.finishExam();
  assert.equal(Number(w.document.getElementById('finalScore').textContent), n > 100 ? n : 100);
  assert.equal(w.document.getElementById('resultTotalScore').textContent, String(n > 100 ? n : 100));
  w.resetExam();
  assert.equal(w.document.getElementById('userInfoForm').style.display, 'block');
  w.document.getElementById('name').value = '再次考试';
  w.document.getElementById('employeeId').value = '002';
  w.document.getElementById('questionCount').value = '5';
  w.startExam();
  assert.equal(w.document.querySelectorAll('#questionsContainer .question').length, 5);
  assert.ok([...w.document.querySelectorAll('#questionsContainer input')].every(input => !input.checked && !input.disabled));
  // Direct radio click must grade and lock the answer, not skip due to native checked state.
  const radioNode = [...w.document.querySelectorAll('.question')].find(node => node.dataset.type !== 'multiple');
  if (radioNode) {
    w.goToQuestion(Number(radioNode.dataset.index));
    radioNode.querySelector(`input[value="${radioNode.dataset.answer}"]`).click();
    assert.ok([...radioNode.querySelectorAll('input')].every(input => input.disabled));
    assert.ok(radioNode.querySelector('.answer-feedback').classList.contains('correct'));
  }
  dom.window.close();
}
for (const value of ['0', '-1', '1.5', '121']) {
  const {dom,w,alerts} = setup();
  w.document.getElementById('questionCount').value = value;
  w.startExam();
  assert.equal(alerts.length,1);
  assert.notEqual(w.document.getElementById('userInfoForm').style.display,'none');
  dom.window.close();
}
// All-question mode preserves source order and tests all input interaction types.
{
  const {dom,w} = setup();
  w.startExam();
  const nodes = [...w.document.querySelectorAll('.question')];
  assert.ok(nodes[0].querySelector('.question-content').textContent.includes('题库题目 0'));
  // Wrong single choice is locked and can be reviewed after finishing.
  nodes[0].querySelector('.option').click();
  assert.ok(nodes[0].querySelector('.answer-feedback').classList.contains('wrong'));
  w.goToQuestion(1);
  nodes[1].querySelector('label[for="q1_opt0"]').click();
  assert.equal(nodes[1].querySelector('input[value="0"]').checked, true);
  assert.equal(nodes[1].querySelector('input[value="2"]').disabled, false);
  nodes[1].querySelectorAll('.option')[2].click();
  assert.ok(nodes[1].querySelector('.answer-feedback').classList.contains('correct'));
  assert.ok([...nodes[1].querySelectorAll('input')].every(input => input.disabled));
  w.nextQuestion();
  assert.ok(nodes[2].classList.contains('active'));
  w.finishExam();
  assert.equal(w.document.getElementById('finalScore').textContent, '1');
  w.reviewWrongQuestions();
  assert.ok(nodes[0].classList.contains('active'));
  assert.ok(nodes[0].querySelector('.answer-feedback').classList.contains('wrong'));
  dom.window.close();
}
// Controlled RNG proves selection is not simply the first N questions.
{
  const {dom,w} = setup();
  w.Math.random = () => 0;
  w.document.getElementById('questionCount').value = '5';
  w.startExam();
  const nodes = [...w.document.querySelectorAll('.question')];
  assert.ok(nodes[0].querySelector('.question-content').textContent.includes('题库题目 1'));
  w.resetExam();
  w.document.getElementById('name').value = '再试';
  w.document.getElementById('employeeId').value = '002';
  w.Math.random = () => 0.999999;
  w.startExam();
  assert.ok(w.document.querySelector('.question-content').textContent.includes('题库题目 0'));
  dom.window.close();
}
console.log('Random question DOM tests: PASS');
