// Kiểm tra nhanh phần tự nhập của demo tĩnh, không cần thư viện trình duyệt.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const html = fs.readFileSync(process.argv[2] || 'demo.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert(script, 'thiếu script demo');
new vm.Script(script[1]);
const start = script[1].indexOf('function renderScenario(){');
const end = script[1].indexOf('function init(){', start);
assert(start >= 0 && end > start, 'thiếu renderScenario');
const values = {
  scBalance:3500000, scDays:12, scSpend:180000, scPayday:5000000,
  scIncome:0, scIncomeDay:5, scExtra:0, scExtraDay:4
};
const elements = Object.fromEntries(Object.entries(values).map(([k,v])=>[k,{value:String(v)}]));
elements.scenarioResult = {innerHTML:'',textContent:''};
const context = {$: id=>elements[id], Intl, Number};
vm.createContext(context);
vm.runInContext(script[1].slice(start,end), context);
function run(){ elements.scenarioResult.innerHTML=''; elements.scenarioResult.textContent=''; context.renderScenario(); return elements.scenarioResult.innerHTML || elements.scenarioResult.textContent; }
function set(id,value){elements[id].value=String(value);}
let result=run();
assert(result.includes('1.340.000 VND') && result.includes('trên ngưỡng'), 'kịch bản cơ bản');
set('scPayday',9000000);
assert(run().includes('1.340.000 VND'), 'tiền ngày kỳ sau không đổi số dư trước kỳ');
set('scExtra',2000000);
result=run();
assert(result.includes('-660.000 VND') && result.includes('dưới ngưỡng'), 'khoản chi thêm');
set('scIncome',1000000);
assert(run().includes('340.000 VND'), 'khoản tiền vào giữa kỳ');
set('scIncomeDay',13);
assert(run().includes('Hãy nhập số không âm'), 'ngày phát sinh ngoài chu kỳ');
console.log('PASS: cú pháp JS và 5 tình huống nhập thử');
